# config.py
import sys
import logging
from pathlib import Path

class Config:
    def __init__(self):
        self.BASE_DIR = Path('.')
        # 변환 파일 저장 폴더: 모든 변환된 SQL 파일은 converted_sqls 내부에 위치
        self.CONVERTED_DIR = self.BASE_DIR / 'converted_sqls'
        # DDL 결과용 폴더 (converted_sqls/DDL/...)
        self.DDL_DIR = self.CONVERTED_DIR / 'DDL'
        self.DDL_SUCCESS_DIR = self.DDL_DIR / 'success_sqls'
        self.DDL_MANUAL_DIR = self.DDL_DIR / 'manual_sqls'
        self.DDL_NOCHANGE_DIR = self.DDL_DIR / 'nochange_sqls'
        # DML 결과용 폴더 (converted_sqls/DML/...)
        self.DML_DIR = self.CONVERTED_DIR / 'DML'
        self.DML_SUCCESS_DIR = self.DML_DIR / 'success_sqls'
        self.DML_MANUAL_DIR = self.DML_DIR / 'manual_sqls'
        self.DML_NOCHANGE_DIR = self.DML_DIR / 'nochange_sqls'
        # 로그 및 보고서 폴더
        self.LOG_DIR = self.BASE_DIR / 'logs'
        self.REPORT_DIR = self.BASE_DIR / 'reports'
        # 변환 규칙 파일 설정
        self.TRANSFORMATIONS_FILE = 'transformations.json'
        self.manual_check_keywords = ['DECLARE', 'EXCEPTION WHEN OTHERS', 'CONNECT BY PRIOR']
        # 리포트 파일명 설정
        self.CSV_REPORT_NAME = 'transformation_report.csv'
        self.HTML_REPORT_NAME = 'transformation_report.html'

        self.create_directories()
        self.setup_logging()

    def create_directories(self):
        directories = [
            self.DDL_SUCCESS_DIR,
            self.DDL_MANUAL_DIR,
            self.DDL_NOCHANGE_DIR,
            self.DML_SUCCESS_DIR,
            self.DML_MANUAL_DIR,
            self.DML_NOCHANGE_DIR,
            self.LOG_DIR,
            self.REPORT_DIR
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def setup_logging(self):
        logging.basicConfig(
            format='%(asctime)s - %(levelname)s - %(message)s',
            level=logging.INFO,
            handlers=[
                logging.FileHandler(self.LOG_DIR / 'sql_transformation.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )