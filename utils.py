import json
import requests
import os
import stat
from colorama import Fore, Style

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

# Give colored print statements
def logBright(color, string):
    print(color + Style.BRIGHT + string + Style.RESET_ALL)

def logLight(color, string):
    print(color + string + Style.RESET_ALL)