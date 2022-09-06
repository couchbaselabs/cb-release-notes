import datetime
import os
from inspect import getmembers, isfunction

import editor
import jinja2
import pyfiglet
import yaml
from InquirerPy import inquirer
from alive_progress import alive_bar
from jinja2 import FileSystemLoader
from jira import JIRA
from termcolor import colored

import release_note_filters
import release_note_functions

DEFAULT_JIRA_BATCH_SIZE = 100


class UserSettings:
    password_file = None
    templates_directory = None
    jira_batch_size = DEFAULT_JIRA_BATCH_SIZE
    settings = None
    fields = {}
    output_file = None

    def __str__(self):
        return f'settings = {self.settings}; \
          fields = {self.fields}  \
          output file = {self.output_file}'


def load_config():
    config_stream = open("cb_release_notes_config.yaml", "r")
    config = yaml.load(config_stream, Loader=yaml.FullLoader)
    return config


def show_banner(version_number):
    os.system('cls' if os.name == 'nt' else 'clear')
    print(colored(pyfiglet.figlet_format(f'CB Release Notes\nversion {version_number}'), 'green'))


def get_user_options(config):
    user_settings = UserSettings()

    user_settings.password_file = config['password_file']
    user_settings.templates_directory = config['templates_directory']

    if "jira_batch_size" in config:
        user_settings.jira_batch_size = config["jira_batch_size"]

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

    user_settings.settings = next(setting for setting in config['release_settings'] if setting['name'] == release_set)

    if 'fields' in user_settings.settings:
        for field in [item for item in user_settings.settings['fields']]:

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
                    validate=lambda entered_text: len(entered_text) > 0,
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

    # Timestamp the filename
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
    login = get_login_details(user_settings.password_file, user_settings.settings['url'])

    if 'token' in login:
        jira = JIRA(user_settings.settings['url'], token_auth=(login['token']))
    else:
        jira = JIRA(user_settings.settings['url'], basic_auth=(login['username'], login['password']))

    return jira


def parse_search_str(user_settings):
    search_str = user_settings.settings['jql']
    # Replace variables if you find any
    for user_variable in list(user_settings.fields.keys()):
        search_str = search_str.replace(f'{{{{{user_variable}}}}}', user_settings.fields[user_variable])

    return search_str


def retrieve_issues(jira, search_str, start_at, batch_size):
    issues = jira.search_issues(search_str, startAt=start_at, maxResults=batch_size)
    return issues


def render_release_notes(user_settings, issue_list):
    environment = jinja2.Environment(loader=FileSystemLoader(user_settings.templates_directory), trim_blocks=True)

    support_filters = {name: function for name, function in getmembers(release_note_filters) if isfunction(function)}
    environment.filters.update(support_filters)

    support_functions = {name: function for name, function in getmembers(release_note_functions) if
                         isfunction(function)}
    environment.globals.update(support_functions)

    template = environment.get_template(user_settings.settings['template'])
    content = template.render(user_settings=user_settings, issues=issue_list)
    with open(user_settings.output_file, mode="wt") as results:
        results.write(content)


def main():
    configuration = load_config()
    show_banner(configuration['version'])
    settings = get_user_options(configuration)
    jira = get_jira_client(settings)

    issue_list = []
    list_position = 0
    search = parse_search_str(settings)

    print(f'\nSearching on ==>\n{search}\n')

    with alive_bar(title='Retrieving jiras ...', manual=True, dual_line=True,) as bar:

        while True:
            retrieved_issues = retrieve_issues(jira, search, list_position, settings.jira_batch_size)
            if len(retrieved_issues) > 0:
                issue_list.extend(retrieved_issues)
                list_position += len(retrieved_issues)
                bar(len(issue_list) / retrieved_issues.total)
                bar.text(f'{len(issue_list)} retrieved ...')
            else:
                break

    print('\nCreating document ...\n')
    render_release_notes(settings, issue_list)
    print('Done.\n')


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
