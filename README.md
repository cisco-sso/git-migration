**Migrate repositories from BitBucket to GitHub Enterprise**

Prerequisites:

- python3, pip3
- pipenv

If running python from Anaconda distribution, `pipenv` should be preinstalled.

Otherwise, to install `pipenv` run: `pip3 install pipenv`

------

In the root of the project, run:

`pipenv shell` - Initiate the virutal environment

`pipenv install` - Install the dependencies from Pipfile

------

Steps for setting up credentials:

1. In your BitBucket dashboard, go to *<u>Manage account > Personal access tokens > Create a token</u>*. Feel free to name it anything. Give the permissions - <u>Project: Read</u> and <u>Repositories: Read (inherited)</u>.
2. After the token is generated, copy it and paste it in *credentials.json* in the project's root as ***Bitbucket_AccessToken***.
3. In your GitHub dashboard, go to *<u>Profile settings > Developer settings > Personal access tokens > Generate new token</u>*. Name it anything you want. Make sure the <u>repo</u> and <u>admin:org</u> scopes are ticked.
4. Copy the generated token and paste it in *credentials.json* in the project's root as ***Github_AccessToken***.
5. Also enter the ***BitBucket_AccountID*** and ***Github_AccountID*** in *credentials.json*. This should usually just be your CEC ID. Save the file.

------

After this, you can run `python migrate.py YOUR_PROJECT_KEY` to migrate the repositories over to the github account. The Project Key can be found in the *<u>BitBucket Dashboard > Projects</u>* Tab.

Repositories with open Pull Requests are blocked from migrating as the PRs cannot be migrated. Close the PRs and then try again.

If GitHub account already has a repository with the same as the one in BitBucket, that specific repository will be blocked from migrating.

------

Hope your migration completes without any hassles. Cheers!