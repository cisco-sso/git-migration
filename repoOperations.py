# Library imports
import json
import os
import shutil
import requests
import colorama as color

# Custom imports
import utils

class repoOps:
    def __init__(self):
        self.bitbucketAPI, self.githubAPI = utils.APIUtils.getAPILinks()

    # Returns list of all projects on BitBucket
    def getBitbucketProjects(self, bitbucketAccessToken):
        projectNames = []
        isLastPage = False
        start = 0
        # Get list of projects
        while(not isLastPage):
            projectsUrl = self.bitbucketAPI+"/projects/?start={}".format(start)
            projects = requests.get(
                projectsUrl,
                headers={"Authorization": "Bearer {}".format(bitbucketAccessToken)}
            )
            projects = json.loads(projects.text)

            # Check if last page
            isLastPage = projects["isLastPage"]
            if(not isLastPage):
                start = projects["nextPageStart"]

            # Populate the project names
            projectNames += [ "{}:{}".format(project["name"], project["key"]) for project in projects["values"]]
        return projectNames

    # Return all repositories from a given project on BitBucket
    def getBitbucketRepos(self, projectKey, bitbucketAccessToken):
        repoNames = []
        isLastPage = False
        start = 0
        # Get list of all repos
        while(not isLastPage):
            # Get list of repos under the mentioned project on BitBucket
            projectReposLink = self.bitbucketAPI+"/projects/{}/repos?start={}".format(projectKey, start)
            projectRepos = requests.get(
                projectReposLink,
                headers={"Authorization": "Bearer {}".format(bitbucketAccessToken)}
            )
            projectRepos = json.loads(projectRepos.text)
            
            # Check if last page
            isLastPage = projectRepos["isLastPage"]
            if(not isLastPage):
                start = projectRepos["nextPageStart"]

            # Populate the project names
            # repoNames += [ { 'name':"{}".format(repo["name"]) } for repo in projectRepos["values"]]
            repoNames += [ "{}".format(repo["name"]) for repo in projectRepos["values"]]
        return repoNames

    # Check metadata of given repositories and reject repos with open PRs and ones that already exist on mentioned destination
    # Returns list of accepted and rejected repos
    def processBitbucketRepos(self, repositories, projectKey, pushToOrg, bitbucketAccessToken, githubAccountID, githubAccessToken):
        # Repo metadata added to these lists
        accepts = []
        openPRs = []
        alreadyExisting = []
        # Preprocess repository data
        for repoName in repositories:
            # Get all info on a repo
            repoInfo = {
                "openPRs": None,
                "alreadyExisting": None
            }
            repoInfo["name"] = repoName
            repoResponse = requests.get(
                self.bitbucketAPI+"/projects/{}/repos/{}".format(projectKey, repoName),
                headers={"Authorization": "Bearer {}".format(bitbucketAccessToken)}
            )
            repoResponse = json.loads(repoResponse.text)
            if("description" in repoResponse.keys()):
                repoInfo["description"] = repoResponse["description"]
            # else:
            #     repoInfo["description"] = None
            link = list(filter(utils.MiscUtils.isHTTP, repoResponse["links"]["clone"]))
            repoInfo["cloneLink"] = link[0]["href"]


            if (pushToOrg):
                # Check if same repository already exists on GitHub ***REMOVED*** Org
                githubOrgRepoCheckLink = self.githubAPI+"/repos/***REMOVED***/{}".format(repoName)
                githubOrgRepoCheck = requests.get(
                    githubOrgRepoCheckLink,
                    headers={"Authorization": "Bearer {}".format(githubAccessToken)}
                )
                # Repository with a similar name already exists on GitHub
                if(githubOrgRepoCheck.status_code!=404):
                    utils.LogUtils.logLight(color.Fore.RED, "Repo {}: Rejected - {} already exists on the ***REMOVED*** Organization".format(repoName, repoName))
                    repoInfo["alreadyExisting"] = True
                    alreadyExisting.append(repoInfo)
                    continue
            else:
                # Check if same repository already exists on GitHub
                githubRepoCheckLink = self.githubAPI+"/repos/{}/{}".format(githubAccountID, repoName)
                githubRepoCheck = requests.get(
                    githubRepoCheckLink,
                    headers={"Authorization": "Bearer {}".format(githubAccessToken)}
                )
                # Repository with a similar name already exists on GitHub
                if(githubRepoCheck.status_code!=404):
                    utils.LogUtils.logLight(color.Fore.RED, "Repo {}: Rejected - {} already exists on GitHub Account".format(repoName, repoName))
                    repoInfo["alreadyExisting"] = True
                    alreadyExisting.append(repoInfo)
                    continue

            # Check if repository has open PRs on BitBucket
            repoPRLink = self.bitbucketAPI+"/projects/{}/repos/{}/pull-requests/".format(projectKey, repoName)
            pullRequests = requests.get(
                repoPRLink,
                headers={"Authorization": "Bearer {}".format(bitbucketAccessToken)}
            )
            pullRequests = json.loads(pullRequests.text)
            # Active pull requests on Bitbucket
            if(pullRequests["size"] != 0):
                utils.LogUtils.logLight(color.Fore.GREEN, "Repo {}: Accepted - {} active PRs".format(repoName, pullRequests["size"]))
                repoInfo["openPRs"] = pullRequests["size"]
                openPRs.append(repoInfo)
                continue

            # No PRs on Bitbucket and Repo doesn't already exist on GitHub
            utils.LogUtils.logLight(color.Fore.GREEN, "Repo {}: Accepted".format(repoName))
            accepts.append(repoInfo)
        return accepts, openPRs, alreadyExisting

    # Migrate all given repos to given destination
    def migrateRepos(self, repositories, pushToOrg, bitbucketAccountID, bitbucketAccessToken, githubAccountID, githubAccessToken):
        # Make a temporary folder in CWD to clone repos from BitBucket
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        isDir = os.path.isdir("migration_temp")
        if(not isDir):
            os.mkdir("migration_temp")
        os.chdir("migration_temp")

        for repo in repositories:
            bitbucketName = repo["name"]
            bitbucketLink = repo["cloneLink"]

            # Remove any existing folder with same name
            if(os.path.isdir(bitbucketName)):
                try:
                    shutil.rmtree(bitbucketName, onerror=utils.FileUtils.remove_readonly)
                except:
                    utils.LogUtils.logLight(color.Fore.BLUE, "Unable to delete pre-existing folder with same name: Retry after deleting it manually.")
                    continue
            # Bare clone the repository
            bitbucketLinkDomain = bitbucketLink.split("//")[1]
            os.system("git clone --bare https://{}:{}@{}".format(bitbucketAccountID, bitbucketAccessToken, bitbucketLinkDomain))
            os.chdir("{}.git".format(bitbucketName))

            # API call to make new remote repo on GitHub
            requestPayload = {
                "name": utils.StringUtils.remove_control_characters(bitbucketName),
                "private": True
            }
            if("description" in repo.keys()):
                requestPayload["description"] = utils.StringUtils.remove_control_characters(repo["description"])
            
            if(pushToOrg):
                # Create new repo of same name on GitHub ***REMOVED*** Org
                gitResponse = requests.post(
                    self.githubAPI+"/orgs/***REMOVED***/repos",
                    data=json.dumps(requestPayload),
                    headers={"Authorization": "Bearer {}".format(githubAccessToken)}
                )
            else:
                # Create new repo of same name on GitHub Account
                gitResponse = requests.post(
                    self.githubAPI+"/user/repos",
                    data=json.dumps(requestPayload),
                    headers={"Authorization": "Bearer {}".format(githubAccessToken)}
                )

            # Mirror the codebase to remote GitHub URL
            githubRepoData = json.loads(gitResponse.text)
            githubCloneLink = githubRepoData["clone_url"]
            githubCloneLinkDomain = githubCloneLink.split("//")[1]
            os.system("git push --mirror https://{}:{}@{}".format(githubAccountID, githubAccessToken, githubCloneLinkDomain))

            # Remove local clone of repo
            os.chdir("..")
            try:
                shutil.rmtree("{}.git".format(bitbucketName), onerror=utils.FileUtils.remove_readonly)
            except:
                utils.LogUtils.logLight(color.Fore.BLUE, "Unable to delete the locally cloned repo: Try doing it manually.")
                continue

        # Remove temporary folder
        if(not isDir):
            os.chdir("..")
            try:
                shutil.rmtree("migration_temp", onerror=utils.FileUtils.remove_readonly)
            except:
                utils.LogUtils.logLight(color.Fore.BLUE, "Unable to delete the migration_temp folder: Try doing it manually.")
        return True

    # Get list of all teams from GHE ***REMOVED*** org
    def getTeamsInfo(self, githubAccessToken):
        teamsInfoList = requests.get(
            self.githubAPI+"/orgs/***REMOVED***/teams",
            headers={"Authorization": "Bearer {}".format(githubAccessToken)}
        )
        teamsInfoList = json.loads(teamsInfoList.text)
        return teamsInfoList

    # Assign the selected repos to selected teams in the organization
    def assignReposToTeams(self, repoAssignment, githubAccessToken):
        adminPermissions = { 'permission': 'admin' }
        assignResult = {}
        for team, repos in repoAssignment.items(): # key, value :: team, repos
            utils.LogUtils.logLight(color.Fore.YELLOW, "Assigning repos to {} team".format(team))

            # Get Team's ID
            teamInfo = requests.get(
                self.githubAPI+"/orgs/***REMOVED***/teams/{}".format(team),
                headers={"Authorization": "Bearer {}".format(githubAccessToken)}
            )
            teamInfo = json.loads(teamInfo.text)
            teamID = teamInfo['id']
            # print("obtained", team, teamID)

            successCount = 0
            failureCount = 0
            for repo in repos:
                # Assign repo to team
                assignResponse = requests.put(
                    self.githubAPI+"/teams/{}/repos/***REMOVED***/{}".format(teamID, repo),
                    data=json.dumps(adminPermissions),
                    headers={"Authorization": "Bearer {}".format(githubAccessToken)}
                )
                if(assignResponse.status_code != 204):
                    failureCount += 1
                    utils.LogUtils.logLight(color.Fore.RED, "Failed to assign {} repo to {} team: Error code {}".format(repo, team, assignResponse.status_code))
                else:
                    successCount += 1
                    utils.LogUtils.logLight(color.Fore.GREEN, "Successfully assigned {} repo to {} team".format(repo, team))
            assignResult[team] = {
                'success': successCount,
                'failure': failureCount
            }
            utils.LogUtils.logBright(color.Fore.BLUE, "\nAssigned repos to {} team:".format(team))
            print(
                color.Style.BRIGHT + color.Fore.GREEN + "Success: {}\t".format(successCount) + color.Fore.RED + "Failure: {} (Check if repo exists on ***REMOVED*** org, try assigning manually)\n".format(failureCount) + color.Style.RESET_ALL
            )
        return assignResult