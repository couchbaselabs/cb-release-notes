import datetime
import os
import jinja2
import pyfiglet
import yaml
from InquirerPy import inquirer
from jinja2 import FileSystemLoader
from jira import JIRA
from termcolor import colored
from inspect import getmembers, isfunction
import release_note_filters
import editor

import release_note_functions


class UserSettings:
    password_file = None
    templates_directory = None
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
    print(colored(pyfiglet.figlet_format(f'CB Release Notes  {version_number}', width=100), 'green'))


def get_user_options(config):
    user_settings = UserSettings()

    user_settings.password_file = config['password_file']
    user_settings.templates_directory = config['templates_directory']

    # Get the settings details from the configuration
    release_sets = [item['name'] for item in config['release_settings']]

    release_set = inquirer.select(
        message="Select Release item:",
        choices=release_sets,
        validate=lambda setting: len(setting) > 0,
        invalid_message="You must select a setting",
        height=6
    ).execute()

    user_settings.settings = next(setting for setting in config['release_settings'] if setting['name'] == release_set)

    if 'fields' in user_settings.settings:
        for field in [item for item in user_settings.settings['fields']]:

            if field['type'] == 'text':
                text = inquirer.text(
                    message=field['message'],
                    validate=lambda entered_text: len(entered_text) > 0,
                    invalid_message="You must enter a value"
                ).execute()
                user_settings.fields[field['name']] = text

            if field['type'] == 'multiline':
                text = inquirer.text(
                    message=field['message'],
                    multiline=True,
                    validate=lambda entered_text: len(entered_text) > 0,
                    invalid_message="You must enter a value"
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
                    validate=lambda selected_choices: len(selected_choices) > 0,
                    invalid_message="You must select at least one setting",
                ).execute()
                user_settings.fields[field['name']] = ','.join(choices)

            elif field['type'] == 'select':
                choice = inquirer.select(
                    message=field['message'],
                    choices=field['choices'],
                    validate=lambda selected_choice: len(selected_choice) > 0,
                    invalid_message="You must select one",
                ).execute()
                user_settings.fields[field['name']] = choice

    # Timestamp the filename
    file_stamp = datetime.datetime.now().strftime('%Y%m%d')
    user_settings.output_file = inquirer.filepath(
        message="Now, what's the name of the asciidoc file you wish to create?",
        default=f'{release_set}-{file_stamp}-release-note.adoc',
        validate=lambda file_name: file_name.endswith('.adoc'),

    ).execute()

    return user_settings


def get_login_details(password_file, url_str):
    login_details_stream = open(password_file, "r")
    login_details = yaml.load(login_details_stream, Loader=yaml.FullLoader)
    return login_details[url_str]


def retrieve_issues(user_settings):
    login = get_login_details(user_settings.password_file, user_settings.settings['url'])

    if 'token' in login:
        jira = JIRA(user_settings.settings['url'], token_auth=(login['token']))
    else:
        jira = JIRA(user_settings.settings['url'], basic_auth=(login['username'], login['password']))

    search_str = user_settings.settings['jql']
    # Replace variables if you find any
    for user_variable in list(user_settings.fields.keys()):
        print(f'{user_variable} ==> {user_settings.fields[user_variable]}')
        search_str = search_str.replace(f'{{{{{user_variable}}}}}', user_settings.fields[user_variable])

    print(f'Searching with => {search_str}')
    issues = jira.search_issues(search_str, maxResults=100000)
    return issues


def render_release_notes(user_settings, issue_list):
    environment = jinja2.Environment(loader=FileSystemLoader(user_settings.templates_directory), trim_blocks=True)

    support_filters = {name: function for name, function in getmembers(release_note_filters) if isfunction(function)}
    environment.filters.update(support_filters)

    support_functions = {name: function for name, function in getmembers(release_note_functions) if isfunction(function)}
    environment.globals.update(support_functions)

    template = environment.get_template(user_settings.settings['template'])
    content = template.render(user_settings=user_settings, issues=issue_list)
    with open(user_settings.output_file, mode="wt") as results:
        results.write(content)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    configuration = load_config()
    show_banner(configuration['version'])
    settings = get_user_options(configuration)
    released_issues = retrieve_issues(settings)
    render_release_notes(settings, released_issues)
