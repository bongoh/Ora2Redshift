import sqlparse
from typing import List, Tuple

# 분류용 키워드 집합
DDL_KEYWORDS = {'CREATE', 'ALTER', 'DROP', 'TRUNCATE', 'COMMENT'}
DML_KEYWORDS = {'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'MERGE'}
CONTROL_KEYWORDS = {'COMMIT', 'ROLLBACK', 'SAVEPOINT'}
PLSQL_KEYWORDS = {'DECLARE', 'BEGIN', 'EXCEPTION', 'END', 'CURSOR', 'LOOP'}

def classify_statements(sql_text: str) -> List[Tuple[str, str]]:
    """
    SQL 텍스트를 문장 단위로 분리하고,
    DDL, DML, PLSQL, CONTROL, UNKNOWN 중 하나로 분류합니다.

    :param sql_text: 전체 SQL 스크립트 텍스트
    :return: [(SQL 문장, 유형), ...]
    """
    # 주석 제거 및 정리
    cleaned = sqlparse.format(sql_text, strip_comments=True).strip()
    statements = sqlparse.split(cleaned)

    results: List[Tuple[str, str]] = []

    for stmt in statements:
        stripped = stmt.strip()
        if not stripped:
            continue

        parsed = sqlparse.parse(stripped)
        if not parsed:
            results.append((stripped, 'UNKNOWN'))
            continue

        stmt_upper = stripped.upper()

        # PLSQL 키워드 포함 여부 판단 (BEGIN 블록, DECLARE 등)
        if any(keyword in stmt_upper for keyword in PLSQL_KEYWORDS):
            kind = 'PLSQL'

        # CONTROL 문 판단
        elif any(stmt_upper.startswith(k) for k in CONTROL_KEYWORDS):
            kind = 'CONTROL'

        else:
            # 첫 키워드 기준으로 DDL/DML 판별
            first_token = parsed[0].token_first(skip_cm=True)
            token_value = first_token.value.upper() if first_token else ''

            keyword = token_value.split()[0] if token_value else ''
            if keyword in DDL_KEYWORDS:
                kind = 'DDL'
            elif keyword in DML_KEYWORDS:
                kind = 'DML'
            else:
                kind = 'UNKNOWN'

        results.append((stripped, kind))

    return results