import jsons
import logging
import traceback
from logging import LogRecord
import requests
from .enochecker import BaseChecker, CheckerTask
from typing import Optional, Callable, Any, Dict, List, Union, Type
from dataclasses import dataclass

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

def exception_to_string(excp):
    stack = traceback.extract_stack()[:-3] + traceback.extract_tb(excp.__traceback__)  # add limit=?? 
    pretty = traceback.format_list(stack)
    return ''.join(pretty) + '\n  {} {}'.format(excp.__class__,excp)

class ScopedLogHandle:
    def __init__(self, checker: BaseChecker, checker_task: CheckerTask):
        self.checker_task = checker_task
        self.checker = checker

    def create_message(msg: str):
        return EnoLogMessage(checker.name,
            "infrastructure",
            "INFO",
            "timestamp",
            checker.name,
            "default function",
            checker_task.flag,
            checker_task.flagIndex,
            checker_task.runId,
            checker_task.round,
            msg,
            checker_task.team,
            checker.service_name)

    def info(self, text: str):
        msg = create_message(msg)
        logging.info(msg)

class ELKFormatter(logging.Formatter):
    def __init__(self, checker, fmt=None, datefmt="%Y-%m-%dT%H:%M:%S%z", style='%'):
        # type: (BaseChecker, str, str, str) -> None
        super().__init__(fmt, datefmt, style)
        self.checker = checker  # type: BaseChecker

    def format(self, record: EnoLogMessage) -> str:
        return jsons.dumps(record)
