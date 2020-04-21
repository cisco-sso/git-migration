# Library imports
import questionary
import os

# Custom imports
from app import utils, credOperations, repoOperations


def startSession(bitbucketAccountID, bitbucketAccessToken, githubAccountID, githubAccessToken, bitbucketAPI, githubAPI, consoleLogLevel, consoleLogNormal, fileLogLevel):
    # Objects for operations related to credentials and repository actions
    credOps = credOperations.credOps(bitbucketAPI, githubAPI, consoleLogLevel, consoleLogNormal, fileLogLevel)
    repoOps = repoOperations.repoOps(bitbucketAPI, githubAPI, consoleLogLevel, consoleLogNormal, fileLogLevel)
    log = utils.LogUtils.getLogger(os.path.basename(__file__), consoleLogLevel, consoleLogNormal, fileLogLevel)
    targetOrg = utils.ReadUtils.getTargetOrg()
    # Ask for migration destination
    pushAnswer = questionary.select("Migrate repositories to?",
                                    choices=["GitHub {} org".format(targetOrg), "Personal Github Account"]).ask()
    pushToOrg = pushAnswer == "GitHub {} org".format(targetOrg)

    # Check if credentials are right and can push to the chosen destination
    githubPushCheck = credOps.checkGithubPushCreds(pushToOrg, githubAccountID, githubAccessToken)
    githubPullCheck = credOps.checkGithubPullCreds(githubAccessToken)
    if (not (githubPushCheck and githubPullCheck)):
        exit(0)

    # Get list of projects
    projectNames = repoOps.getBitbucketProjects(bitbucketAccessToken)

    # Ask which project to migrate
    projectAnswer = questionary.select('Which project to migrate? (Enter to select)', choices=projectNames).ask()

    # Check access to BitBucket project and check GitHub credentials
    [projectName, projectKey] = projectAnswer.split(":")
    bitbucketPullCheck = credOps.checkBitbucketPullCreds(projectKey, bitbucketAccessToken)
    if (not bitbucketPullCheck):
        exit(1)

    # Get list of all repos
    repoNames = repoOps.getBitbucketRepos(projectKey, bitbucketAccessToken)
    repoList = [{'name': "{}".format(repo)} for repo in repoNames]

    # Ask which repos to migrate
    repoAnswers = questionary.checkbox("Which repos to migrate from {}:{}?".format(projectName, projectKey),
                                       choices=repoList).ask()

    # Process repos to obtain details
    processedRepos, totalRepos, newRepos = repoOps.processRepos(projectKey, repoAnswers, pushToOrg,
                                                                bitbucketAccessToken, githubAccountID,
                                                                githubAccessToken)
    if (totalRepos == 0):
        log.debug("NO REPOSITORIES SYNCED OR MIGRATED")
        exit(0)
    # Used later for team assignments
    migrationRepos = [{'name': repo['name']} for repo in processedRepos if ('githubLink' not in repo)]

    # Confirm to proceed with syncing and migration
    confirmMigrate = questionary.confirm('Proceed with syncing {} and migrating {} repos?'.format(
        totalRepos - newRepos, newRepos)).ask()
    if (not confirmMigrate):
        log.debug("NO REPOSITORIES SYNCED OR MIGRATED")
        exit(0)

    # Sync existing repos and migrate over the new repos
    repoOps.syncRepos(pushToOrg, processedRepos, bitbucketAccountID, bitbucketAccessToken, githubAccountID,
                      githubAccessToken)
    log.debug("Successful - {} repos synced and {} repositories migrated to GitHub".format(
        totalRepos - newRepos, newRepos),
             totalRepos=totalRepos,
             newRepos=newRepos)

    # --------- TEAM ASSIGNMENT ---------
    if (not pushToOrg):
        exit(0)
    confirmAssignToTeam = questionary.confirm(
        'Do you want to assign some of the migrated repos to different teams?').ask()
    if (not confirmAssignToTeam):
        log.debug("None of the {} migrated repositories assigned to any teams".format(newRepos), newRepos=newRepos)
        exit(0)

    # Fetch list of existing teams on github
    teamsInfoList = repoOps.getTeamsInfo(githubAccessToken)
    teamsChecklist = [{'name': team['slug']} for team in teamsInfoList]

    # Ask which teams to assign repos to
    selectedTeams = questionary.checkbox('Select the teams to which you want to assign the repos',
                                         choices=teamsChecklist).ask()

    # print(json.dumps())
    # Get all repos that were newly created and migrated
    # allMigratedRepos = [ {'name': repo['name']} for repo in processedRepos if ('githubLink' not in repo) ]

    # print(allMigratedRepos)
    # Ask which repos to assign to which team
    repoAssignment = {}
    for team in selectedTeams:
        reposForTeams = questionary.checkbox('Select the repos to assign to {} team'.format(team),
                                             choices=migrationRepos).ask()
        if (len(reposForTeams) != 0):
            repoAssignment[team] = reposForTeams
        else:
            log.debug("No repositories selected to assign to {} team".format(team), teamName=team)

    # Assign the repos to selected teams
    repoOps.assignReposToTeams(repoAssignment, githubAccessToken)
