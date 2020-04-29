# The Git-Migration CLI



- Migrate repositories from BitBucket to GitHub Enterprise.
- Keep the GitHub repositories synced with the changes in BitBucket.



### Prerequisites:

- python3, pip3
- pipenv

If running python from Anaconda distribution, `pipenv` should be preinstalled.

Otherwise, to install `pipenv` run: `pip3 install pipenv`

------



### Installation:

```bash
# Clone the source code
git clone https://***REMOVED***/***REMOVED***/git-migration.git

# Enter the directory
cd git-migration

# Enter the virtual environment shell
pipenv shell

# Install the dependencies
pipenv install

# Install the Git-Migration CLI
make install

# Use the Git-Migration CLI
git-migration --help
```

------



### Setup API Links and Personal Access Tokens:

1. In your BitBucket dashboard, go to *Manage account > Personal access tokens > Create a token*. Feel free to name it anything. Give the permissions - Project: Read and Repositories: Read (inherited).
2. After the token is generated, copy it and paste it somewhere handy, we'll use it later.
3. In your GitHub dashboard, go to *Profile settings > Developer settings > Personal access tokens > Generate new token*. Name it anything you want. Make sure the repo and admin:org scopes are ticked.
4. Copy the generated token and paste it somewhere handy.



Depending on which shell you are using, paste the following into `.bash_profile` (bash shell) or `.zprofile` (zsh)

```bash
# environment variables for git-migration
export GIT_MIGRATION_BITBUCKET_ACCOUNT_ID="CEC ID"
export GIT_MIGRATION_BITBUCKET_ACCESS_TOKEN="Bitbucket Access Token"
export GIT_MIGRATION_GITHUB_ACCOUNT_ID="CEC ID"
export GIT_MIGRATION_GITHUB_ACCESS_TOKEN="GitHub Access Token"
```



After this, don't forget to source the file before running the CLI

```bash
# bash users
source ~/.bash_profile

# zsh users
source ~/.zprofile
```

------



### `git-migration sync auto`

Automatically syncs the repositories from the projects mentioned in the `config.yml` . This config supports normal strings as well as regex patterns to filter the repositories to sync over to GitHub.



### `git-migration sync interactive`

If needed to just migrate a handful repositories from a project on BitBucket.

------



## Config file

While most of the config file is self explanatory, the format for sync_config adheres to the following format:



There are 2 main keys, `include` and `exclude`. These together control which repositories are selected for sync.

```yaml
sync_config:
  include:
    # config for repositories to include
  exclude:
    # config for repositories to exclude
```



Within these keys, you can specify the projects from which to pull repositories and also assign the repositories to some teams on GitHub Enterprise after migration. You can include the same repository under multiple names too.



You can choose to exclude the repositories from the sync/migration too. **Exclusion takes precedence over inclusion** therefore, if there is a repository mentioned in both include and exclude, it won't be considered for syncing.

```yaml
sync_config:
  include:
    # config for repositories to include
    project-key-1:
      - repo-name-1 # These repositories not assigned to any team
      - repo-name-two # after being migrated over to GitHub Enterprise
      - team-name-alpha:
        - repo-name-3
        - repo-name-4
      - team-name-beta:
        - repo-name-4
        - repo-name-two # This repo shall be assigned to team-beta as it is mentioned again
        - repo-name-5
    project-key-2:
      - repo-name-35
      - team-name-sharks:
        - repo-name-27
  exclude:
    # config for repositories to exclude
    project-key-1:
      - repo-name-5
    project-key-2:
      - repo-name-something
```



By default, these names are taken and matched as they are to filter out repository names. If preferable, you can choose to use regular expressions too!

You can specify that matching should occur with regex matching instead of normal string matching at any level in the `sync_config` tree with the additional `regex` key. Just make sure that if a `regex` key is mentioned, move the rest of the config of that level under a separate `repo_config` key.

```yaml
sync_config:
  include:
    regex: true
    repo_config:
      project-key-1: # project name
        regex: false # Override the parent attribute by redefining as false for this project
        repo_config:
          - repo-name-1
          - team-name-alpha: # team name
              regex: true # Override the project setting by mentioning for this team
              repo_config:
                - ***REMOVED*** # The regex pattern to match
      project-key-2: # project name, derives regex matching as true from parent include
        - team-name-alpha: # team name
            - ***REMOVED*** # 
  exclude:
    regex: true # Works for exclude as well
    repo_config:
      project-key-1: # regex matching attribute for these are inherited from the parent
        - ***REMOVED***
      project-key-2: # this too is regex matched
        - some-regex-pattern
```



The `regex` setting defined at any level is propogated to all it's children and this can be overriden within any level in the `sync_config` tree.



You can move the repository from one team to another in between running the sync and the new team will also have access to the repository. **But, the old team will not be removed from the access list.**



IMPORTANT:

- The `include.regex` and `exclude.regex` do NOT affect each other and are not inherited.
- Do NOT mention a `sync_config.regex`. Support for that is NOT added.
- By default, regex is FALSE.