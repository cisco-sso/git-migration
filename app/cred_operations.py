import requests
import os

from app import utils


class CredOps:
    def __init__(self, bitbucket_api, github_api, console_log_level, console_log_normal, file_log_level):
        self.bitbucket_api = bitbucket_api
        self.github_api = github_api
        self.log = utils.LogUtils.get_logger(os.path.basename(__file__), console_log_level, console_log_normal,
                                             file_log_level)
        self.target_org = utils.ReadUtils.get_target_org()

    # Check if BitBucket access tokens are valid and can access the specified project
    def check_bitbucket_pull_creds(self, project_key, bitbucket_access_token):
        # Check BitBucket Access Token
        bitbucket_access_check_link = self.bitbucket_api + "/projects/{}/repos".format(project_key)
        bitbucket_access_check = requests.get(bitbucket_access_check_link,
                                              headers={"Authorization": "Bearer {}".format(bitbucket_access_token)})
        if (bitbucket_access_check.status_code == 200):
            self.log.debug("BitBucket credentials check PASSED", bitbucket_access_token=bitbucket_access_token)
            return True
        else:
            if (bitbucket_access_check.status_code == 404):
                self.log.error("Bitbucket Project not found: Please check the project key", project_key=project_key)
            elif (bitbucket_access_check.status_code == 401):
                self.log.error("BitBucket Access Token Failed: Unauthorized",
                               bitbucket_access_token=bitbucket_access_token)
            else:
                self.log.error("BitBucket credentials check Failed: Code {}".format(bitbucket_access_check.status_code),
                               bitbucket_access_token=bitbucket_access_token,
                               statusCode=bitbucket_access_check.status_code)
            return False

    # Check if GitHub access tokens are valid
    def check_github_pull_creds(self, github_access_token):
        # Check GitHub Access Token
        github_access_token_check_link = self.github_api + "/user/repos"
        github_access_token_check = requests.get(github_access_token_check_link,
                                                 headers={"Authorization": "Bearer {}".format(github_access_token)})
        if (github_access_token_check.status_code == 200):
            self.log.debug("GitHub credentials check PASSED", github_access_token=github_access_token)
            return True
        else:
            if (github_access_token_check.status_code == 401):
                self.log.error("GitHub Access Token Failed: Unauthorized", github_access_token=github_access_token)
            else:
                self.log.error("GitHub credentials check Failed: Code {}".format(github_access_token_check.status_code),
                               github_access_token=github_access_token,
                               errorCode=github_access_token_check.status_code)
            return False

    # Check if GitHub credentials allow to push to given destination
    def check_github_push_creds(self, push_to_org, github_account_id, github_access_token):
        if (push_to_org):
            self.log.info("Checking credentials for push : {} organization".format(self.target_org),
                          pushDestination=self.target_org)
            is_member = requests.get(self.github_api + "/orgs/{}/members/{}".format(self.target_org, github_account_id),
                                     headers={"Authorization": "Bearer {}".format(github_access_token)})
            # API returns 401 if the user's access token is incorrect
            if (is_member.status_code == 401):
                self.log.error("GitHub Access Token Failed: Unauthorized",
                               github_account_id=github_account_id,
                               github_access_token=github_access_token)
                return False
            # API returns 204 if the person checking the membership is a member of the org
            if (not is_member.status_code == 204):
                self.log.error("Not a member of {} Organization".format(self.target_org),
                               github_account_id=github_account_id)
                return False
            self.log.debug("Organization membership check PASSED!", github_account_id=github_account_id)
            return True
        else:
            self.log.info("Checking credentials for push : {}".format(github_account_id),
                          pushDestination=github_account_id)
            # Check GitHub Access Token
            github_access_token_check_link = self.github_api + "/users/{}/repos".format(github_account_id)
            github_access_token_check = requests.get(github_access_token_check_link,
                                                     headers={"Authorization": "Bearer {}".format(github_access_token)})
            if (github_access_token_check.status_code == 401):
                self.log.error("GitHub Access Token Failed: Unauthorized",
                               github_account_id=github_account_id,
                               github_access_token=github_access_token)
                return False
            self.log.debug("Push access check to personal account PASSED!", github_account_id=github_account_id)
            return True
