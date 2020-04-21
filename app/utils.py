import json
import unicodedata
import logging
import datetime
import pythonjsonlogger.jsonlogger as jsonlogger
import os
import re
import stat
import colorama as color
import structlog


class ReadUtils():
    # Read and return projects to sync and repos to exculde from sync
    @staticmethod
    def get_sync_config():
        cur_dir_path = os.getcwd()
        with open(cur_dir_path + "/config.json") as file:
            sync_config = json.load(file)['sync_config']
        to_include = sync_config['include']
        to_exclude = sync_config['exclude']
        return to_include, to_exclude

    # Read and return the target organization to sync repositories to
    @staticmethod
    def get_target_org():
        cur_dir_path = os.getcwd()
        with open(cur_dir_path + "/config.json") as file:
            target_org = json.load(file)['target_org']
        return target_org


class RegexUtils():
    @staticmethod
    def filter_repos(repositories, regex_list, exclude_matches=False):
        if (not regex_list):
            return repositories
        result_repos = []
        for pattern in regex_list:
            if (exclude_matches):
                result = [repo_name for repo_name in repositories if not re.match(pattern, repo_name)]
            else:
                result = [repo_name for repo_name in repositories if re.match(pattern, repo_name)]
            result_repos += result
        result_repos = sorted(list(set(result_repos)))
        return result_repos


class MiscUtils():
    # Filter function to get http links to clone repo
    @staticmethod
    def is_http(link):
        if (link["name"] == "http" or link["name"] == "https"):
            return True
        else:
            return False


class FileUtils():
    # Error handler for shutil.rmtree on windows READ-ONLY paths
    @staticmethod
    def remove_readonly(func, path, excinfo):
        os.chmod(path, stat.S_IWRITE)
        func(path)


class StringUtils():
    # Remove control characters from a string (otherwise GHE API calls fail)
    @staticmethod
    def remove_control_characters(s):
        return "".join(ch for ch in s if unicodedata.category(ch)[0] != "C")


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            now = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            log_record['timestamp'] = now
        if log_record.get('func'):
            log_record['function'] = log_record['func']
        else:
            log_record['function'] = record.funcName
        log_record['level'] = record.levelname
        keep_keys = ["timestamp", "level", "name", "message", "function"]
        params = {}
        param_keys = [key for key in log_record if (key not in keep_keys)]
        for key in param_keys:
            params[key] = log_record[key]
            del log_record[key]
        if (params):
            log_record["params"] = params


class LogUtils():
    # Give colored print statements
    @staticmethod
    def log_bright(log_color, log_string):
        print(log_color + color.Style.BRIGHT + log_string + color.Style.RESET_ALL)

    @staticmethod
    def log_light(log_color, log_string):
        print(log_color + log_string + color.Style.RESET_ALL)

    @staticmethod
    def get_console_log_level():
        cur_dir_path = os.getcwd()
        with open(cur_dir_path + "/config.json") as file:
            console_log_level = json.load(file)['console_log_level']
        return console_log_level

    @staticmethod
    def get_console_log_normal():
        cur_dir_path = os.getcwd()
        with open(cur_dir_path + "/config.json") as file:
            console_log_normal = json.load(file)['console_log_normal']
        return console_log_normal

    @staticmethod
    def get_file_log_level():
        cur_dir_path = os.getcwd()
        with open(cur_dir_path + "/config.json") as file:
            file_log_level = json.load(file)['file_log_level']
        return file_log_level

    @staticmethod
    def resolve_log_level(log_level):
        log_level.lower()
        if (log_level == 'debug'):
            return logging.DEBUG
        elif (log_level == 'info'):
            return logging.INFO
        elif (log_level == 'warning'):
            return logging.WARNING
        elif (log_level == 'error'):
            return logging.ERROR
        elif (log_level == 'critical'):
            return logging.CRITICAL
        else:
            return logging.INFO

    @staticmethod
    def get_logger(logger_name, console_log_level, console_log_normal, file_log_level):
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                # structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.stdlib.render_to_log_kwargs,
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] - %(funcName)s: %(message)s")
        json_formatter = CustomJsonFormatter('(timestamp) (level) (name) (message)')

        cur_dir_path = os.getcwd()
        if (not os.path.isdir(cur_dir_path + "/logs")):
            os.mkdir("logs")

        file_handler = logging.FileHandler("logs/migration.log")
        file_handler.setFormatter(log_formatter)
        file_handler.setLevel(LogUtils.resolve_log_level(file_log_level))

        json_file_handler = logging.FileHandler("logs/migration-json.log")
        json_file_handler.setFormatter(json_formatter)
        json_file_handler.setLevel(LogUtils.resolve_log_level(file_log_level))

        console_handler = logging.StreamHandler()
        if (console_log_normal):
            console_handler.setFormatter(log_formatter)
        else:
            console_handler.setFormatter(json_formatter)
        console_handler.setLevel(LogUtils.resolve_log_level(console_log_level))

        logger = structlog.get_logger(logger_name)
        logger.addHandler(file_handler)
        logger.addHandler(json_file_handler)
        logger.addHandler(console_handler)

        logger.setLevel(logging.DEBUG)
        return logger
