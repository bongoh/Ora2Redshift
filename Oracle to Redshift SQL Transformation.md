# Oracle to Redshift SQL Transformation Examples

이 문서는 Oracle SQL 구문을 Amazon Redshift에 맞게 변환하는 예제를 제공합니다.  
각 예제에는 **As-Is**(원본) 쿼리와 **To-Be**(변환 후) 쿼리를 포함하며, 사용 용도, 변환 시 주의할 점, 스크립트 자동화 가능 여부를 명시합니다.

---

## 목차
1. [선언/제어문](#1-선언제어문)  
2. [데이터 타입 변환](#2-데이터-타입-변환)  
3. [날짜/시간 함수 변환](#3-날짜시간-함수-변환)  
4. [수학 함수 변환](#4-수학-함수-변환)  
5. [문자열 함수 변환](#5-문자열-함수-변환)  
6. [널 처리 및 CASE](#6-널-처리-및-case)  
7. [시퀀스](#7-시퀀스)  
8. [예외 처리](#8-예외-처리)  
9. [계층 쿼리](#9-계층-쿼리)  
10. [기타 변환](#10-기타-변환)

---

## 1. 선언/제어문

> PL/SQL 익명 블록을 Redshift의 PL/pgSQL로 변환할 때 사용합니다.

| Category     | 용도                | As-Is (Oracle)                                     | To-Be (Redshift)                                                                                                                                      | 스크립트 | 주의                              |
|--------------|---------------------|----------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|----------|-----------------------------------|
| DECLARE      | 변수 선언 및 초기화 | ```sql<br>DECLARE my_var NUMBER;<br>BEGIN<br>  my_var := 1;<br>END;``` | ```sql<br>DO $$<br>DECLARE my_var INTEGER;<br>BEGIN<br>  my_var := 1;<br>END;<br>$$ LANGUAGE plpgsql;```                                                | 불가능   | 데이터 타입 매핑 수동 검토 필요    |
| BEGIN/END    | 익명 블록 시작/종료 | ```sql<br>BEGIN<br>  NULL;<br>END;```              | ```sql<br>BEGIN;<br>  -- SQL 문<br>END;```                                                                                                             | 불필요   | 구문 차이 없음                     |

---

## 2. 데이터 타입 변환

> Oracle과 Redshift의 데이터 타입 차이를 보완하기 위한 변환입니다.

| Category       | 용도                        | As-Is (Oracle)      | To-Be (Redshift)     | 스크립트 | 주의                       |
|----------------|-----------------------------|---------------------|----------------------|----------|----------------------------|
| NUMBER(n,m)    | 소수점 포함 숫자 (금액, 비율) | `col NUMBER(10,2)`  | `col DECIMAL(10,2)`  | 가능     | 정밀도 최대 38자리 확인    |
| NUMBER(10,0)   | 10자리 정수 (큰 식별자)       | `col NUMBER(10,0)`  | `col BIGINT`         | 가능     | ±9.22e18 범위 확인         |
| NUMBER(1,0)    | 1자리 정수 (플래그)           | `col NUMBER(1,0)`   | `col SMALLINT`       | 가능     | 없음                       |
| VARCHAR2(n)    | 가변 길이 문자열 (이름, 설명) | `col VARCHAR2(100)` | `col VARCHAR(100)`   | 가능     | 최대 65535자 확인          |
| CLOB           | 대용량 문자 (문서, 로그)      | `col CLOB`          | `col VARCHAR(MAX)`   | 부분 가능| 성능·크기 제한 검토        |

---

## 3. 날짜/시간 함수 변환

> 날짜/시간 함수는 포맷 차이와 타임존 기본값 처리에 유의하세요.

| Category             | 용도                        | As-Is (Oracle)                                    | To-Be (Redshift)                                        | 스크립트 | 주의                      |
|----------------------|-----------------------------|---------------------------------------------------|---------------------------------------------------------|----------|---------------------------|
| TO_DATE (표준)       | 문자열→날짜 (YYYY‑MM‑DD)     | `TO_DATE('2025-04-13','YYYY-MM-DD')`               | `CAST('2025-04-13' AS TIMESTAMP)`                        | 가능     | 형식 일치 확인            |
| TO_DATE (커스텀)     | 다양한 입력 포맷 처리       | `TO_DATE('13/04/2025','DD/MM/YYYY')`               | `TO_TIMESTAMP('13/04/2025','DD/MM/YYYY')`                | 불가능   | 수동 포맷 지정 필요       |
| SYSDATE              | 시스템 현재 시간            | `SYSDATE`                                         | `CURRENT_TIMESTAMP`                                     | 가능     | 타임존 설정 확인          |
| TRUNC(day)           | 일별 집계용 절삭            | `TRUNC(SYSDATE)`                                   | `DATE_TRUNC('day', CURRENT_TIMESTAMP)`                   | 가능     | 시간 정보 제거됨          |
| TRUNC(month)         | 월별 집계용 절삭            | `TRUNC(SYSDATE,'MM')`                              | `DATE_TRUNC('month', CURRENT_TIMESTAMP)`                 | 가능     | 월 첫날 00:00 설정 확인   |

---

## 4. 수학 함수 변환

> 기본 함수는 동일, 비표준 함수는 수식으로 대체하세요.

| Category    | 용도                   | As-Is (Oracle)      | To-Be (Redshift)          | 스크립트 | 주의               |
|-------------|------------------------|---------------------|---------------------------|----------|--------------------|
| ABS         | 절댓값                 | `ABS(x)`            | `ABS(x)`                  | 불필요   | 없음               |
| CEIL        | 올림                   | `CEIL(x)`           | `CEIL(x)`                 | 불필요   | 없음               |
| BITAND      | 비트 AND (플래그)      | `BITAND(n,m)`       | `n & m`                   | 가능     | 연산자 우선순위    |
| REMAINDER   | 나머지                 | `REMAINDER(n1,n2)`  | `n1 - n2 * ROUND(n1/n2)`  | 가능     | 음수 결과 주의     |

---

## 5. 문자열 함수 변환

> 함수명 및 파라미터 순서 차이에 유의하세요.

| Category  | 용도                   | As-Is (Oracle)       | To-Be (Redshift)                       | 스크립트 | 주의                   |
|-----------|------------------------|----------------------|----------------------------------------|----------|------------------------|
| NVL       | 널 대체 (기본값)       | `NVL(a,b)`           | `COALESCE(a,b)`                        | 가능     | 다중 인자 지원         |
| CONCAT    | 문자열 결합            | `CONCAT(a,b)`        | `CONCAT(a,b)`                          | 불필요   | NULL 처리 차이         |
| SUBSTR    | 부분 문자열 추출      | `SUBSTR(s,pos,len)`  | `SUBSTRING(s FROM pos FOR len)`        | 가능     | 인덱스 시작 1-based    |

---

## 6. 널 처리 및 CASE

> DECODE는 CASE WHEN으로 변환하세요.

| Category | 용도            | As-Is (Oracle)                                         | To-Be (Redshift)                                                                 | 스크립트 | 주의               |
|----------|-----------------|--------------------------------------------------------|----------------------------------------------------------------------------------|----------|--------------------|
| DECODE   | 조건 분기       | `DECODE(status,'A','Active','I','Inactive')`           | `CASE WHEN status='A' THEN 'Active' WHEN status='I' THEN 'Inactive' ELSE 'Unknown' END` | 불가능   | ELSE 절 추가       |

---

## 7. 시퀀스

> Redshift 표준 NEXTVAL/CURRVAL 함수 사용.

| Category | 용도            | As-Is (Oracle)  | To-Be (Redshift)   | 스크립트 | 주의              |
|----------|-----------------|-----------------|--------------------|----------|-------------------|
| NEXTVAL  | 다음 시퀀스 값  | `seq.NEXTVAL`   | `NEXTVAL('seq')`   | 가능     | 시퀀스 존재 여부  |
| CURRVAL  | 현재 시퀀스 값  | `seq.CURRVAL`   | `CURRVAL('seq')`   | 가능     | NEXTVAL 선행     |

---

## 8. 예외 처리

> PL/pgSQL 예외 처리 구조로 변환해야 합니다.

| Category  | 용도           | As-Is (Oracle)                | To-Be (Redshift)                                    | 스크립트 | 주의               |
|-----------|----------------|-------------------------------|-----------------------------------------------------|----------|--------------------|
| EXCEPTION | 예외 처리 블록 | `EXCEPTION WHEN OTHERS THEN …` | `EXCEPTION WHEN OTHERS THEN RAISE NOTICE '…';`      | 불가능   | RAISE NOTICE 사용  |

---

## 9. 계층 쿼리

> CONNECT BY는 재귀 CTE로 변환하세요.

| Category    | 용도            | As-Is (Oracle)                   | To-Be (Redshift)                              | 스크립트 | 주의               |
|-------------|-----------------|----------------------------------|-----------------------------------------------|----------|--------------------|
| CONNECT BY  | 계층 구조 조회  | `CONNECT BY PRIOR id=parent_id`   | ```sql<br>WITH RECURSIVE cte AS (... )<br>SELECT * FROM cte;``` | 불가능   | 재귀 깊이 제한     |

---

## 10. 기타 변환

> DDL 힌트 및 옵션은 제거하거나 주석 처리하세요.

| Category           | 용도                 | As-Is (Oracle)                  | To-Be (Redshift)               | 스크립트 | 주의                       |
|--------------------|----------------------|---------------------------------|--------------------------------|----------|----------------------------|
| Hint 제거          | 실행 계획 힌트       | `/*+ INDEX(emp emp_idx) */`     | `-- 제거`                      | 가능     | 없음                       |
| 스토리지 옵션      | TABLESPACE/ STORAGE  | `STORAGE(...)`                  | `-- 제거`                      | 가능     | DDL 검토                   |
| PCTFREE 등 제거    | 테이블 옵션          | `PCTFREE ... INITRANS ...`      | `-- 제거`                      | 가능     | 없음                       |
| PRAGMA/AUTONOMOUS   | 트랜잭션 옵션        | `PRAGMA AUTONOMOUS_TRANSACTION` | `-- 제거`                      | 불가능   | 수동 로직 재작성 필요      |