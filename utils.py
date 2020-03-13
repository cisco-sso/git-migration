import json
import requests
from colorama import init, Fore, Style

# Filter function to get http links to clone repo
def isHTTP(link):
    if(link["name"]=="http" or link["name"]=="https"):
        return True
    else:
        return False

# Give colored print statements
def logBright(color, string):
    print(color + Style.BRIGHT + string + Style.RESET_ALL)

def logLight(color, string):
    print(color + string + Style.RESET_ALL)