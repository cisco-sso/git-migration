# Library imports
import click
import os

# Custom imports
from app import utils
from app import repoOperations
from app import credOperations
from app import interactiveSync
from app import cli as app_cli


@click.group()
# TODO (***REMOVED***): Add sane default that will work.
@click.option('--bitbucket-url',
              prompt=len(os.environ.get('GIT_MIGRATION_BITBUCKET_API_URL', '')) == 0,
              default=lambda: os.environ.get('GIT_MIGRATION_BITBUCKET_API_URL', ''),
              show_default='env GIT_MIGRATION_BITBUCKET_API_URL',
              type=str,
              help="Bitbucket Base API URL")
# TODO (***REMOVED***): Add sane default that will work.
@click.option('--github-url',
              prompt=len(os.environ.get('GIT_MIGRATION_GITHUB_API_URL', '')) == 0,
              default=lambda: os.environ.get('GIT_MIGRATION_GITHUB_API_URL', ''),
              show_default='env GIT_MIGRATION_GITHUB_API_URL',
              type=str,
              help="GitHub Base API URL")
@click.option('--bitbucket-account-id',
              prompt=len(os.environ.get('GIT_MIGRATION_BITBUCKET_ACCOUNT_ID', '')) == 0,
              default=lambda: os.environ.get('GIT_MIGRATION_BITBUCKET_ACCOUNT_ID', ''),
              show_default='env GIT_MIGRATION_BITBUCKET_ACCOUNT_ID',
              type=str,
              help="BitBucket Account ID, usually CEC ID")
@click.option('--bitbucket-access-token',
              prompt=len(os.environ.get('GIT_MIGRATION_BITBUCKET_ACCESS_TOKEN', '')) == 0,
              default=lambda: os.environ.get('GIT_MIGRATION_BITBUCKET_ACCESS_TOKEN', ''),
              show_default='env GIT_MIGRATION_BITBUCKET_ACCESS_TOKEN',
              type=str,
              help="BitBucket Access Token")
@click.option('--github-account-id',
              prompt=len(os.environ.get('GIT_MIGRATION_GITHUB_ACCOUNT_ID', '')) == 0,
              default=lambda: os.environ.get('GIT_MIGRATION_GITHUB_ACCOUNT_ID', ''),
              show_default='env GIT_MIGRATION_GITHUB_ACCOUNT_ID',
              type=str,
              help="GitHub Account ID, usually CEC ID")
@click.option('--github-access-token',
              prompt=len(os.environ.get('GIT_MIGRATION_GITHUB_ACCESS_TOKEN', '')) == 0,
              default=lambda: os.environ.get('GIT_MIGRATION_GITHUB_ACCESS_TOKEN', ''),
              show_default='env GIT_MIGRATION_GITHUB_ACCESS_TOKEN',
              type=str,
              help="GitHub Access Token")
@app_cli.pass_context
def cli(ctx, bitbucket_url, github_url, bitbucket_account_id, bitbucket_access_token, github_account_id,
        github_access_token):
    """Sync Bitbucket and GitHub repositories"""
    ctx.bitbucketAPI = bitbucket_url
    ctx.githubAPI = github_url
    ctx.bitbucketAccountID = bitbucket_account_id
    ctx.bitbucketAccessToken = bitbucket_access_token
    ctx.githubAccountID = github_account_id
    ctx.githubAccessToken = github_access_token


@cli.command()
@click.option('--run-once', is_flag=True, help="Syncs the repositories once")
@app_cli.pass_context
# By default, run in a loop at time intervals - TBD
def auto(ctx, run_once):
    """Automatically sync all according to config file"""
    credOps = credOperations.credOps(ctx.bitbucketAPI, ctx.githubAPI)
    repoOps = repoOperations.repoOps(ctx.bitbucketAPI, ctx.githubAPI)
    toInclude, toExclude = utils.ReadUtils.getSyncConfig()
    for projectKey in toInclude:
        # Check credentials for given project
        if (not credOps.checkCredentials(projectKey, ctx.bitbucketAccessToken, ctx.githubAccessToken)):
            exit(1)
        includeRegexList = toInclude[projectKey]
        excludeRegexList = toExclude[projectKey]
        repoNames = repoOps.getBitbucketRepos(projectKey, ctx.bitbucketAccessToken)
        # Filter repositories based on config file regex patterns
        repoNames = utils.RegexUtils.filterRepos(repoNames, includeRegexList)
        repoNames = utils.RegexUtils.filterRepos(repoNames, excludeRegexList, excludeMatches=True)

        # Eventually, even if repos don't exist on github, should migrate them over - TBD
        reposOnGithub = repoOps.existsOnGithub(projectKey, repoNames, ctx.bitbucketAccessToken, ctx.githubAccessToken)

        # Put an exit(0) just before this for testing other functionality without syncing
        # Sync the filtered repositories repositories
        repoOps.syncDelta(reposOnGithub, ctx.bitbucketAccountID, ctx.bitbucketAccessToken, ctx.githubAccountID,
                          ctx.githubAccessToken)


@cli.command()
@app_cli.pass_context
def interactive(ctx):
    """Select the projects and repositories to migrate/sync"""
    interactiveSync.startSession(ctx.bitbucketAccountID, ctx.bitbucketAccessToken, ctx.githubAccountID,
                                 ctx.githubAccessToken, ctx.bitbucketAPI, ctx.githubAPI)
