# Library imports
import json
import os
import shutil
import requests
from colorama import Fore, Style

# Custom imports
from utils import logBright, logLight, isHTTP

# Returns list of all projects on BitBucket
def getBitbucketProjects(bitbucketAccessToken):
    projectNames = []
    isLastPage = False
    start = 0
    # Get list of projects
    while(not isLastPage):
        projectsUrl = "https://***REMOVED***/bitbucket/rest/api/1.0/projects/?start={}".format(start)
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
def getBitbucketRepos(projectKey, bitbucketAccessToken):
    repoNames = []
    isLastPage = False
    start = 0
    # Get list of all repos
    while(not isLastPage):
        # Get list of repos under the mentioned project on BitBucket
        projectReposLink = "https://***REMOVED***/bitbucket/rest/api/1.0/projects/{}/repos?start={}".format(projectKey, start)
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
def processRepos(repositories, projectKey, pushToOrg, bitbucketAccessToken, githubAccountID, githubAccessToken):
    # Repo metadata added to these lists
    accepts = []
    openPRs = []
    alreadyExisting = []
    # Preprocess repository data
    for repoName in repositories["repos"]:
        # Get all info on a repo
        repoInfo = {
            "openPRs": None,
            "alreadyExisting": None
        }
        repoInfo["name"] = repoName
        repoResponse = requests.get(
            "https://***REMOVED***/bitbucket/rest/api/1.0/projects/{}/repos/{}".format(projectKey, repoName),
            headers={"Authorization": "Bearer {}".format(bitbucketAccessToken)}
        )
        repoResponse = json.loads(repoResponse.text)
        if("description" in repoResponse.keys()):
            repoInfo["description"] = repoResponse["description"]
        else:
            repoInfo["description"] = None
        link = list(filter(isHTTP, repoResponse["links"]["clone"]))
        repoInfo["cloneLink"] = link[0]["href"]

        # Check if repository has open PRs on BitBucket
        repoPRLink = "https://***REMOVED***/bitbucket/rest/api/1.0/projects/{}/repos/{}/pull-requests/".format(projectKey, repoName)
        pullRequests = requests.get(
            repoPRLink,
            headers={"Authorization": "Bearer {}".format(bitbucketAccessToken)}
        )
        pullRequests = json.loads(pullRequests.text)
        # Active pull requests on Bitbucket
        if(pullRequests["size"] != 0):
            logLight(Fore.RED, "Repo {}: Rejected - {} active PRs".format(repoName, pullRequests["size"]))
            repoInfo["openPRs"] = pullRequests["size"]

        if (pushToOrg):
            # Check if same repository already exists on GitHub ***REMOVED*** Org
            githubOrgRepoCheckLink = "https://***REMOVED***/api/v3/repos/***REMOVED***/{}".format(repoName)
            githubOrgRepoCheck = requests.get(
                githubOrgRepoCheckLink,
                headers={"Authorization": "Bearer {}".format(githubAccessToken)}
            )
            # Repository with a similar name already exists on GitHub
            if(githubOrgRepoCheck.status_code!=404):
                logLight(Fore.RED, "Repo {}: Rejected - {} already exists on the ***REMOVED*** Organization".format(repoName, repoName))
                repoInfo["alreadyExisting"] = True
        else:
            # Check if same repository already exists on GitHub
            githubRepoCheckLink = "https://***REMOVED***/api/v3/repos/{}/{}".format(githubAccountID, repoName)
            githubRepoCheck = requests.get(
                githubRepoCheckLink,
                headers={"Authorization": "Bearer {}".format(githubAccessToken)}
            )
            # Repository with a similar name already exists on GitHub
            if(githubRepoCheck.status_code!=404):
                logLight(Fore.RED, "Repo {}: Rejected - {} already exists on GitHub Account".format(repoName, repoName))
                repoInfo["alreadyExisting"] = True

        if (repoInfo["alreadyExisting"]):
            alreadyExisting.append(repoInfo)
        elif (repoInfo["openPRs"] != None):
            openPRs.append(repoInfo)
        # No PRs on Bitbucket and Repo doesn't already exist on GitHub
        else:
            logLight(Fore.GREEN, "Repo {}: Accepted".format(repoName))
            accepts.append(repoInfo)
    return accepts, openPRs, alreadyExisting

