import json
import requests
import unicodedata
import os
import stat
import colorama as color

# Read and return API base URLs from apis.json
def getAPILinks():
    # Get required API Links from JSON file
    with open("./apis.json") as file:
        apis = json.load(file)
    bitbucketAPI = apis['DEFAULT']['BitBucket_API_BaseURL']
    githubAPI = apis['DEFAULT']['GitHub_API_BaseURL']
    return bitbucketAPI, githubAPI

# Filter function to get http links to clone repo
def isHTTP(link):
    if(link["name"]=="http" or link["name"]=="https"):
        return True
    else:
        return False

# Error handler for shutil.rmtree on windows READ-ONLY paths
def remove_readonly(func, path, excinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)

# Remove control characters from a string (otherwise GHE API calls fail)
def remove_control_characters(s):
    return "".join(ch for ch in s if unicodedata.category(ch)[0]!="C")

# Give colored print statements
def logBright(logColor, logString):
    print(logColor + color.Style.BRIGHT + logString + color.Style.RESET_ALL)

def logLight(logColor, logString):
    print(logColor + logString + color.Style.RESET_ALL)