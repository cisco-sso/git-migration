# Library imports
from PyInquirer import prompt, print_json
import requests
import json
import os
import shutil
from colorama import init, Fore, Style

# Custom imports
from utils import logBright, logLight
from credOperations import getCredentials, checkCredentials, checkCredsForPush
from repoOperations import getBitbucketProjects, getBitbucketRepos, processRepos, migrateRepos

# To enable colored printing on Windows as well
init()

# Get required credentials from JSON file
bitbucketAccountID, bitbucketAccessToken, githubAccountID, githubAccessToken = getCredentials()

# Ask for migration destination
pushQuestion = [
    {
        'type': 'list',
        'name': 'pushDestination',
        'message': "Migrate repositories to?",
        'choices': ["GitHub CX Engineering Org", "Personal Github Account"]
    }
]
pushAnswer = prompt(pushQuestion)
pushToOrg = pushAnswer["pushDestination"] == "GitHub CX Engineering Org"

# Check if credentials are right to push to the chosen destination
pushCheckPassed = checkCredsForPush(pushToOrg, githubAccountID, githubAccessToken)
if (not pushCheckPassed):
    exit(0)

# Get list of projects
logLight(Fore.BLUE, "Getting list of projects...\n")
projectNames = getBitbucketProjects(bitbucketAccessToken)

# Ask which project to migrate
projectQuestion = [
    {
        'type': 'list',
        'name': 'project',
        'message': 'Which project to migrate? (Enter to select)',
        'choices': projectNames
    }
]
projectAnswer = prompt(projectQuestion)

# Check access to BitBucket project and check GitHub credentials
[projectName, projectKey] = projectAnswer["project"].split(":")
if(not checkCredentials(projectKey, bitbucketAccessToken, githubAccessToken)):
    exit(1)

# Get list of all repos
logLight(Fore.BLUE, "Getting list of repositories...\n")
repoNames = getBitbucketRepos(projectKey, bitbucketAccessToken)
repoList = [ { 'name':"{}".format(repo) } for repo in repoNames ]

# Ask which repos to migrate
reposQuestion = [
    {
        'type': 'checkbox',
        'name': 'repos',
        'message': "Which repos to migrate from {}:{}?\n(Spacebar to toggle selection, Enter to continue)".format(projectName, projectKey),
        'choices': repoList
    }
]
repoAnswers = prompt(reposQuestion)

# Process repos to check for Open PRs or pre-existing repos on GitHub with same name
accepts, openPRs, alreadyExisting = processRepos(repoAnswers, projectKey, pushToOrg, bitbucketAccessToken, githubAccountID, githubAccessToken)
acceptedNumber = len(accepts)
openPRsNumber = len(openPRs)
alreadyExistingNumber = len(alreadyExisting)
print(
    Style.BRIGHT + Fore.GREEN + "Accepted: {}\t".format(acceptedNumber) + Fore.RED +"Rejected: {} ( {} with open PRs, {} already existing on GitHub )".format(
    openPRsNumber+alreadyExistingNumber,
    openPRsNumber,
    alreadyExistingNumber
) + Style.RESET_ALL)

logBright(Fore.BLUE, "Close all PRs before migrating a repo.")

if(acceptedNumber==0):
    logBright(Fore.BLUE, "No repositories migrated")
    exit(0)

# Confirm migration of accepted repos
continueMigrationQuestion = [
    {
        'type': 'confirm',
        'name': 'continueMigration',
        'message': "Continue with migrating accepted repos?",
        'default': True
    }
]
continueMigration = prompt(continueMigrationQuestion)['continueMigration']
if(not continueMigration):
    logBright(Fore.BLUE, "No repositories migrated")
    exit(0)

# Migrate all accepted repos
logLight(Fore.BLUE, "Migrating {} repositories...".format(len(accepts)))
migrateRepos(accepts, pushToOrg, bitbucketAccountID, bitbucketAccessToken, githubAccountID, githubAccessToken)

logBright(Fore.GREEN, "Migration successfully completed - {} repositories copied to GitHub".format(acceptedNumber))