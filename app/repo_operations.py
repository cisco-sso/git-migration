# Library imports
import json
import os
import re
import requests
from sh.contrib import git
from sh import ErrorReturnCode

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
            if (projects.status_code == 200):
                self.log.debug("Fetched project list", result="SUCCESS")
                projects = json.loads(projects.text)
            else:
                self.log.error("Failed to fetch project list", result="FAILED", status_code=projects.status_code)
                exit(1)

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
        self.log.info("Fetching repository list", project_key=project_key)
        while (not is_last_page):
            # Get list of repos under the mentioned project on BitBucket
            project_repos_link = self.bitbucket_api + "/projects/{}/repos?start={}".format(project_key, start)
            project_repos = requests.get(project_repos_link,
                                         headers={"Authorization": "Bearer {}".format(bitbucket_access_token)})
            # Error while fetching repos
            if (project_repos.status_code != 200):
                self.log.error("Failed to fetch repository list",
                               result="FAILED",
                               project_key=project_key,
                               status_code=project_repos.status_code)
                exit(1)

            project_repos = json.loads(project_repos.text)

            # Check if last page
            is_last_page = project_repos["isLastPage"]
            if (not is_last_page):
                start = project_repos["nextPageStart"]

            # Populate the project names
            repo_names += [repo["name"] for repo in project_repos["values"]]
        return repo_names

    # Process the list of repositories for a project and return metadata and repository links
    def process_repos(self, project_key, repositories, push_to_org, bitbucket_access_token, github_account_id,
                      github_access_token):
        processed_repos = []
        new_repos = 0
        self.log.info("Processing repos from project", project_key=project_key)

        for repo_name in repositories:
            # Add name
            repo_info = {"name": repo_name}
            bitbucket_repo_response = requests.get(
                self.bitbucket_api + "/projects/{}/repos/{}".format(project_key, repo_name),
                headers={"Authorization": "Bearer {}".format(bitbucket_access_token)})

            if (bitbucket_repo_response.status_code == 404):
                self.log.error("Repository not found on BitBucket", repo_name=repo_name)
                continue
            elif (bitbucket_repo_response.status_code != 200):
                self.log.error("Failed to process repository", result="FAILED", repo_name=repo_name)
                continue
            else:  # Success: 200 OK
                bitbucket_repo_response = json.loads(bitbucket_repo_response.text)

            # Add description
            if ("description" in bitbucket_repo_response):
                repo_info["description"] = bitbucket_repo_response["description"]
            # Add BitBucket Link
            link = list(filter(utils.MiscUtils.is_http, bitbucket_repo_response["links"]["clone"]))
            repo_info["bitbucket_link"] = link[0]["href"]
            self.log.debug("Added repository details from BitBucket", repo_name=repo_name)

            # Add GitHub Link
            if (push_to_org):
                # Check if same repository already exists on GitHub target org
                github_org_repo_check_link = self.github_api + "/repos/{}/{}".format(self.target_org, repo_name)
                github_org_repo_check = requests.get(github_org_repo_check_link,
                                                     headers={"Authorization": "Bearer {}".format(github_access_token)})
                # Repository with a similar name already exists on GitHub
                if (github_org_repo_check.status_code == 200):  # Existing repository
                    github_org_repo_check = json.loads(github_org_repo_check.text)
                    self.log.debug("Repository exists on organization",
                                   exists="YES",
                                   repo_name=repo_name,
                                   target_org=self.target_org)
                    repo_info["github_link"] = github_org_repo_check["clone_url"]
                elif (github_org_repo_check.status_code != 404):  # Error
                    self.log.error("Failed to check for repository on github",
                                   result="FAILED",
                                   repo_name=repo_name,
                                   status_code=github_org_repo_check.status_code)
                    continue
                else:  # 404 Not Found
                    new_repos += 1
                    self.log.debug("Repository does not exist on organization",
                                   exists="NO",
                                   repo_name=repo_name,
                                   target_org=self.target_org)
            else:
                # Check if same repository already exists on GitHub
                github_repo_check_link = self.github_api + "/repos/{}/{}".format(github_account_id, repo_name)
                github_repo_check = requests.get(github_repo_check_link,
                                                 headers={"Authorization": "Bearer {}".format(github_access_token)})
                # Repository with a similar name already exists on GitHub
                if (github_repo_check.status_code == 200):  # Existing repository
                    github_repo_check = json.loads(github_repo_check.text)
                    self.log.debug("Repository exists on GHE account",
                                   exists="YES",
                                   repo_name=repo_name,
                                   github_account_id=github_account_id)
                    repo_info["github_link"] = github_repo_check["clone_url"]
                elif (github_repo_check.status_code != 404):  # Error
                    self.log.error("Failed to check for repository on github",
                                   result="FAILED",
                                   repo_name=repo_name,
                                   status_code=github_repo_check.status_code)
                else:  # 404 Not Found
                    new_repos += 1
                    self.log.debug("Repository does no exist on GHE account",
                                   exists="NO",
                                   repo_name=repo_name,
                                   github_account_id=github_account_id)
            processed_repos.append(repo_info)
        total_repos = len(processed_repos)
        self.log.info("Syncing/Migrating repositories to GitHub",
                      total_repos=total_repos,
                      to_sync=total_repos - new_repos,
                      to_migrate=new_repos)
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
            if (git_response.status_code != 201):
                self.log.error("Failed to create new repository on organization",
                               result="FAILED",
                               repo_name=repo_name,
                               target_org=self.target_org)
                return None
            self.log.debug("New repository created on GitHub organization",
                           result="SUCCESS",
                           repo_name=repo_name,
                           target_org=self.target_org)
        else:
            # Create new repo of same name on GitHub Account
            git_response = requests.post(self.github_api + "/user/repos",
                                         data=json.dumps(request_payload),
                                         headers={"Authorization": "Bearer {}".format(github_access_token)})
            if (git_response.status_code != 201):
                self.log.error("Failed to create new repository on personal account",
                               result="FAILED",
                               repo_name=repo_name,
                               github_account_id=github_account_id)
                return None
            self.log.debug("New repository created on GitHub account",
                           result="SUCCESS",
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
                # github_link = repo['github_link']
                pass
            else:
                github_link = self.make_new_repo(push_to_org, repo, github_account_id, github_access_token)
                if (github_link is None):
                    self.log.error("Failed to make new repository", result="FAILED", repo_name=repo_name)
                    continue
                repo['github_link'] = github_link
            bitbucket_link = repo['bitbucket_link']

            self.log.info("Syncing repository", repo_name=repo_name)

            # Clone the repository from BitBucket
            if (not os.path.isdir(repo_name)):

                bitbucket_link_domain = bitbucket_link.split("//")[1]
                self.log.info("Cloning repository", repo_name=repo_name)
                try:
                    git.clone("https://{}:{}@{}".format(bitbucket_account_id, bitbucket_access_token,
                                                        bitbucket_link_domain))
                    self.log.debug("Cloned repository", result="SUCCESS", repo_name=repo_name)
                except ErrorReturnCode as e:
                    self.log.error("Failed to cloen repository",
                                   result="FAILED",
                                   repo_name=repo_name,
                                   exit_code=e.exit_code)
                    continue

            os.chdir(repo_name)  # IMPORTANT DO NOT DELETE
            tags_sync_success, all_tags, failed_tags = self.sync_tags(repo, github_account_id, github_access_token)
            if (not tags_sync_success):
                self.log.warning("Failed to sync tags for repository",
                                 result="FAILED",
                                 repo_name=repo_name,
                                 failed_tags=failed_tags)
            branches_sync_success, all_branches, failed_branches = self.sync_branches(
                repo, github_account_id, github_access_token)
            if (not branches_sync_success):
                self.log.warning("Failed to sync branches for repository",
                                 result="FAILED",
                                 repo_name=repo_name,
                                 failed_branches=failed_branches)

            if (tags_sync_success and branches_sync_success):
                self.log.debug("Successfully synced all tags and branches for repository", repo_name=repo_name)
            os.chdir("..")  # IMPORTANT DO NOT DELETE

    def sync_tags(self, repo, github_account_id, github_access_token):
        # Tags are populated in local repository when a clone is made, NO N***REMOVED*** TO PULL from bitbucket-remote
        # TODO (***REMOVED***): The comment above is no longer true, because you're only cloning
        #   if the directory doesn't exist.  I'm pretty sure you need to fix this.  Nice that you commented this.
        repo_name = repo['name']
        github_link = repo['github_link']
        github_link_domain = github_link.split("//")[1]
        bitbucket_link = repo['bitbucket_link']

        git.remote('set-url', 'origin', bitbucket_link)
        self.log.debug("Syncing Tags. Set origin to BitBucket", repo_name=repo_name, bitbucket_link=bitbucket_link)

        remote_tags = []
        # Get remote tags
        try:
            remote_tags = git('ls-remote', '--tags', 'origin').split('\n')
            remote_tags = [re.sub('^.*\trefs/tags/', '', tag_name) for tag_name in remote_tags if tag_name]
            self.log.debug("Listed remote tags", repo_name=repo_name)
        except ErrorReturnCode as e:
            self.log.warning("Could not list remote tags", repo_name=repo_name, exit_code=e.exit_code)

        # Fetch tags from origin (bitbucket)
        try:
            git.fetch('origin')
            self.log.debug("Fetched tags from BitBucket", result="SUCCESS", repo_name=repo_name)
        except ErrorReturnCode as e:
            self.log.error("Failed to fetch tags from BitBucket",
                           result="FAILED",
                           repo_name=repo_name,
                           exit_code=e.exit_code)
            return False, remote_tags, remote_tags

        tags = git.tag().split('\n')
        tags = [tag.lstrip().rstrip() for tag in tags if tag]

        success_tags = []
        failed_tags = []

        # Set origin to github
        git.remote('set-url', 'origin', github_link)
        self.log.debug("Syncing tags. Set origin to Github", repo_name=repo_name, github_link=github_link)

        # Push each tag individually, log error if any fails and continue to next tag
        for tag_name in tags:
            self.log.info("Syncing tag for repository", repo_name=repo_name, tag_name=tag_name)
            try:
                git.push('https://{}:{}@{}'.format(github_account_id, github_access_token, github_link_domain),
                         tag_name)
                self.log.debug("Pushed tag for repository", result="SUCCESS", repo_name=repo_name, tag_name=tag_name)
                success_tags.append(tag_name)
            except ErrorReturnCode as e:
                # TODO (***REMOVED***): Very nice.  I'd like to see this pattern for the http requests you've made,
                #   where thiere is no error checking.
                self.log.error("Failed to push tag to github",
                               result="FAILED",
                               repo_name=repo_name,
                               tag_name=tag_name,
                               exit_code=e.exit_code,
                               stderr=e.stderr)
                failed_tags.append(tag_name)
                continue

        tags_sync_success = set(tags) == set(success_tags)
        return tags_sync_success, tags, failed_tags

    def sync_branches(self, repo, github_account_id, github_access_token):
        repo_name = repo['name']
        github_link = repo['github_link']
        bitbucket_link = repo['bitbucket_link']
        github_link_domain = github_link.split("//")[1]

        success_branches = []
        failed_branches = []
        local_branches = git.branch().split("\n")
        local_branches = [branch.lstrip('* ').rstrip() for branch in local_branches if (branch)]

        # Set remote to bitbucket
        git.remote('set-url', 'origin', bitbucket_link)
        self.log.debug("Syncing branches. Set origin to Bitbucket", repo_name=repo_name, bitbucket_link=bitbucket_link)

        remote_branches = git.branch("-r").split("\n")
        remote_branches = [
            remote.lstrip().rstrip() for remote in remote_branches
            if (remote and not re.match("^.*/HEAD -> .*$", remote))
        ]

        # Push changes to each branch individually, log error if any fails and continue to next branch
        for remote in remote_branches:
            [remote_name, branch_name] = remote.split('/', 1)

            self.log.info("Syncing branch for repository", repo_name=repo_name, branch_name=branch_name)

            # Set up a tracking branch for the remote branch (bitbucket) if it doesn't already exist locally
            if ((branch_name not in local_branches) and (remote_name == 'origin')):
                # Set up a local tracking branch from origin (bitbucket)
                try:
                    git.branch('--track', branch_name, remote)
                    self.log.debug("Set up tracking branch for repository",
                                   result="SUCCESS",
                                   repo_name=repo_name,
                                   branch_name=branch_name)
                except ErrorReturnCode as e:
                    self.log.error("Failed to setup tracking branch for repository",
                                   result="FAILED",
                                   repo_name=repo_name,
                                   branch_name=branch_name,
                                   exit_code=e.exit_code,
                                   stderr=e.stderr)
                    failed_branches.append(branch_name)
                    continue
            elif (remote_name == 'origin'):
                pass
            else:
                continue

            # Pull changes for the tracking branch from origin (bitbucket)
            # Checkout to the branch
            try:
                git.checkout(branch_name)
                self.log.debug("Checkout to branch on repository",
                               result="SUCCESS",
                               repo_name=repo_name,
                               branch_name=branch_name)
            except ErrorReturnCode as e:
                self.log.error("Failed to checkout to branch on repository",
                               result="SUCCESS",
                               repo_name=repo_name,
                               branch_name=branch_name,
                               exit_code=e.exit_code,
                               stderr=e.stderr)
                failed_branches.append(branch_name)
                continue
            # Pull changes from origin (bitbucket)
            try:
                git.pull(remote_name, branch_name, "--ff-only")
                self.log.debug("Pulled changes from remote branch",
                               result="SUCCESS",
                               repo_name=repo_name,
                               branch_name=branch_name)
            except ErrorReturnCode as e:
                self.log.error("Failed to pull changes from remote branch",
                               result="FAILED",
                               repo_name=repo_name,
                               branch_name=branch_name,
                               exit_code=e.exit_code,
                               stderr=e.stderr)
                failed_branches.append(branch_name)
                continue

            # Push changes to origin (github)
            # Set origin to github
            git.remote('set-url', 'origin', github_link)
            self.log.debug("Syncing branches. Set origin to Github", repo_name=repo_name, github_link=github_link)
            # Push changes to origin
            try:
                self.log.info("Pushing branch for repository", repo_name=repo_name, branch_name=branch_name)
                git.push('https://{}:{}@{}'.format(github_account_id, github_access_token, github_link_domain),
                         branch_name)
                self.log.debug("Pushed changes to origin branch",
                               result="SUCCESS",
                               repo_name=repo_name,
                               branch_name=branch_name)
            except ErrorReturnCode as e:
                self.log.error("Failed to push changes to origin branch",
                               result="FAILED",
                               repo_name=repo_name,
                               branch_name=branch_name,
                               exit_code=e.exit_code,
                               stderr=e.stderr)
                failed_branches.append(branch_name)
                continue
            # Success on syncing current branch
            success_branches.append(branch_name)
            self.log.debug("Successfully synced branch for repository",
                           result="SUCCESS",
                           repo_name=repo_name,
                           branch_name=branch_name)

            # Set origin back to bitbucket so the next branch can pull changes
            git.remote('set-url', 'origin', bitbucket_link)
            self.log.debug("Syncing branches. Set origin to Bitbucket",
                           repo_name=repo_name,
                           bitbucket_link=bitbucket_link)

        all_remote_branches = [branch_name.lstrip('origin/') for branch_name in remote_branches]
        branches_sync_success = set(all_remote_branches) == set(success_branches)
        return branches_sync_success, all_remote_branches, failed_branches

    # Get list of all teams from GHE target org
    def get_teams_info(self, github_access_token):
        self.log.info("Fetching teams list from GitHub")
        teams_info_list = requests.get(self.github_api + "/orgs/{}/teams".format(self.target_org),
                                       headers={"Authorization": "Bearer {}".format(github_access_token)})
        if (teams_info_list.status_code != 200):
            self.log.error("Failed to fetch teams list", result="FAILED", target_org=self.target_org)
            exit(1)
        teams_info_list = json.loads(teams_info_list.text)
        return teams_info_list

    # Assign the selected repos to selected teams in the organization
    def assign_repos_to_teams(self, repo_assignment, github_access_token):
        admin_permissions = {'permission': 'admin'}
        assign_result = {}
        for team, repos in repo_assignment.items():  # key, value :: team, repos
            self.log.info("Assigning repos to team", teamName=team)

            # Get Team's ID
            self.log.info("Fetching Team ID", teamName=team)
            team_info = requests.get(self.github_api + "/orgs/{}/teams/{}".format(self.target_org, team),
                                     headers={"Authorization": "Bearer {}".format(github_access_token)})
            if (team_info.status_code != 200):
                self.log.error("Failed to fetch team information", result="FAILED", team_name=team)
                self.log.error("No repositories assigned to team", result="FAILED", team_name=team)
                continue
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
                    self.log.warning("Failed to assign repository to team",
                                     result="FAILED",
                                     repo_name=repo,
                                     teamName=team,
                                     status_code=assign_response.status_code)
                else:
                    success_count += 1
                    self.log.debug("Assigned repository to team", result="SUCCESS", repo_name=repo, teamName=team)
            assign_result[team] = {'success': success_count, 'failure': failure_count}
            self.log.debug("Assigned repositories to team", teamName=team, success_count=success_count)
            if (failure_count != 0):
                self.log.warning("Failed to assign repositories to team",
                                 result="FAILED",
                                 teamName=team,
                                 failure_count=failure_count)
        return assign_result
