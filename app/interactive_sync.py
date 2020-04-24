# Library imports
import questionary
import os

# Custom imports
from app import utils, cred_operations, repo_operations


def start_session(bitbucket_account_id, bitbucket_access_token, github_account_id, github_access_token, bitbucket_api,
                  github_api, prefix, console_log_level, console_log_normal, file_log_level):
    # Objects for operations related to credentials and repository actions
    cred_ops = cred_operations.CredOps(bitbucket_api, github_api, console_log_level, console_log_normal, file_log_level)
    repo_ops = repo_operations.RepoOps(bitbucket_api, github_api, prefix, console_log_level, console_log_normal,
                                       file_log_level)
    log = utils.LogUtils.get_logger(os.path.basename(__file__), console_log_level, console_log_normal, file_log_level)
    target_org = utils.ReadUtils.get_target_org()
    # Ask for migration destination
    push_answer = questionary.select("Migrate repositories to?",
                                     choices=["GitHub {} org".format(target_org), "Personal Github Account"]).ask()
    push_to_org = push_answer == "GitHub {} org".format(target_org)

    # Check if credentials are right and can push to the chosen destination
    github_push_check = cred_ops.check_github_push_creds(push_to_org, github_account_id, github_access_token)
    github_pull_check = cred_ops.check_github_pull_creds(github_access_token)
    if (not (github_push_check and github_pull_check)):
        exit(0)

    # Get list of projects
    project_names = repo_ops.get_bitbucket_projects(bitbucket_access_token)

    # Ask which project to migrate
    project_answer = questionary.select('Which project to migrate? (Enter to select)', choices=project_names).ask()

    # Check access to BitBucket project and check GitHub credentials
    [project_name, project_key] = project_answer.split(":")
    bitbucket_pull_check = cred_ops.check_bitbucket_pull_creds(project_key, bitbucket_access_token)
    if (not bitbucket_pull_check):
        exit(1)

    # Get list of all repos
    repo_names = repo_ops.get_bitbucket_repos(project_key, bitbucket_access_token)
    repo_list = [{'name': "{}".format(repo)} for repo in repo_names]

    # Ask which repos to migrate
    repo_answers = questionary.checkbox("Which repos to migrate from {}:{}?".format(project_name, project_key),
                                        choices=repo_list).ask()

    # Process repos to obtain details
    processed_repos, total_repos, new_repos = repo_ops.process_repos(project_key, repo_answers, push_to_org,
                                                                     bitbucket_access_token, github_account_id,
                                                                     github_access_token)
    if (total_repos == 0):
        log.debug("NO REPOSITORIES SYNCED OR MIGRATED")
        exit(0)
    # Used later for team assignments
    prefixed_migration_repos = [{
        'name': prefix + repo['name']
    } for repo in processed_repos if ('github_link' not in repo)]

    # Confirm to proceed with syncing and migration
    confirm_migrate = questionary.confirm('Proceed with syncing {} and migrating {} repos?'.format(
        total_repos - new_repos, new_repos)).ask()
    if (not confirm_migrate):
        log.debug("NO REPOSITORIES SYNCED OR MIGRATED")
        exit(0)

    # Sync existing repos and migrate over the new repos
    repo_ops.sync_repos(push_to_org, processed_repos, bitbucket_account_id, bitbucket_access_token, github_account_id,
                        github_access_token)
    log.debug("Successful - repositories synced/migrated to GitHub",
              total_repos=total_repos,
              synced_repos=total_repos - new_repos,
              migrated_repos=new_repos)

    # --------- TEAM ASSIGNMENT ---------
    if (not push_to_org):
        exit(0)
    confirm_assign_to_team = questionary.confirm(
        'Do you want to assign some of the migrated repos to different teams?').ask()
    if (not confirm_assign_to_team):
        log.debug("No migrated repositories assigned to teams", new_repos=new_repos)
        exit(0)

    # Fetch list of existing teams on github
    teams_info_list = repo_ops.get_teams_info(github_access_token)
    teams_checklist = [{'name': team['slug']} for team in teams_info_list]

    # Ask which teams to assign repos to
    selected_teams = questionary.checkbox('Select the teams to which you want to assign the repos',
                                          choices=teams_checklist).ask()

    # print(json.dumps())
    # Get all repos that were newly created and migrated
    # allMigratedRepos = [ {'name': repo['name']} for repo in processed_repos if ('github_link' not in repo) ]

    # print(allMigratedRepos)
    # Ask which repos to assign to which team
    repo_assignment = {}
    for team in selected_teams:
        repos_for_teams = questionary.checkbox('Select the repos to assign to {} team'.format(team),
                                               choices=prefixed_migration_repos).ask()
        if (len(repos_for_teams) != 0):
            repo_assignment[team] = repos_for_teams
        else:
            log.debug("No repositories selected to assign to team", team_name=team)

    # Assign the repos to selected teams
    repo_ops.assign_repos_to_teams(repo_assignment, github_access_token)
