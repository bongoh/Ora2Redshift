
import json

# 주어진 변환 규칙
# Transformations data
transformations = [
    # 데이터 타입 변환
    {
        "NUMBER(n, m) → DECIMAL(n, m)": (r'NUMBER\((\d+),\s*(\d+)\)', r'DECIMAL(\1, \2)'),
        "NUMBER(1,0) → SMALLINT": (r'NUMBER\(1,0\)', r'SMALLINT'),
        "NUMBER(10,0) → BIGINT": (r'NUMBER\(10,0\)', r'BIGINT'),
        "RAW(n) → BYTEA": (r'RAW\((\d+)\)', r'BYTEA'),
        "VARCHAR2(n) / NVARCHAR2(n) → VARCHAR(n)": (r'(VARCHAR2|NVARCHAR2)\((\d+)\)', r'VARCHAR(\2)'),
        "CHAR(n) → CHAR(n)": (r'CHAR\((\d+)\)', r'CHAR(\1)'),
        "LONG / CLOB → VARCHAR(65535)": (r'\b(LONG|CLOB)\b', r'VARCHAR(65535)'),
        "BLOB → BYTEA": (r'BLOB', r'BYTEA'),
        "FLOAT → DOUBLE PRECISION": (r'FLOAT', r'DOUBLE PRECISION'),
        "BOOLEAN → BOOLEAN": (r'BOOLEAN', r'BOOLEAN'),
        "INTERVAL → INTERVAL": (r'INTERVAL\((\w+)\)', r'INTERVAL \1'),
        "BFILE → NOT SUPPORTED": (r'\bBFILE\b', r'-- NOT SUPPORTED (Check alternative solution)')
    },
    # 수학 함수 변환
    {
        "ABS / CEIL / FLOOR / ROUND / TRUNC / SIGN / SQRT / MOD / POWER / EXP / COS / SIN / TAN / ACOS / ASIN / ATAN → 동일 함수명 유지": (r'(ABS|CEIL|FLOOR|ROUND|TRUNC|SIGN|SQRT|MOD|POWER|EXP|COS|SIN|TAN|ACOS|ASIN|ATAN)\((.+?)\)', r'\1(\2)'),
        "BITAND(n, m) → (n & m)": (r'BITAND\((.+?),\s*(.+?)\)', r'(\1 & \2)'),
        "REMAINDER(n2, n1) → n2 - n1 * ROUND(n2 / n1)": (r'REMAINDER\((.+?),\s*(.+?)\)', r'(\1 - \2 * round(\1 / \2))'),
        "LOG(m, n) → log(m, n)": (r'LOG\(([^,]+),\s*([^,]+)\)', r'log(\1, \2)'),
        "LOG(n) / LN(n) → ln(n)": (r'LOG|LN\(([^,]+)\)', r'ln(\1)'),
        "TANH(n) → (exp(n) - exp(-n)) / (exp(n) + exp(-n))": (r'TANH\(([^)]+)\)', r'((exp(\1) - exp(-\1)) / (exp(\1) + exp(-\1)))')
    },
    # 문자열 함수 변환
    {
        "ASCII / LENGTH / INITCAP / LOWER / UPPER → 동일 함수명 유지": (r'(ASCII|LENGTH|INITCAP|LOWER|UPPER)\((.+?)\)', r'\1(\2)'),
        "RPAD(string, n, char) → LEFT(string || REPEAT(char, n), n)": (r'RPAD\((.+?),\s*(\d+),\s*(.+?)\)', r'LEFT(\1 || REPEAT(\3, \2), \2)'),
        "LPAD(string, n, char) → RIGHT(REPEAT(char, n) || string, n)": (r'LPAD\((.+?),\s*(\d+),\s*(.+?)\)', r'RIGHT(REPEAT(\3, \2) || \1, \2)'),
        "CHR(n) → ASCII_TO_CHAR(n)": (r'CHR\((.+?)\)', r'ASCII_TO_CHAR(\1)'),
        "INSTR(string, substring) → strpos(string, substring)": (r'INSTR\((.+?),\s*(.+?)\)', r'strpos(\1, \2)'),
        "CONCAT(char1, char2) → concat(char1, char2)": (r'CONCAT\((.+?),\s*(.+?)\)', r'concat(\1, \2)'),
        "LTRIM(char, set) / RTRIM(char, set) → 동일 함수명 유지": (r'(LTRIM|RTRIM)\((.+?),\s*(.+?)\)', r'\1(\2, \3)'),
        "SUBSTR → SUBSTRING": (r'SUBSTR\((.*?),\s*(\d+),\s*(\d+)\)', r'SUBSTRING(\1 FROM \2 FOR \3)')
    },
    # 날짜 및 시간 함수 변환
    {
        "DATE → TIMESTAMP": (r'\bDATE\b', r'TIMESTAMP'),
        "SYSDATE → current_date, current_timestamp, clock_timestamp": (r'\bSYSDATE\b', r'current_date, current_timestamp, clock_timestamp'),
        "CURRENT_DATE / CURRENT_TIMESTAMP → 동일 함수명 유지": (r'\b(CURRENT_DATE|CURRENT_TIMESTAMP)\b', r'\1'),
        "TO_CHAR(value) → CAST(value AS VARCHAR)": (r'TO_CHAR\((.+?)\)', r'CAST(\1 AS VARCHAR)')
    },
    # 기타 변환
    {
        "NVL → COALESCE": (r'NVL\((.*?),\s*(.*?)\)', r'COALESCE(\1, \2)'),
        "DECODE → CASE WHEN": (r'DECODE\((.*?),\s*(.*?),\s*(.*?)\)', r'CASE WHEN \1 = \2 THEN \3 END'),
    }
]



# 변환 규칙을 JSON 형식으로 변환하는 함수
def convert_to_json_format(transformations):
    json_rules = []
    
    for category in transformations:
        for description, (pattern, replacement) in category.items():
            json_rules.append({
                "description": description,
                "pattern": pattern,
                "replacement": replacement
            })
    
    return json_rules

# 변환 실행
json_data = convert_to_json_format(transformations)

# JSON 파일로 저장
output_file = 'transformations.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(json_data, f, indent=4, ensure_ascii=False)

print(f"JSON 파일이 '{output_file}'로 저장되었습니다.")
