import os
import yaml


class ReadUtils():
    # NOTE Function used only in test command: testing with new config file format
    # Read and return different integrations
    @staticmethod
    def get_integrations():
        cur_dir_path = os.getcwd()
        with open(cur_dir_path + "/doc/testing/test_config.yaml") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
        integrations = config["integrations"]
        return integrations

    # Read and return the prefix to be used for repo migrations and sync
    @staticmethod
    def get_prefix():
        cur_dir_path = os.getcwd()
        with open(cur_dir_path + "/config.yml") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
        prefix = config["prefix"] if ("prefix" in config) else ""
        return prefix

    # Read and return the prefis to be used for renaming the master branch
    @staticmethod
    def get_master_branch_prefix():
        cur_dir_path = os.getcwd()
        with open(cur_dir_path + "/config.yml") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
        master_branch_prefix = config["master_branch_prefix"] if ("master_branch_prefix" in config) else ""
        return master_branch_prefix


class MiscUtils():
    @staticmethod
    def get_api_base_url(server_type, server_url):
        if (server_type == "bitbucket"):
            return f"{server_url}/bitbucket/rest/api/1.0"
        elif (server_type == "github-enterprise"):
            return f"{server_url}/api/v3"
        elif (server_type == "github-public"):
            return "https://api.github.com"
        else:
            # Matches none of the supported server types
            return None
