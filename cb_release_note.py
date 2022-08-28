import datetime
import os
import jinja2
import pyfiglet
import yaml
from InquirerPy import inquirer
from jinja2 import FileSystemLoader
from jira import JIRA
from termcolor import colored


class UserSettings:
    password_file = None
    templates_directory = None
    settings = None
    fields = {}
    output_file = None

    def __str__(self):
        return f'repo = {self.settings}; \
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
    repo_details = list(config['release-settings'].keys())
    release_setting = inquirer.select(
        message="Select Release item:",
        choices=repo_details,
        validate=lambda repo: len(repo) > 0,
        invalid_message="You must select a setting",
        height=6
    ).execute()

    user_settings.settings = config['release-settings'][release_setting]

    for field_name in list(user_settings.settings["fields"].keys()):

        field = user_settings.settings["fields"][field_name]

        if field['type'] == 'text':
            text = inquirer.text(
                message=field['message'],
                validate=lambda entered_text: len(entered_text) > 0,
                invalid_message="You must enter a value"
            ).execute()
            user_settings.fields[field_name] = text

        elif field['type'] == 'choice':
            choices = inquirer.checkbox(
                message=field['message'],
                choices=field['choices'],
                validate=lambda selected_choices: len(selected_choices) > 0,
                invalid_message="You must select at least one setting",
            ).execute()
            user_settings.fields[field_name] = ','.join(choices)

        elif field['type'] == 'select':
            choice = inquirer.select(
                message=field['message'],
                choices=field['choices'],
                validate=lambda selected_choice: len(selected_choice) > 0,
                invalid_message="You must select one",
            ).execute()
            user_settings.fields[field_name] = choice

    # Timestamp the filename
    file_stamp = datetime.datetime.now().strftime('%Y%m%d')
    user_settings.output_file = inquirer.filepath(
        message="Now, what's the name of the asciidoc file you wish to create?",
        default=f'{release_setting}-{file_stamp}-release-note.adoc',
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
    issues = jira.search_issues(search_str)
    return issues


def filter_by_component(issues, components):
    filtered_list = []
    for issue in issues:
        for issue_component in issue.fields.components:
            if issue_component.name in components:
                filtered_list.append(issue)
    return filtered_list


def filter_by_issue_type(issues, issue_types):
    filtered_list = []
    for issue in issues:
        for issue_type in issue.fields.issuetype:
            if issue_type in issue_types:
                filtered_list.append(issue)


def replace_dots(string_to_fix, char_to_replace):
    return string_to_fix.replace('.', char_to_replace)


def render_release_notes(user_settings, issue_list):
    environment = jinja2.Environment(loader=FileSystemLoader(user_settings.templates_directory), trim_blocks=True)

    environment.filters['filter_by_component'] = filter_by_component
    environment.filters['filter_by_issue_type'] = filter_by_issue_type
    environment.filters['replace_dots'] = replace_dots

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
