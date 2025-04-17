
import os
import logging
from pathlib import Path
import chardet  # pip install chardet

def read_file_lines(file_path):
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        detected = chardet.detect(raw_data)
        file_encoding = detected.get("encoding", "utf-8")
        decoded_data = raw_data.decode(file_encoding, errors="replace")
        return decoded_data.splitlines(keepends=True)
    except Exception as e:
        logging.error(f"파일 읽기 오류 (인코딩 감지 실패): {e}")
        raise

class FileProcessor:
    def __init__(self, config, transformer, reporter):
        self.config = config
        self.transformer = transformer
        self.reporter = reporter

    def determine_sql_type(self, sql_text):
        upper_sql = sql_text.upper()
        ddl_keywords = ["CREATE", "ALTER", "DROP", "TRUNCATE", "COMMENT", "RENAME"]
        dml_keywords = ["SELECT", "INSERT", "UPDATE", "DELETE", "MERGE"]

        for kw in ddl_keywords:
            if kw in upper_sql:
                return "DDL"
        for kw in dml_keywords:
            if kw in upper_sql:
                return "DML"
        return "DDL"

    def process_sql_file(self, file_path):
        if not os.path.isfile(file_path):
            logging.error(f"유효하지 않은 파일 경로입니다: {file_path}")
            return

        file_name = Path(file_path).name

        try:
            query_lines = read_file_lines(file_path)
        except Exception as e:
            logging.error(f"파일 읽기 오류: {e}")
            return

        transformed_lines = []
        change_log = []
        applied_changes = set()
        all_manual_reasons = []
        all_applied_rules = []
        manual_required_flag = False

        for idx, line in enumerate(query_lines, start=1):
            # apply_transformations는 (new_line, logs, manual_req, manual_reasons) 튜플을 반환합니다.
            new_line, logs, manual_req, manual_reasons = \
                self.transformer.apply_transformations(line, idx, applied_changes)

            transformed_lines.append(new_line.rstrip('\n'))
            change_log.extend(logs)
            if manual_req:
                manual_required_flag = True
                all_manual_reasons.extend(manual_reasons)

        # 적용된 룰 목록은 applied_changes 집합에서 가져옵니다.
        all_applied_rules = list(applied_changes)

        formatted_sql = self.transformer.format_sql("\n".join(transformed_lines))
        full_sql_text = "".join(query_lines)
        sql_type = self.determine_sql_type(full_sql_text)

        if not change_log:
            conversion_method = "변환 불필요"
            output_dir = self.config.DDL_NOCHANGE_DIR if sql_type == "DDL" else self.config.DML_NOCHANGE_DIR
        elif manual_required_flag:
            conversion_method = "메뉴얼 변경"
            output_dir = self.config.DDL_MANUAL_DIR if sql_type == "DDL" else self.config.DML_MANUAL_DIR
        else:
            conversion_method = "변환 성공"
            output_dir = self.config.DDL_SUCCESS_DIR if sql_type == "DDL" else self.config.DML_SUCCESS_DIR

        file_basename = Path(file_path).with_suffix('').name.replace(' ', '_')
        output_file = output_dir / f"{file_basename}_converted.sql"
        log_file = self.config.LOG_DIR / (output_file.stem + '_log.txt')

        try:
            with open(output_file, 'w', encoding="utf-8") as out_f:
                out_f.write(formatted_sql)
        except Exception as e:
            logging.error(f"변환된 SQL 파일 저장 오류: {e}")

        if change_log:
            try:
                with open(log_file, 'w', encoding="utf-8") as log_f:
                    log_f.write("\n".join(change_log) + "\n")
            except Exception as e:
                logging.error(f"변환 로그 파일 저장 오류: {e}")
        else:
            log_file = None

        manual_reason_summary = ", ".join(set(all_manual_reasons)) if manual_required_flag else None

        self.reporter.add_execution_result(
            file_name=file_name,
            original_sql=full_sql_text,
            transformed_sql=formatted_sql,
            execution_time=0.0,
            error=manual_reason_summary,
            plan="(변환기 전용)",
            rows="",
            cpu_time="",
            applied_rules=all_applied_rules
        )

        self.reporter.html_logs.append((file_name, full_sql_text, formatted_sql, "\n".join(change_log)))
        logging.info(f"변환 완료: {output_file} [SQL 유형: {sql_type}, 전환 방법: {conversion_method}], 변경 로그: {log_file.name if log_file else '없음'}")


    def process_directory(self, dir_path):
        if not os.path.isdir(dir_path):
            logging.error(f"유효하지 않은 디렉토리 경로입니다: {dir_path}")
            return
        files = list(Path(dir_path).rglob('*.sql'))
        if not files:
            logging.info("디렉토리에서 SQL 파일을 찾을 수 없습니다.")
            return
        for file in files:
            self.process_sql_file(str(file))