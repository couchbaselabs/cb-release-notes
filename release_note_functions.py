def url_with_jira(url, jira_key, jira_summary=None):
    if jira_summary is None:
        return f'{url}/browse/{jira_key}/[{jira_key}]'
    else:
        return f'{url}/browse/{jira_key}/[++{jira_summary}++]'
