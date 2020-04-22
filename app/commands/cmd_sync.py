# Library imports
import click
import os
import sys

# Custom imports
from app import utils
from app import repo_operations
from app import cred_operations
from app import interactive_sync
from app import cli as app_cli


def is_help_called():
    return ('--help' in sys.argv) or ('-h' in sys.argv)


def is_interactive():
    return 'interactive' in sys.argv


@click.group()
@click.option('--bitbucket-url',
              default='https://***REMOVED***/bitbucket/rest/api/1.0',
              show_default='https://***REMOVED***/bitbucket/rest/api/1.0',
              type=str,
              help="Bitbucket API Base URL")
@click.option('--github-url',
              default='https://***REMOVED***/api/v3',
              show_default='https://***REMOVED***/api/v3',
              type=str,
              help="GitHub API Base URL")
# For the following options, ensure that 'interactive' mode prompts the user
#   for missing settings, and 'auto' mode does not prom pt user and instead
#   shows help usage.
@click.option('--bitbucket-account-id',
              prompt=not is_help_called() and is_interactive(),
              required=not is_help_called() and not is_interactive(),
              default=lambda: os.environ.get('GIT_MIGRATION_BITBUCKET_ACCOUNT_ID'),
              show_default='env GIT_MIGRATION_BITBUCKET_ACCOUNT_ID',
              type=str,
              help="BitBucket Account ID, usually CEC ID")
@click.option('--bitbucket-access-token',
              prompt=not is_help_called() and is_interactive(),
              required=not is_help_called() and not is_interactive(),
              default=lambda: os.environ.get('GIT_MIGRATION_BITBUCKET_ACCESS_TOKEN'),
              show_default='env GIT_MIGRATION_BITBUCKET_ACCESS_TOKEN',
              type=str,
              help="BitBucket Access Token")
@click.option('--github-account-id',
              prompt=not is_help_called() and is_interactive(),
              required=not is_help_called() and not is_interactive(),
              default=lambda: os.environ.get('GIT_MIGRATION_GITHUB_ACCOUNT_ID', None),
              show_default='env GIT_MIGRATION_GITHUB_ACCOUNT_ID',
              type=str,
              help="GitHub Account ID, usually CEC ID")
@click.option('--github-access-token',
              prompt=not is_help_called() and is_interactive(),
              required=not is_help_called() and not is_interactive(),
              default=lambda: os.environ.get('GIT_MIGRATION_GITHUB_ACCESS_TOKEN'),
              show_default='env GIT_MIGRATION_GITHUB_ACCESS_TOKEN',
              type=str,
              help="GitHub Access Token")
@app_cli.pass_context
def cli(ctx, bitbucket_url, github_url, bitbucket_account_id, bitbucket_access_token, github_account_id,
        github_access_token):
    """Sync Bitbucket and GitHub repositories"""
    ctx.bitbucket_api = bitbucket_url
    ctx.github_api = github_url
    ctx.bitbucket_account_id = bitbucket_account_id
    ctx.bitbucket_access_token = bitbucket_access_token
    ctx.github_account_id = github_account_id
    ctx.github_access_token = github_access_token


@cli.command()
@click.option('--run-once', is_flag=True, help="Syncs the repositories once")
@click.option('--personal-account', is_flag=True, help="Migrates/Syncs the repositories to personal GitHub account")
@click.option('--block-new-migrations',
              is_flag=True,
              help="Block new migrations and sync only existing repos on GitHub")
@app_cli.pass_context
# By default, run in a loop at time intervals - TBD
def auto(ctx, run_once, personal_account, block_new_migrations):
    """Automatically sync all according to config file"""
    # Use ctx.log.info("message") to log
    push_to_org = not personal_account
    cred_ops = cred_operations.CredOps(ctx.bitbucket_api, ctx.github_api, ctx.console_log_level, ctx.console_log_normal,
                                       ctx.file_log_level)
    repo_ops = repo_operations.RepoOps(ctx.bitbucket_api, ctx.github_api, ctx.console_log_level, ctx.console_log_normal,
                                       ctx.file_log_level)

    # Check if credentials are right and can push to the chosen destination
    github_push_check = cred_ops.check_github_push_creds(push_to_org, ctx.github_account_id, ctx.github_access_token)
    github_pull_check = cred_ops.check_github_pull_creds(ctx.github_access_token)
    if (not (github_push_check and github_pull_check)):
        exit(0)

    to_include, to_exclude = utils.ReadUtils.get_sync_config()
    for project_key in to_include:
        # Check credentials for given project
        bitbucket_pull_check = cred_ops.check_bitbucket_pull_creds(project_key, ctx.bitbucket_access_token)
        if (not bitbucket_pull_check):
            exit(1)
        include_regex_list = to_include[project_key]
        exclude_regex_list = to_exclude[project_key]
        repo_names = repo_ops.get_bitbucket_repos(project_key, ctx.bitbucket_access_token)
        # Filter repositories based on config file regex patterns
        repo_names = utils.RegexUtils.filter_repos(repo_names, include_regex_list)
        repo_names = utils.RegexUtils.filter_repos(repo_names, exclude_regex_list, exclude_matches=True)
        # Process and obtain metadata, links and details about repos
        processed_repos, total_repos, new_repos = repo_ops.process_repos(project_key, repo_names, push_to_org,
                                                                         ctx.bitbucket_access_token,
                                                                         ctx.github_account_id, ctx.github_access_token)
        # Sync only the repos that already exist on GitHub
        if (block_new_migrations):
            processed_repos = [repo for repo in processed_repos if ('github_link' in repo)]
        # Put an exit(0) just before this for testing other functionality without syncing
        # Sync the filtered repositories repositories
        repo_ops.sync_repos(push_to_org, processed_repos, ctx.bitbucket_account_id, ctx.bitbucket_access_token,
                            ctx.github_account_id, ctx.github_access_token)

        # TODO (***REMOVED***): still need to assign repos to teams
        #   AND this needs to be reflected in the configuration file.

@cli.command()
@app_cli.pass_context
def interactive(ctx):
    """Select the projects and repositories to migrate/sync"""
    # Use ctx.log.info("message") to log
    interactive_sync.start_session(ctx.bitbucket_account_id, ctx.bitbucket_access_token, ctx.github_account_id,
                                   ctx.github_access_token, ctx.bitbucket_api, ctx.github_api, ctx.console_log_level,
                                   ctx.console_log_normal, ctx.file_log_level)
