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
@click.option('--personal-account', is_flag=True, help="Migrates/Syncs the repositories to personal GitHub account")
@click.option('--block-new-migrations', is_flag=True, help="Block new migrations and sync only existing repos on GitHub")
@app_cli.pass_context
# By default, run in a loop at time intervals - TBD
def auto(ctx, run_once, personal_account, block_new_migrations):
    """Automatically sync all according to config file"""
    # Use ctx.log.info("message") to log
    pushToOrg = not personal_account
    credOps = credOperations.credOps(ctx.bitbucketAPI, ctx.githubAPI, ctx.console_log_level, ctx.console_log_normal, ctx.file_log_level)
    repoOps = repoOperations.repoOps(ctx.bitbucketAPI, ctx.githubAPI, ctx.console_log_level, ctx.console_log_normal, ctx.file_log_level)
    
    # Check if credentials are right and can push to the chosen destination
    githubPushCheck = credOps.checkGithubPushCreds(pushToOrg, ctx.githubAccountID, ctx.githubAccessToken)
    githubPullCheck = credOps.checkGithubPullCreds(ctx.githubAccessToken)
    if (not (githubPushCheck and githubPullCheck)):
        exit(0)

    toInclude, toExclude = utils.ReadUtils.getSyncConfig()
    for projectKey in toInclude:
        # Check credentials for given project
        bitbucketPullCheck = credOps.checkBitbucketPullCreds(projectKey, ctx.bitbucketAccessToken)
        if (not bitbucketPullCheck):
            exit(1)
        includeRegexList = toInclude[projectKey]
        excludeRegexList = toExclude[projectKey]
        repoNames = repoOps.getBitbucketRepos(projectKey, ctx.bitbucketAccessToken)
        # Filter repositories based on config file regex patterns
        repoNames = utils.RegexUtils.filterRepos(repoNames, includeRegexList)
        repoNames = utils.RegexUtils.filterRepos(repoNames, excludeRegexList, excludeMatches=True)
        # Process and obtain metadata, links and details about repos
        processedRepos, totalRepos, newRepos = repoOps.processRepos(projectKey, repoNames, pushToOrg,
                                                                    ctx.bitbucketAccessToken, ctx.githubAccountID,
                                                                    ctx.githubAccessToken)
        # Sync only the repos that already exist on GitHub
        if (block_new_migrations):
            processedRepos = [repo for repo in processedRepos if ('githubLink' in repo)]
        # Put an exit(0) just before this for testing other functionality without syncing
        # Sync the filtered repositories repositories
        repoOps.syncRepos(pushToOrg, processedRepos, ctx.bitbucketAccountID, ctx.bitbucketAccessToken,
                          ctx.githubAccountID, ctx.githubAccessToken)


@cli.command()
@app_cli.pass_context
def interactive(ctx):
    """Select the projects and repositories to migrate/sync"""
    # Use ctx.log.info("message") to log
    interactiveSync.startSession(ctx.bitbucketAccountID, ctx.bitbucketAccessToken, ctx.githubAccountID,
                                 ctx.githubAccessToken, ctx.bitbucketAPI, ctx.githubAPI, ctx.console_log_level, ctx.console_log_normal, ctx.file_log_level)
