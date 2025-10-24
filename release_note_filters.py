# Support filters for the Jinja conversion.
import re


def filter_by_component(issues, selected_components):
    return [issue for issue in issues if
            [component for component in issue.fields.components if component.name in selected_components]]


def filter_out_by_component(issues, selected_components):
    return [issue for issue in issues if
            [component for component in issue.fields.components if component.name not in selected_components]]


def filter_by_status(issues, selected_statuses):
    return [issue for issue in issues if issue.fields.status.name in selected_statuses]


def filter_by_resolution(issues, selected_resolutions):
    return [issue for issue in issues if issue.fields.resolution.name in selected_resolutions]


def filter_by_issue_type(issues, selected_issue_types):
    return [issue for issue in issues if issue.fields.issuetype in selected_issue_types]


def filter_by_fix_version(issues, selected_fix_versions):
    return [issue for issue in issues if
            [fix_version for fix_version in issue.fields.fixVersions if fix_version.name in selected_fix_versions]]


def filter_by_label(issues, selected_labels):
    return [issue for issue in issues if
            [label for label in issue.fields.labels if label in selected_labels]]


def replace_dots(string_to_fix, char_to_replace):
    return string_to_fix.replace('.', char_to_replace)

def convert_to_asciidoc_urls(string_to_fix, enable=False):

    if enable:
        pattern = r'\[(https?:\/\/.*[\r\n]*)\|(.*[\r\n]*)\]\[(.*)\]'
        replacement = r'\1[\3]'
        return re.sub(pattern, replacement, string_to_fix, flags=re.MULTILINE + re.IGNORECASE)
    else:
        return string_to_fix


