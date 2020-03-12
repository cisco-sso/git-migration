import argparse
import requests
import json
import os
import shutil

import utils

# Get required credentials from JSON file
with open("./credentials.json") as file:
    creds = json.load(file)
bitbucketAccountID = creds['BitBucket_AccountID']
bitbucketAccessToken = creds['Bitbucket_AccessToken']
githubToken = creds['Github_AccessToken']
githubAccountID = creds['Github_AccountID']

# Get arguments (project name to migrate)
parser = argparse.ArgumentParser('Migrate Repositories')
parser.add_argument('-c', '--***REMOVED***', action='store_true', help='Pass flag to push to ***REMOVED*** organization')
parser.add_argument('project', metavar='P', type=str, help='KEY of BitBucket project to be migrated')
args = parser.parse_args()
print('Target project: ', args.project)

if (not utils.checkCredentials(args.project)):
    exit(1)

pushToOrg = args.***REMOVED***
if (pushToOrg):
    print('Push destination: CX Engineering organization')

    isMember = requests.get(
        "https://***REMOVED***/api/v3/orgs/***REMOVED***/members/{}".format(githubAccountID),
        headers={"Authorization": "Bearer {}".format(githubToken)}
    )
    # API returns 401 if the user's access token is incorrect
    if (isMember.status_code == 401):
        print("While checking your organization membership...\nGitHub Access Token Failed: Unauthorized\nPlease check access token.")
        exit(0)
    # API returns 204 if the person checking the membership is a member of the org
    if (not isMember.status_code == 204):
        print("\nYou appear to not be a member of the ***REMOVED*** Organization\nCheck the GitHub Account ID in credentials.json\nOr try again after being added as a member.")
        exit(0)
    print("Organization membership check PASSED!")
    confirmMigrate = utils.yes_or_no("Migrate to GitHub ***REMOVED*** Org?")
    if(not confirmMigrate):
        print("Rerun script without --cex flag to migrate to GitHub personal Account")
        exit(0)
else:
    print('Push destination: Personal Account - {}'.format(githubAccountID))
    confirmMigrate = utils.yes_or_no("Migrate to GitHub Personal Account?")
    if(not confirmMigrate):
        print("Rerun script with --cex flag to migrate to GitHub ***REMOVED*** Org")
        exit(0)

# Loop control variables
isLastPage = False
start = 0

# Repo metadata added to these lists
accepts = []
openPRs = []
alreadyExisting = []

print("\nAquiring and checking repo metadata...")
while(not isLastPage):
    # Get list of repos under the mentioned project on BitBucket
    projectReposLink = "https://***REMOVED***/bitbucket/rest/api/1.0/projects/{}/repos?start={}".format(args.project, start)
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
        # Check if repository has open PRs on BitBucket
        repoPRLink = "https://***REMOVED***/bitbucket/rest/api/1.0/projects/{}/repos/{}/pull-requests".format(args.project, repo["name"])
        pullRequests = requests.get(
            repoPRLink,
            headers={"Authorization": "Bearer {}".format(bitbucketAccessToken)}
        )
        pullRequests = json.loads(pullRequests.text)
        # Active pull requests on Bitbucket
        if(pullRequests["size"] != 0):
            print("Repo {}: Rejected - {} active PRs".format(repo["name"], pullRequests["size"]))
            openPRs.append({ repo["name"]: pullRequests["size"] })
            continue

        if (pushToOrg):
            # Check if same repository already exists on GitHub ***REMOVED*** Org
            githubOrgRepoCheckLink = "https://***REMOVED***/api/v3/repos/***REMOVED***/{}".format(repo["name"])
            githubOrgRepoCheck = requests.get(
                githubOrgRepoCheckLink,
                headers={"Authorization": "Bearer {}".format(githubToken)}
            )
            # Repository with a similar name already exists on GitHub
            if(githubOrgRepoCheck.status_code!=404):
                print("Repo {}: Rejected - {} already exists on the ***REMOVED*** Organization".format(repo["name"], repo["name"]))
                alreadyExisting.append({ repo["name"]: pullRequests["size"] })
                continue
        else:
            # Check if same repository already exists on GitHub Account
            githubRepoCheckLink = "https://***REMOVED***/api/v3/repos/{}/{}".format(githubAccountID, repo["name"])
            githubRepoCheck = requests.get(
                githubRepoCheckLink,
                headers={"Authorization": "Bearer {}".format(githubToken)}
            )
            # Repository with a similar name already exists on GitHub
            if(githubRepoCheck.status_code!=404):
                print("Repo {}: Rejected - {} already exists on GitHub Account".format(repo["name"], repo["name"]))
                alreadyExisting.append({ repo["name"]: pullRequests["size"] })
                continue

        # No PRs on Bitbucket and Repo doesn't already exist on GitHub
        print("Repo {}: Accepted".format(repo["name"]))
        repoInfo = {}
        repoInfo["name"] = repo["name"]
        if("description" in repo.keys()):
            repoInfo["description"] = repo["description"]
        link = list(filter(utils.isHTTP, repo["links"]["clone"]))
        repoInfo["cloneLink"] = link[0]["href"]
        accepts.append(repoInfo)

acceptedNumber = len(accepts)
openPRsNumber = len(openPRs)
alreadyExistingNumber = len(alreadyExisting)
print("Accepted: {}\tRejected: {} ( {} with open PRs, {} already existing on GitHub )".format(
    acceptedNumber,
    openPRsNumber+alreadyExistingNumber,
    openPRsNumber,
    alreadyExistingNumber
))

print("Close all PRs before migrating a repo.")

if(acceptedNumber==0):
    exit(0)

confirm = utils.yes_or_no("Continue with migrating accepted repos?")
if(not confirm):
    print("No repositories migrated")
    exit(0)
print("Migrating {} repositories...".format(len(accepts)))

# Make a temporary folder in CWD to clone repos from BitBucket
os.chdir(os.path.dirname(os.path.realpath(__file__)))
isDir = os.path.isdir("migration_temp")
if(not isDir):
    os.mkdir("migration_temp")
os.chdir("migration_temp")

for repo in accepts:
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
            headers={"Authorization": "Bearer {}".format(githubToken)}
        )
    else:
        # Create new repo of same name on GitHub Account
        gitResponse = requests.post(
            "https://***REMOVED***/api/v3/user/repos",
            data=json.dumps(requestPayload),
            headers={"Authorization": "Bearer {}".format(githubToken)}
        )

    # Mirror the codebase to remote GitHub URL
    githubRepoData = json.loads(gitResponse.text)
    githubCloneLink = githubRepoData["clone_url"]
    githubCloneLinkDomain = githubCloneLink.split("//")[1]
    os.system("git push --mirror https://{}:{}@{}".format(githubAccountID, githubToken, githubCloneLinkDomain))

    # Remove local clone of repo
    os.chdir("..")
    shutil.rmtree("{}.git".format(bitbucketName))

# Remove temporary folder
if(not isDir):
    os.chdir("..")
    shutil.rmtree("migration_temp")

print("Migration successfully completed - {} repositories copied to GitHub".format(acceptedNumber))