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
from repoOperations import getBitbucketProjects, getAndProcessBitbucketRepos , migrateRepos, assignReposToTeams

# To enable colored printing on Windows as well
init()

# Get required credentials from JSON file
bitbucketAccountID, bitbucketAccessToken, githubAccountID, githubAccessToken = getCredentials()

# Get arguments (project name to migrate)
parser = argparse.ArgumentParser('Migrate Repositories')
parser.add_argument('-c', '--***REMOVED***', action='store_true', help='Pass flag to push to ***REMOVED*** organization')
parser.add_argument('-p', '--pr', action="store_true", help='Pass flag to migrate repos with Open PRs')
parser.add_argument('project', metavar='P', type=str, help='KEY of BitBucket project to be migrated')
args = parser.parse_args()

projectKey = args.project
logBright(Fore.YELLOW , 'Target project: ' + projectKey)

# Check credentials for given project
if (not checkCredentials(args.project, bitbucketAccessToken, githubAccessToken)):
    exit(1)

# True if --pr flag is passed
migrateOpenPRs = args.pr

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

logBright(Fore.BLUE, "Recommended to close all PRs before migrating a repo.")

if(acceptedNumber+openPRsNumber==0):
    logBright(Fore.BLUE, "No repositories migrated")
    exit(0)

# Ask whether to migrate repos with OpenPRs
acceptedOnly = "Accepted repos only"
acceptedAllOpenPRs = "Accepted repos and ALL repos with Open PRs"
acceptedSomeOpenPRs = "Accepted repos and SELECTED repos with Open PRs"
allOpenPRs = "ALL repos with Open PRs"
someOpenPRs = "SELECTED repos with Open PRs"

whichMigrateQuestionChoices = []

if (acceptedNumber == 0):
    whichMigrateQuestionChoices.append(allOpenPRs)
    whichMigrateQuestionChoices.append(someOpenPRs)
else:
    whichMigrateQuestionChoices.append(acceptedOnly)
    if (openPRsNumber != 0):
        whichMigrateQuestionChoices.append(acceptedAllOpenPRs)
        whichMigrateQuestionChoices.append(acceptedSomeOpenPRs)

whichMigrateQuestion = [
    {
        'type': 'list',
        'name': 'whichMigrate',
        'message': "Which repositories to migrate? (Pull Requests won't be migrated)",
        'choices': whichMigrateQuestionChoices
    }
]
whichMigrate = prompt(whichMigrateQuestion)["whichMigrate"]

if (not (whichMigrate == acceptedSomeOpenPRs or whichMigrate == someOpenPRs)):
    # Confirm migration of accepted repos
    continueMigrationQuestion = [
        {
            'type': 'confirm',
            'name': 'continueMigration',
            'message': "Continue with migrating [{}]?".format(whichMigrate),
            'default': True
        }
    ]
    continueMigration = prompt(continueMigrationQuestion)['continueMigration']
    if(not continueMigration):
        logBright(Fore.BLUE, "No repositories migrated")
        exit(0)
    # Accepted and ALL Open PR repos
    elif (whichMigrate==acceptedAllOpenPRs):
        repositories = accepts + openPRs
    # ALL Open PR Repos
    elif (whichMigrate==allOpenPRs):
        repositories = openPRs
    # Only accepted repos
    else:
        repositories = accepts
