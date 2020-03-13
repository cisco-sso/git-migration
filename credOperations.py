import json
import requests
from colorama import init, Fore, Style


from utils import logBright, logLight

# Read and return IDs and Access token from credentials.json
def getCredentials():
    # Get required credentials from JSON file
    with open("./credentials.json") as file:
        creds = json.load(file)
    bitbucketAccountID = creds['BitBucket_AccountID']
    bitbucketAccessToken = creds['Bitbucket_AccessToken']
    githubAccountID = creds['Github_AccountID']
    githubAccessToken = creds['Github_AccessToken']
    return bitbucketAccountID, bitbucketAccessToken, githubAccountID, githubAccessToken

# Check if BitBucket and GitHub tokens are valid
def checkCredentials(project_ID, bitbucketAccessToken, githubAccessToken):
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
        headers={"Authorization": "Bearer {}".format(githubAccessToken)}
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

# Check if GitHub credentials allow to push to given destination
def checkCredsForPush(pushToOrg, githubAccountID, githubAccessToken):
    if (pushToOrg):
        logBright(Fore.YELLOW, 'Push destination: CX Engineering organization')
        isMember = requests.get(
            "https://***REMOVED***/api/v3/orgs/***REMOVED***/members/{}".format(githubAccountID),
            headers={"Authorization": "Bearer {}".format(githubAccessToken)}
        )
        # API returns 401 if the user's access token is incorrect
        if (isMember.status_code == 401):
            logBright(Fore.RED, "While checking your organization membership...\nGitHub Access Token Failed: Unauthorized\nPlease check access token.")
            return False
        # API returns 204 if the person checking the membership is a member of the org
        if (not isMember.status_code == 204):
            logBright(Fore.RED, "\nYou appear to not be a member of the ***REMOVED*** Organization\nCheck the GitHub Account ID in credentials.json\nOr try again after being added as a member.")
            return False
        logBright(Fore.GREEN, "Organization membership check PASSED!")
        return True
    else:
        logBright(Fore.YELLOW, 'Push destination: Personal Account - {}'.format(githubAccountID))
        # Check GitHub Access Token
        githubAccessTokenCheckLink = "https://***REMOVED***/api/v3/users/{}/repos".format(githubAccountID)
        githubAccessTokenCheck = requests.get(
            githubAccessTokenCheckLink,
            headers={"Authorization": "Bearer {}".format(githubAccessToken)}
        )
        if (githubAccessTokenCheck.status_code == 401):
            logBright(Fore.RED, "While checking push access to personal account...\nGitHub Access Token Failed: Unauthorized\nPlease check access token.")
            return False
        logBright(Fore.GREEN, "Push access check to personal account PASSED!")
        return True