# Get all BitBucket repos and check metadata together to reduce API requests
# Returns list of accepted and rejected repos
def getAndProcessBitbucketRepos(projectKey, pushToOrg, bitbucketAccessToken, githubAccountID, githubAccessToken):
    # Loop control variables
    isLastPage = False
    start = 0

    # Repo metadata added to these lists
    accepts = []
    openPRs = []
    alreadyExisting = []

    logLight(Fore.BLUE, "\nAquiring and checking repo metadata...")
    while(not isLastPage):
        # Get list of repos under the mentioned project on BitBucket
        projectReposLink = "https://***REMOVED***/bitbucket/rest/api/1.0/projects/{}/repos?start={}".format(projectKey, start)
        projectRepos = requests.get(
            projectReposLink,
            headers={"Authorization": "Bearer {}".format(bitbucketAccessToken)}
        )
        projectRepos = json.loads(projectRepos.text)

        # Check if last page
        isLastPage = projectRepos["isLastPage"]
        if(not isLastPage):
            start = projectRepos["nextPageStart"]

        # Preprocess repository data
        for repo in projectRepos["values"]:
            # Get all info on a repo
            repoName = repo["name"]
            repoInfo = {
                "openPRs": None,
                "alreadyExisting": None
            }
            repoInfo["name"] = repoName
            repoResponse = requests.get(
                "https://***REMOVED***/bitbucket/rest/api/1.0/projects/{}/repos/{}".format(projectKey, repoName),
                headers={"Authorization": "Bearer {}".format(bitbucketAccessToken)}
            )
            repoResponse = json.loads(repoResponse.text)
            if("description" in repoResponse.keys()):
                repoInfo["description"] = repoResponse["description"]
            else:
                repoInfo["description"] = None
            link = list(filter(isHTTP, repoResponse["links"]["clone"]))
            repoInfo["cloneLink"] = link[0]["href"]

            # Check if repository has open PRs on BitBucket
            repoPRLink = "https://***REMOVED***/bitbucket/rest/api/1.0/projects/{}/repos/{}/pull-requests/".format(projectKey, repoName)
            pullRequests = requests.get(
                repoPRLink,
                headers={"Authorization": "Bearer {}".format(bitbucketAccessToken)}
            )
            pullRequests = json.loads(pullRequests.text)
            # Active pull requests on Bitbucket
            if(pullRequests["size"] != 0):
                logLight(Fore.RED, "Repo {}: Rejected - {} active PRs".format(repoName, pullRequests["size"]))
                repoInfo["openPRs"] = pullRequests["size"]

            if (pushToOrg):
                # Check if same repository already exists on GitHub ***REMOVED*** Org
                githubOrgRepoCheckLink = "https://***REMOVED***/api/v3/repos/***REMOVED***/{}".format(repoName)
                githubOrgRepoCheck = requests.get(
                    githubOrgRepoCheckLink,
                    headers={"Authorization": "Bearer {}".format(githubAccessToken)}
                )
                # Repository with a similar name already exists on GitHub
                if(githubOrgRepoCheck.status_code!=404):
                    logLight(Fore.RED, "Repo {}: Rejected - {} already exists on the ***REMOVED*** Organization".format(repoName, repoName))
                    repoInfo["alreadyExisting"] = True
            else:
                # Check if same repository already exists on GitHub
                githubRepoCheckLink = "https://***REMOVED***/api/v3/repos/{}/{}".format(githubAccountID, repoName)
                githubRepoCheck = requests.get(
                    githubRepoCheckLink,
                    headers={"Authorization": "Bearer {}".format(githubAccessToken)}
                )
                # Repository with a similar name already exists on GitHub
                if(githubRepoCheck.status_code!=404):
                    logLight(Fore.RED, "Repo {}: Rejected - {} already exists on GitHub Account".format(repoName, repoName))
                    repoInfo["alreadyExisting"] = True

            if (repoInfo["alreadyExisting"]):
                alreadyExisting.append(repoInfo)
            elif (repoInfo["openPRs"] != None):
                openPRs.append(repoInfo)
            # No PRs on Bitbucket and Repo doesn't already exist on GitHub
            else:
                logLight(Fore.GREEN, "Repo {}: Accepted".format(repoName))
                accepts.append(repoInfo)
    return accepts, openPRs, alreadyExisting

# Migrate all given repos to given destination
def migrateRepos(repositories, pushToOrg, bitbucketAccountID, bitbucketAccessToken, githubAccountID, githubAccessToken):
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
            shutil.rmtree(bitbucketName, ignore_errors=True)
        # Bare clone the repository
        bitbucketLinkDomain = bitbucketLink.split("//")[1]
        os.system("git clone --bare https://{}:{}@{}".format(bitbucketAccountID, bitbucketAccessToken, bitbucketLinkDomain))
        os.chdir("{}.git".format(bitbucketName))

        # API call to make new remote repo on GitHub
        requestPayload = {
            "name": bitbucketName,
            "private": True
        }
        if("description" in repo.keys()):
            requestPayload["description"] = repo["description"]
        
        if(pushToOrg):
            # Create new repo of same name on GitHub ***REMOVED*** Org
            gitResponse = requests.post(
                "https://***REMOVED***/api/v3/orgs/***REMOVED***/repos",
                data=json.dumps(requestPayload),
                headers={"Authorization": "Bearer {}".format(githubAccessToken)}
            )
        else:
            # Create new repo of same name on GitHub Account
            gitResponse = requests.post(
                "https://***REMOVED***/api/v3/user/repos",
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
        shutil.rmtree("{}.git".format(bitbucketName))

    # Remove temporary folder
    if(not isDir):
        os.chdir("..")
        shutil.rmtree("migration_temp")
    return True