else:
    # Ask to selet specific repos with Open PRs
    openPRsRepoList = [ {'name': repo['name']} for repo in openPRs ]
    whichOpenPRsQuestion = [
        {
            'type': 'checkbox',
            'name': 'whichOpenPRs',
            'message': 'Which repos with Open PRs to migrate?',
            'choices': openPRsRepoList
        }
    ]
    whichOpenPRs = prompt(whichOpenPRsQuestion)['whichOpenPRs']
    selectedOpenPRs = list(filter( lambda repo: repo["name"] in whichOpenPRs, openPRs))
    # Only SELECTED Open PR repos
    if (whichMigrate == someOpenPRs):
        repositories = selectedOpenPRs
    # Accepted and SELECTED Open PR repos
    else:
        repositories = accepts + selectedOpenPRs

    reposNumber = len(repositories)
    if (reposNumber == 0):
        logBright(Fore.BLUE, "No repositories selected to migrate")
        exit(0) 
    # Confirm migration of accepted repos and selected repos with Open PRs
    continueMigrationQuestion = [
        {
            'type': 'confirm',
            'name': 'continueMigration',
            'message': "Continue with migrating [{} accepted repos and {} selected repos with Open PRs]?".format(acceptedNumber, len(selectedOpenPRs)),
            'default': True
        }
    ]
    continueMigration = prompt(continueMigrationQuestion)['continueMigration']
    if(not continueMigration):
        logBright(Fore.BLUE, "No repositories migrated")
        exit(0)

# Migrate specified repositories
reposNumber = len(repositories)
if (reposNumber == 0):
    logBright(Fore.BLUE, "No repositories selected to migrate")
    exit(0)

logLight(Fore.BLUE, "Migrating {} repositories...".format(reposNumber))
migrateRepos(repositories, pushToOrg, bitbucketAccountID, bitbucketAccessToken, githubAccountID, githubAccessToken)

logBright(Fore.GREEN, "Migration successfully completed - {} repositories copied to GitHub".format(reposNumber))

# No assignment to teams if repos migrated to personal account
if (not pushToOrg):
    exit(0)

# Ask how to assign migrated repos
noAssign = 'DO NOT ASSIGN any repos to any team'
allAssign = 'ASSIGN ALL repos to ONE team'
someAssign = 'ASSIGN repos to DIFFERENT teams'

assignToTeamsQuestion = [
    {
        'type': 'list',
        'name': 'assignToTeams',
        'message': 'Would you like to assign the migrated repos to teams?',
        'choices': [noAssign, allAssign, someAssign]
    }
]
assignToTeams = prompt(assignToTeamsQuestion)['assignToTeams']

if (assignToTeams == noAssign):
    logLight(Fore.BLUE, "None of the {} migrated repositories assigned to any teams".format(reposNumber))
    exit(0)

# Get list of all teams from GHE ***REMOVED*** org
teamsInfoList = requests.get(
    "https://***REMOVED***/api/v3/orgs/***REMOVED***/teams",
    headers={"Authorization": "Bearer {}".format(githubAccessToken)}
)
teamsInfoList = json.loads(teamsInfoList.text)
teamsList = [ team['slug'] for team in teamsInfoList ]
teamsChecklist = [ {'name':team['slug']} for team in teamsInfoList]

repoAssignment = {}
if (assignToTeams == allAssign):
    oneTeamQuestion = [
        {
            'type': 'list',
            'name': 'oneTeam',
            'message': 'Assign all projects to which team?',
            'choices': teamsList
        }
    ]

    oneTeam = prompt(oneTeamQuestion)['oneTeam']
    repoAssignment[oneTeam] = [ repo['name'] for repo in repositories ]

elif (assignToTeams == someAssign):
    selectTeamsQuestion = [
        {
            'type': 'checkbox',
            'name': 'selectTeams',
            'message': 'Select the teams to which you want to assign the repos',
            'choices': teamsChecklist
        }
    ]
    selectedTeams = prompt(selectTeamsQuestion)['selectTeams']

    allMigratedRepos = [ { 'name': repo['name'] } for repo in repositories ]

    repoAssignment = {}

    for team in selectedTeams:
        reposForTeamQuestion = [
            {
                'type': 'checkbox',
                'name': 'reposForTeams',
                'message': 'Select the repos to assign to {} team'.format(team),
                'choices': allMigratedRepos
            }
        ]
        reposForTeams = prompt(reposForTeamQuestion)['reposForTeams']
        if (len(reposForTeams)!=0):
            repoAssignment[team] = reposForTeams
        else:
            logLight(Fore.BLUE, "No repositories selected to assign to {} team".format(team))

assignResult = assignReposToTeams(repoAssignment, githubAccessToken)