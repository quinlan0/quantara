"""
日志模块
提供统一的日志记录功能
"""

import datetime
from pathlib import Path
from typing import Optional

try:
    from loguru import logger
    HAS_LOGURU = True
except ImportError:
    # 如果没有loguru，使用标准logging
    import logging
    HAS_LOGURU = False
    logger = logging.getLogger(__name__)


class Logger:
    """日志管理器"""

    DEFAULT_LOG_DIR = "/tmp/tmp_log/"
    DEFAULT_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} [{level}] [{file}:{line}] {message}"

    def __init__(self):
        self._initialized = False

    def init_logger(self, name: Optional[str] = None, log_dir: Optional[str] = None,
                   log_level: str = "INFO") -> None:
        """
        初始化日志记录器

        Args:
            name: 日志名称，如果为None则使用当前文件名
            log_dir: 日志目录，如果为None则使用默认目录
            log_level: 日志级别
        """
        if self._initialized:
            return

        log_dir_path = Path(log_dir if log_dir else self.DEFAULT_LOG_DIR)
        if not log_dir_path.exists():
            log_dir_path.mkdir(parents=True)

        now_dt = datetime.datetime.now()
        current_filename = Path(__file__).stem
        log_name = name if name else current_filename
        log_filename = f"{log_name}_{now_dt.strftime('%Y%m%d-%H%M%S')}.log"

        if HAS_LOGURU:
            # 使用loguru
            logger.add(
                str(log_dir_path / log_filename),
                format=self.DEFAULT_FORMAT,
                level=log_level,
                rotation="10 MB",  # 日志轮转
                retention="1 week"  # 保留1周
            )
        else:
            # 使用标准logging
            logging.basicConfig(
                filename=str(log_dir_path / log_filename),
                level=getattr(logging, log_level.upper(), logging.INFO),
                format=self.DEFAULT_FORMAT.replace("{time:", "%(asctime)s").replace(
                    "{level}", "%(levelname)s").replace("{file}:{line}", "%(filename)s:%(lineno)d").replace(
                    "{message}", "%(message)s")
            )

        self._initialized = True

    def get_logger(self):
        """获取日志记录器"""
        if not self._initialized:
            self.init_logger()
        return logger


# 全局日志实例
logger_manager = Logger()

# 为了向后兼容，提供init_logger函数
def init_logger(name: Optional[str] = None, log_dir: Optional[str] = None) -> None:
    """
    初始化日志记录器（向后兼容函数）

    Args:
        name: 日志名称
        log_dir: 日志目录
    """
    logger_manager.init_logger(name=name, log_dir=log_dir)


def get_logger():
    """获取日志记录器"""
    return logger_manager.get_logger()


if __name__ == "__main__":
    # 测试日志功能
    init_logger("test_logger")
    log = get_logger()

    log.info("测试信息日志")
    log.warning("测试警告日志")
    log.error("测试错误日志")
    log.debug("测试调试日志")

    print("日志测试完成，请检查 /tmp/tmp_log/ 目录下的日志文件")