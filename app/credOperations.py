import requests
import os

from app import utils

class credOps:
    def __init__(self, bitbucketAPI, githubAPI, consoleLogLevel, consoleLogNormal, fileLogLevel):
        self.bitbucketAPI = bitbucketAPI
        self.githubAPI = githubAPI
        self.log = utils.LogUtils.getLogger(os.path.basename(__file__), consoleLogLevel, consoleLogNormal, fileLogLevel)
        self.targetOrg = utils.ReadUtils.getTargetOrg()

    # Check if BitBucket access tokens are valid and can access the specified project
    def checkBitbucketPullCreds(self, projectKey, bitbucketAccessToken):
        # Check BitBucket Access Token
        bitbucketAccessCheckLink = self.bitbucketAPI + "/projects/{}/repos".format(projectKey)
        bitbucketAccessCheck = requests.get(bitbucketAccessCheckLink,
                                            headers={"Authorization": "Bearer {}".format(bitbucketAccessToken)})
        if (bitbucketAccessCheck.status_code == 200):
            self.log.debug("BitBucket credentials check PASSED", bitbucketAccessToken=bitbucketAccessToken)
            return True
        else:
            if (bitbucketAccessCheck.status_code == 404):
                self.log.error("Bitbucket Project not found: Please check the project key", projectKey=projectKey)
            elif (bitbucketAccessCheck.status_code == 401):
                self.log.error("BitBucket Access Token Failed: Unauthorized", bitbucketAccessToken=bitbucketAccessToken)
            else:
                self.log.error("BitBucket credentials check Failed: Code {}".format(bitbucketAccessCheck.status_code), bitbucketAccessToken=bitbucketAccessToken, statusCode=bitbucketAccessCheck.status_code)
            return False
    
    # Check if GitHub access tokens are valid
    def checkGithubPullCreds(self, githubAccessToken):
        # Check GitHub Access Token
        githubAccessTokenCheckLink = self.githubAPI + "/user/repos"
        githubAccessTokenCheck = requests.get(githubAccessTokenCheckLink,
                                              headers={"Authorization": "Bearer {}".format(githubAccessToken)})
        if (githubAccessTokenCheck.status_code == 200):
            self.log.debug("GitHub credentials check PASSED", githubAccessToken=githubAccessToken)
            return True
        else:
            if (githubAccessTokenCheck.status_code == 401):
                self.log.error("GitHub Access Token Failed: Unauthorized", githubAccessToken=githubAccessToken)
            else:
                self.log.error("GitHub credentials check Failed: Code {}".format(githubAccessTokenCheck.status_code),
                               githubAccessToken=githubAccessToken, errorCode=githubAccessTokenCheck.status_code)
            return False

    # Check if GitHub credentials allow to push to given destination
    def checkGithubPushCreds(self, pushToOrg, githubAccountID, githubAccessToken):
        if (pushToOrg):
            self.log.info("Checking credentials for push : {} organization".format(self.targetOrg), pushDestination=self.targetOrg)
            isMember = requests.get(self.githubAPI + "/orgs/{}/members/{}".format(self.targetOrg, githubAccountID),
                                    headers={"Authorization": "Bearer {}".format(githubAccessToken)})
            # API returns 401 if the user's access token is incorrect
            if (isMember.status_code == 401):
                self.log.error("GitHub Access Token Failed: Unauthorized",
                               githubAccountID=githubAccountID,
                               githubAccessToken=githubAccessToken)
                return False
            # API returns 204 if the person checking the membership is a member of the org
            if (not isMember.status_code == 204):
                self.log.error("Not a member of {} Organization".format(self.targetOrg), githubAccountID=githubAccountID)
                return False
            self.log.debug("Organization membership check PASSED!", githubAccountID=githubAccountID)
            return True
        else:
            self.log.info("Checking credentials for push : {}".format(githubAccountID), pushDestination=githubAccountID)
            # Check GitHub Access Token
            githubAccessTokenCheckLink = self.githubAPI + "/users/{}/repos".format(githubAccountID)
            githubAccessTokenCheck = requests.get(githubAccessTokenCheckLink,
                                                  headers={"Authorization": "Bearer {}".format(githubAccessToken)})
            if (githubAccessTokenCheck.status_code == 401):
                self.log.error("GitHub Access Token Failed: Unauthorized",
                               githubAccountID=githubAccountID,
                               githubAccessToken=githubAccessToken)
                return False
            self.log.debug("Push access check to personal account PASSED!", githubAccountID=githubAccountID)
            return True
