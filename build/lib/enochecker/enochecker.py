import datetime
import logging
import jsons
import traceback
import aiohttp

from typing import Optional, Callable, Any, Dict, List, Union, Type
from quart import Quart, Response
from quart import request
from logging import LogRecord
from dataclasses import dataclass
from datetime import datetime
from concurrent.futures import TimeoutError

from .useragents import random_useragent

CHECKER_TASK_RESULT_OK = "OK"
CHECKER_TASK_RESULT_MUMBLE = "MUMBLE"
CHECKER_TASK_RESULT_DOWN = "DOWN"
CHECKER_TASK_RESULT_INTERNAL_ERROR = "INTERNAL_ERROR"

CHECKER_TASK_TYPE_PUTFLAG = "putflag"
CHECKER_TASK_TYPE_GETFLAG = "getflag"
CHECKER_TASK_TYPE_PUTNOISE = "putnoise"
CHECKER_TASK_TYPE_GETNOISE = "getnoise"
CHECKER_TASK_TYPE_HAVOC = "havoc"

@dataclass
class CheckerResult:
    result: str

@dataclass
class EnoLogMessage:
    tool: str
    type: str
    severity: str
    timestamp: str
    module: str
    function: str
    flag: Optional[int]
    flagIndex: Optional[int]
    runId: Optional[int]
    round: Optional[int]
    message: str
    teamName: Optional[str]
    serviceName: str

@dataclass
class CheckerTask:
    runId: int
    method: str
    address: str
    serviceId: str
    serviceName: str
    teamId: str
    team: str
    relatedRoundId: int
    round: int
    flag: Optional[str]
    flagIndex: Optional[int]

class BrokenServiceException(Exception):
    pass

class OfflineException(Exception):
    pass

class BaseChecker():
    def __init__(self, service_name: str) -> None:
        self.service_name = service_name
        self.name = service_name + "Checker"

class ELKFormatter(logging.Formatter):
    def format(self, record: LogRecord) -> str:
        return jsons.dumps(self.create_message(record))

    def create_message(self, record: LogRecord):
        return EnoLogMessage(record.checker.name,
            "infrastructure",
            record.levelname,
            datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            record.checker.name,
            record.funcName,
            record.checker_task.flag,
            record.checker_task.flagIndex,
            record.checker_task.runId,
            record.checker_task.round,
            record.msg,
            record.checker_task.team,
            record.checker.service_name)

def create_app(checker: BaseChecker) -> None:
    app = Quart(__name__)
    checker = checker
    logger = logging.getLogger(__name__)
    
    @app.route('/', methods=["GET"])
    async def handle_get() -> Response:
        logging.info("GET /")
        return Response('<h1>Welcome to {}Checker)</h1>'.format(checker.service_name))

    @app.route('/', methods=['POST'])
    async def handle_post() -> Response:
        # read request
        req = await request.get_data()
        checker_task = jsons.loads(req, CheckerTask)

        # create LoggerAdapter
        extra = { 'checker_task': checker_task, 'checker': checker }
        scoped_logger = logging.LoggerAdapter(logger, extra=extra)
        scoped_logger.info("Received task (id={}, teamid={}, method={}, index={})".format(checker_task.runId, checker_task.teamId, checker_task.method, checker_task.flagIndex))

        # call method
        try:
            if checker_task.method == CHECKER_TASK_TYPE_PUTFLAG:
                await checker.putflag(scoped_logger, checker_task)
            elif checker_task.method == CHECKER_TASK_TYPE_GETFLAG:
                await checker.getflag(scoped_logger, checker_task)
            elif checker_task.method == CHECKER_TASK_TYPE_PUTNOISE:
                await checker.putnoise(scoped_logger, checker_task)
            elif checker_task.method == CHECKER_TASK_TYPE_GETNOISE:
                await checker.getnoise(scoped_logger, checker_task)
            elif checker_task.method == CHECKER_TASK_TYPE_HAVOC:
                await checker.havoc(scoped_logger, checker_task)
            else:
                raise Exception("Unknown rpc method {}".format(checker_task.method))
            scoped_logger.info("Task finished OK (id={}, teamid={}, method={}, index={})".format(checker_task.runId, checker_task.teamId, checker_task.method, checker_task.flagIndex))
            return jsons.dumps(CheckerResult(CHECKER_TASK_RESULT_OK))
        except (aiohttp.ClientConnectionError, aiohttp.ClientResponseError, OfflineException) as ex:
            stacktrace = ''.join(traceback.format_exception(None, ex, ex.__traceback__))
            scoped_logger.warn("Task finished DOWN: {}".format(stacktrace))
            return jsons.dumps(CheckerResult(CHECKER_TASK_RESULT_DOWN))
        except BrokenServiceException as ex:
            stacktrace = ''.join(traceback.format_exception(None, ex, ex.__traceback__))
            scoped_logger.warn("Task finished MUMBLE: {}".format(stacktrace))
            return jsons.dumps(CheckerResult(CHECKER_TASK_RESULT_MUMBLE))
        except Exception as ex:
            stacktrace = ''.join(traceback.format_exception(None, ex, ex.__traceback__))
            scoped_logger.error("Task finished INTERNAL_ERROR: {}".format(stacktrace))
            return jsons.dumps(CheckerResult(CHECKER_TASK_RESULT_INTERNAL_ERROR))
    return app
