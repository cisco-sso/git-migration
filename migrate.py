import argparse
import requests
import json
import os
import shutil

# Get required credentials from JSON file
with open("./credentials.json") as file:
    creds = json.load(file)
bitbucketAccountID = creds['BitBucket_AccountID']
bitbucketAccessToken = creds['Bitbucket_AccessToken']
githubToken = creds['Github_AccessToken']
githubAccountID = creds['Github_AccountID']

# Get arguments (project name to migrate)
parser = argparse.ArgumentParser('Migrate Repositories')
parser.add_argument('project', metavar='P', type=str, help='ID of bitbucket project to be migrated')
args = parser.parse_args()
print('Target project: ', args.project)

# Check BitBucket Access Token
bitbucketAccessCheckLink = "https://***REMOVED***/bitbucket/rest/api/1.0/projects/{}/repos".format(args.project)
bitbucketAccessCheck = requests.get(
    bitbucketAccessCheckLink,
    headers={"Authorization": "Bearer {}".format(bitbucketAccessToken)}
)

# Check GitHub Access Token
githubAccessTokenCheckLink = "https://***REMOVED***/api/v3/user/repos"
githubAccessTokenCheck = requests.get(
    "https://***REMOVED***/api/v3/user/repos",
    headers={"Authorization": "Bearer {}".format(githubToken)}
)

if(githubAccessTokenCheck.status_code!=200 or bitbucketAccessCheck.status_code!=200):
    print("Something went wrong!")
    # Check which access token failed
    if(githubAccessTokenCheck.status_code==401 and bitbucketAccessCheck.status_code==401):
        print("GitHub and BitBucket Access Tokens Failed: Unauthorized\nPlease check access tokens.")
    elif(bitbucketAccessCheck.status_code==404):
        print("Bitbucket Project not found: Please check the project ID.")
    elif(bitbucketAccessCheck.status_code==401):
        print("BitBucket Access Token Failed: Unauthorized\nPlease check access token.")
    elif(githubAccessTokenCheck.status_code==401):
        print("GitHub Access Token Failed: Unauthorized\nPlease check access token.")
    else:
        print("BitBucket Status: {}".format(bitbucketAccessCheck.status_code))
        print("GitHub Status: {}".format(githubAccessTokenCheck.status_code))
    exit(1)
else:
    print("Access Tokens working!")

# Filter function to get http links to clone repo
def isHTTP(link):
    if(link["name"]=="http" or link["name"]=="https"):
        return True
    else:
        return False

# Confirmation prompt from user
def yes_or_no(question):
    while "the answer is invalid":
        reply = str(input(question+' (y/n): ')).lower().strip()
        if reply[0] == 'y':
            return True
        if reply[0] == 'n':
            return False

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
    isLastPage = True#projectRepos["isLastPage"]
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
        # Check if same repository already exists on GitHub
        githubRepoCheckLink = "https://***REMOVED***/api/v3/repos/{}/{}".format(githubAccountID, repo["name"])
        githubRepoCheck = requests.get(
            githubRepoCheckLink,
            headers={"Authorization": "Bearer {}".format(githubToken)}
        )

        # Active pull requests on Bitbucket
        if(pullRequests["size"] != 0):
            print("Repo {}: Rejected - {} active PRs".format(repo["name"], pullRequests["size"]))
            openPRs.append({ repo["name"]: pullRequests["size"] })
        # Repository with a similar name already exists on GitHub
        elif(githubRepoCheck.status_code!=404):
            print("Repo {}: Rejected - {} already exists on GitHub Account".format(repo["name"], repo["name"]))
            alreadyExisting.append({ repo["name"]: pullRequests["size"] })
        # No PRs on Bitbucket and Repo doesn't already exist on GitHub
        else:
            print("Repo {}: Accepted".format(repo["name"]))
            repoInfo = {}
            repoInfo["name"] = repo["name"]
            if("description" in repo.keys()):
                repoInfo["description"] = repo["description"]
            link = list(filter(isHTTP, repo["links"]["clone"]))
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

confirm = yes_or_no("Continue with migrating accepted repos?")
if(not confirm):
    print("No repositories migrated")
    exit(0)
print("Migrating {} repositories...".format(len(accepts)))

# Make a temporary folder in root to clone repos from BitBucket
os.chdir(os.path.expanduser('~'))
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
    }
    if("description" in repo.keys()):
        requestPayload["description"] = repo["description"]
    # Create new repo of same name
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