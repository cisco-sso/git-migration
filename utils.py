import json
import requests

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
        return False
    else:
        print("Access Tokens working!")
        return True

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