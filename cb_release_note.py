import os
from inspect import getmembers, isfunction

import click
import jinja2
import pyfiglet
import yaml
from InquirerPy import inquirer
from InquirerPy.base import Choice
from alive_progress import alive_bar
from jinja2 import FileSystemLoader
from jira import JIRA
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from termcolor import colored

import release_note_filters
import release_note_functions
import release_note_save_settings
import release_note_tests
from AI_Clients import ai_client_factory

DEFAULT_JIRA_BATCH_SIZE = 10
RELEASE_NOTE_JIRA_FIELD = 'customfield_11402'


class UserSettings:
    password_file = None
    templates_directory = None
    jira_batch_size = DEFAULT_JIRA_BATCH_SIZE
    release_set = None
    fields = {}
    output_file = None
    ai_service = None
    ai_api_key = None
    ai_prompt = None
    ai_model = None

    def __str__(self) -> str:
        return f'settings = {self.release_set}; \
          fields = {self.fields}  \
          output file = {self.output_file}'


def load_config(configuration_file: str) -> dict:
    config_stream = open(configuration_file, "r")
    schema_stream = open("cb_release_config_schema.yaml", "r")
    config = yaml.load(config_stream, Loader=yaml.FullLoader)
    schema = yaml.load(schema_stream, Loader=yaml.FullLoader)
    validate(config, schema)

    return config


def show_banner(version_number):
    os.system('cls' if os.name == 'nt' else 'clear')
    click.echo(colored(pyfiglet.figlet_format(f'CB Release Notes\nversion {version_number}'), 'green'))

def get_user_options(user_settings: UserSettings, config: dict) -> UserSettings:
    user_settings.templates_directory = config['templates_directory']

    if "jira_batch_size" in config:
        user_settings.jira_batch_size = config["jira_batch_size"]

    user_settings.password_file = config['password_file']

    # Get the settings details from the configuration
    release_sets = [item['name'] for item in config['release_settings']]

    release_set = inquirer.select(
        message="Select Release item:",
        choices=release_sets,
        validate=lambda setting: len(setting) > 0,
        invalid_message="You must select a setting",
        height=10,
        qmark='',
        amark=''
    ).execute()

    user_settings.release_set = next(
        setting for setting in config['release_settings'] if setting['name'] == release_set)

    conn = release_note_save_settings.load_database('.saved_settings.db')

    if 'fields' in user_settings.release_set:

        for field in [item for item in user_settings.release_set['fields']]:

            if field['type'] == 'text':
                text = inquirer.text(
                    message=field['message'],
                    validate=lambda entered_text: len(entered_text) > 0,
                    invalid_message="You must enter a value",
                    default=release_note_save_settings.get_saved_items(conn, release_set, field['name']),
                    qmark='',
                    amark=''
                ).execute()

                user_settings.fields[field['name']] = text
                release_note_save_settings.save_item(conn, release_set, field['name'], text)


            if field['type'] == 'multiline':
                text = inquirer.text(
                    message=field['message'],
                    multiline=True,
                    invalid_message="You must enter a value",
                    default=release_note_save_settings.get_saved_items(conn, release_set, field['name']),
                    qmark='',
                    amark=''
                ).execute()
                user_settings.fields[field['name']] = text
                release_note_save_settings.save_item(conn, release_set, field['name'], text)


            elif field['type'] == 'choice':
                choices = inquirer.checkbox(
                    message=field['message'],
                    choices=list(map(lambda x: Choice(x, enabled=True)
                        if x in release_note_save_settings.get_saved_items(conn, release_set, field['name']).split(',')
                            else Choice(x, enabled=False) , field['choices'])),
                    qmark='',
                    amark=''
                ).execute()
                user_settings.fields[field['name']] = ','.join(choices)
                release_note_save_settings.save_item(conn, release_set, field['name'], ','.join(choices))

            elif field['type'] == 'select':
                choice = inquirer.select(
                    message=field['message'],
                    choices=field['choices'],
                    default=release_note_save_settings.get_saved_items(conn, release_set, field['name']),
                    validate=lambda selected_choice: len(selected_choice) > 0,
                    invalid_message="You must select one",
                    qmark='',
                    amark=''
                ).execute()
                user_settings.fields[field['name']] = choice
                release_note_save_settings.save_item(conn, release_set, field['name'], choice)

            elif field['type'] == 'file':
                file_path = inquirer.filepath(
                    message=field['message'],
                    default=release_note_save_settings.get_saved_items(conn, release_set, field['name']),
                    qmark='',
                    amark='',
                    validate=lambda file_name: file_name.endswith('.adoc'),
                ).execute()
                user_settings.fields[field['name']] = file_path
                release_note_save_settings.save_item(conn, release_set, field['name'], file_path)
                user_settings.output_file = file_path

    release_note_save_settings.close_database(conn)
    return user_settings

def get_password_set(password_file: str) -> dict:
    password_stream = open(password_file, "r")
    password_config = yaml.load(password_stream, Loader=yaml.FullLoader)
    return password_config


