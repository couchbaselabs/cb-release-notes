import datetime
import os
from inspect import getmembers, isfunction

import click
import editor
import jinja2
import pyfiglet
import yaml
from InquirerPy import inquirer
from alive_progress import alive_bar
from jinja2 import FileSystemLoader
from jira import JIRA
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from termcolor import colored
from openai import OpenAI

import release_note_filters
import release_note_functions
import release_note_tests

DEFAULT_JIRA_BATCH_SIZE = 100


class UserSettings:
    password_file = None
    templates_directory = None
    jira_batch_size = DEFAULT_JIRA_BATCH_SIZE
    ai_prompt = None
    release_set = None
    fields = {}
    output_file = None
    openai_api_key = None

    def __str__(self):
        return f'settings = {self.release_set}; \
          fields = {self.fields}  \
          output file = {self.output_file}'


def load_config(configuration_file):
    config_stream = open(configuration_file, "r")
    schema_stream = open("cb_release_config_schema.yaml", "r")
    config = yaml.load(config_stream, Loader=yaml.FullLoader)
    schema = yaml.load(schema_stream, Loader=yaml.FullLoader)
    validate(config, schema)

    return config


def show_banner(version_number):
    os.system('cls' if os.name == 'nt' else 'clear')
    click.echo(colored(pyfiglet.figlet_format(f'CB Release Notes\nversion {version_number}'), 'green'))


def get_user_options(user_settings, config):
    user_settings.password_file = config['password_file']
    user_settings.templates_directory = config['templates_directory']

    if "jira_batch_size" in config:
        user_settings.jira_batch_size = config["jira_batch_size"]

    if "openai_api_key" in config:
        user_settings.openai_api_key = config["openai_api_key"]

    # Get the settings details from the configuration
    release_sets = [item['name'] for item in config['release_settings']]

    release_set = inquirer.select(
        message="Select Release item:",
        choices=release_sets,
        validate=lambda setting: len(setting) > 0,
        invalid_message="You must select a setting",
        height=6,
        qmark='',
        amark=''
    ).execute()

    user_settings.release_set = next(
        setting for setting in config['release_settings'] if setting['name'] == release_set)

    if 'fields' in user_settings.release_set:
        for field in [item for item in user_settings.release_set['fields']]:

            if field['type'] == 'text':
                text = inquirer.text(
                    message=field['message'],
                    validate=lambda entered_text: len(entered_text) > 0,
                    invalid_message="You must enter a value",
                    qmark='',
                    amark=''
                ).execute()
                user_settings.fields[field['name']] = text

            if field['type'] == 'multiline':
                text = inquirer.text(
                    message=field['message'],
                    multiline=True,
                    invalid_message="You must enter a value",
                    qmark='',
                    amark=''
                ).execute()
                user_settings.fields[field['name']] = text

            if field['type'] == 'editor':
                prompt_text = str.encode(f'{field["message"]}')
                text = editor.edit(contents=prompt_text)
                user_settings.fields[field['name']] = text.decode()

            elif field['type'] == 'choice':
                choices = inquirer.checkbox(
                    message=field['message'],
                    choices=field['choices'],
                    qmark='',
                    amark=''
                ).execute()
                user_settings.fields[field['name']] = ','.join(choices)

            elif field['type'] == 'select':
                choice = inquirer.select(
                    message=field['message'],
                    choices=field['choices'],
                    validate=lambda selected_choice: len(selected_choice) > 0,
                    invalid_message="You must select one",
                    qmark='',
                    amark=''
                ).execute()
                user_settings.fields[field['name']] = choice

    # Create and Timestamp the filename if one hasn't been supplied on the command line.
    if user_settings.output_file is None:
        file_stamp = datetime.datetime.now().strftime('%Y%m%d')
        user_settings.output_file = inquirer.filepath(
            message="File name:",
            default=f'{release_set}-{file_stamp}-release-note.adoc',
            qmark='',
            amark='',
            validate=lambda file_name: file_name.endswith('.adoc'),
        ).execute()

    return user_settings


def get_login_details(password_file, url_str):
    login_details_stream = open(password_file, "r")
    login_details = yaml.load(login_details_stream, Loader=yaml.FullLoader)
    return login_details[url_str]


