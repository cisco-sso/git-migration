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
from repoOperations import getBitbucketProjects, getBitbucketRepos, processRepos, migrateRepos, assignReposToTeams

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
        'message': "Which repos to migrate from {}:{}?".format(projectName, projectKey),
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

if (not pushToOrg):
    exit(0)

confirmAssignToTeamQuestion = [
    {
        'type': 'confirm',
        'name':  'confirmAssignToTeam',
        'message': 'Do you want to assign some of the migrated repos to different teams?',
        'default': True
    }
]
confirmAssignToTeam = prompt(confirmAssignToTeamQuestion)['confirmAssignToTeam']

if (not confirmAssignToTeam):
    logLight(Fore.BLUE, "None of the {} migrated repositories assigned to any teams".format(55))
    exit(0)

teamsList = requests.get(
    "https://***REMOVED***/api/v3/orgs/***REMOVED***/teams",
    headers={"Authorization": "Bearer {}".format(githubAccessToken)}
)
teamsList = json.loads(teamsList.text)
teamsList = [ {'name':team['slug']} for team in teamsList]

selectTeamsQuestion = [
    {
        'type': 'checkbox',
        'name': 'selectTeams',
        'message': 'Select the teams to which you want to assign the repos',
        'choices': teamsList
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


