# Library imports
import colorama as color
import questionary

# Custom imports
from app import utils, credOperations, repoOperations


def startSession(bitbucketAccountID, bitbucketAccessToken, githubAccountID, githubAccessToken, bitbucketAPI, githubAPI):
    # Objects for operations related to credentials and repository actions
    credOps = credOperations.credOps(bitbucketAPI, githubAPI)
    repoOps = repoOperations.repoOps(bitbucketAPI, githubAPI)

    # Ask for migration destination
    pushAnswer = questionary.select("Migrate repositories to?",
                                    choices=["GitHub CX Engineering Org", "Personal Github Account"]).ask()
    pushToOrg = pushAnswer == "GitHub CX Engineering Org"

    # Check if credentials are right to push to the chosen destination
    pushCheckPassed = credOps.checkCredsForPush(pushToOrg, githubAccountID, githubAccessToken)
    if (not pushCheckPassed):
        exit(0)

    # Get list of projects
    utils.LogUtils.logLight(color.Fore.BLUE, "Getting list of projects...\n")
    projectNames = repoOps.getBitbucketProjects(bitbucketAccessToken)

    # Ask which project to migrate
    projectAnswer = questionary.select('Which project to migrate? (Enter to select)', choices=projectNames).ask()

    # Check access to BitBucket project and check GitHub credentials
    [projectName, projectKey] = projectAnswer.split(":")
    if (not credOps.checkCredentials(projectKey, bitbucketAccessToken, githubAccessToken)):
        exit(1)

    # Get list of all repos
    utils.LogUtils.logLight(color.Fore.BLUE, "Getting list of repositories...\n")
    repoNames = repoOps.getBitbucketRepos(projectKey, bitbucketAccessToken)
    repoList = [{'name': "{}".format(repo)} for repo in repoNames]

    # Ask which repos to migrate
    repoAnswers = questionary.checkbox("Which repos to migrate from {}:{}?".format(projectName, projectKey),
                                       choices=repoList).ask()

    # Process repos to check for Open PRs or pre-existing repos on GitHub with same name
    accepts, openPRs, alreadyExisting = repoOps.processBitbucketRepos(repoAnswers, projectKey, pushToOrg,
                                                                      bitbucketAccessToken, githubAccountID,
                                                                      githubAccessToken)
    acceptedNumber = len(accepts)
    openPRsNumber = len(openPRs)
    alreadyExistingNumber = len(alreadyExisting)

    print(color.Style.BRIGHT + color.Fore.GREEN +
          "Accepted: {} ( {} with open PRs)\t".format(acceptedNumber, openPRsNumber) + color.Fore.RED +
          "Rejected: {} ( already existing on GitHub )".format(alreadyExistingNumber) + color.Style.RESET_ALL)

    # utils.LogUtils.logBright(color.Fore.BLUE, "Recommended to close all PRs before migrating a repo.")

    if (acceptedNumber + openPRsNumber == 0):
        utils.LogUtils.logBright(color.Fore.BLUE, "No repositories migrated")
        exit(0)

    confirmMigrate = questionary.confirm(
        'Migrate all accepted repositories? ( {} with open PRs on BitBucket )'.format(openPRsNumber)).ask()

    if (not confirmMigrate):
        utils.LogUtils.logBright(color.Fore.BLUE, "No repositories migrated")
        exit(0)

    # Migrate repositories
    repositories = accepts + openPRs
    reposNumber = len(repositories)

    utils.LogUtils.logLight(color.Fore.BLUE, "Migrating {} repositories...".format(reposNumber))
    repoOps.migrateRepos(repositories, pushToOrg, bitbucketAccountID, bitbucketAccessToken, githubAccountID,
                         githubAccessToken)

    utils.LogUtils.logBright(color.Fore.GREEN,
                             "Migration successfully completed - {} repositories copied to GitHub".format(reposNumber))

    if (not pushToOrg):
        exit(0)

    confirmAssignToTeam = questionary.confirm(
        'Do you want to assign some of the migrated repos to different teams?').ask()

    if (not confirmAssignToTeam):
        utils.LogUtils.logLight(color.Fore.BLUE,
                                "None of the {} migrated repositories assigned to any teams".format(reposNumber))
        exit(0)

    teamsInfoList = repoOps.getTeamsInfo(githubAccessToken)
    teamsChecklist = [{'name': team['slug']} for team in teamsInfoList]

    selectedTeams = questionary.checkbox('Select the teams to which you want to assign the repos',
                                         choices=teamsChecklist)
    allMigratedRepos = [{'name': repo['name']} for repo in repositories]

    repoAssignment = {}

    for team in selectedTeams:
        reposForTeams = questionary.checkbox('Select the repos to assign to {} team'.format(team),
                                             choices=allMigratedRepos)
        if (len(reposForTeams) != 0):
            repoAssignment[team] = reposForTeams
        else:
            utils.LogUtils.logLight(color.Fore.BLUE, "No repositories selected to assign to {} team".format(team))

    repoOps.assignReposToTeams(repoAssignment, githubAccessToken)
