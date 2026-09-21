# SQL Injection (SQL 삽입)

## 1. 개념

**SQL Injection(SQLi)**은 애플리케이션이 사용자 입력값을 검증 없이 **SQL 쿼리문**에 포함시킬 때 발생하는 취약점이다. 공격자는 입력값에 SQL 구문을 끼워 넣어, 개발자가 의도하지 않은 쿼리를 데이터베이스에서 실행시킬 수 있다.

- **OWASP 분류**: A03:2021 - Injection
- **영향**: 인증 우회, 개인정보/DB 데이터 탈취, 데이터 변조·삭제 등
  (실제 영향 범위는 쿼리가 실행되는 위치와 DB 계정 권한에 따라 달라진다)

## 2. 발생 원리

쿼리를 **문자열로 직접 조립(concatenation)** 할 때 발생한다.

### 취약한 코드 예시 (PHP)

```php
<?php
$id = $_POST['id'];
$pw = $_POST['pw'];
// 입력값을 그대로 쿼리에 연결 → 취약
$query = "SELECT * FROM users WHERE id='$id' AND pw='$pw'";
$result = mysqli_query($conn, $query);
?>
```

정상 요청 (`id=admin`, `pw=1234`):
```sql
SELECT * FROM users WHERE id='admin' AND pw='1234'
```

## 3. 대표 공격 기법

### (1) 인증 우회 (Authentication Bypass)

`id` 입력값에 `' OR '1'='1` 를 넣으면:

```sql
SELECT * FROM users WHERE id='' OR '1'='1' AND pw='...'
```

`'1'='1'` 은 항상 참이므로 조건이 무력화되어 로그인이 우회될 수 있다.
주석(`-- `, `#`)을 이용해 뒷부분을 잘라내는 방식도 흔하다:

```
id: admin'--
→ SELECT * FROM users WHERE id='admin'-- ' AND pw='...'
   (-- 뒤는 주석 처리되어 pw 검사가 사라짐)
```

### (2) UNION 기반 (UNION-based)

`UNION SELECT`를 이용해 원래 쿼리 결과에 공격자가 원하는 SELECT 결과를 이어 붙인다.
이때 원래 쿼리와 **컬럼 개수와 데이터 타입이 맞아야** 하며,
`ORDER BY n` 이나 `UNION SELECT NULL,NULL,...` 로 컬럼 개수를 먼저 찾는다.

```sql
' UNION SELECT username, password FROM users -- 
```

### (3) 에러 기반 (Error-based)

DB 에러 메시지에 데이터가 노출되도록 유도해 정보를 얻는다. (예: `extractvalue()`, `updatexml()`)

### (4) 블라인드 (Blind SQLi)

결과나 에러가 화면에 안 보일 때, 참/거짓 반응이나 응답 시간으로 한 글자씩 추론한다.

- **Boolean-based**: `AND 1=1`(참) vs `AND 1=2`(거짓)의 페이지 차이로 판단
- **Time-based**: `AND SLEEP(5)` 로 응답 지연 여부 확인

```sql
' AND SUBSTR((SELECT password FROM users LIMIT 1),1,1)='a' -- 
```

## 4. 방어 방법 (가장 중요)

1. **Prepared Statement (파라미터 바인딩)** ★ 근본 대책
   ```php
   // 안전: 쿼리 구조와 데이터를 분리
   $stmt = $conn->prepare("SELECT * FROM users WHERE id=? AND pw=?");
   $stmt->bind_param("ss", $id, $pw);
   $stmt->execute();
   ```
   ```python
   # Python 예시
   cursor.execute("SELECT * FROM users WHERE id=%s AND pw=%s", (id, pw))
   ```
   → 입력값이 항상 "데이터"로만 취급되어 SQL 구문으로 해석되지 않는다.

2. **입력값 검증** — 타입/길이/형식 검증 (화이트리스트)
3. **최소 권한 DB 계정** — 웹 애플리케이션 계정에 불필요한 권한(DROP, 파일 접근 등) 부여 금지
4. **에러 메시지 숨기기** — DB 에러를 사용자에게 그대로 노출하지 않음
5. **ORM / 안전한 쿼리 빌더 사용** — 직접 문자열 조립 회피
6. **WAF (웹 방화벽)** — 보조 방어 수단

## 5. 핵심 요약

> SQLi의 근본 원인은 "쿼리 구조와 사용자 데이터가 섞이는 것"이다. **Prepared Statement로 이 둘을 분리**하는 것이 가장 확실한 대책이며, 입력 검증·최소 권한은 이를 보완한다.
