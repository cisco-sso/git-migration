# Library imports
import PyInquirer as inquirer
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

# To enable colored printing on Windows as well
color.init()

# Get required credentials from JSON file
bitbucketAccountID, bitbucketAccessToken, githubAccountID, githubAccessToken = credOps.getCredentials()

# Ask for migration destination
pushQuestion = [
    {
        'type': 'list',
        'name': 'pushDestination',
        'message': "Migrate repositories to?",
        'choices': ["GitHub CX Engineering Org", "Personal Github Account"]
    }
]
pushAnswer = inquirer.prompt(pushQuestion)
pushToOrg = pushAnswer["pushDestination"] == "GitHub CX Engineering Org"

# Check if credentials are right to push to the chosen destination
pushCheckPassed = credOps.checkCredsForPush(pushToOrg, githubAccountID, githubAccessToken)
if (not pushCheckPassed):
    exit(0)

# Get list of projects
utils.LogUtils.logLight(color.Fore.BLUE, "Getting list of projects...\n")
projectNames = repoOps.getBitbucketProjects(bitbucketAccessToken)

# Ask which project to migrate
projectQuestion = [
    {
        'type': 'list',
        'name': 'project',
        'message': 'Which project to migrate? (Enter to select)',
        'choices': projectNames
    }
]
projectAnswer = inquirer.prompt(projectQuestion)

# Check access to BitBucket project and check GitHub credentials
[projectName, projectKey] = projectAnswer["project"].split(":")
if(not credOps.checkCredentials(projectKey, bitbucketAccessToken, githubAccessToken)):
    exit(1)

# Get list of all repos
utils.LogUtils.logLight(color.Fore.BLUE, "Getting list of repositories...\n")
repoNames = repoOps.getBitbucketRepos(projectKey, bitbucketAccessToken)
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
repoAnswers = inquirer.prompt(reposQuestion)

# Process repos to check for Open PRs or pre-existing repos on GitHub with same name
accepts, openPRs, alreadyExisting = repoOps.processBitbucketRepos(repoAnswers["repos"], projectKey, pushToOrg, bitbucketAccessToken, githubAccountID, githubAccessToken)
acceptedNumber = len(accepts)
openPRsNumber = len(openPRs)
alreadyExistingNumber = len(alreadyExisting)

print(
    color.Style.BRIGHT +
    color.Fore.GREEN + "Accepted: {} ( {} with open PRs)\t".format(acceptedNumber, openPRsNumber) +
    color.Fore.RED + "Rejected: {} ( already existing on GitHub )".format(alreadyExistingNumber) + 
    color.Style.RESET_ALL
)

# utils.LogUtils.logBright(color.Fore.BLUE, "Recommended to close all PRs before migrating a repo.")

if(acceptedNumber+openPRsNumber==0):
    utils.LogUtils.logBright(color.Fore.BLUE, "No repositories migrated")
    exit(0)

confirmMigrateQuestion = [
    {
        'type': 'confirm',
        'name': 'confirmMigrate',
        'message': 'Migrate all accepted repositories? ( {} with open PRs on BitBucket )'.format(openPRsNumber),
        'default': True
    }
]
confirmMigrate = inquirer.prompt(confirmMigrateQuestion)['confirmMigrate']

if (not confirmMigrate):
    utils.LogUtils.logBright(color.Fore.BLUE, "No repositories migrated")
    exit(0)

# Migrate repositories
repositories = accepts + openPRs
reposNumber = len(repositories)

utils.LogUtils.logLight(color.Fore.BLUE, "Migrating {} repositories...".format(reposNumber))
repoOps.migrateRepos(repositories, pushToOrg, bitbucketAccountID, bitbucketAccessToken, githubAccountID, githubAccessToken)

utils.LogUtils.logBright(color.Fore.GREEN, "Migration successfully completed - {} repositories copied to GitHub".format(reposNumber))

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
confirmAssignToTeam = inquirer.prompt(confirmAssignToTeamQuestion)['confirmAssignToTeam']

if (not confirmAssignToTeam):
    utils.LogUtils.logLight(color.Fore.BLUE, "None of the {} migrated repositories assigned to any teams".format(reposNumber))
    exit(0)

teamsInfoList = repoOps.getTeamsInfo(githubAccessToken)
teamsChecklist = [ {'name':team['slug']} for team in teamsInfoList]

selectTeamsQuestion = [
    {
        'type': 'checkbox',
        'name': 'selectTeams',
        'message': 'Select the teams to which you want to assign the repos',
        'choices': teamsChecklist
    }
]
selectedTeams = inquirer.prompt(selectTeamsQuestion)['selectTeams']

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
    reposForTeams = inquirer.prompt(reposForTeamQuestion)['reposForTeams']
    if (len(reposForTeams)!=0):
        repoAssignment[team] = reposForTeams
    else:
        utils.LogUtils.logLight(color.Fore.BLUE, "No repositories selected to assign to {} team".format(team))

assignResult = repoOps.assignReposToTeams(repoAssignment, githubAccessToken)