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

Automatically syncs the repositories from the projects mentioned in the `app/config.json` . This config takes regex patterns to filter the repositories to sync over to GitHub.



### `git-migration sync interactive`

If needed to just migrate a handful repositories from a project on BitBucket.

------

