import logging
import structlog
import os
import re
from typing import Dict, Any

def custom_processor(_, __, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    event_dict["source"] = f"{event_dict.pop('filename')}:{event_dict.pop('lineno')}"
    if event_dict.get("level") == "error" and "exception" in event_dict:
        exception_info = event_dict.pop("exception")
        match = re.search(r'File \".*?\", line (\d+)', exception_info)
        if match:
            event_dict["source"] = f"{event_dict['source'].split(':')[0]}:{match.group(1)}"
    return event_dict

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.CallsiteParameterAdder(
            [structlog.processors.CallsiteParameter.FILENAME, structlog.processors.CallsiteParameter.LINENO]
        ),
        custom_processor,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
