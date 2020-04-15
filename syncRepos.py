import requests
import json
import os
import shutil
import colorama as color

# Custom imports
import utils
import credOperations
import repoOperations

# Objects for operations related to credentials and repository actions
credOps = credOperations.credOps()
repoOps = repoOperations.repoOps()

bitbucketAccountID, bitbucketAccessToken, githubAccountID, githubAccessToken = credOps.getCredentials()

toSync, toExclude = utils.ReadUtils.getSyncProjects()

for projectKey in toSync:
    # Check credentials for given project
    if (not credOps.checkCredentials(projectKey, bitbucketAccessToken, githubAccessToken)):
        exit(1)
    
    utils.LogUtils.logLight(color.Fore.BLUE, "Getting list of projects...\n")
    repoNames = repoOps.getBitbucketRepos(projectKey, bitbucketAccessToken)
    reposOnGithub = repoOps.existsOnGithub(projectKey, repoNames, bitbucketAccessToken, githubAccessToken)

    utils.LogUtils.logLight(color.Fore.BLUE, "Syncing {} project\n".format(projectKey))
    repoOps.syncDelta(reposOnGithub, bitbucketAccountID, bitbucketAccessToken, githubAccountID, githubAccessToken)