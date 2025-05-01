import logging
import sys
from utils.config import settings

# 로거 설정
def get_logger():
    logger = logging.getLogger("github_bot")
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        # 콘솔 핸들러
        console_handler = logging.StreamHandler(sys.stdout)
        console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_format)
        
        # 파일 핸들러
        file_handler = logging.FileHandler("github_bot.log")
        file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_format)
        
        # 핸들러 추가
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger

logger = get_logger()