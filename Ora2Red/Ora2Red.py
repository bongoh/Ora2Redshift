import sys
import logging
import os
from config import Config
from sql_transformer import SQLTransformer
from report_generator import ReportGenerator
from file_processor import FileProcessor

def choose_directory_or_file(processor):
    while True:
        try:
            choice = input("디렉토리를 선택하려면 1, 파일을 선택하려면 2를 입력하세요: ").strip()
            if choice == '1':
                dir_path = input("디렉토리 경로를 입력하세요: ").strip()
                if not os.path.isdir(dir_path):
                    print("유효한 디렉토리 경로가 아닙니다. 다시 시도하세요.")
                    continue
                processor.process_directory(dir_path)
                break
            elif choice == '2':
                file_path = input("파일 경로를 입력하세요: ").strip()
                if not os.path.isfile(file_path):
                    print("유효한 파일 경로가 아닙니다. 다시 시도하세요.")
                    continue
                processor.process_sql_file(file_path)
                break
            else:
                print("잘못된 입력입니다. 1 또는 2를 입력하세요.")
        except KeyboardInterrupt:
            logging.info("프로그램이 사용자에 의해 종료되었습니다.")
            sys.exit(0)
        except Exception as ex:
            logging.error(f"입력 처리 중 에러 발생: {ex}")
            print("입력 처리 중 문제가 발생했습니다. 다시 시도해주세요.")

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
    )

    try:
        config = Config()
        transformer = SQLTransformer(config)
        reporter = ReportGenerator(config)
        processor = FileProcessor(config, transformer, reporter)

        result_file = os.path.join(config.REPORT_DIR, "validation_results.json")

        # 기존 결과 파일 불러오기
        if os.path.exists(result_file):
            use_existing = input("기존 결과 파일이 있습니다. 불러오시겠습니까? (y/n): ").strip().lower()
            if use_existing == 'y':
                reporter.import_results_from_json(result_file)
                print("📋 [디버그] 불러온 csv_results 구조:")
                for i, row in enumerate(reporter.csv_results):
                    print(f"  [{i}] {type(row)} → {row}")
        choose_directory_or_file(processor)

        # 결과물 저장
        os.makedirs(config.REPORT_DIR, exist_ok=True)
        reporter.export_results_to_json(result_file)

        # 리포트 생성
        reporter.generate_csv()
        reporter.generate_html()

        print(f"📊 리포트가 생성되었습니다: {config.REPORT_DIR}")
    except Exception as e:
        logging.error(f"프로그램 실행 중 예외 발생: {e}")
        print("프로그램 실행 중 오류가 발생했습니다. 로그를 확인해주세요.")

if __name__ == "__main__":
    main()