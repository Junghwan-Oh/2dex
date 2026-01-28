"""통합 로깅 유틸리티"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


def setup_logger(
    name: str,
    logLevel: str = "INFO",
    logDir: Optional[str] = None,
    logToFile: bool = True,
    logToConsole: bool = True
) -> logging.Logger:
    """
    로거 설정

    Args:
        name: 로거 이름
        logLevel: 로그 레벨 ('DEBUG', 'INFO', 'WARNING', 'ERROR')
        logDir: 로그 파일 디렉토리 (None이면 현재 디렉토리/logs)
        logToFile: 파일 로깅 활성화
        logToConsole: 콘솔 로깅 활성화

    Returns:
        설정된 로거
    """
    logger = logging.getLogger(name)

    # 이미 핸들러가 있으면 제거 (중복 방지)
    if logger.handlers:
        logger.handlers.clear()

    logger.setLevel(getattr(logging, logLevel.upper()))

    # 포맷터 생성
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 콘솔 핸들러
    if logToConsole:
        consoleHandler = logging.StreamHandler(sys.stdout)
        consoleHandler.setFormatter(formatter)
        logger.addHandler(consoleHandler)

    # 파일 핸들러
    if logToFile:
        if logDir is None:
            logDir = "logs"

        logPath = Path(logDir)
        logPath.mkdir(parents=True, exist_ok=True)

        # 날짜별 로그 파일
        today = datetime.now().strftime("%Y%m%d")
        logFile = logPath / f"{name}_{today}.log"

        fileHandler = logging.FileHandler(logFile, encoding='utf-8')
        fileHandler.setFormatter(formatter)
        logger.addHandler(fileHandler)

    return logger