def get_jira_client(user_settings):
    login = get_login_details(user_settings.password_file, user_settings.release_set['url'])
    jira = JIRA(basic_auth=(login['username'], login['token']), options={'server': user_settings.release_set['url']})
    return jira


def parse_search_str(user_settings):
    search_str = user_settings.release_set['jql']
    # Replace variables if you find any
    for user_variable in list(user_settings.fields.keys()):
        search_str = search_str.replace(f'{{{{{user_variable}}}}}', user_settings.fields[user_variable])

    return search_str


def retrieve_issues(jira, search_str, start_at, batch_size):
    issues = jira.search_issues(search_str, startAt=start_at, maxResults=batch_size)
    return issues

def get_openai_client(api_key):
    return OpenAI(api_key=api_key)

def get_release_note_summary(ai_client, ai_prompt, text_to_summarize):


    return ai_client.responses.create(
        model="gpt-4o",
        instructions=ai_prompt,
        input= f"{text_to_summarize}"
    )

def retrieve_description(issue):
    return issue.fields.summary


def retrieve_comments(issue):
    return " ".join(comment.body for comment in issue.fields.comment.comments)


def render_release_notes(user_settings, issue_list):
    environment = jinja2.Environment(loader=FileSystemLoader(user_settings.templates_directory), trim_blocks=True)

    support_filters = {name: function for name, function in getmembers(release_note_filters) if isfunction(function)}
    environment.filters.update(support_filters)

    support_functions = {name: function for name, function in getmembers(release_note_functions) if
                         isfunction(function)}
    environment.globals.update(support_functions)

    support_tests = {name: function for name, function in getmembers(release_note_tests) if
                     isfunction(function)}
    environment.tests.update(support_tests)

    environment.trim_blocks = True
    environment.lstrip_blocks = True

    template = environment.get_template(user_settings.release_set['template'])
    content = template.render(user_settings=user_settings, issues=issue_list)
    with open(user_settings.output_file, mode="wt") as results:
        results.write(content)


@click.command()
@click.option('--config', default='cb_release_notes_config.yaml',
              help='The configuration YAML file to use in the setup', type=click.Path())
@click.option('--output', help='The name of the output file', type=click.Path(), required=False)
@click.option('--summarize', help='Add an OpenAI generated summary to notes without a release note description',
              is_flag=True, default=False)
@click.version_option(version='1.0.0')
def main(config, output, summarize):
    """Creates release notes from Couchbase Jiras."""
    try:

        configuration = load_config(config)
        show_banner(configuration['version'])

        user_settings = UserSettings()

        if output is not None:
            user_settings.output_file = output

        settings = get_user_options(user_settings, configuration)
        jira = get_jira_client(settings)

        issue_list = []
        list_position = 0
        search = parse_search_str(settings)

        with alive_bar(title='Retrieving jira tickets ...', manual=True, dual_line=True, ) as bar:

            while True:
                retrieved_issues = retrieve_issues(jira, search, list_position, settings.jira_batch_size)
                if len(retrieved_issues) > 0:
                    issue_list.extend(retrieved_issues)
                    list_position += len(retrieved_issues)
                    bar(len(issue_list) / retrieved_issues.total)
                    bar.text(f'{len(issue_list)} retrieved ...')
                else:
                    break

            bar.text(f'{len(issue_list)} retrieved ...')

        ai_client = get_openai_client(user_settings.openai_api_key)

        if summarize:

            with alive_bar(title='Summarizing descriptions and comments ...', manual=True, dual_line=True, ) as bar:

                bar.text('summarizing ...')

                for index, issue in enumerate(issue_list):
                    issue_summary = retrieve_description(issue)
                    issue_comments = retrieve_comments(issue)
                    ai_summary = get_release_note_summary(ai_client,
                                                          user_settings.release_set['ai_prompt'],
                                                          issue_summary + issue_comments)
                    issue.fields.ai_summary = ai_summary.output_text
                    bar((index + 1) / len(issue_list))
                    bar.text(f'{index + 1} summarized ...')


        render_release_notes(settings, issue_list)
        click.echo('Done!')


    except ValidationError as vE:
        click.echo(f'Error in configuration file ==> {vE.message}')


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
