import json
import requests
from colorama import init, Fore, Style

init()

def checkCredentials(project_ID):
    # Get required credentials from JSON file
    with open("./credentials.json") as file:
        creds = json.load(file)
    # bitbucketAccountID = creds['BitBucket_AccountID']
    bitbucketAccessToken = creds['Bitbucket_AccessToken']
    githubToken = creds['Github_AccessToken']
    # githubAccountID = creds['Github_AccountID']

    # Check BitBucket Access Token
    bitbucketAccessCheckLink = "https://***REMOVED***/bitbucket/rest/api/1.0/projects/{}/repos".format(project_ID)
    bitbucketAccessCheck = requests.get(
        bitbucketAccessCheckLink,
        headers={"Authorization": "Bearer {}".format(bitbucketAccessToken)}
    )

    # Check GitHub Access Token
    githubAccessTokenCheckLink = "https://***REMOVED***/api/v3/user/repos"
    githubAccessTokenCheck = requests.get(
        githubAccessTokenCheckLink,
        headers={"Authorization": "Bearer {}".format(githubToken)}
    )

    if(githubAccessTokenCheck.status_code!=200 or bitbucketAccessCheck.status_code!=200):
        logBright(Fore.RED, "Something went wrong!")
        # Check which access token failed
        if(githubAccessTokenCheck.status_code==401 and bitbucketAccessCheck.status_code==401):
            logBright(Fore.RED, "GitHub and BitBucket Access Tokens Failed: Unauthorized\nPlease check access tokens.")
        elif(bitbucketAccessCheck.status_code==404):
            logBright(Fore.RED, "Bitbucket Project not found: Please check the project ID.")
        elif(bitbucketAccessCheck.status_code==401):
            logBright(Fore.RED, "BitBucket Access Token Failed: Unauthorized\nPlease check access token.")
        elif(githubAccessTokenCheck.status_code==401):
            logBright(Fore.RED, "GitHub Access Token Failed: Unauthorized\nPlease check access token.")
        else:
            logBright(Fore.RED, "BitBucket Status: {}".format(bitbucketAccessCheck.status_code))
            logBright(Fore.RED, "GitHub Status: {}".format(githubAccessTokenCheck.status_code))
        return False
    else:
        logBright(Fore.GREEN, "Access Tokens working!")
        return True

# Filter function to get http links to clone repo
def isHTTP(link):
    if(link["name"]=="http" or link["name"]=="https"):
        return True
    else:
        return False

def logBright(color, string):
    print(color + Style.BRIGHT + string + Style.RESET_ALL)

def logLight(color, string):
    print(color + string + Style.RESET_ALL)