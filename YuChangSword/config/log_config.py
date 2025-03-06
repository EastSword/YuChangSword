# config/log_config.py
import logging
import sys
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

def configure_logger(name=__name__):
    # 创建日志目录
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # 避免重复添加handler
    if logger.hasHandlers():
        return logger

    # 统一格式
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(module)s] - %(message)s'
    )

    # 控制台Handler (INFO+)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # 文件Handler (DEBUG+)
    file_handler = TimedRotatingFileHandler(
        filename=log_dir / 'js_analyzer.log',
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # 错误专用Handler (ERROR+)
    error_handler = logging.FileHandler(
        log_dir / 'error.log',
        mode='a',
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    
    return logger