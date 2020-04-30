# Library imports
import click
import os
import sys
import json

# Custom imports
from app.testing import utils
# from app import repo_operations
# from app import cred_operations
# from app import interactive_sync
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
#   for missing settings, and 'auto' mode does not prompt user and instead
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
@click.option('--prefix',
              prompt=not is_help_called() and is_interactive(),
              required=not is_help_called() and not is_interactive(),
              default=utils.ReadUtils.get_prefix(),
              show_default=utils.ReadUtils.get_prefix(),
              type=str,
              help="Prefix to be added to the names of sync'd repositories at destination")
@click.option('--master-branch-prefix',
              prompt=not is_help_called() and is_interactive(),
              required=not is_help_called() and not is_interactive(),
              default=utils.ReadUtils.get_master_branch_prefix(),
              show_default=utils.ReadUtils.get_master_branch_prefix(),
              type=str,
              help="Prefix to be added to rename the master branch from BitBucket")
@app_cli.pass_context
def cli(ctx, bitbucket_url, github_url, bitbucket_account_id, bitbucket_access_token, github_account_id,
        github_access_token, prefix, master_branch_prefix):
    """Sync Bitbucket and GitHub repositories"""
    ctx.bitbucket_api = bitbucket_url
    ctx.github_api = github_url
    ctx.bitbucket_account_id = bitbucket_account_id
    ctx.bitbucket_access_token = bitbucket_access_token
    ctx.github_account_id = github_account_id
    ctx.github_access_token = github_access_token
    ctx.prefix = prefix
    ctx.master_branch_prefix = master_branch_prefix


@cli.command()
@app_cli.pass_context
def parse(ctx):
    integrations = utils.ReadUtils.get_integrations()
    # NOTE Will need something pretty different than the current repo_operations and cred_operations to
    #       account for different types of sources and targets. Have to read up on how to approach a
    #       plugin system style of developemnt.
    print(json.dumps(integrations, indent=2))
