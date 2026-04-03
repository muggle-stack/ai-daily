"""统一日志模块。"""

import logging
import os
import sys

_configured = False


def get_logger(name: str) -> logging.Logger:
    """获取带统一格式的 logger。

    Args:
        name: logger 名称，通常传 __name__。

    Returns:
        配置好的 Logger 实例。
    """
    global _configured
    if not _configured:
        level = os.environ.get("LOG_LEVEL", "INFO").upper()
        logging.basicConfig(
            level=getattr(logging, level, logging.INFO),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
            force=True,
        )
        _configured = True
    return logging.getLogger(name)
