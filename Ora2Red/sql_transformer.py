import re
import json
import logging
from difflib import ndiff
from typing import List, Tuple, Set


class SQLTransformer:
    def __init__(self, config):
        self.config = config
        self.transformations = self.load_transformations(self.config.TRANSFORMATIONS_FILE)
        self.compiled_rules = self.compile_rules(self.transformations)

    def load_transformations(self, file_path: str) -> List[dict]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"변환 규칙 로드 실패: {e}")
            raise

    def compile_rules(self, transformations: List[dict]) -> List[dict]:
        sorted_transforms = sorted(transformations, key=lambda x: x.get("priority", 1000))
        compiled = []
        for rule in sorted_transforms:
            compiled_rule = {
                "pattern": re.compile(rule["pattern"], re.IGNORECASE),
                "replacement": rule["replacement"],
                "description": rule["description"],
                "manual_review_required": rule.get("manual_review_required", False),
                "manual_reason": rule.get("manual_reason", ""),
                "priority": rule.get("priority", 0),
                "applicable_to": rule.get("applicable_to", ["DDL", "DML"]),
                "criticality": rule.get("criticality", "low"),
                "notes": rule.get("notes", "")
            }
            compiled.append(compiled_rule)
        return compiled

    def apply_transformations(
        self,
        line: str,
        line_number: int,
        applied_changes: Set[str],
        sql_type: str = None
    ) -> Tuple[str, List[str], bool, List[str]]:
        original_line = line.rstrip('\n')
        leading_spaces = re.match(r"\s*", original_line).group()
        stripped_line = original_line.strip()
        transformed_line = stripped_line
        change_log = []
        manual_required = False
        manual_reasons = []

        for rule in self.compiled_rules:
            if sql_type and sql_type.upper() not in rule.get("applicable_to", []):
                continue

            pattern = rule["pattern"]
            replacement = rule["replacement"]
            desc = rule["description"]
            manual_review_required = rule["manual_review_required"]
            manual_reason = rule["manual_reason"]

            new_line, num_changes = pattern.subn(replacement, transformed_line)

            if num_changes > 0 and stripped_line != new_line:
                new_line_with_indent = leading_spaces + new_line
                manual_info = f" ⚠️ 수동 검토 필요: {manual_reason}" if manual_review_required and manual_reason else ""
                log_key = f"{line_number}-{desc}-{pattern.pattern}"

                if log_key not in applied_changes:
                    log_entry = (
                        f"<div style='margin-bottom: 10px;'>"
                        f"<b>[Line {line_number}] 🔄 {desc}{manual_info}</b><br>"
                        f"<span style='background-color: #ffe5e5;'>🟢 변경 전: {original_line}</span><br>"
                        f"<span style='background-color: #e5ffe5;'>🔵 변경 후: {new_line_with_indent}</span>"
                        f"</div>"
                    )
                    change_log.append(log_entry)
                    applied_changes.add(log_key)

                transformed_line = new_line
                if manual_review_required:
                    manual_required = True
                    if manual_reason:
                        manual_reasons.append(manual_reason)

        return leading_spaces + transformed_line, change_log, manual_required, list(set(manual_reasons))

    def format_sql(self, sql_text: str) -> str:
        return sql_text

    def add_line_numbers(self, text: str) -> str:
        lines = text.splitlines()
        return "\n".join(f"{str(i+1).rjust(4)} | {line}" for i, line in enumerate(lines))

    def diff_lines(self, original: str, converted: str) -> str:
        diff = ndiff(original.splitlines(), converted.splitlines())
        return "\n".join([
            f"<span style='background-color: #ffe5e5;'>- {line[2:]}</span>" if line.startswith('- ') else
            f"<span style='background-color: #e5ffe5;'>+ {line[2:]}</span>" if line.startswith('+ ') else
            f"  {line[2:]}"
            for line in diff
        ])

    def needs_manual_conversion(self, sql_text: str) -> Tuple[bool, str]:
        upper_sql = sql_text.upper()
        reasons = [kw for kw in self.config.manual_check_keywords if kw in upper_sql]
        return (len(reasons) > 0), ', '.join(reasons)