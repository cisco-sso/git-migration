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
    def __init__(self, bitbucket_api, github_api, prefix, master_branch_prefix, console_log_level, console_log_normal,
                 file_log_level):
        self.bitbucket_api = bitbucket_api
        self.github_api = github_api
        self.prefix = prefix
        self.log = utils.LogUtils.get_logger(os.path.basename(__file__), console_log_level, console_log_normal,
                                             file_log_level)
        self.target_org = utils.ReadUtils.get_target_org()
        self.master_branch_prefix = master_branch_prefix

    # Returns list of all projects on BitBucket
    def get_bitbucket_projects(self, bitbucket_access_token):
        project_names = []
        is_last_page = False
        start = 0
        # Get list of projects
        self.log.info("Fetching project list")
        while (not is_last_page):
            projects_url = self.bitbucket_api + f"/projects/?start={start}"
            projects = requests.get(projects_url, headers={"Authorization": f"Bearer {bitbucket_access_token}"})
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
            project_repos_link = self.bitbucket_api + f"/projects/{project_key}/repos?start={start}"
            project_repos = requests.get(project_repos_link,
                                         headers={"Authorization": f"Bearer {bitbucket_access_token}"})
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

    # Returns a list of repo objects with information regarding which teams they need to be assigned to
    def populate_team_info(self, project_key, bitbucket_repo_names, to_include, to_exclude, github_access_token):
        repositories = []

        # First make a mapping of which repos are assigned to which teams (can be multiple teams)
        # Then transform to a list of repos and return
        repository_team_mapping = {}

        # To verify if the teams mentioned in the config files actually exist on the org
        teams_list = self.get_teams_info(github_access_token)
        teams_list = [team['slug'] for team in teams_list]

        # If include is not mentioned in config file
        if to_include is None:
            self.log.warning("Nothing to include", project_key=project_key)
            return repositories

        # Boolean to use/not-use regex matching for repository names
        include_regex = to_include["regex"] if ("regex" in to_include) else False
        include_config = to_include["repo_config"] if ("repo_config" in to_include) else to_include

        # config for repositories to include from the current project
        project_include_config = include_config[project_key] if (project_key in include_config) else []
        if not project_include_config:
            self.log.warning("Nothing to include", project_key=project_key)
            return repositories

        # Boolean to use/not-use regex matching for repository names in this project
        project_regex = project_include_config["regex"] if ("regex" in project_include_config) else include_regex
        project_include_config = project_include_config["repo_config"] if (
            "repo_config" in project_include_config) else project_include_config
        for repo_or_team in project_include_config:
            if isinstance(repo_or_team, str):  # Repository name
                if (not project_regex):
                    # No regex matching for repository names, exact match
                    # Add START (^) and END ($) regex symbols and use regex itself instead of string matching
                    repo_name_regex = f"^{repo_or_team}$"
                    filtered_repo_list = utils.RegexUtils.filter_repos(bitbucket_repo_names, [repo_name_regex])
                    if (filtered_repo_list and (repo_or_team not in repository_team_mapping)):
                        repository_team_mapping[repo_or_team] = []
                    else:
                        self.log.error("Could not find the repository mentioned in config file",
                                       repo_name=repo_or_team,
                                       project_key=project_key)
                        self.log.warning("Skipping repository. Recheck name and project",
                                         repo_name=repo_or_team,
                                         project_key=project_key)
                else:
                    # Regex matching of repository names
                    repo_names = utils.RegexUtils.filter_repos(bitbucket_repo_names, [repo_or_team])
                    for repo_name in repo_names:
                        if (repo_name not in repository_team_mapping):
                            repository_team_mapping[repo_name] = []
            elif isinstance(repo_or_team, dict):  # Team assignment
                # Create a mapping of repo_names and their assigned teams (can be multiple teams)
                for team_name, team_config in repo_or_team.items():

                    # Boolean to use/not-use regex matching for repository names in this team
                    team_regex = team_config["regex"] if ("regex" in team_config) else project_regex
                    team_config = team_config["repo_config"] if ("repo_config" in team_config) else team_config

                    repo_names = team_config

                    # Assign to the mentioned team only if the team with the name exists on the org
                    team_found = True
                    if (team_name not in teams_list):
                        self.log.error("Could not find team mentioned in config file", team_name=team_name)
                        team_found = False

                    if (not team_regex):
                        # No regex matching for repository names, exact match
                        for repo_name in repo_names:
                            # Add START (^) and END ($) regex symbols and use regex itself instead of string matching
                            repo_name_regex = f"^{repo_name}$"
                            filtered_repo_list = utils.RegexUtils.filter_repos(bitbucket_repo_names, [repo_name_regex])
                            if (filtered_repo_list and (repo_name not in repository_team_mapping)):
                                repository_team_mapping[repo_name] = [team_name] if team_found else []
                            elif (filtered_repo_list):
                                repository_team_mapping[repo_name] += [team_name] if team_found else []
                            else:
                                self.log.error("Could not find the repository mentioned in config file",
                                               repo_name=repo_or_team,
                                               project_key=project_key)
                                self.log.warning("Skipping repository. Recheck name and project",
                                                 repo_name=repo_or_team,
                                                 project_key=project_key)
                    else:
                        # Regex matching of repository names
                        repos_to_assign = utils.RegexUtils.filter_repos(bitbucket_repo_names, repo_names)
                        for repo_name in repos_to_assign:
                            if (repo_name not in repository_team_mapping):
                                repository_team_mapping[repo_name] = [team_name] if team_found else []
                            else:
                                repository_team_mapping[repo_name] += [team_name] if team_found else []
            else:
                continue
        # Convert mapping to objects containing info about each repo
        for repo_name, team_names in repository_team_mapping.items():
            if (team_names):
                repositories.append({"name": repo_name, "teams": team_names})
            else:
                repositories.append({"name": repo_name})

        # If exclude is not mentioned in config file
        if (to_exclude is None):
            self.log.debug("Nothing to exclude", project_key=project_key)
            return repositories

        # Boolean to use/not-use regex matching for repository names
        exclude_regex = to_exclude["regex"] if ("regex" in to_exclude) else False
        exclude_config = to_exclude["repo_config"] if ("repo_config" in to_exclude) else to_exclude
        project_exclude_config = exclude_config[project_key] if (project_key in exclude_config) else []

        if not project_exclude_config:
            self.log.debug("Nothing to exclude", project_key=project_key)
            return repositories

        # Boolean to use/not-use regex matching for repository names for this project
        project_exclude_regex = project_exclude_config["regex"] if ("regex"
                                                                    in project_exclude_config) else exclude_regex
        project_exclude_config = project_exclude_config["repo_config"] if (
            "repo_config" in project_exclude_config) else project_exclude_config

        if (not project_exclude_regex):  # No regex matching for excluding repo names
            # Add START (^) and END ($) regex symbols and use regex itself instead of string matching
            project_exclude_config = [f"^{repo_name}$" for repo_name in project_exclude_config]
        repositories = utils.RegexUtils.filter_repo_dicts(repositories, project_exclude_config, exclude_matches=True)
        return repositories

    # Process the list of repositories for a project and return metadata and repository links
    def process_repos(self, project_key, repositories, push_to_org, bitbucket_access_token, github_account_id,
                      github_access_token):
        processed_repos = []
        new_repos = 0
        self.log.info("Processing repos from project", project_key=project_key)

        for repo in repositories:

            if isinstance(repo, str):  # repositories is a list of repository names
                # Add name
                repo_name = repo
                repo_info = {"name": repo_name}
            else:  # repositories is a list of repository dicts
                repo_name = repo["name"]
                repo_info = repo

            bitbucket_repo_response = requests.get(self.bitbucket_api + f"/projects/{project_key}/repos/{repo_name}",
                                                   headers={"Authorization": f"Bearer {bitbucket_access_token}"})

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

            # Use prefixed repo names while checking for anything on GitHub
            prefixed_repo_name = self.prefix + repo_name
            # Add GitHub Link
            if (push_to_org):
                # Check if same repository already exists on GitHub target org
                github_org_repo_check_link = self.github_api + f"/repos/{self.target_org}/{prefixed_repo_name}"
                github_org_repo_check = requests.get(github_org_repo_check_link,
                                                     headers={"Authorization": f"Bearer {github_access_token}"})
                # Repository with a similar name already exists on GitHub
                if (github_org_repo_check.status_code == 200):  # Existing repository
                    github_org_repo_check = json.loads(github_org_repo_check.text)
                    self.log.debug("Repository exists on organization",
                                   exists="YES",
                                   repo_name=prefixed_repo_name,
                                   prefix=self.prefix,
                                   target_org=self.target_org)
                    repo_info["github_link"] = github_org_repo_check["clone_url"]
                elif (github_org_repo_check.status_code != 404):  # Error
                    self.log.error("Failed to check for repository on github",
                                   result="FAILED",
                                   repo_name=prefixed_repo_name,
                                   prefix=self.prefix,
                                   status_code=github_org_repo_check.status_code)
                    continue
                else:  # 404 Not Found
                    new_repos += 1
                    self.log.debug("Repository does not exist on organization",
                                   exists="NO",
                                   repo_name=prefixed_repo_name,
                                   prefix=self.prefix,
                                   target_org=self.target_org)
            else:
                # Check if same repository already exists on GitHub
                github_repo_check_link = self.github_api + f"/repos/{github_account_id}/{prefixed_repo_name}"
                github_repo_check = requests.get(github_repo_check_link,
                                                 headers={"Authorization": f"Bearer {github_access_token}"})
                # Repository with a similar name already exists on GitHub
                if (github_repo_check.status_code == 200):  # Existing repository
                    github_repo_check = json.loads(github_repo_check.text)
                    self.log.debug("Repository exists on GHE account",
                                   exists="YES",
                                   repo_name=prefixed_repo_name,
                                   prefix=self.prefix,
                                   github_account_id=github_account_id)
                    repo_info["github_link"] = github_repo_check["clone_url"]
                elif (github_repo_check.status_code != 404):  # Error
                    self.log.error("Failed to check for repository on github",
                                   result="FAILED",
                                   repo_name=prefixed_repo_name,
                                   prefix=self.prefix,
                                   status_code=github_repo_check.status_code)
                else:  # 404 Not Found
                    new_repos += 1
                    self.log.debug("Repository does no exist on GHE account",
                                   exists="NO",
                                   repo_name=prefixed_repo_name,
                                   prefix=self.prefix,
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
        prefixed_repo_name = self.prefix + repo_name

        request_payload = {"name": utils.StringUtils.remove_control_characters(prefixed_repo_name), "private": True}
        if ("description" in repo):
            request_payload["description"] = utils.StringUtils.remove_control_characters(repo["description"])

        if (push_to_org):
            # Create new repo of same name on GitHub target org
            git_response = requests.post(self.github_api + f"/orgs/{self.target_org}/repos",
                                         data=json.dumps(request_payload),
                                         headers={"Authorization": f"Bearer {github_access_token}"})
            if (git_response.status_code != 201):
                self.log.error("Failed to create new repository on organization",
                               result="FAILED",
                               repo_name=prefixed_repo_name,
                               prefix=self.prefix,
                               target_org=self.target_org)
                return None
            self.log.debug("New repository created on GitHub organization",
                           result="SUCCESS",
                           repo_name=prefixed_repo_name,
                           prefix=self.prefix,
                           target_org=self.target_org)
        else:
            # Create new repo of same name on GitHub Account
            git_response = requests.post(self.github_api + "/user/repos",
                                         data=json.dumps(request_payload),
                                         headers={"Authorization": f"Bearer {github_access_token}"})
            if (git_response.status_code != 201):
                self.log.error("Failed to create new repository on personal account",
                               result="FAILED",
                               repo_name=prefixed_repo_name,
                               prefix=self.prefix,
                               github_account_id=github_account_id)
                return None
            self.log.debug("New repository created on GitHub account",
                           result="SUCCESS",
                           repo_name=prefixed_repo_name,
                           prefix=self.prefix,
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
            prefixed_repo_name = self.prefix + repo_name
            teams_to_assign = repo["teams"] if ("teams" in repo) else []
            if ('github_link' in repo):
                github_link = repo['github_link']
                repo['new_migration'] = False
                pass
            else:
                github_link = self.make_new_repo(push_to_org, repo, github_account_id, github_access_token)
                if (github_link is None):
                    self.log.error("Failed to make new repository", result="FAILED", repo_name=prefixed_repo_name)
                    continue
                repo['github_link'] = github_link
                repo['new_migration'] = True
            
            # Use this instead of setting the authenticated link as a new remote.
            # Remote links get stored in git config
            bitbucket_link = repo['bitbucket_link']
            bitbucket_link_domain = bitbucket_link.split("//")[1]
            authenticated_bitbucket_link = f"https://{bitbucket_account_id}:{bitbucket_access_token}@{bitbucket_link_domain}"

            self.log.info("Syncing repository", repo_name=repo_name)

            # Clone the repository from BitBucket
            if (not os.path.isdir(repo_name)):
                self.log.info("Cloning repository", repo_name=repo_name)
                try:
                    git.clone(authenticated_bitbucket_link)
                    self.log.debug("Cloned repository", result="SUCCESS", repo_name=repo_name)
                except ErrorReturnCode as e:
                    self.log.error("Failed to clone repository",
                                   result="FAILED",
                                   repo_name=repo_name,
                                   exit_code=e.exit_code)
                    continue

            os.chdir(repo_name)  # IMPORTANT DO NOT DELETE
            # Sync all tags individually
            tags_sync_success, all_tags, failed_tags = self.sync_tags(repo, bitbucket_account_id, bitbucket_access_token, github_account_id, github_access_token)
            if (not tags_sync_success):
                self.log.warning("Failed to sync tags for repository",
                                 result="FAILED",
                                 repo_name=repo_name,
                                 failed_tags=failed_tags)
            # Sync all branches individually
            branches_sync_success, all_branches, failed_branches = self.sync_branches(
                repo, bitbucket_account_id, bitbucket_access_token, github_account_id, github_access_token)
            if (not branches_sync_success):
                self.log.warning("Failed to sync branches for repository",
                                 result="FAILED",
                                 repo_name=repo_name,
                                 failed_branches=failed_branches)

            if (tags_sync_success and branches_sync_success):
                self.log.debug("Successfully synced all tags and branches for repository",
                               result="SUCCESS",
                               repo_name=repo_name)
            # Assign repo to teams, reuse existing function assign_repos_to_teams()
            if (push_to_org and github_link and teams_to_assign):
                repo_assignment = {}
                for team_name in teams_to_assign:
                    repo_assignment[team_name] = [prefixed_repo_name]
                self.assign_repos_to_teams(repo_assignment, github_access_token)
            os.chdir("..")  # IMPORTANT DO NOT DELETE

    def sync_tags(self, repo, bitbucket_account_id, bitbucket_access_token, github_account_id, github_access_token):
        # Everytime, tags are fetched from remote (bitbucket) and then pushed to github
        repo_name = repo['name']
        prefixed_repo_name = self.prefix + repo_name
        github_link = repo['github_link']
        bitbucket_link = repo['bitbucket_link']

        # Use this instead of setting the authenticated link as a new remote.
        # Remote links get stored in git config
        github_link_domain = github_link.split("//")[1]
        authenticated_github_link = f"https://{github_account_id}:{github_access_token}@{github_link_domain}"

        bitbucket_link_domain = bitbucket_link.split("//")[1]
        authenticated_bitbucket_link = f"https://{bitbucket_account_id}:{bitbucket_access_token}@{bitbucket_link_domain}"

        git.remote('set-url', 'origin', bitbucket_link)
        self.log.debug("Syncing Tags. Set origin to BitBucket", repo_name=repo_name, bitbucket_link=bitbucket_link)

        # Fetch tags from origin (bitbucket)
        self.log.info("Fetching refs (tags) from origin", repo_name=repo_name)
        # git.fetch('origin')
        git.fetch(authenticated_bitbucket_link)
        self.log.debug("Fetched refs (tags) from BitBucket", result="SUCCESS", repo_name=repo_name)

        # List all tags
        tags = git.tag().split('\n')
        tags = [tag.lstrip().rstrip() for tag in tags if tag]

        success_tags = []
        failed_tags = []

        # Set origin to github
        # git.remote('set-url', 'origin', github_link)
        self.log.debug("Syncing tags. Set origin to Github",
                       repo_name=prefixed_repo_name,
                       prefix=self.prefix,
                       github_link=github_link)

        # Push each tag individually, log error if any fails and continue to next tag
        for tag_name in tags:
            self.log.info("Syncing tag for repository", repo_name=repo_name, tag_name=tag_name)
            try:
                tag_refspec = f"refs/tags/{tag_name}:refs/tags/{tag_name}"
                git.push(authenticated_github_link, tag_refspec)
                self.log.debug("Pushed tag for repository",
                               result="SUCCESS",
                               repo_name=prefixed_repo_name,
                               prefix=self.prefix,
                               tag_name=tag_name)
                success_tags.append(tag_name)
            except ErrorReturnCode as e:
                # Redact or remove the access token before logging
                stderr = utils.StringUtils.redact_error(e.stderr, github_access_token, "<ACCESS-TOKEN>")
                self.log.error("Failed to push tag to github",
                               result="FAILED",
                               repo_name=prefixed_repo_name,
                               prefix=self.prefix,
                               tag_name=tag_name,
                               exit_code=e.exit_code,
                               stderr=stderr)
                failed_tags.append(tag_name)
                continue

        tags_sync_success = set(tags) == set(success_tags)
        return tags_sync_success, tags, failed_tags

    def sync_branches(self, repo, bitbucket_account_id, bitbucket_access_token, github_account_id, github_access_token):
        repo_name = repo['name']
        prefixed_repo_name = self.prefix + repo_name
        github_link = repo['github_link']
        bitbucket_link = repo['bitbucket_link']

        # Boolean: whether the repo is a new migration to GitHub
        new_migration = repo['new_migration']

        # Use this instead of setting the authenticated link as a new remote.
        # Remote links get stored in git config
        github_link_domain = github_link.split("//")[1]
        authenticated_github_link = f"https://{github_account_id}:{github_access_token}@{github_link_domain}"

        bitbucket_link_domain = bitbucket_link.split("//")[1]
        authenticated_bitbucket_link = f"https://{bitbucket_account_id}:{bitbucket_access_token}@{bitbucket_link_domain}"

        # Set remote to bitbucket
        git.remote('set-url', 'origin', bitbucket_link)
        self.log.debug("Syncing branches. Set origin to Bitbucket", repo_name=repo_name, bitbucket_link=bitbucket_link)

        # Fetch branches from origin (bitbucket)
        self.log.info("Fetching refs (branches) from origin", repo_name=repo_name)
        # git.fetch('origin')
        git.fetch(authenticated_bitbucket_link)
        self.log.debug("Fetched refs (branches) from BitBucket", result="SUCCESS", repo_name=repo_name)

        # List remote branches
        remote_branches = git.branch("-r").split("\n")
        remote_branches = [
            remote.lstrip().rstrip() for remote in remote_branches
            if (remote and not re.match("^.*/HEAD -> .*$", remote))
        ]

        try:
            # if master exists on origin, move that to the start of the array
            # pushing 'master' first makes it the default branch on github
            has_master = remote_branches.remove('origin/master') == None
            remote_branches = ['origin/master'] + remote_branches
        except:
            # 'master' did not exist on origin
            pass

        success_branches = []
        failed_branches = []

        # Push changes to each branch individually, log error if any fails and continue to next branch
        for remote in remote_branches:
            [remote_name, branch_name] = remote.split('/', 1)

            self.log.info("Syncing branch for repository", repo_name=repo_name, branch_name=branch_name)

            if (remote_name == 'origin'):

                # Different way to handle master branches, support prefixing.
                if (branch_name == "master"):
                    master_branch_refspecs = []
                    prefix_exists = self.master_branch_prefix != ""
                    if (prefix_exists):
                        # Order is IMPORTANT, 'master' should be added before prefixed_master.
                        # Default branch is the first branch that is pushed to GitHub
                        if (new_migration):
                            master_branch_refspecs.append(f"refs/remotes/origin/{branch_name}:refs/heads/{branch_name}")
                        prefixed_master_branch_name = self.master_branch_prefix + branch_name
                        master_branch_refspecs.append(f"refs/remotes/origin/{branch_name}:refs/heads/{prefixed_master_branch_name}")
                    else:
                        master_branch_refspecs.append(f"refs/remotes/origin/{branch_name}:refs/heads/{branch_name}")
                    for branch_refspec in master_branch_refspecs:
                        target_branch_name = branch_refspec.split('/')[-1]
                        try:
                            self.log.info("Pushing branch for repository",
                                        repo_name=prefixed_repo_name,
                                        prefix=self.prefix,
                                        branch_name=branch_name,
                                        target_branch_name=target_branch_name)
                            git.push(authenticated_github_link, branch_refspec)
                            # Success on syncing current branch
                            self.log.debug("Successfully synced branch for repository",
                                        result="SUCCESS",
                                        repo_name=prefixed_repo_name,
                                        prefix=self.prefix,
                                        branch_name=branch_name,
                                        target_branch_name=target_branch_name)
                            success_branches.append(branch_name)
                        except ErrorReturnCode as e:
                            # Redact or remove the access token before logging
                            stderr = utils.StringUtils.redact_error(e.stderr, github_access_token, "<ACCESS-TOKEN>")
                            self.log.error("Failed to push changes to origin branch",
                                        result="FAILED",
                                        repo_name=prefixed_repo_name,
                                        prefix=self.prefix,
                                        branch_name=branch_name,
                                        target_branch_name=target_branch_name,
                                        exit_code=e.exit_code,
                                        stderr=stderr)
                            failed_branches.append(branch_name)
                            continue # Continue to the next master_branch_refspec
                    continue # Continue to the next branch

                branch_refspec = f"refs/remotes/origin/{branch_name}:refs/heads/{branch_name}"
                try:
                    self.log.info("Pushing branch for repository",
                                  repo_name=prefixed_repo_name,
                                  prefix=self.prefix,
                                  branch_name=branch_name)
                    git.push(authenticated_github_link, branch_refspec)
                    # Success on syncing current branch
                    self.log.debug("Successfully synced branch for repository",
                                   result="SUCCESS",
                                   repo_name=prefixed_repo_name,
                                   prefix=self.prefix,
                                   branch_name=branch_name)
                    success_branches.append(branch_name)
                except ErrorReturnCode as e:
                    # Redact or remove the access token before logging
                    stderr = utils.StringUtils.redact_error(e.stderr, github_access_token, "<ACCESS-TOKEN>")
                    self.log.error("Failed to push changes to origin branch",
                                   result="FAILED",
                                   repo_name=prefixed_repo_name,
                                   prefix=self.prefix,
                                   branch_name=branch_name,
                                   exit_code=e.exit_code,
                                   stderr=stderr)
                    failed_branches.append(branch_name)
                    continue
            else:
                continue

        all_remote_branches = [branch_name.split('origin/')[1] for branch_name in remote_branches]
        branches_sync_success = set(all_remote_branches) == set(success_branches)
        return branches_sync_success, all_remote_branches, failed_branches

    # Get list of all teams from GHE target org
    def get_teams_info(self, github_access_token):
        self.log.info("Fetching teams list from GitHub")
        teams_info_list = requests.get(self.github_api + f"/orgs/{self.target_org}/teams",
                                       headers={"Authorization": f"Bearer {github_access_token}"})
        if (teams_info_list.status_code != 200):
            self.log.error("Failed to fetch teams list", result="FAILED", target_org=self.target_org)
            exit(1)
        teams_info_list = json.loads(teams_info_list.text)
        return teams_info_list

    # Assign the selected repos to selected teams in the organization
    def assign_repos_to_teams(self, repo_assignment, github_access_token):
        admin_permissions = {'permission': 'admin'}
        assign_result = {}
        for team, prefixed_repos in repo_assignment.items():  # key, value :: team, repos
            self.log.info("Assigning repos to team", teamName=team)

            # Get Team's ID
            self.log.info("Fetching Team ID", teamName=team)
            team_info = requests.get(self.github_api + f"/orgs/{self.target_org}/teams/{team}",
                                     headers={"Authorization": f"Bearer {github_access_token}"})
            if (team_info.status_code != 200):
                self.log.error("Failed to fetch team information", result="FAILED", team_name=team)
                self.log.error("No repositories assigned to team", result="FAILED", team_name=team)
                continue
            team_info = json.loads(team_info.text)
            team_id = team_info['id']

            success_count = 0
            failure_count = 0
            for prefixed_repo_name in prefixed_repos:
                # Assign repo to team
                assign_response = requests.put(self.github_api +
                                               f"/teams/{team_id}/repos/{self.target_org}/{prefixed_repo_name}",
                                               data=json.dumps(admin_permissions),
                                               headers={"Authorization": f"Bearer {github_access_token}"})
                if (assign_response.status_code != 204):
                    failure_count += 1
                    self.log.error("Failed to assign repository to team",
                                   result="FAILED",
                                   repo_name=prefixed_repo_name,
                                   prefix=self.prefix,
                                   teamName=team,
                                   status_code=assign_response.status_code)
                else:
                    success_count += 1
                    self.log.debug("Assigned repository to team",
                                   result="SUCCESS",
                                   repo_name=prefixed_repo_name,
                                   prefix=self.prefix,
                                   teamName=team)
            assign_result[team] = {'success': success_count, 'failure': failure_count}
            self.log.debug("Assigned repositories to team", teamName=team, success_count=success_count)
            if (failure_count != 0):
                self.log.warning("Failed to assign repositories to team",
                                 result="FAILED",
                                 teamName=team,
                                 failure_count=failure_count)
        return assign_result
