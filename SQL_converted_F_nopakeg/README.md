
# 개요
 - 이 도구는 Oracle SQL 파일을 읽어 Redshift SQL로 자동 변환하고, 변경 로그 및 수동 확인이 필요한 항목을 식별합니다. 변환 결과는 다음 세 가지 포맷으로 저장됩니다

## 기능 
### 1. 자동 변환
 - transformations.json에 정의된 규칙으로 줄 단위 변환 수행
 - 기존 들여쓰기 유지
 - 변경 발생 시 변경 전/후 로그 저장

### 2. 수동 검토 키워드 탐지
 - 다음 키워드가 포함된 경우 수동 검토 대상
   - [ 'DECLARE', 'EXCEPTION WHEN OTHERS', 'CONNECT BY PRIOR' ]

### 3. 리포트 출력
 - HTML 리포트 (reports/sql_transformation_report.html)
   - 파일별 SQL 원문, 변환문, diff, 변경 로그 시각화
   - 검색 및 필터 기능 포함 (변경된 파일/수동 필요 필터)

 - CSV 요약 (reports/sql_transformation_result.csv)
 
    | 번호 |  파일명  |     변경 파일명    |  로그 파일명 | 변경 유무 체크 | 수동 변환 필요 | 비고 |
    |:----:|:--------:|:------------------:|:------------:|:--------------:|:--------------:|:----:|
    | 1    | test.sql | test_converted.sql | test_log.txt | O              | X              |      |


### 4. 내부 함수 요약
| 함수명                   | 설명                                |
|--------------------------|-------------------------------------|
| apply_transformations    | SQL 한 줄 단위로 변환 수행          |
| process_sql_file         | 단일 SQL 파일 전체 처리             |
| process_directory        | 폴더 내 모든 SQL 파일 처리          |
| generate_html_report     | HTML 리포트 생성                    |
| save_csv_summary         | CSV 요약 파일 저장                  |
| choose_directory_or_file | 실행 모드 선택 (디렉토리 또는 파일) |

## 디렉토리 구조
```
.
├── transformations.json         # 변환 규칙 정의
├── converted_sqls/              # 변환된 SQL 파일 저장 위치
├── logs/                        # 각 SQL에 대한 로그 저장 위치
├── reports/                     # HTML 리포트 및 CSV 요약 파일 저장
├── sql_transformer.py          # 메인 실행 파일

```


# 실행 방법
```bash
python sql_transformer.py

디렉토리를 선택하려면 1, 파일을 선택하려면 2를 입력하세요: 1
디렉토리 경로를 입력하세요: ./oracle_sqls
```


# 변환 
## ✅ Oracle → Redshift SQL 변환 규칙표 (자동 변환 가능 항목 포함)

