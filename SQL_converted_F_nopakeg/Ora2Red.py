import os
import re
import sys
import logging
import json
import csv
from pathlib import Path
from datetime import datetime
from difflib import ndiff

# 로그 설정
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("sql_transformation.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

BASE_DIR = Path(".")
CONVERTED_DIR = BASE_DIR / "converted_sqls"
LOG_DIR = BASE_DIR / "logs"
REPORT_DIR = BASE_DIR / "reports"

for directory in [CONVERTED_DIR, LOG_DIR, REPORT_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

csv_results = []
html_logs = []

TRANSFORMATIONS_FILE = 'transformations.json'
manual_check_keywords = ['DECLARE', 'EXCEPTION WHEN OTHERS', 'CONNECT BY PRIOR']

def load_transformations(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"변환 규칙 로드 실패: {e}")
        raise

try:
    transformations = load_transformations(TRANSFORMATIONS_FILE)
    compiled_rules = [(re.compile(rule["pattern"], re.IGNORECASE), rule["replacement"], rule["description"]) for rule in transformations]
except Exception:
    sys.exit(1)

def apply_transformations(line, line_number, applied_changes):
    original_line = line.rstrip('\n')
    leading_spaces = re.match(r"\s*", original_line).group()
    stripped_line = original_line.strip()
    transformed_line = stripped_line
    change_log = []

    for pattern, replacement, desc in compiled_rules:
        new_line, num_changes = pattern.subn(replacement, transformed_line)
        if num_changes > 0 and stripped_line != new_line:
            new_line_with_indent = leading_spaces + new_line
            log_entry = f"""
            <div style="margin-bottom: 10px;">
              <b>[Line {line_number}] 🔄 {desc}</b><br>
              <span style="background-color: #ffe5e5;">🟢 변경 전: {original_line}</span><br>
              <span style="background-color: #e5ffe5;">🔵 변경 후: {new_line_with_indent}</span>
            </div>
            """
            if log_entry not in applied_changes:
                change_log.append(log_entry)
                applied_changes.add(log_entry)
            transformed_line = new_line

    return leading_spaces + transformed_line, change_log

def format_sql(sql_text):
    return sql_text  # 들여쓰기 유지

def add_line_numbers(text):
    lines = text.splitlines()
    return "\n".join(f"{str(i+1).rjust(4)} | {line}" for i, line in enumerate(lines))

def diff_lines(original, converted):
    diff = ndiff(original.splitlines(), converted.splitlines())
    return "\n".join([
        f"<span style='background-color: #ffe5e5;'>- {line[2:]}</span>" if line.startswith('- ') else
        f"<span style='background-color: #e5ffe5;'>+ {line[2:]}</span>" if line.startswith('+ ') else
        f"  {line[2:]}"
        for line in diff
    ])

def needs_manual_conversion(sql_text):
    upper_sql = sql_text.upper()
    reasons = [kw for kw in manual_check_keywords if kw in upper_sql]
    return (len(reasons) > 0), ', '.join(reasons)

def process_sql_file(file_path):
    if not os.path.isfile(file_path):
        logging.error(f"유효하지 않은 파일 경로입니다: {file_path}")
        return

    file_name = Path(file_path).name
    output_file = CONVERTED_DIR / Path(file_path).with_suffix('').name.replace(' ', '_')
    output_file = output_file.with_name(output_file.name + '_converted.sql')
    log_file = LOG_DIR / (output_file.stem + '_log.txt')

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            query_lines = f.readlines()
    except Exception as e:
        logging.error(f"파일 읽기 오류: {e}")
        return

    transformed_lines = []
    change_log = []
    applied_changes = set()

    for idx, line in enumerate(query_lines, start=1):
        transformed_line, line_change_log = apply_transformations(line, idx, applied_changes)
        transformed_lines.append(transformed_line + '\n')
        change_log.extend(line_change_log)

    formatted_sql = format_sql("".join(transformed_lines))

    try:
        with open(output_file, 'w', encoding='utf-8') as out_f:
            out_f.write(formatted_sql)
    except Exception as e:
        logging.error(f"변환된 SQL 파일 저장 오류: {e}")

    if change_log:
        try:
            with open(log_file, 'w', encoding='utf-8') as log_f:
                log_f.write("\n".join(change_log) + "\n")
        except Exception as e:
            logging.error(f"변환 로그 파일 저장 오류: {e}")
    else:
        log_file = ''

    changed = 'O' if change_log else 'X'
    full_sql_text = "".join(query_lines)
    
    manual_required_flag, manual_reason = needs_manual_conversion(full_sql_text)
    manual_required = 'O' if manual_required_flag else 'X'
    remark = manual_reason if manual_required_flag else ''

    csv_results.append([file_name, output_file.name, Path(log_file).name, changed, manual_required, remark])
    html_logs.append((file_name, full_sql_text, formatted_sql, "".join(change_log)))

    logging.info(f"변환 완료: {output_file}, 변경 로그: {log_file if change_log else '없음'}")

def generate_html_report(output=REPORT_DIR / 'sql_transformation_report.html'):
    nav_links = "".join([
        f"<li data-changed='{csv_results[i][3]}' data-manual='{csv_results[i][4]}'>"
        f"<a href='#report_{i}' onclick='showReport({i}); return false;' id='nav_{i}'>{file}</a></li>"
        for i, (file, *_ ) in enumerate(html_logs)
    ])
    
    rows = ""
    for i, (filename, original, converted, log_text) in enumerate(html_logs):
        diff_html = diff_lines(original, converted)
        display = "block" if i == 0 else "none"
        rows += f"""
        <div class='report' id='report_{i}' style='display:{display};'>
            <h2>{filename}</h2>
            <div class='top'>
                <div class='left'><h3>원본 SQL</h3><pre>{add_line_numbers(original)}</pre></div>
                <div class='right'><h3>변환된 SQL</h3><pre>{add_line_numbers(converted)}</pre></div>
            </div>
            <div class='bottom'>
                <h3>Diff 보기</h3>
                <pre style='background:#f4f4f4;'>{diff_html}</pre>
                <h3>변경 로그</h3>
                {log_text}
            </div>
        </div>
        <hr>
        """
    
    html = f"""
    <html>
    <head>
        <meta charset='UTF-8'>
        <title>SQL 변환 리포트</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; }}
            ul {{
                position: fixed; top: 0; left: 0; width: 250px; height: 100%;
                overflow-y: auto; background: #f0f0f0; padding: 20px 10px 10px 10px; box-sizing: border-box;
                border-right: 1px solid #ccc;
            }}
            ul li {{ margin-bottom: 5px; list-style: none; }}
            ul li a {{
                display: block; padding: 5px 10px; text-decoration: none;
                color: #333; border-radius: 4px;
            }}
            ul li a:hover, ul li a.active {{
                background-color: #007BFF; color: white;
            }}
            .report {{ margin-left: 270px; padding: 20px; }}
            .top {{ display: flex; height: 40vh; overflow: hidden; }}
            .left, .right {{
                width: 50%; overflow: auto; padding: 10px; box-sizing: border-box;
            }}
            .bottom {{ margin-top: 20px; overflow: auto; background: #f9f9f9; padding: 10px; box-sizing: border-box; }}
            pre {{ white-space: pre-wrap; word-wrap: break-word; }}
            .search-bar {{
                margin-bottom: 10px;
                display: flex;
                flex-direction: column;
                gap: 5px;
            }}
            .search-bar input, .search-bar button {{
                padding: 5px;
                border-radius: 4px;
                border: 1px solid #ccc;
            }}
            .search-bar button {{
                background-color: #007BFF;
                color: white;
                cursor: pointer;
            }}
            .search-bar button:hover {{
                background-color: #0056b3;
            }}
        </style>
        <script>
            function showReport(index) {{
                let total = {len(html_logs)};
                for (let i = 0; i < total; i++) {{
                    document.getElementById('report_' + i).style.display = 'none';
                    document.getElementById('nav_' + i).classList.remove('active');
                }}
                document.getElementById('report_' + index).style.display = 'block';
                document.getElementById('nav_' + index).classList.add('active');
                window.scrollTo({{ top: 0, behavior: 'smooth' }});
            }}

            function filterList() {{
                const keyword = document.getElementById("searchInput").value.toLowerCase();
                const changedOnly = document.getElementById("filterChanged").checked;
                const manualOnly = document.getElementById("filterManual").checked;

                document.querySelectorAll("ul li").forEach((li, i) => {{
                    const text = li.textContent.toLowerCase();
                    const changed = li.getAttribute("data-changed") === "O";
                    const manual = li.getAttribute("data-manual") === "O";
                    const match = text.includes(keyword);
                    const passChanged = !changedOnly || changed;
                    const passManual = !manualOnly || manual;

                    li.style.display = (match && passChanged && passManual) ? "block" : "none";
                }});
            }}

            document.addEventListener('DOMContentLoaded', function() {{
                // 스크롤 동기화
                document.querySelectorAll('.report').forEach(function(report) {{
                    var leftDiv = report.querySelector('.left');
                    var rightDiv = report.querySelector('.right');
                    if (leftDiv && rightDiv) {{
                        leftDiv.addEventListener('scroll', function() {{
                            rightDiv.scrollTop = leftDiv.scrollTop;
                        }});
                        rightDiv.addEventListener('scroll', function() {{
                            leftDiv.scrollTop = rightDiv.scrollTop;
                        }});
                    }}
                }});
            }});
        </script>
    </head>
    <body>
        <ul>
            <div class="search-bar">
                <input type="text" id="searchInput" placeholder="파일명 검색..." oninput="filterList()" />
                <label><input type="checkbox" id="filterChanged" onchange="filterList()"> 변경된 SQL만 보기</label>
                <label><input type="checkbox" id="filterManual" onchange="filterList()"> 수동 변환 필요만 보기</label>
            </div>
            {nav_links}
        </ul>
        <div>
            <h1 style='text-align:center; margin-left:240px;'>SQL 변환 리포트</h1>
            {rows}
        </div>
    </body>
    </html>
    """
    with open(output, 'w', encoding='utf-8') as f:
        f.write(html)
    logging.info(f"HTML 리포트 생성 완료: {output}")

def process_directory(dir_path):
    if not os.path.isdir(dir_path):
        logging.error(f"유효하지 않은 디렉토리 경로입니다: {dir_path}")
        return

    files = list(Path(dir_path).rglob('*.sql'))
    if not files:
        logging.info("디렉토리에서 SQL 파일을 찾을 수 없습니다.")
        return

    for file in files:
        process_sql_file(str(file))

def save_csv_summary(csv_file=REPORT_DIR / 'sql_transformation_result.csv'):
    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['번호', '파일명', '변경 파일명', '로그 파일명', '변경 유무 체크', '수동 변환 필요', '비고'])
        for idx, row in enumerate(csv_results, start=1):
            writer.writerow([idx] + row)
    logging.info(f"CSV 요약 파일 저장 완료: {csv_file}")

def choose_directory_or_file():
    while True:
        try:
            choice = input("디렉토리를 선택하려면 1, 파일을 선택하려면 2를 입력하세요: ").strip()
            if choice == '1':
                dir_path = input("디렉토리 경로를 입력하세요: ").strip()
                process_directory(dir_path)
                generate_html_report()
                save_csv_summary()
                break
            elif choice == '2':
                file_path = input("파일 경로를 입력하세요: ").strip()
                process_sql_file(file_path)
                generate_html_report()
                save_csv_summary()
                break
            else:
                print("잘못된 입력입니다. 1 또는 2를 입력하세요.")
        except KeyboardInterrupt:
            logging.info("프로그램이 사용자에 의해 종료되었습니다.")
            sys.exit(0)

if __name__ == "__main__":
    choose_directory_or_file()