def get_login_details(password_file: str, url_str: str) -> dict:
    login_details = get_password_set(password_file)
    return login_details['jira'][url_str]


def get_jira_client(user_settings: UserSettings) -> JIRA:
    login = get_login_details(user_settings.password_file, user_settings.release_set['url'])
    jira = JIRA(basic_auth=(login['username'], login['token']),
                options={'server': user_settings.release_set['url']},
                get_server_info=True)
    return jira


def parse_search_str(user_settings: UserSettings) -> str:
    search_str = user_settings.release_set['jql']
    # Replace variables if you find any
    for user_variable in list(user_settings.fields.keys()):
        search_str = search_str.replace(f'{{{{{user_variable}}}}}', user_settings.fields[user_variable])

    return search_str


def retrieve_issues(jira: JIRA, search_str: str, page_token, batch_size) -> dict:
    issues = jira.enhanced_search_issues(jql_str=search_str, nextPageToken=page_token, maxResults=batch_size)
    return issues

def get_release_note_summary(ai_client, text_to_summarize) -> str:
    return ai_client.get_ai_response(text_to_summarize)

def retrieve_description(issue) -> str:
    return issue.fields.summary

def retrieve_comments(issue) -> str:
    return " ".join(comment.body for comment in issue.fields.comment.comments)


def render_release_notes(user_settings, issue_list):
    environment = jinja2.Environment(loader=FileSystemLoader(user_settings.templates_directory), trim_blocks=True, lstrip_blocks=True)

    support_filters = {name: function for name, function in getmembers(release_note_filters) if isfunction(function)}
    environment.filters.update(support_filters)

    support_functions = {name: function for name, function in getmembers(release_note_functions) if
                         isfunction(function)}
    environment.globals.update(support_functions)

    support_tests = {name: function for name, function in getmembers(release_note_tests) if
                     isfunction(function)}
    environment.tests.update(support_tests)

    template = environment.get_template(user_settings.release_set['template'])
    content = template.render(user_settings=user_settings, issues=issue_list)
    with open(user_settings.output_file, mode="wt") as results:
        results.write(content)


@click.command()
@click.option('--config', default='cb_release_notes_config.yaml',
              help='The configuration YAML file to use in the setup', type=click.Path())
@click.option('--output', help='The name of the output file', type=click.Path(), required=False)
@click.option('--summarize', '--summarise',
              help='Add an OpenAI generated summary to notes without a release note description',
              is_flag=True, default=False)
@click.option('--version', is_flag=True)
@click.pass_context
def main(ctx, config, output, summarize, version):
    """Creates release notes from Couchbase Jiras."""
    try:

        configuration = load_config(config)

        user_settings = UserSettings()

        if output is not None:
            user_settings.output_file = output

        if version:
            click.echo(f'Version {configuration["version"]}')
            ctx.exit()

        show_banner(configuration['version'])

        settings = get_user_options(user_settings, configuration)

        jira = get_jira_client(settings)

        issue_list = []

        search = parse_search_str(settings)

        with alive_bar(title='Retrieving jira tickets ...', manual=True, dual_line=True, ) as bar:

            page_token = None

            while True:
                issues = retrieve_issues(jira, search, page_token=page_token, batch_size=settings.jira_batch_size)

                if len(issues) > 0:
                    issue_list.extend(issues)

                if hasattr(issues, "total") and len(issues) > 0:
                    bar(len(issue_list) / issues.total)
                    bar.text(f'{len(issue_list)} retrieved ...')

                page_token = getattr(issues, "nextPageToken", None)

                if not page_token:
                    break

        if summarize:

            password_config = get_password_set(user_settings.password_file)

            if user_settings.release_set['ai_service'] is not None:
                ai_password_config = password_config['ai'][user_settings.release_set['ai_service']['name']]
            else:
                raise Exception('No AI service configured')

            ai_client = ai_client_factory(ai_password_config['api_key'],
                                          user_settings.release_set['ai_service'])

            with alive_bar(title=f"[{user_settings.release_set['ai_service']['prompt']}] ...",
                           manual=True, dual_line=True, ) as bar:

                bar.text('summarizing ...')

                for index, issue in enumerate(issue_list):

                    if not getattr(issue.fields, RELEASE_NOTE_JIRA_FIELD):

                        issue_summary = retrieve_description(issue)
                        issue_comments = retrieve_comments(issue)
                        ai_summary = get_release_note_summary(ai_client=ai_client,
                                                              text_to_summarize=issue_summary + issue_comments)
                        issue.fields.ai_summary = ai_summary
                        issue.fields.ai_service = user_settings.release_set['ai_service']
                        bar((index + 1) / len(issue_list))
                        bar.text(f'{index + 1} ➞ {issue.key} summarized ...')

        render_release_notes(settings, issue_list)

        click.echo(f'{len(issue_list)} tickets retrieved ...')
        click.echo(f'Release notes written to ➞ {user_settings.output_file}')

    except ValidationError as vE:
        click.echo(f'Error in configuration file ➞ {vE.message}')


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
