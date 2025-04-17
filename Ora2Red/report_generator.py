import os
import difflib
from difflib import ndiff
from jinja2 import Environment, FileSystemLoader
import pandas as pd
import datetime

class ReportGenerator:
    def __init__(self, config):
        self.config = config
        self.csv_results = []
        self.html_logs = []

    def add_execution_result(self, file_name, original_sql, transformed_sql,
                             execution_time, error=None, plan="", rows="", cpu_time="", applied_rules=None):
        changed = original_sql.strip() != transformed_sql.strip()
        manual_required = bool(error)
        reason = error if manual_required else ""
        first_token = original_sql.strip().split()[0].upper() if original_sql.strip() else ''
        category = 'DDL' if first_token in ('CREATE', 'ALTER', 'DROP', 'TRUNCATE', 'COMMENT') else 'DML'
        transformed_file = file_name
        log_file = ''

        self.csv_results.append({
            "file_name": file_name,
            "transformed_file": transformed_file,
            "log_file": log_file,
            "changed": 'O' if changed else '',
            "manual_required": 'O' if manual_required else '',
            "reason": reason,
            "category": category,
            "applied_rules": ", ".join(applied_rules or [])
        })

    def _get_config_value(self, key):
        if isinstance(self.config, dict):
            return self.config.get(key)
        else:
            if key == 'output_dir':
                return self.config.REPORT_DIR
            elif key == 'html_name':
                return self.config.HTML_REPORT_NAME
            elif key == 'csv_name':
                return self.config.CSV_REPORT_NAME
            else:
                return None

    def _generate_unique_filename(self, base_name):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        base, ext = os.path.splitext(base_name)
        return f"{base}_{timestamp}{ext}"

    def generate_csv(self):
        output_dir = self._get_config_value('output_dir')
        os.makedirs(output_dir, exist_ok=True)
        csv_base = os.path.join(output_dir, self._get_config_value('csv_name'))
        csv_path = self._generate_unique_filename(csv_base)

        # 한글 컬럼명 정의
        column_map = {
            "file_name": "원본 파일명",
            "transformed_file": "변환된 파일",
            "log_file": "로그 파일",
            "changed": "변경 여부",
            "manual_required": "수동 검토 필요",
            "reason": "수동 검토 사유",
            "category": "SQL 유형"
        }

        summary_columns = ['file_name', 'transformed_file', 'log_file', 'changed', 'manual_required', 'reason', 'category']
        df = pd.DataFrame(self.csv_results, columns=column_map.keys())
        df.rename(columns=column_map, inplace=True)
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        # CSV 파일 마지막 줄에 검증 방법 요약 주석 추가
        with open(csv_path, 'a', encoding='utf-8-sig') as f:
            f.write("\n# 검증 방법: SQL AST 파싱 및 SQLite EXPLAIN을 사용하여 쿼리의 문법 및 최소 실행 계획 여부를 검증함.")
        print(f"CSV 리포트 생성: {csv_path}")
        return df

    def save_csv_summary(self, df, output_dir):
        # 외부에서 호출 시 generate_csv() 대신 사용
        return self.generate_csv()

    def generate_custom_line_diff(self, original_sql, transformed_sql, is_manual=False):
        orig_lines = original_sql.splitlines()
        trans_lines = transformed_sql.splitlines()
        max_lines = max(len(orig_lines), len(trans_lines))
        html_parts = ["<table class='diff'>"]
        html_parts.append("<tr><th class='line-number'>#</th><th>원본</th><th>변경</th></tr>")
        for i in range(max_lines):
            orig_line = orig_lines[i] if i < len(orig_lines) else ""
            trans_line = trans_lines[i] if i < len(trans_lines) else ""
            if orig_line.strip() != trans_line.strip():
                css_class_sub = 'diff_sub_manual' if is_manual else 'diff_sub'
                css_class_add = 'diff_add_manual' if is_manual else 'diff_add'
                orig_cell = f"<td class='{css_class_sub}'>{orig_line}</td>"
                trans_cell = f"<td class='{css_class_add}'>{trans_line}</td>"
            else:
                orig_cell = f"<td>{orig_line}</td>"
                trans_cell = f"<td>{trans_line}</td>"
            html_parts.append(f"<tr><td class='line-number'>{i+1}</td>{orig_cell}{trans_cell}</tr>")
        html_parts.append("</table>")
        return "".join(html_parts)

    def generate_word_level_diff(self, original_sql, transformed_sql, is_manual=False):
        def word_diff_line(orig_line, trans_line):
            orig_words = orig_line.split()
            trans_words = trans_line.split()
            sm = difflib.SequenceMatcher(a=orig_words, b=trans_words)
            result = []
            del_color = "#ffff99" if is_manual else "#ffdddd"
            ins_color = "#ffff99" if is_manual else "#ddffdd"
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == 'equal':
                    result.append(" ".join(orig_words[i1:i2]))
                elif tag == 'delete':
                    deleted_text = " ".join(orig_words[i1:i2])
                    result.append(f"<span style='background-color: {del_color}; display:inline-block;'>{deleted_text}<br><span style='font-size:0.8em; color: red;'>-</span></span>")
                elif tag == 'insert':
                    inserted_text = " ".join(trans_words[j1:j2])
                    result.append(f"<span style='background-color: {ins_color}; display:inline-block;'>{inserted_text}<br><span style='font-size:0.8em; color: green;'>+</span></span>")
                elif tag == 'replace':
                    deleted_text = " ".join(orig_words[i1:i2])
                    inserted_text = " ".join(trans_words[j1:j2])
                    result.append(f"<span style='background-color: {del_color}; display:inline-block;'>{deleted_text}<br><span style='font-size:0.8em; color: red;'>-</span></span>")
                    result.append(f"<span style='background-color: {ins_color}; display:inline-block;'>{inserted_text}<br><span style='font-size:0.8em; color: green;'>+</span></span>")
            return " ".join(result)

        orig_lines = original_sql.splitlines()
        trans_lines = transformed_sql.splitlines()
        diff_lines = []
        max_lines = max(len(orig_lines), len(trans_lines))
        for i in range(max_lines):
            orig_line = orig_lines[i] if i < len(orig_lines) else ""
            trans_line = trans_lines[i] if i < len(trans_lines) else ""
            diff_lines.append(word_diff_line(orig_line, trans_line))
        return "<br>".join(diff_lines)

    def diff_lines(self, original, converted):
        diff = ndiff(original.splitlines(), converted.splitlines())
        return "\n".join([
            f"<span style='background-color: #ffe5e5;'>- {line[2:]}</span>" if line.startswith('- ') else
            f"<span style='background-color: #e5ffe5;'>+ {line[2:]}</span>" if line.startswith('+ ') else
            f"  {line[2:]}" for line in diff
        ])

    def generate_html_report(self, results, output_dir, use_custom_diff=True, use_word_level=False, use_ndiff=False):

        os.makedirs(output_dir, exist_ok=True)
        summary_columns = ['file_name', 'transformed_file', 'log_file', 'changed', 'manual_required', 'reason', 'category']
        df = pd.DataFrame(results, columns=summary_columns)
        manual_dict = {r['file_name']: r['manual_required'] for r in df.to_dict(orient='records')}
        diff_dict = {}
        change_log_dict = {}
        for log in self.html_logs:
            file_name, original_sql, transformed_sql, change_log = log
            is_manual = (manual_dict.get(file_name, '') == 'O')
            if original_sql.strip() == transformed_sql.strip():
                diff_html = "<div style='padding:10px;'>변경 없음</div>"
            else:
                if use_word_level:
                    diff_html = self.generate_word_level_diff(original_sql, transformed_sql, is_manual=is_manual)
                elif use_ndiff:
                    diff_html = self.diff_lines(original_sql, transformed_sql)
                elif use_custom_diff:
                    diff_html = self.generate_custom_line_diff(original_sql, transformed_sql, is_manual=is_manual)
                else:
                    html_diff_obj = difflib.HtmlDiff(wrapcolumn=80)
                    diff_html = html_diff_obj.make_table(original_sql.splitlines(), transformed_sql.splitlines(),
                                                        fromdesc="원본", todesc="변경", context=True, numlines=3)
            diff_dict[file_name] = diff_html
            change_log_dict[file_name] = change_log
        df['diff'] = df['file_name'].map(lambda fn: diff_dict.get(fn, ""))
        df['change_log'] = df['file_name'].map(lambda fn: change_log_dict.get(fn, ""))
        total_files = len(df)
        changed_files = df[df['changed'] == 'O'].shape[0]
        manual_files = df[df['manual_required'] == 'O'].shape[0]
        global_summary = f"총 파일 수: {total_files}, 변경된 파일 수: {changed_files}, 수동 검토 필요: {manual_files}"
        
        env = Environment(loader=FileSystemLoader(searchpath="."))
        template = env.from_string("""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
      <meta charset="UTF-8">
      <title>Transformation Report</title>
      <style>
        body { font-family: Arial, sans-serif; background: #f7f9fc; margin: 0; padding: 0; transition: font-size 0.3s ease; }
        #container { display: flex; height: 100vh; }
        #sidebar { width: 30%; max-width: 300px; background: #ffffff; padding: 10px; overflow-y: auto; border-right: 1px solid #ccc; }
        #globalSummary { margin-bottom: 10px; font-weight: bold; }
        /* UI 컨트롤 스타일 */
        #ui-controls { padding: 10px; text-align: center; background: #eef; }
        #ui-controls label { font-size: 14px; }
        #ui-controls input { vertical-align: middle; }
        #ui-controls span { font-size: 14px; }
        #filterButtons { margin-bottom: 10px; }
        #filterButtons button { margin-right: 5px; padding: 5px 8px; }
        #sidebar input { width: 100%; padding: 5px; margin-bottom: 10px; }
        #sidebar ul { list-style: none; padding: 0; margin: 0; }
        #sidebar li { padding: 5px; cursor: pointer; border-bottom: 1px solid #eee; }
        #sidebar li:hover { background: #f0f0f0; }
        #content { flex: 1; padding: 20px; overflow-y: auto; }
        .badge { display: inline-block; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; }
        .ok { background-color: #48bb78; color: white; }
        .manual { background-color: #f6ad55; color: white; }
        .nochange { background-color: #a0aec0; color: white; }
        pre { background: #f0f0f0; color: #333; padding: 10px; border-radius: 6px; font-family: monospace; white-space: pre-wrap; }
        table.diff { width: 100%; border-collapse: collapse; margin-top: 10px; }
        table.diff th, table.diff td { padding: 4px; border: 1px solid #ddd; }
        .line-number { width: 40px; text-align: right; color: #888; }
        .diff_sub { background-color: #ffdddd; }
        .diff_add { background-color: #ddffdd; }
        .diff_sub_manual { background-color: #ffff99; }
        .diff_add_manual { background-color: #ffff99; }
        .modal-btn { padding: 8px 12px; background-color: #007BFF; border: none; color: white; border-radius: 4px; cursor: pointer; margin-top: 10px; }
        .modal-btn:hover { background-color: #0056b3; }
        footer { text-align: center; font-size: 10px; color: #555; margin-top: 20px; }
      </style>
    </head>
    <body>
      <div id="ui-controls">
        <label for="fontsize">글꼴 크기: </label>
        <input type="range" id="fontsize" min="10" max="24" value="14" />
        <span id="fontsize-value">14px</span>
      </div>
      <div id="container">
        <div id="sidebar">
          <div id="globalSummary">{{ global_summary }}</div>
          <div id="filterButtons">
            <button class="filter-btn" data-filter="all">전체</button>
            <button class="filter-btn" data-filter="not_modified">수정 없음</button>
            <button class="filter-btn" data-filter="auto_modified">수정 완료</button>
            <button class="filter-btn" data-filter="manual_modified">메뉴얼 수정</button>
          </div>
          <input type="text" id="searchInput" placeholder="파일 검색">
          <ul id="fileList">
            {% for row in rows %}
              <li class="file-item" data-index="{{ loop.index0 }}">{{ row.transformed_file }}</li>
            {% endfor %}
          </ul>
        </div>
        <div id="content">
          <h2>파일 상세 내용</h2>
          <div id="fileDetail" contenteditable="false" style="border: none;">
            <p>좌측에서 파일을 선택하세요.</p>
          </div>
        </div>
      </div>
      <footer>
        검증 방법: SQL AST 파싱 및 SQLite EXPLAIN을 사용하여 쿼리의 문법 및 최소 실행 계획 여부를 검증함.
      </footer>
      <script>
        // 글꼴 크기 조절 컨트롤
        const fontSizeSlider = document.getElementById("fontsize");
        const fontSizeValue = document.getElementById("fontsize-value");
        fontSizeSlider.addEventListener("input", function(){
            var size = fontSizeSlider.value;
            fontSizeValue.textContent = size + "px";
            document.body.style.fontSize = size + "px";
        });
        
        const rows = {{ rows|tojson }};
        const fileList = document.getElementById('fileList');
        const searchInput = document.getElementById('searchInput');
        const filterButtons = document.querySelectorAll(".filter-btn");
        let currentFilter = "all";
        function filterFileList() {
          const searchText = searchInput.value.toLowerCase();
          const items = fileList.getElementsByTagName('li');
          for (let i = 0; i < items.length; i++) {
            const index = items[i].getAttribute('data-index');
            const row = rows[index];
            const matchesSearch = row.transformed_file.toLowerCase().includes(searchText);
            let matchesFilter = false;
            if (currentFilter === "all") { matchesFilter = true; }
            else if (currentFilter === "not_modified") { matchesFilter = (row.changed !== "O"); }
            else if (currentFilter === "auto_modified") { matchesFilter = (row.changed === "O" && row.manual_required !== "O"); }
            else if (currentFilter === "manual_modified") { matchesFilter = (row.manual_required === "O"); }
            items[i].style.display = (matchesSearch && matchesFilter) ? "" : "none";
          }
        }
        searchInput.addEventListener('keyup', filterFileList);
        filterButtons.forEach(function(btn) {
          btn.addEventListener('click', function() {
            currentFilter = this.getAttribute('data-filter');
            filterButtons.forEach(b => b.classList.remove("active"));
            this.classList.add("active");
            filterFileList();
          });
        });
        const items = document.getElementsByClassName('file-item');
        Array.from(items).forEach(function(item) {
          item.addEventListener('click', function() {
            const index = parseInt(this.getAttribute('data-index'));
            const row = rows[index];
            let detailHTML = "<h3>변환 된 파일 경로: " + row.transformed_file + "</h3>";
            detailHTML += "<p><strong>로그 파일:</strong> " + row.log_file + "</p>";
            detailHTML += "<p><strong>검증 결과:</strong> ";
            if (row.changed === 'O') {
              detailHTML += '<span class="badge manual">문제 있음</span>';
            } else {
              detailHTML += '<span class="badge ok">문제 없음</span>';
            }
            detailHTML += "</p>";
            detailHTML += "<p><strong>추가 검증:</strong> ";
            if (row.manual_required === 'O') {
              detailHTML += '<span class="badge manual">검증 필요</span>';
            } else {
              detailHTML += '<span class="badge ok">검증 불필요</span>';
            }
            detailHTML += "</p>";
            detailHTML += "<p><strong>카테고리 (DDL/DML):</strong> " + row.category + "</p>";
            detailHTML += "<p><strong>전환 방법 설명:</strong> " + (row.reason || '') + "</p>";
            detailHTML += "<h4>Diff 결과</h4>";
            detailHTML += row.diff;
            if (row.change_log) {
              detailHTML += "<br><button class='modal-btn' id='transformationLogBtn'>Transformation Log 보기</button>";
            }
            document.getElementById('fileDetail').innerHTML = detailHTML;
            const logBtn = document.getElementById('transformationLogBtn');
            if (logBtn) {
              logBtn.addEventListener('click', function() {
                let newWindow = window.open("", "TransformationLog", "width=800,height=600,scrollbars=yes");
                newWindow.document.write("<html><head><title>Transformation Log</title>");
                newWindow.document.write("<style>");
                newWindow.document.write("body { font-family: Arial, sans-serif; padding: 10px; transition: font-size 0.3s ease; }");
                newWindow.document.write("pre { background: #f0f0f0; padding: 10px; border-radius: 6px; white-space: pre-wrap; }");
                newWindow.document.write("</style>");
                // 모달 창 내 UI 컨트롤 추가 (글꼴 크기 조절 슬라이더)
                newWindow.document.write("</head><body>");
                newWindow.document.write("<div id='modal-ui-controls' style='padding:10px; background:#eef; text-align:center;'>");
                newWindow.document.write("<label for='modal-fontsize'>글꼴 크기: </label>");
                newWindow.document.write("<input type='range' id='modal-fontsize' min='10' max='24' value='14' />");
                newWindow.document.write("<span id='modal-fontsize-value'>14px</span>");
                newWindow.document.write("</div>");
                newWindow.document.write("<h4>Transformation Log</h4>");
                newWindow.document.write("<pre>" + row.change_log + "</pre>");
                newWindow.document.write("<script>");
                newWindow.document.write("const modalFontSizeSlider = document.getElementById('modal-fontsize');");
                newWindow.document.write("const modalFontSizeValue = document.getElementById('modal-fontsize-value');");
                newWindow.document.write("modalFontSizeSlider.addEventListener('input', function(){");
                newWindow.document.write(" var size = modalFontSizeSlider.value;");
                newWindow.document.write(" modalFontSizeValue.textContent = size + 'px';");
                newWindow.document.write(" document.body.style.fontSize = size + 'px';");
                newWindow.document.write("});");
                newWindow.document.write("<\/script>");
                newWindow.document.write("</body></html>");
                newWindow.document.close();
              });
            }
          });
        });
      </script>
    </body>
    </html>
        """)
        html_output = template.render(rows=df.to_dict(orient='records'), global_summary=global_summary)
        # HTML 리포트 파일을 output_dir 바로 하위에 생성 (예: reports/)
        output_dir = self._get_config_value('output_dir')
        os.makedirs(output_dir, exist_ok=True)
        html_base = os.path.join(output_dir, self._get_config_value('html_name'))
        html_path = self._generate_unique_filename(html_base)
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_output)
        print(f"HTML 리포트 생성: {html_path}")
        return df

    def generate_html(self):

        output_dir = self._get_config_value('output_dir')
        return self.generate_html_report(self.csv_results, output_dir)
    
    def import_results_from_json(self, json_path):
        import json
        if not os.path.exists(json_path):
            print(f"파일이 존재하지 않습니다: {json_path}")
            return
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            raw_results = data.get("csv_results", [])
            cleaned_results = []
            for i, row in enumerate(raw_results):
                if isinstance(row, dict):
                    cleaned_results.append(row)
                else:
                    print(f"⚠️ [WARNING] csv_results[{i}]가 dict가 아님 → {type(row)}: {row}")
            self.csv_results = cleaned_results
            self.html_logs = data.get("html_logs", [])
        print(f"기존 결과 파일을 불러왔습니다: {json_path}")

    def export_results_to_json(self, json_path):
        import json
        os.makedirs(os.path.dirname(json_path), exist_ok=True)

        # ✅ 딕셔너리만 저장하도록 필터링 추가
        safe_csv_results = [dict(row) for row in self.csv_results if isinstance(row, dict)]

        data = {
            "csv_results": safe_csv_results,
            "html_logs": self.html_logs
        }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"결과가 JSON으로 저장되었습니다: {json_path}")