| Category     | Description                                     | Pattern                                                                 | Replacement                                                  |
|--------------|-------------------------------------------------|-------------------------------------------------------------------------|--------------------------------------------------------------|
| 선언/제어문   | Oracle DECLARE → 수동 변환 필요                   | `DECLARE\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+[^;]+;`                            | `-- DECLARE \1 ... (convert manually)`                      |
| 예외 처리     | EXCEPTION WHEN OTHERS → Redshift 없음              | `EXCEPTION\s+WHEN\s+OTHERS\s+THEN`                                      | `-- EXCEPTION WHEN OTHERS THEN (convert manually)`          |
| 제어문       | BEGIN / END 블록 유지                             | `\bBEGIN`                                                               | `BEGIN`                                                     |
| 제어문       |                                                  | `\bEND\b`                                                                | `END`                                                       |
| 데이터 타입   | NUMBER(n,m) → DECIMAL(n,m)                       | `NUMBER\((\d+),\s*(\d+)\)`                                              | `DECIMAL(\1, \2)`                                           |
| 데이터 타입   | NUMBER(10,0) → BIGINT                            | `NUMBER\(10,\s*0\)`                                                    | `BIGINT`                                                    |
| 데이터 타입   | NUMBER(1,0) → SMALLINT                           | `NUMBER\(1,\s*0\)`                                                     | `SMALLINT`                                                  |
| 데이터 타입   | RAW(n) → BYTEA                                   | `\bRAW\(\d+\)`                                                          | `BYTEA`                                                     |
| 데이터 타입   | VARCHAR2(n), NVARCHAR2(n) → VARCHAR(n)           | `\b(VARCHAR2|NVARCHAR2)\((\d+)\)`                                       | `VARCHAR(\2)`                                               |
| 데이터 타입   | CHAR(n) 유지                                     | `\bCHAR\((\d+)\)`                                                       | `CHAR(\1)`                                                  |
| 데이터 타입   | LONG, CLOB → VARCHAR(65535)                      | `\b(LONG|CLOB)\b`                                                       | `VARCHAR(65535)`                                            |
| 데이터 타입   | BLOB → BYTEA                                     | `\bBLOB\b`                                                              | `BYTEA`                                                     |
| 데이터 타입   | FLOAT → DOUBLE PRECISION                         | `\bFLOAT\b`                                                             | `DOUBLE PRECISION`                                          |
| 데이터 타입   | BOOLEAN 유지                                     | `\bBOOLEAN\b`                                                           | `BOOLEAN`                                                   |
| 데이터 타입   | INTERVAL(n) → INTERVAL n                         | `INTERVAL\((\w+)\)`                                                     | `INTERVAL \1`                                               |
| 데이터 타입   | BFILE → 지원 안 함                                | `\bBFILE\b`                                                             | `-- NOT SUPPORTED (Use external storage)`                  |
| 수학 함수     | 수학 함수는 유지                                  | `\bABS`                                                                 | `CEIL`                                                      |
| 수학 함수     | BITAND(n, m) → (n & m)                           | `BITAND\((.*?),\s*(.*?)\)`                                             | `(\1 & \2)`                                                 |
| 수학 함수     | REMAINDER(n1, n2) → n1 - n2 * ROUND(n1 / n2)     | `REMAINDER\((.*?),\s*(.*?)\)`                                          | `(\1 - \2 * ROUND(\1 / \2))`                                |
| 수학 함수     | LOG(m, n) → LOG(m, n)                            | `LOG\((.*?),\s*(.*?)\)`                                                | `LOG(\1, \2)`                                               |
| 수학 함수     | LOG(n), LN(n) → LN(n)                            | `LOG\((.*?)\)`                                                          | `LN(\1)`                                                    |
| 수학 함수     | TANH(n) → 수식으로 변환                           | `TANH\((.*?)\)`                                                         | `((EXP(\1) - EXP(-\1)) / (EXP(\1) + EXP(-\1)))`             |
| 문자열 함수   | ASCII 유지                                       | `\bASCII`                                                               | `ASCII`                                                     |
| 문자열 함수   | RPAD → LEFT(str)                                 | `RPAD\((.*?),\s*(.*?),\s*(.*?)\)`                                      | `LEFT(\1, \2)`                                              |
| 문자열 함수   | LPAD → RIGHT(REPEAT(pad, n))                    | `LPAD\((.*?),\s*(.*?),\s*(.*?)\)`                                      | `RIGHT(REPEAT(\3, \2), \2)`                                |
| 문자열 함수   | CHR(n) → ASCII_TO_CHAR(n)                        | `CHR\((.*?)\)`                                                          | `ASCII_TO_CHAR(\1)`                                         |
| 문자열 함수   | INSTR(a, b) → STRPOS(a, b)                       | `INSTR\((.*?),\s*(.*?)\)`                                              | `STRPOS(\1, \2)`                                            |
| 문자열 함수   | CONCAT(a, b) → 유지                              | `CONCAT\((.*?),\s*(.*?)\)`                                             | `CONCAT(\1, \2)`                                            |
| 문자열 함수   | LTRIM / RTRIM 유지                               | `LTRIM\((.*?),\s*(.*?)\)`                                              | `RTRIM(\1, \2)`                                             |
| 문자열 함수   | SUBSTR → SUBSTRING FROM FOR                     | `SUBSTR\((.*?),\s*(.*?),\s*(.*?)\)`                                    | `SUBSTRING(\1 FROM \2 FOR \3)`                             |
| 날짜/시간     | DATE → TIMESTAMP                                 | `\bDATE\b`                                                              | `TIMESTAMP`                                                 |
| 날짜/시간     | CURRENT_DATE, CURRENT_TIMESTAMP 유지             | `\bCURRENT_DATE\b`                                                     | `CURRENT_DATE`                                              |
| 날짜/시간     | SYSDATE → CURRENT_TIMESTAMP                      | `\bSYSDATE\b`                                                           | `CURRENT_TIMESTAMP`                                         |
| 날짜/시간     | TO_CHAR(expr) → CAST(expr AS VARCHAR)           | `TO_CHAR\((.*?)\)`                                                     | `CAST(\1 AS VARCHAR)`                                      |
| 널 처리       | NVL → COALESCE                                   | `NVL\((.*?),\s*(.*?)\)`                                                | `COALESCE(\1, \2)`                                          |
| CASE 처리     | DECODE → CASE WHEN                               | `DECODE\((.*?),\s*(.*?),\s*(.*?)\)`                                    | `CASE WHEN \1 = \2 THEN \3 END`                             |
| 시퀀스        | seq.NEXTVAL → NEXTVAL                            | `(\w+)\.NEXTVAL`                                                       | `NEXTVAL('\1')`                                             |
| 시퀀스        | seq.CURRVAL → CURRVAL                            | `(\w+)\.CURRVAL`                                                       | `CURRVAL('\1')`                                             |
| 계층 쿼리     | CONNECT BY PRIOR → WITH RECURSIVE 변환 필요      | `CONNECT BY PRIOR (\w+) = (\w+)`                                       | `-- Use WITH RECURSIVE to convert CONNECT BY PRIOR`        |



