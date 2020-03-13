# Library imports
import argparse
from PyInquirer import prompt, print_json
import requests
import json
import os
import shutil
from colorama import init, Fore, Style

# Custom imports
from utils import logBright, logLight
from credOperations import getCredentials, checkCredentials, checkCredsForPush
from repoOperations import getBitbucketProjects, getAndProcessBitbucketRepos , migrateRepos

# To enable colored printing on Windows as well
init()

# Get required credentials from JSON file
bitbucketAccountID, bitbucketAccessToken, githubAccountID, githubAccessToken = getCredentials()

# Get arguments (project name to migrate)
parser = argparse.ArgumentParser('Migrate Repositories')
parser.add_argument('-c', '--***REMOVED***', action='store_true', help='Pass flag to push to ***REMOVED*** organization')
parser.add_argument('project', metavar='P', type=str, help='KEY of BitBucket project to be migrated')
args = parser.parse_args()

projectKey = args.project
logBright(Fore.YELLOW , 'Target project: ' + projectKey)

# Check credentials for given project
if (not checkCredentials(args.project, bitbucketAccessToken, githubAccessToken)):
    exit(1)

pushToOrg = args.***REMOVED***
# Check if credentials are right to push to the chosen destination
pushCheckPassed = checkCredsForPush(pushToOrg, githubAccountID, githubAccessToken)
if (not pushCheckPassed):
    exit(0)

# Confirm migration to destination
if (pushToOrg):
    confirmMigrateQuestion = [
        {
            'type': 'confirm',
            'name': 'confirmMigrate',
            'message': "Migrate to GitHub ***REMOVED*** Org?",
            'default': True
        }
    ]
    confirmMigrate = prompt(confirmMigrateQuestion)['confirmMigrate']
    if(not confirmMigrate):
        logLight(Fore.BLUE, "Rerun script without --***REMOVED*** flag to migrate to GitHub personal Account")
        exit(0)
else:
    confirmMigrateQuestion = [
        {
            'type': 'confirm',
            'name': 'confirmMigrate',
            'message': "Migrate to GitHub Personal Account?",
            'default': True
        }
    ]
    confirmMigrate = prompt(confirmMigrateQuestion)['confirmMigrate']
    if(not confirmMigrate):
        logLight(Fore.BLUE, "Rerun script with --***REMOVED*** flag to migrate to GitHub ***REMOVED*** Org")
        exit(0)

# Check repos and get accepted and rejected ones
accepts, openPRs, alreadyExisting = getAndProcessBitbucketRepos(projectKey, pushToOrg, bitbucketAccessToken, githubAccountID, githubAccessToken)

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