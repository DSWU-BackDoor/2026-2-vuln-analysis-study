# SQL Injection

## 1. 데이터베이스와 DBMS의 기본 개념

### 데이터베이스(Database)

데이터를 체계적으로 저장하고 관리하기 위한 시스템이다.

웹 애플리케이션에서는 사용자 정보, 게시글, 상품 정보, 로그인 정보 등 다양한 데이터를 데이터베이스에 저장한다.

### DBMS(Database Management System)

데이터베이스를 생성하고, 데이터를 저장·조회·수정·삭제할 수 있도록 관리하는 소프트웨어이다.

대표적인 관계형 DBMS(RDBMS)는 다음과 같다.

- MySQL
- MariaDB
- PostgreSQL
- Oracle
- Microsoft SQL Server
- SQLite

---

## 2. SQL과 SQL Injection 공격 기법

### SQL이란?

SQL(Structured Query Language)은 관계형 데이터베이스의 데이터를 관리하기 위해 사용하는 언어이다.

SQL은 크게 다음과 같이 구분할 수 있다.

| 구분 | 설명                    | 예시                                   |
| ---- | ----------------------- | -------------------------------------- |
| DML  | 데이터를 조작           | `SELECT`, `INSERT`, `UPDATE`, `DELETE` |
| DDL  | 데이터 구조를 정의      | `CREATE`                               |
| DCL  | 데이터 접근 권한을 제어 | `GRANT`, `REVOKE`                      |

### 기본 SQL

#### 데이터 조회

```sql
SELECT * FROM member;
```

#### 특정 데이터 조회

```sql
SELECT * FROM member
WHERE user_id = 'anesra';
```

#### 데이터 수정

```sql
UPDATE member
SET user_pw = 'new_password'
WHERE user_id = 'anesra';
```

#### 데이터 삭제

```sql
DELETE FROM member
WHERE user_id = 'wasabimilk';
```

### SQL Injection이란?

SQL Injection(SQLi)은 **웹 애플리케이션과 데이터베이스가 연동되는 과정에서 공격자가 입력값을 통해 SQL 쿼리를 조작하는 공격 기법**이다.

주로 다음과 같은 입력 지점에서 발생할 수 있다.

- 로그인
- 게시물 검색
- 우편번호 검색
- 자료실

SQL Injection이 발생하면 원래 접근할 수 없었던 데이터를 조회하거나, 데이터를 수정·삭제하는 등의 피해가 발생할 수 있다.

### SQL Injection의 기본 원리

```text
사용자 입력
    ↓
웹 애플리케이션
    ↓
SQL 쿼리 생성
    ↓
데이터베이스
```

사용자 입력값이 SQL 구문의 일부로 처리되면 공격자가 의도하지 않은 SQL 명령이 실행될 수 있다.

### SQL Injection의 유형

#### In-band SQL Injection

공격과 결과 확인이 동일한 통신 채널에서 이루어지는 방식이다.

대표적으로 다음과 같은 방식이 있다.

- Error-based SQL Injection
- UNION-based SQL Injection

#### Error-based SQL Injection

데이터베이스에서 발생하는 오류 메시지를 이용하여 데이터베이스 구조 등의 정보를 알아내는 방식이다.

#### UNION-based SQL Injection

UNION 연산자를 이용하여 여러 SELECT 문의 결과를 결합하고 이를 HTTP 응답을 통해 확인하는 방식이다.

예를 들어 다음과 같이 사용할 수 있다.

```sql
SELECT user_id, user_pw FROM member
UNION
SELECT id, pw FROM admin;
```

PDF에서는 `member` 테이블과 `admin` 테이블의 데이터를 UNION으로 결합하는 실습을 진행한다.

#### Blind SQL Injection

웹 애플리케이션을 통해 데이터가 직접 반환되지 않더라도 애플리케이션의 응답이나 데이터베이스의 동작을 관찰하여 정보를 추론하는 방식이다.

#### Out-of-band SQL Injection

기존 통신 채널이 아닌 별도의 통신 채널을 이용하는 방식이다.

시간 기반 추론 공격이 적합하지 않은 환경에서 대안으로 사용될 수 있으며, 데이터베이스의 특정 기능 활성화 여부 등에 따라 가능 여부가 달라진다.

---
