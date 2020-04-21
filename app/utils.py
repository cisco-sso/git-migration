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
    
    # Read and return the target organization to sync repositories to
    @staticmethod
    def getTargetOrg():
        curDirPath = str(pathlib.Path(__file__).parent)
        with open(curDirPath + "/config.json") as file:
            targetOrg = json.load(file)['targetOrg']
        return targetOrg


class RegexUtils():
    @staticmethod
    def filterRepos(repositories, regexList, excludeMatches=False):
        if (not regexList):
            return repositories
        resultRepos = []
        for pattern in regexList:
            if (excludeMatches):
                result = [repoName for repoName in repositories if not re.match(pattern, repoName)]
            else:
                result = [repoName for repoName in repositories if re.match(pattern, repoName)]
            resultRepos += result
        resultRepos = sorted(list(set(resultRepos)))
        return resultRepos


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
            now = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            log_record['timestamp'] = now
        if log_record.get('func'):
            log_record['function'] = log_record['func']
        else:
            log_record['function'] = record.funcName
        log_record['level'] = record.levelname
        keepKeys = ["timestamp", "level", "name", "message", "function"]
        params = {}
        paramKeys = [ key for key in log_record if (key not  in keepKeys)]
        for key in paramKeys:
            params[key] = log_record[key]
            del log_record[key]
        if (params):
            log_record["params"] = params


class LogUtils():
    # Give colored print statements
    @staticmethod
    def logBright(logColor, logString):
        print(logColor + color.Style.BRIGHT + logString + color.Style.RESET_ALL)

    @staticmethod
    def logLight(logColor, logString):
        print(logColor + logString + color.Style.RESET_ALL)
    
    @staticmethod
    def getConsoleLogLevel():
        curDirPath = str(pathlib.Path(__file__).parent)
        with open(curDirPath + "/config.json") as file:
            consoleLogLevel = json.load(file)['consoleLogLevel']
        return consoleLogLevel
    
    @staticmethod
    def getConsoleLogNormal():
        curDirPath = str(pathlib.Path(__file__).parent)
        with open(curDirPath + "/config.json") as file:
            consoleLogNormal = json.load(file)['consoleLogNormal']
        return consoleLogNormal
    
    @staticmethod
    def getFileLogLevel():
        curDirPath = str(pathlib.Path(__file__).parent)
        with open(curDirPath + "/config.json") as file:
            fileLogLevel = json.load(file)['fileLogLevel']
        return fileLogLevel

    @staticmethod
    def resolveLogLevel(logLevel):
        logLevel.lower()
        if (logLevel == 'debug'):
            return logging.DEBUG
        elif (logLevel == 'info'):
            return logging.INFO
        elif (logLevel == 'warning'):
            return logging.WARNING
        elif (logLevel == 'error'):
            return logging.ERROR
        elif (logLevel == 'critical'):
            return logging.CRITICAL
        else:
            return logging.INFO

    @staticmethod
    def getLogger(loggerName, consoleLogLevel, consoleLogNormal, fileLogLevel):
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
        fileHandler.setLevel(LogUtils.resolveLogLevel(fileLogLevel))

        jsonFileHandler = logging.FileHandler("logs/migration-json.log")
        jsonFileHandler.setFormatter(jsonFormatter)
        jsonFileHandler.setLevel(LogUtils.resolveLogLevel(fileLogLevel))

        consoleHandler = logging.StreamHandler()
        if (consoleLogNormal):
            consoleHandler.setFormatter(logFormatter)
        else:
            consoleHandler.setFormatter(jsonFormatter)
        consoleHandler.setLevel(LogUtils.resolveLogLevel(consoleLogLevel))

        logger = structlog.get_logger(loggerName)
        logger.addHandler(fileHandler)
        logger.addHandler(jsonFileHandler)
        logger.addHandler(consoleHandler)

        logger.setLevel(logging.DEBUG)
        return logger
