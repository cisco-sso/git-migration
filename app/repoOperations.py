# Library imports
import json
import os
import requests
import colorama as color
import pathlib

# Custom imports
from app import utils


class repoOps:
    def __init__(self, bitbucketAPI, githubAPI):
        self.bitbucketAPI = bitbucketAPI
        self.githubAPI = githubAPI
        self.log = utils.LogUtils.getLogger(os.path.basename(__file__))
        self.targetOrg = utils.ReadUtils.getTargetOrg()

    # Returns list of all projects on BitBucket
    def getBitbucketProjects(self, bitbucketAccessToken):
        projectNames = []
        isLastPage = False
        start = 0
        # Get list of projects
        self.log.info("Fetching project list")
        while (not isLastPage):
            projectsUrl = self.bitbucketAPI + "/projects/?start={}".format(start)
            projects = requests.get(projectsUrl, headers={"Authorization": "Bearer {}".format(bitbucketAccessToken)})
            projects = json.loads(projects.text)

            # Check if last page
            isLastPage = projects["isLastPage"]
            if (not isLastPage):
                start = projects["nextPageStart"]

            # Populate the project names
            projectNames += ["{}:{}".format(project["name"], project["key"]) for project in projects["values"]]
        return projectNames

    # Return all repositories from a given project on BitBucket
    def getBitbucketRepos(self, projectKey, bitbucketAccessToken):
        repoNames = []
        isLastPage = False
        start = 0
        # Get list of all repos
        self.log.info("Fetching repository list for {}".format(projectKey), projectKey=projectKey)
        while (not isLastPage):
            # Get list of repos under the mentioned project on BitBucket
            projectReposLink = self.bitbucketAPI + "/projects/{}/repos?start={}".format(projectKey, start)
            projectRepos = requests.get(projectReposLink,
                                        headers={"Authorization": "Bearer {}".format(bitbucketAccessToken)})
            projectRepos = json.loads(projectRepos.text)

            # Check if last page
            isLastPage = projectRepos["isLastPage"]
            if (not isLastPage):
                start = projectRepos["nextPageStart"]

            # Populate the project names
            # repoNames += [ { 'name':"{}".format(repo["name"]) } for repo in projectRepos["values"]]
            repoNames += [repo["name"] for repo in projectRepos["values"]]
        return repoNames

    # Process the list of repositories for a project and return metadata and repository links
    def processRepos(self, projectKey, repositories, pushToOrg, bitbucketAccessToken, githubAccountID,
                     githubAccessToken):
        processedRepos = []
        newRepos = 0
        self.log.info("Processing repos from project {}".format(projectKey))

        for repoName in repositories:
            # Add name
            repoInfo = {"name": repoName}
            bitbucketRepoResponse = requests.get(self.bitbucketAPI +
                                                 "/projects/{}/repos/{}".format(projectKey, repoName),
                                                 headers={"Authorization": "Bearer {}".format(bitbucketAccessToken)})
            bitbucketRepoResponse = json.loads(bitbucketRepoResponse.text)
            # Add description
            if ("description" in bitbucketRepoResponse):
                repoInfo["description"] = bitbucketRepoResponse["description"]
            # Add BitBucket Link
            link = list(filter(utils.MiscUtils.isHTTP, bitbucketRepoResponse["links"]["clone"]))
            repoInfo["bitbucketLink"] = link[0]["href"]
            self.log.debug("Added {} repository details from BitBucket".format(repoName))

            # Add GitHub Link
            if (pushToOrg):
                # Check if same repository already exists on GitHub target org
                # TODO(***REMOVED***): Must parameterize the target org on Github
                #   Place in Config file, instead of hard-coding here
                githubOrgRepoCheckLink = self.githubAPI + "/repos/{}/{}".format(self.targetOrg, repoName)
                githubOrgRepoCheck = requests.get(githubOrgRepoCheckLink,
                                                  headers={"Authorization": "Bearer {}".format(githubAccessToken)})
                # Repository with a similar name already exists on GitHub
                if (githubOrgRepoCheck.status_code != 404):
                    githubOrgRepoCheck = json.loads(githubOrgRepoCheck.text)
                    self.log.info("Repo {} - Exists on {} org".format(repoName, self.targetOrg), repoName=repoName)
                    repoInfo["githubLink"] = githubOrgRepoCheck["clone_url"]
                else:
                    newRepos += 1
                    self.log.info("Repo {} - Doesn't exist on {} org".format(repoName, self.targetOrg), repoName=repoName)
            else:
                # Check if same repository already exists on GitHub
                githubRepoCheckLink = self.githubAPI + "/repos/{}/{}".format(githubAccountID, repoName)
                githubRepoCheck = requests.get(githubRepoCheckLink,
                                               headers={"Authorization": "Bearer {}".format(githubAccessToken)})
                # Repository with a similar name already exists on GitHub
                if (githubRepoCheck.status_code != 404):
                    githubRepoCheck = json.loads(githubRepoCheck.text)
                    self.log.info("Repo {} - Exists on GHE account {}".format(repoName, githubAccountID),
                                  repoName=repoName,
                                  githubAccountID=githubAccountID)
                    repoInfo["githubLink"] = githubRepoCheck["clone_url"]
                else:
                    newRepos += 1
                    self.log.info("Repo {} - Doesn't exist on GHE account".format(repoName), repoName=repoName)
            processedRepos.append(repoInfo)
        totalRepos = len(processedRepos)
        self.log.info("Syncing {} repositories, {} will be newly migrated to GitHub",
                      totalRepos=totalRepos,
                      newRepos=newRepos)
        return processedRepos, totalRepos, newRepos

    # Makes a new repo through API calls on either target org or GHE personal account and returns repo link
    def makeNewRepo(self, pushToOrg, repo, githubAccountID, githubAccessToken):
        # API call to make new remote repo on GitHub
        repoName = repo["name"]

        requestPayload = {"name": utils.StringUtils.remove_control_characters(repoName), "private": True}
        if ("description" in repo):
            requestPayload["description"] = utils.StringUtils.remove_control_characters(repo["description"])

        if (pushToOrg):
            # Create new repo of same name on GitHub target org
            gitResponse = requests.post(self.githubAPI + "/orgs/{}/repos".format(self.targetOrg),
                                        data=json.dumps(requestPayload),
                                        headers={"Authorization": "Bearer {}".format(githubAccessToken)})
            self.log.debug("New repo {} created on GitHub {}".format(repoName, self.targetOrg), repoName=repoName)
        else:
            # Create new repo of same name on GitHub Account
            gitResponse = requests.post(self.githubAPI + "/user/repos",
                                        data=json.dumps(requestPayload),
                                        headers={"Authorization": "Bearer {}".format(githubAccessToken)})
            self.log.debug("New repo {} created on GitHub {} account".format(repoName, githubAccountID),
                           repoName=repoName,
                           githubAccountID=githubAccountID)

        githubRepoData = json.loads(gitResponse.text)
        githubLink = githubRepoData["clone_url"]
        return githubLink

    # Recieves list of repos with metadata, BitBucker and GitHub repo links
    # Syncs the repos that already exist on GitHub, Migrates over repos that don't exist on GitHub
    def syncRepos(self, pushToOrg, repositories, bitbucketAccountID, bitbucketAccessToken, githubAccountID,
                  githubAccessToken):
        # Make a folder to clone repos from BitBucket
        curDirPath = pathlib.Path(__file__).parent
        os.chdir(str(curDirPath.parent))
        isDir = os.path.isdir("syncDirectory")
        if (not isDir):
            self.log.debug("Created directory syncDirectory")
            os.mkdir("syncDirectory")
        os.chdir("syncDirectory")

        for repo in repositories:
            repoName = repo['name']
            if ('githubLink' in repo):
                githubLink = repo['githubLink']
            else:
                repo['githubLink'] = self.makeNewRepo(pushToOrg, repo, githubAccountID, githubAccessToken)
                githubLink = repo['githubLink']
            bitbucketLink = repo['bitbucketLink']

            self.log.info("Syncing repo {}".format(repoName), repoName=repoName)
            # Clone the repository from BitBucket
            if (not os.path.isdir(repoName)):
                bitbucketLinkDomain = bitbucketLink.split("//")[1]
                self.log.debug("Cloning repo {}".format(repoName), repoName=repoName)
                os.system("git clone https://{}:{}@{}".format(bitbucketAccountID, bitbucketAccessToken,
                                                              bitbucketLinkDomain))
            os.chdir(repoName)
            # Make local tracking branches for all remote branches on origin (bitbucket)
            self.log.debug("Setting origin for {} to bitbucket".format(repoName),
                           repoName=repoName,
                           bitbucketLink=bitbucketLink)
            os.system("git remote set-url origin {}".format(bitbucketLink))
            self.log.debug("Setting up new tracking branches and pulling {}".format(repoName), repoName=repoName)
            os.system("for remote in `git branch -r`; do git branch --track ${remote#origin/} $remote; done")
            os.system("git pull --all")
            # Change origin to point to GitHub
            self.log.debug("Setting origin for {} to github".format(repoName), repoName=repoName, githubLink=githubLink)
            os.system("git remote set-url origin {}".format(githubLink))
            # First push all the tags including new ones that might be created
            githubLinkDomain = githubLink.split("//")[1]
            self.log.debug("Pushing all tags for {}".format(repoName), repoName=repoName)
            os.system("git push https://{}:{}@{} --tags".format(githubAccountID, githubAccessToken, githubLinkDomain))
            # Push all branches including new ones that might be created
            self.log.debug("Pushing all branches for {}".format(repoName), repoName=repoName)
            os.system("git push https://{}:{}@{} --all".format(githubAccountID, githubAccessToken, githubLinkDomain))
            self.log.info("{} synced".format(repoName), repoName=repoName)
            utils.LogUtils.logLight(color.Fore.GREEN, "{} synced".format(repoName))

    # Get list of all teams from GHE target org
    def getTeamsInfo(self, githubAccessToken):
        self.log.debug("Fetching teams list from GitHub")
        teamsInfoList = requests.get(self.githubAPI + "/orgs/{}/teams".format(self.targetOrg),
                                     headers={"Authorization": "Bearer {}".format(githubAccessToken)})
        teamsInfoList = json.loads(teamsInfoList.text)
        return teamsInfoList

    # Assign the selected repos to selected teams in the organization
    def assignReposToTeams(self, repoAssignment, githubAccessToken):
        adminPermissions = {'permission': 'admin'}
        assignResult = {}
        for team, repos in repoAssignment.items():  # key, value :: team, repos
            self.log.info("Assigning repos to {} team".format(team), teamName=team)

            # Get Team's ID
            self.log.debug("Fetching Team ID", teamName=team)
            teamInfo = requests.get(self.githubAPI + "/orgs/{}/teams/{}".format(self.targetOrg, team),
                                    headers={"Authorization": "Bearer {}".format(githubAccessToken)})
            teamInfo = json.loads(teamInfo.text)
            teamID = teamInfo['id']

            successCount = 0
            failureCount = 0
            for repo in repos:
                # Assign repo to team
                assignResponse = requests.put(self.githubAPI + "/teams/{}/repos/{}/{}".format(teamID, self.targetOrg, repo),
                                              data=json.dumps(adminPermissions),
                                              headers={"Authorization": "Bearer {}".format(githubAccessToken)})
                if (assignResponse.status_code != 204):
                    failureCount += 1
                    self.log.warning("Failed to assign {} repo to {} team".format(repo, team),
                                     repoName=repo,
                                     teamName=team,
                                     errorCode=assignResponse.status_code)
                else:
                    successCount += 1
                    self.log.info("Assigned {} repo to {} team".format(repo, team), repoName=repo, teamName=team)
            assignResult[team] = {'success': successCount, 'failure': failureCount}
            self.log.info("Assigned {} repos to {} team".format(successCount, team),
                          teamName=team,
                          successCount=successCount)
            if (failureCount != 0):
                self.log.warning("Failed to assign {} repos to {} team".format(failureCount, team),
                                 teamName=team,
                                 failureCount=failureCount)
        return assignResult
