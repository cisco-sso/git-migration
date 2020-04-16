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
        self.bitbucketAPI, self.githubAPI = utils.ReadUtils.getAPILinks()
        self.log = utils.LogUtils.getLogger(os.path.basename(__file__))

    # Returns list of all projects on BitBucket
    def getBitbucketProjects(self, bitbucketAccessToken):
        projectNames = []
        isLastPage = False
        start = 0
        # Get list of projects
        self.log.info("Fetching project list")
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
        self.log.info("Fetching repository list for {}".format(projectKey), projectKey=projectKey)
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

    # Checks if the repositories exist on GitHub Enterprise and returns the ones that do
    # Returns list of repos with their BitBucket and GitHub repo links
    def existsOnGithub(self, projectKey, repoNames, bitbucketAccessToken, githubAccessToken):
        reposOnGithub = []
        # Check if same repository already exists on GitHub
        for repoName in repoNames[:10]:
            githubRepoCheckLink = self.githubAPI+"/repos/{}/{}".format("***REMOVED***", repoName)
            githubRepoCheck = requests.get(
                githubRepoCheckLink,
                headers={"Authorization": "Bearer {}".format(githubAccessToken)}
            )
            # Repository with a similar name already exists on GitHub
            if(githubRepoCheck.status_code!=404):
                self.log.info("Repo {} - Exists on GitHub".format(repoName), repoName=repoName)
                
                # Add GitHub clone link
                repoDetails = json.loads(githubRepoCheck.text)
                repoInfo = {
                    "name": repoName,
                    "githubLink": repoDetails['clone_url']
                }

                # Get and add BitBucket clone link
                bitbucketRepoResponse = requests.get(
                    self.bitbucketAPI+"/projects/{}/repos/{}".format(projectKey, repoName),
                    headers={"Authorization": "Bearer {}".format(bitbucketAccessToken)}
                )
                bitbucketRepoResponse = json.loads(bitbucketRepoResponse.text)
                link = list(filter(utils.MiscUtils.isHTTP, bitbucketRepoResponse["links"]["clone"]))
                repoInfo["bitbucketLink"] = link[0]["href"]

                reposOnGithub.append(repoInfo)
            else:
                self.log.warning("Repo {} -  Not on GitHub".format(repoName), repoName=repoName)
        return reposOnGithub

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
                    self.log.warning("Repo {} - Already exists on ***REMOVED*** org".format(repoName), repoName=repoName)
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
                    self.log.warning("Repo {} - Already exists on GHE account {}".format(repoName, githubAccountID), repoName=repoName, githubAccountID=githubAccountID)
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
                self.log.info("Repo {} - Accepted".format(repoName), repoName=repoName, pullRequests=pullRequests["size"])
                repoInfo["openPRs"] = pullRequests["size"]
                openPRs.append(repoInfo)
                continue

            # No PRs on Bitbucket and Repo doesn't already exist on GitHub
            self.log.info("Repo {} - Accepted".format(repoName))
            accepts.append(repoInfo)
        return accepts, openPRs, alreadyExisting

    # Migrate all given repos to given destination
    def migrateRepos(self, repositories, pushToOrg, bitbucketAccountID, bitbucketAccessToken, githubAccountID, githubAccessToken):
        # Make a temporary folder in CWD to clone repos from BitBucket
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        isDir = os.path.isdir("migration_temp")
        if(not isDir):
            self.log.debug("Created directory migration_temp")
            os.mkdir("migration_temp")
        os.chdir("migration_temp")

        for repo in repositories:
            bitbucketName = repo["name"]
            bitbucketLink = repo["cloneLink"]
            self.log.info("Migrating repo {}".format(bitbucketName))
            # Remove any existing folder with same name
            if(os.path.isdir(bitbucketName)):
                try:
                    shutil.rmtree(bitbucketName, onerror=utils.FileUtils.remove_readonly)
                except:
                    self.log.warn("Deleting {} in migration_temp failed. Skipping repo.".format(bitbucketName), repoName=bitbucketName)
                    continue
            # Bare clone the repository
            self.log.debug("Bare cloning repo {}".format(bitbucketName), repoName=bitbucketName)
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
                self.log.debug("New repo {} created on GitHub ***REMOVED***".format(bitbucketName), repoName=bitbucketName)
            else:
                # Create new repo of same name on GitHub Account
                gitResponse = requests.post(
                    self.githubAPI+"/user/repos",
                    data=json.dumps(requestPayload),
                    headers={"Authorization": "Bearer {}".format(githubAccessToken)}
                )
                self.log.debug("New repo {} created on GitHub {} account".format(bitbucketName, githubAccountID), repoName=bitbucketName, githubAccountID=githubAccountID)

            # Mirror the codebase to remote GitHub URL
            githubRepoData = json.loads(gitResponse.text)
            githubCloneLink = githubRepoData["clone_url"]
            githubCloneLinkDomain = githubCloneLink.split("//")[1]
            self.log.debug("Mirroring repo {} on GitHub".format(bitbucketName))
            os.system("git push --mirror https://{}:{}@{}".format(githubAccountID, githubAccessToken, githubCloneLinkDomain))

            # Remove local clone of repo
            os.chdir("..")
            try:
                shutil.rmtree("{}.git".format(bitbucketName), onerror=utils.FileUtils.remove_readonly)
                self.log.debug("Deleted {} bare clone".format(bitbucketName), repoName=bitbucketName)
            except:
                self.log.warning("Deleting {} bare clone failed".format(bitbucketName), repoName=bitbucketName)
                continue

        # Remove temporary folder
        if(not isDir):
            os.chdir("..")
            try:
                shutil.rmtree("migration_temp", onerror=utils.FileUtils.remove_readonly)
                self.log.debug("Deleted migration_temp directory")
            except:
                self.log.warning("Deleting migration_temp directory failed")
        return True

    # Syncs the BitBucket repository with the GitHub repository with just the deltas
    def syncDelta(self, repositories, bitbucketAccountID, bitbucketAccessToken, githubAccountID, githubAccessToken):
        # Make a temporary folder in CWD to clone repos from BitBucket
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        isDir = os.path.isdir("syncDirectory")
        if(not isDir):
            self.log.debug("Created directory syncDirectory")
            os.mkdir("syncDirectory")
        os.chdir("syncDirectory")

        for repo in repositories:
            repoName = repo['name']
            githubLink = repo['githubLink']
            bitbucketLink = repo['bitbucketLink']

            self.log.info("Syncing repo {}".format(repoName), repoName=repoName)
            # Clone the repository from BitBucket
            if(not os.path.isdir(repoName)):
                bitbucketLinkDomain = bitbucketLink.split("//")[1]
                self.log.debug("Cloning repo {}".format(repoName), repoName=repoName)
                os.system("git clone https://{}:{}@{}".format(bitbucketAccountID, bitbucketAccessToken, bitbucketLinkDomain))
            os.chdir(repoName)
            # Make local tracking branches for all remote branches on origin (bitbucket)
            self.log.debug("Setting up new tracking branches and pulling {}".format(repoName), repoName=repoName)
            os.system("for remote in `git branch -r`; do git branch --track ${remote#origin/} $remote; done")
            os.system("git pull --all")
            # Change origin to point to GitHub
            self.log.debug("Setting origin for {} to github".format(repoName), repoName=repoName, githubLink=githubLink)
            os.system("git remote set-url origin {}".format(githubLink))
            # First push all the tags including new ones that might be created
            self.log.debug("Pushing all tags for {}".format(repoName), repoName=repoName)
            os.system("git push --tags")
            # Push all branches including new ones that might be created
            self.log.debug("Pushing all branches for {}".format(repoName), repoName=repoName)
            os.system("git push --all")
            self.log("{} synced".format(repoName), repoName=repoName)
            utils.LogUtils.logLight(color.Fore.GREEN, "{} synced".format(repoName))

    # Get list of all teams from GHE ***REMOVED*** org
    def getTeamsInfo(self, githubAccessToken):
        self.log.debug("Fetching teams list from GitHub")
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
            self.log.info("Assigning repos to {} team".format(team), teamName=team)

            # Get Team's ID
            self.log.debug("Fetching Team ID", teamName=team)
            teamInfo = requests.get(
                self.githubAPI+"/orgs/***REMOVED***/teams/{}".format(team),
                headers={"Authorization": "Bearer {}".format(githubAccessToken)}
            )
            teamInfo = json.loads(teamInfo.text)
            teamID = teamInfo['id']

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
                    self.log.warning("Failed to assign {} repo to {} team".format(repo, team), repoName=repo, teamName=team, errorCode=assignResponse.status_code)
                else:
                    successCount += 1
                    self.log.info("Assigned {} repo to {} team".format(repo, team), repoName=repo, teamName=team)
            assignResult[team] = {
                'success': successCount,
                'failure': failureCount
            }
            self.log.info("Assigned {} repos to {} team".format(successCount, team), teamName=team, successCount=successCount)
            self.log.warning("Failed to assign {} repos to {} team".format(failureCount, team), teamName=team, failureCount=failureCount)
        return assignResult