## ⚠️ 수동 변환 가이드 (Manual Conversion Guide)

### 1. EXCEPTION WHEN OTHERS

- **설명**  
  Redshift는 Oracle의 `EXCEPTION WHEN OTHERS` 블록을 지원하지 않습니다. 오류 처리는 애플리케이션 레이어(Python, Java 등)나 ETL 도구에서 처리하거나, 쿼리 구조 자체를 방어적으로 설계해야 합니다.

```sql
-- 예제 Oracle
BEGIN
  -- some logic
  SELECT 1 / 0 INTO dummy FROM dual;
EXCEPTION
  WHEN OTHERS THEN
    INSERT INTO error_log VALUES (SYSDATE, SQLERRM);
END;
```

```sql
-- 예제 Redshift
-- 직접적인 예외 처리는 불가
-- 오류 가능성이 있는 연산은 조건문으로 방지하거나,
-- ETL 도구 또는 애플리케이션에서 TRY / CATCH 처리

-- 예시: 오류를 유발하지 않도록 CASE 사용
SELECT CASE WHEN denominator = 0 THEN NULL ELSE numerator / denominator END AS safe_division
FROM my_table;
```

---

### 2. DECLARE

- **설명**  
  Redshift는 `DECLARE`를 통한 변수 선언을 지원하지 않습니다. 대부분 CTE(Common Table Expression) 또는 SELECT 서브쿼리로 대체할 수 있으며, 복잡한 로직은 외부 로직으로 분리하는 것을 권장합니다.

```sql
-- 예제 Oracle
DECLARE
  v_total NUMBER;
BEGIN
  SELECT COUNT(*) INTO v_total FROM employees;
  DBMS_OUTPUT.PUT_LINE('Total: ' || v_total);
END;
```

```sql
-- 예제 Redshift
-- CTE를 이용한 값 추출
WITH emp_count AS (
  SELECT COUNT(*) AS v_total FROM employees
)
SELECT 'Total: ' || v_total AS output
FROM emp_count;
```

---

### 3. BFILE

- **설명**  
  Redshift는 Oracle의 `BFILE` 타입(외부 바이너리 파일 참조)을 지원하지 않습니다. 대신 S3 URI 또는 외부 스토리지 위치 정보를 문자열로 저장하여 사용합니다.

```sql
-- 예제 Oracle
CREATE TABLE files (
  id NUMBER,
  data BFILE
);
```

```sql
-- 예제 Redshift
CREATE TABLE files (
  id INT,
  file_uri VARCHAR(65535) -- 예: 's3://bucket-name/folder/file.pdf'
);
```

---

### 4. CONNECT BY PRIOR

- **설명**  
  Oracle의 계층 쿼리(트리 탐색)는 `CONNECT BY PRIOR` 구문을 사용하지만, Redshift는 이를 지원하지 않으며 `WITH RECURSIVE`로 대체해야 합니다. Anchor part와 Recursive part 구성, 종료 조건 주의.

```sql
-- 예제 Oracle
SELECT employee_id, manager_id
FROM employees
START WITH manager_id IS NULL
CONNECT BY PRIOR employee_id = manager_id;
```

```sql
-- 예제 Redshift
WITH RECURSIVE employee_hierarchy AS (
  -- Anchor: 최상위 관리자
  SELECT employee_id, manager_id, 1 AS level
  FROM employees
  WHERE manager_id IS NULL

  UNION ALL

  -- Recursive: 하위 직원 탐색
  SELECT e.employee_id, e.manager_id, eh.level + 1
  FROM employees e
  JOIN employee_hierarchy eh ON e.manager_id = eh.employee_id
)
SELECT *
FROM employee_hierarchy;
```
