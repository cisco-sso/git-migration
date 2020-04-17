import json
import unicodedata
import logging
import datetime
import pythonjsonlogger.jsonlogger as jsonlogger
import os
import stat
import colorama as color
import structlog
import pathlib


class ReadUtils():
    # Read and return projects to sync and repos to exculde from sync
    @staticmethod
    def getSyncConfig():
        curDirPath = str(pathlib.Path(__file__).parent)
        with open(curDirPath + "/config.json") as file:
            syncConfig = json.load(file)['syncConfig']
        toInclude = syncConfig['include']
        toExclude = syncConfig['exclude']
        return toInclude, toExclude


class MiscUtils():
    # Filter function to get http links to clone repo
    @staticmethod
    def isHTTP(link):
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
            now = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            log_record['timestamp'] = now
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname
        if log_record.get('func'):
            log_record['function'] = log_record['func']
        else:
            log_record['function'] = record.funcName


class LogUtils():
    # Give colored print statements
    @staticmethod
    def logBright(logColor, logString):
        print(logColor + color.Style.BRIGHT + logString + color.Style.RESET_ALL)

    @staticmethod
    def logLight(logColor, logString):
        print(logColor + logString + color.Style.RESET_ALL)

    @staticmethod
    def getLogger(loggerName):
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

        logFormatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] - %(funcName)s: %(message)s")
        jsonFormatter = CustomJsonFormatter('(timestamp) (level) (name) (message)')

        curDirPath = str(pathlib.Path(__file__).parent)
        if (not os.path.isdir(curDirPath + "/../logs")):
            os.mkdir("logs")

        fileHandler = logging.FileHandler("logs/migration.log")
        fileHandler.setFormatter(logFormatter)
        fileHandler.setLevel(logging.DEBUG)

        jsonFileHandler = logging.FileHandler("logs/migration-json.log")
        jsonFileHandler.setFormatter(jsonFormatter)
        jsonFileHandler.setLevel(logging.DEBUG)

        consoleHandler = logging.StreamHandler()
        consoleHandler.setFormatter(logFormatter)
        consoleHandler.setLevel(logging.INFO)

        logger = structlog.get_logger(loggerName)
        logger.addHandler(fileHandler)
        logger.addHandler(jsonFileHandler)
        logger.addHandler(consoleHandler)

        logger.setLevel(logging.DEBUG)
        return logger
