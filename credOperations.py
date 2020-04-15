import json
import requests
import colorama as color

import utils

class credOps:
    def __init__(self):
        self.bitbucketAPI, self.githubAPI = utils.ReadUtils.getAPILinks()

    # Read and return IDs and Access token from credentials.json
    def getCredentials(self):
        # Get required credentials from JSON file
        with open("./credentials.json") as file:
            creds = json.load(file)
        bitbucketAccountID = creds['BitBucket_AccountID']
        bitbucketAccessToken = creds['Bitbucket_AccessToken']
        githubAccountID = creds['Github_AccountID']
        githubAccessToken = creds['Github_AccessToken']
        return bitbucketAccountID, bitbucketAccessToken, githubAccountID, githubAccessToken

    # Check if BitBucket and GitHub tokens are valid
    def checkCredentials(self, project_ID, bitbucketAccessToken, githubAccessToken):
        # Check BitBucket Access Token
        bitbucketAccessCheckLink = self.bitbucketAPI+"/projects/{}/repos".format(project_ID)
        bitbucketAccessCheck = requests.get(
            bitbucketAccessCheckLink,
            headers={"Authorization": "Bearer {}".format(bitbucketAccessToken)}
        )

        # Check GitHub Access Token
        githubAccessTokenCheckLink = self.githubAPI+"/user/repos"
        githubAccessTokenCheck = requests.get(
            githubAccessTokenCheckLink,
            headers={"Authorization": "Bearer {}".format(githubAccessToken)}
        )

        if(githubAccessTokenCheck.status_code!=200 or bitbucketAccessCheck.status_code!=200):
            utils.LogUtils.logBright(color.Fore.RED, "Something went wrong!")
            # Check which access token failed
            if(githubAccessTokenCheck.status_code==401 and bitbucketAccessCheck.status_code==401):
                utils.LogUtils.logBright(color.Fore.RED, "GitHub and BitBucket Access Tokens Failed: Unauthorized\nPlease check access tokens.")
            elif(bitbucketAccessCheck.status_code==404):
                utils.LogUtils.logBright(color.Fore.RED, "Bitbucket Project not found: Please check the project ID.")
            elif(bitbucketAccessCheck.status_code==401):
                utils.LogUtils.logBright(color.Fore.RED, "BitBucket Access Token Failed: Unauthorized\nPlease check access token.")
            elif(githubAccessTokenCheck.status_code==401):
                utils.LogUtils.logBright(color.Fore.RED, "GitHub Access Token Failed: Unauthorized\nPlease check access token.")
            else:
                utils.LogUtils.logBright(color.Fore.RED, "BitBucket Status: {}".format(bitbucketAccessCheck.status_code))
                utils.LogUtils.logBright(color.Fore.RED, "GitHub Status: {}".format(githubAccessTokenCheck.status_code))
            return False
        else:
            utils.LogUtils.logBright(color.Fore.GREEN, "Access Tokens working!")
            return True

    # Check if GitHub credentials allow to push to given destination
    def checkCredsForPush(self, pushToOrg, githubAccountID, githubAccessToken):
        if (pushToOrg):
            utils.LogUtils.logBright(color.Fore.YELLOW, 'Push destination: CX Engineering organization')
            isMember = requests.get(
                self.githubAPI+"/orgs/***REMOVED***/members/{}".format(githubAccountID),
                headers={"Authorization": "Bearer {}".format(githubAccessToken)}
            )
            # API returns 401 if the user's access token is incorrect
            if (isMember.status_code == 401):
                utils.LogUtils.logBright(color.Fore.RED, "While checking your organization membership...\nGitHub Access Token Failed: Unauthorized\nPlease check access token.")
                return False
            # API returns 204 if the person checking the membership is a member of the org
            if (not isMember.status_code == 204):
                utils.LogUtils.logBright(color.Fore.RED, "\nYou appear to not be a member of the ***REMOVED*** Organization\nCheck the GitHub Account ID in credentials.json\nOr try again after being added as a member.")
                return False
            utils.LogUtils.logBright(color.Fore.GREEN, "Organization membership check PASSED!")
            return True
        else:
            utils.LogUtils.logBright(color.Fore.YELLOW, 'Push destination: Personal Account - {}'.format(githubAccountID))
            # Check GitHub Access Token
            githubAccessTokenCheckLink = self.githubAPI+"/users/{}/repos".format(githubAccountID)
            githubAccessTokenCheck = requests.get(
                githubAccessTokenCheckLink,
                headers={"Authorization": "Bearer {}".format(githubAccessToken)}
            )
            if (githubAccessTokenCheck.status_code == 401):
                utils.LogUtils.logBright(color.Fore.RED, "While checking push access to personal account...\nGitHub Access Token Failed: Unauthorized\nPlease check access token.")
                return False
            utils.LogUtils.logBright(color.Fore.GREEN, "Push access check to personal account PASSED!")
            return True