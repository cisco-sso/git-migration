import requests
import os

from app import utils

# TODO (***REMOVED***): Potential to refactor

#   CredOps is conflating github checks as well as bitbucket checks into one
#   function.  If you think about unit testing, having credOps.checkCredentials
#   do oprations on Bitbucket AND Github is less testable.  Think about
#   decomposing into smaller units.  It would be better if github operations
#   were in individaul github functions, and the same as bitbucket.
#
#     credOps.checkBitbucketPullCreds
#     credOps.checkGithubPullCreds
#     credOps.checkGithubPushCreds


class credOps:
    def __init__(self, bitbucketAPI, githubAPI):
        self.bitbucketAPI = bitbucketAPI
        self.githubAPI = githubAPI
        self.log = utils.LogUtils.getLogger(os.path.basename(__file__))

    # Check if BitBucket and GitHub tokens are valid
    def checkCredentials(self, projectKey, bitbucketAccessToken, githubAccessToken):
        # Check BitBucket Access Token
        bitbucketAccessCheckLink = self.bitbucketAPI + "/projects/{}/repos".format(projectKey)
        bitbucketAccessCheck = requests.get(bitbucketAccessCheckLink,
                                            headers={"Authorization": "Bearer {}".format(bitbucketAccessToken)})

        # Check GitHub Access Token
        githubAccessTokenCheckLink = self.githubAPI + "/user/repos"
        githubAccessTokenCheck = requests.get(githubAccessTokenCheckLink,
                                              headers={"Authorization": "Bearer {}".format(githubAccessToken)})

        if (githubAccessTokenCheck.status_code != 200 or bitbucketAccessCheck.status_code != 200):
            self.log.critical("Credentials Incorrect")
            # Check which access token failed
            if (githubAccessTokenCheck.status_code == 401 and bitbucketAccessCheck.status_code == 401):
                self.log.error("GitHub and BitBucket Access Tokens Failed: Unauthorized",
                               githubAccessToken=githubAccessToken,
                               bitbucketAccessToken=bitbucketAccessToken,
                               projectKey=projectKey)
            elif (bitbucketAccessCheck.status_code == 404):
                self.log.error("Bitbucket Project not found: Please check the project key.", projectKey=projectKey)
            elif (bitbucketAccessCheck.status_code == 401):
                self.log.error("BitBucket Access Token Failed: Unauthorized", bitbucketAccessToken=bitbucketAccessToken)
            elif (githubAccessTokenCheck.status_code == 401):
                self.log.error("GitHub Access Token Failed: Unauthorized", githubAccessToken=githubAccessToken)
            else:
                self.log.error("BitBucket Status: {}".format(bitbucketAccessCheck.status_code),
                               errorCode=bitbucketAccessCheck.status_code)
                self.log.error("GitHub Status: {}".format(githubAccessTokenCheck.status_code),
                               errorCode=githubAccessTokenCheck.status_code)
            return False
        else:
            self.log.info("Access Tokens working!")
            return True

    # Check if GitHub credentials allow to push to given destination
    def checkCredsForPush(self, pushToOrg, githubAccountID, githubAccessToken):
        if (pushToOrg):
            self.log.info("Checking credentials for push : CX Engineering organization", pushDestination="***REMOVED***")
            isMember = requests.get(self.githubAPI + "/orgs/***REMOVED***/members/{}".format(githubAccountID),
                                    headers={"Authorization": "Bearer {}".format(githubAccessToken)})
            # API returns 401 if the user's access token is incorrect
            if (isMember.status_code == 401):
                self.log.error("GitHub Access Token Failed: Unauthorized",
                               githubAccountID=githubAccountID,
                               githubAccessToken=githubAccessToken)
                return False
            # API returns 204 if the person checking the membership is a member of the org
            if (not isMember.status_code == 204):
                self.log.error("Not a member of ***REMOVED*** Organization", githubAccountID=githubAccountID)
                return False
            self.log.info("Organization membership check PASSED!", githubAccountID=githubAccountID)
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
            self.log.info("Push access check to personal account PASSED!", githubAccountID=githubAccountID)
            return True
