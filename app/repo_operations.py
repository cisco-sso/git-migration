# Library imports
import json
import os
import requests
import colorama as color

# Custom imports
from app import utils


class RepoOps:
    def __init__(self, bitbucket_api, github_api, console_log_level, console_log_normal, file_log_level):
        self.bitbucket_api = bitbucket_api
        self.github_api = github_api
        self.log = utils.LogUtils.get_logger(os.path.basename(__file__), console_log_level, console_log_normal,
                                             file_log_level)
        self.target_org = utils.ReadUtils.get_target_org()

    # Returns list of all projects on BitBucket
    def get_bitbucket_projects(self, bitbucket_access_token):
        project_names = []
        is_last_page = False
        start = 0
        # Get list of projects
        self.log.info("Fetching project list")
        while (not is_last_page):
            projects_url = self.bitbucket_api + "/projects/?start={}".format(start)
            projects = requests.get(projects_url, headers={"Authorization": "Bearer {}".format(bitbucket_access_token)})
            projects = json.loads(projects.text)

            # Check if last page
            is_last_page = projects["isLastPage"]
            if (not is_last_page):
                start = projects["nextPageStart"]

            # Populate the project names
            project_names += ["{}:{}".format(project["name"], project["key"]) for project in projects["values"]]
        return project_names

    # Return all repositories from a given project on BitBucket
    def get_bitbucket_repos(self, project_key, bitbucket_access_token):
        repo_names = []
        is_last_page = False
        start = 0
        # Get list of all repos
        self.log.info("Fetching repository list for {}".format(project_key), project_key=project_key)
        while (not is_last_page):
            # Get list of repos under the mentioned project on BitBucket
            project_repos_link = self.bitbucket_api + "/projects/{}/repos?start={}".format(project_key, start)
            project_repos = requests.get(project_repos_link,
                                         headers={"Authorization": "Bearer {}".format(bitbucket_access_token)})
            project_repos = json.loads(project_repos.text)

            # Check if last page
            is_last_page = project_repos["isLastPage"]
            if (not is_last_page):
                start = project_repos["nextPageStart"]

            # Populate the project names
            # repo_names += [ { 'name':"{}".format(repo["name"]) } for repo in project_repos["values"]]
            repo_names += [repo["name"] for repo in project_repos["values"]]
        return repo_names

    # Process the list of repositories for a project and return metadata and repository links
    def process_repos(self, project_key, repositories, push_to_org, bitbucket_access_token, github_account_id,
                      github_access_token):
        processed_repos = []
        new_repos = 0
        self.log.info("Processing repos from project {}".format(project_key), project_key=project_key)

        for repo_name in repositories:
            # Add name
            repo_info = {"name": repo_name}
            bitbucket_repo_response = requests.get(
                self.bitbucket_api + "/projects/{}/repos/{}".format(project_key, repo_name),
                headers={"Authorization": "Bearer {}".format(bitbucket_access_token)})
            bitbucket_repo_response = json.loads(bitbucket_repo_response.text)
            # Add description
            if ("description" in bitbucket_repo_response):
                repo_info["description"] = bitbucket_repo_response["description"]
            # Add BitBucket Link
            link = list(filter(utils.MiscUtils.is_http, bitbucket_repo_response["links"]["clone"]))
            repo_info["bitbucket_link"] = link[0]["href"]
            self.log.debug("Added {} repository details from BitBucket".format(repo_name), repo_name=repo_name)

            # Add GitHub Link
            if (push_to_org):
                # Check if same repository already exists on GitHub target org
                # TODO(***REMOVED***): Must parameterize the target org on Github
                #   Place in Config file, instead of hard-coding here
                github_org_repo_check_link = self.github_api + "/repos/{}/{}".format(self.target_org, repo_name)
                github_org_repo_check = requests.get(github_org_repo_check_link,
                                                     headers={"Authorization": "Bearer {}".format(github_access_token)})
                # Repository with a similar name already exists on GitHub
                if (github_org_repo_check.status_code != 404):
                    github_org_repo_check = json.loads(github_org_repo_check.text)
                    self.log.debug("Repo {} - Exists on {} org".format(repo_name, self.target_org),
                                   repo_name=repo_name,
                                   target_org=self.target_org)
                    repo_info["github_link"] = github_org_repo_check["clone_url"]
                else:
                    new_repos += 1
                    self.log.debug("Repo {} - Doesn't exist on {} org".format(repo_name, self.target_org),
                                   repo_name=repo_name,
                                   target_org=self.target_org)
            else:
                # Check if same repository already exists on GitHub
                github_repo_check_link = self.github_api + "/repos/{}/{}".format(github_account_id, repo_name)
                github_repo_check = requests.get(github_repo_check_link,
                                                 headers={"Authorization": "Bearer {}".format(github_access_token)})
                # Repository with a similar name already exists on GitHub
                if (github_repo_check.status_code != 404):
                    github_repo_check = json.loads(github_repo_check.text)
                    self.log.debug("Repo {} - Exists on GHE account {}".format(repo_name, github_account_id),
                                   repo_name=repo_name,
                                   github_account_id=github_account_id)
                    repo_info["github_link"] = github_repo_check["clone_url"]
                else:
                    new_repos += 1
                    self.log.debug("Repo {} - Doesn't exist on GHE account".format(repo_name),
                                   repo_name=repo_name,
                                   github_account_id=github_account_id)
            processed_repos.append(repo_info)
        total_repos = len(processed_repos)
        self.log.info("Syncing {} repositories, {} will be newly migrated to GitHub".format(
            total_repos - new_repos, new_repos),
                      total_repos=total_repos,
                      new_repos=new_repos)
        return processed_repos, total_repos, new_repos

    # Makes a new repo through API calls on either target org or GHE personal account and returns repo link
    def make_new_repo(self, push_to_org, repo, github_account_id, github_access_token):
        # API call to make new remote repo on GitHub
        repo_name = repo["name"]

        request_payload = {"name": utils.StringUtils.remove_control_characters(repo_name), "private": True}
        if ("description" in repo):
            request_payload["description"] = utils.StringUtils.remove_control_characters(repo["description"])

        if (push_to_org):
            # Create new repo of same name on GitHub target org
            git_response = requests.post(self.github_api + "/orgs/{}/repos".format(self.target_org),
                                         data=json.dumps(request_payload),
                                         headers={"Authorization": "Bearer {}".format(github_access_token)})
            self.log.debug("New repo {} created on GitHub {}".format(repo_name, self.target_org),
                           repo_name=repo_name,
                           target_org=self.target_org)
        else:
            # Create new repo of same name on GitHub Account
            git_response = requests.post(self.github_api + "/user/repos",
                                         data=json.dumps(request_payload),
                                         headers={"Authorization": "Bearer {}".format(github_access_token)})
            self.log.debug("New repo {} created on GitHub {} account".format(repo_name, github_account_id),
                           repo_name=repo_name,
                           github_account_id=github_account_id)

        github_repo_data = json.loads(git_response.text)
        github_link = github_repo_data["clone_url"]
        return github_link

    # Recieves list of repos with metadata, BitBucker and GitHub repo links
    # Syncs the repos that already exist on GitHub, Migrates over repos that don't exist on GitHub
    def sync_repos(self, push_to_org, repositories, bitbucket_account_id, bitbucket_access_token, github_account_id,
                   github_access_token):
        # Make a folder to clone repos from BitBucket
        cur_dir_path = os.getcwd()
        os.chdir(cur_dir_path)
        is_dir = os.path.isdir("syncDirectory")
        if (not is_dir):
            self.log.debug("Created directory syncDirectory")
            os.mkdir("syncDirectory")
        os.chdir("syncDirectory")

        for repo in repositories:
            repo_name = repo['name']
            if ('github_link' in repo):
                github_link = repo['github_link']
            else:
                repo['github_link'] = self.make_new_repo(push_to_org, repo, github_account_id, github_access_token)
                github_link = repo['github_link']
            bitbucket_link = repo['bitbucket_link']

            self.log.info("Syncing repo {}".format(repo_name), repo_name=repo_name)
            # Clone the repository from BitBucket
            if (not os.path.isdir(repo_name)):
                bitbucket_link_domain = bitbucket_link.split("//")[1]
                self.log.info("Cloning repo {}".format(repo_name), repo_name=repo_name)
                os.system("git clone https://{}:{}@{}".format(bitbucket_account_id, bitbucket_access_token,
                                                              bitbucket_link_domain))
            os.chdir(repo_name)
            # Make local tracking branches for all remote branches on origin (bitbucket)
            self.log.info("Setting origin for {} to bitbucket".format(repo_name),
                          repo_name=repo_name,
                          bitbucket_link=bitbucket_link)
            os.system("git remote set-url origin {}".format(bitbucket_link))
            self.log.info("Setting up new tracking branches and pulling {}".format(repo_name), repo_name=repo_name)
            os.system("for remote in `git branch -r`; do git branch --track ${remote#origin/} $remote; done")
            os.system("git pull --all")
            # Change origin to point to GitHub
            self.log.info("Setting origin for {} to github".format(repo_name),
                          repo_name=repo_name,
                          github_link=github_link)
            os.system("git remote set-url origin {}".format(github_link))
            # First push all the tags including new ones that might be created
            github_link_domain = github_link.split("//")[1]
            self.log.info("Pushing all tags for {}".format(repo_name), repo_name=repo_name)
            os.system("git push https://{}:{}@{} --tags".format(github_account_id, github_access_token,
                                                                github_link_domain))
            # Push all branches including new ones that might be created
            self.log.info("Pushing all branches for {}".format(repo_name), repo_name=repo_name)
            os.system("git push https://{}:{}@{} --all".format(github_account_id, github_access_token,
                                                               github_link_domain))
            self.log.debug("{} synced".format(repo_name), repo_name=repo_name)
            utils.LogUtils.log_light(color.Fore.GREEN, "{} synced".format(repo_name))
            os.chdir("..")

    # Get list of all teams from GHE target org
    def get_teams_info(self, github_access_token):
        self.log.info("Fetching teams list from GitHub")
        teams_info_list = requests.get(self.github_api + "/orgs/{}/teams".format(self.target_org),
                                       headers={"Authorization": "Bearer {}".format(github_access_token)})
        teams_info_list = json.loads(teams_info_list.text)
        return teams_info_list

    # Assign the selected repos to selected teams in the organization
    def assign_repos_to_teams(self, repo_assignment, github_access_token):
        admin_permissions = {'permission': 'admin'}
        assign_result = {}
        for team, repos in repo_assignment.items():  # key, value :: team, repos
            self.log.info("Assigning repos to {} team".format(team), teamName=team)

            # Get Team's ID
            self.log.info("Fetching Team ID", teamName=team)
            team_info = requests.get(self.github_api + "/orgs/{}/teams/{}".format(self.target_org, team),
                                     headers={"Authorization": "Bearer {}".format(github_access_token)})
            team_info = json.loads(team_info.text)
            team_id = team_info['id']

            success_count = 0
            failure_count = 0
            for repo in repos:
                # Assign repo to team
                assign_response = requests.put(self.github_api +
                                               "/teams/{}/repos/{}/{}".format(team_id, self.target_org, repo),
                                               data=json.dumps(admin_permissions),
                                               headers={"Authorization": "Bearer {}".format(github_access_token)})
                if (assign_response.status_code != 204):
                    failure_count += 1
                    self.log.warning("Failed to assign {} repo to {} team. Code {}".format(
                        repo, team, assign_response.status_code),
                                     repo_name=repo,
                                     teamName=team,
                                     errorCode=assign_response.status_code)
                else:
                    success_count += 1
                    self.log.debug("Assigned {} repo to {} team".format(repo, team), repo_name=repo, teamName=team)
            assign_result[team] = {'success': success_count, 'failure': failure_count}
            self.log.debug("Assigned {} repos to {} team".format(success_count, team),
                           teamName=team,
                           success_count=success_count)
            if (failure_count != 0):
                self.log.warning("Failed to assign {} repos to {} team".format(failure_count, team),
                                 teamName=team,
                                 failure_count=failure_count)
        return assign_result