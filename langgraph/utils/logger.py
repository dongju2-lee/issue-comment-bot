import os
import logging
from logging.handlers import TimedRotatingFileHandler
import sys
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 로그 레벨 설정
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
log_levels = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

# 로그 디렉토리 설정
log_dir = os.getenv('LOG_DIR', 'log')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 로그 보존 일수
log_retention_days = int(os.getenv('LOG_RETENTION_DAYS', '30'))

def setup_logger(name):
    """
    일자별 로깅을 위한 로거 설정 함수
    Args:
        name: 로거 이름
    Returns:
        설정된 로거 객체
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_levels.get(log_level, logging.INFO))
    
    # 이미 핸들러가 설정되어 있으면 추가하지 않음
    if not logger.handlers:
        # 콘솔 핸들러 설정
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # 파일 핸들러 설정 (일자별 로그 파일)
        log_file_path = os.path.join(log_dir, f'{name}.log')
        file_handler = TimedRotatingFileHandler(
            filename=log_file_path,
            when='midnight',    # 매일 자정에 로테이션
            interval=1,         # 1일 간격
            backupCount=log_retention_days,  # 지정된 일수만큼 보관
            encoding='utf-8'
        )
        
        # 커스텀 이름 지정 함수 (YYYY-MM-DD 형식으로 파일명 변경)
        def namer(default_name):
            # 기본 이름에서 날짜 부분 추출
            base_path = os.path.dirname(default_name)
            base_name = os.path.basename(default_name)
            if '.' not in base_name:
                return default_name
                
            name_parts = base_name.split('.')
            module_name = name_parts[0]
            date_part = name_parts[-1]
            
            # 새 파일명 형식: log/module_name.YYYY-MM-DD.log
            return os.path.join(base_path, f"{module_name}.{date_part}.log")
            
        file_handler.namer = namer
        
        # 파일 로그 포매터 설정
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger