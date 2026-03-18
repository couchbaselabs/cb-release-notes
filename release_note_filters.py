# Support filters for the Jinja conversion.
import re

from jinja2 import pass_context

# We need to maintain a running list of issues that have been rendered on the page so far,
# because some tickets have more than one component label. Even so, the item should only
# appear once on the page. After each item in the component set is found, add it to the
# list so that it won't be rendered again.


@pass_context
def filter_by_component(ctx, issues, selected_components):

    if not hasattr(ctx, 'issues_processed_so_far'):
        ctx.issues_processed_so_far = []

    issue_list = [issue for issue in issues if
            [component for component in issue.fields.components
             if component.name in selected_components and issue not in ctx.issues_processed_so_far]]

    ctx.issues_processed_so_far.extend(issue_list)

    return issue_list

@pass_context
def filter_out_by_component(ctx, issues, selected_components):

    if not hasattr(ctx, 'issues_processed_so_far'):
        ctx.issues_processed_so_far = []

    return [issue for issue in issues if
            [component for component in issue.fields.components
             if component.name not in selected_components and issue not in ctx.issues_processed_so_far]]


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


def convert_to_asciidoc_urls(string_to_fix, disable=False):
    if disable:
        return string_to_fix
    else:
        pattern = r'\[(https?:\/\/.*[\r\n]*)\|(.*[\r\n]*)\]\[(.*)\]'
        replacement = r'\1[\3]'
        return re.sub(pattern, replacement, string_to_fix, flags=re.MULTILINE + re.IGNORECASE)
