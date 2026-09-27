# XSS (Cross-Site Scripting)

## 1. XSS란?

**XSS(Cross-Site Scripting)**는 웹 애플리케이션에서 사용자가 입력한 데이터가 제대로 검증·처리되지 않아, 공격자가 삽입한 **악성 스크립트가 다른 사용자의 브라우저에서 실행되는 취약점**이다.

주로 JavaScript를 이용하여 쿠키 탈취, 세션 탈취, 피싱 페이지 삽입 등의 공격을 수행할 수 있다.

> XSS의 핵심은 **신뢰할 수 없는 입력값이 웹 페이지에 포함되어 브라우저에서 코드로 실행되는 것**이다.

---

## 2. XSS 발생 원리

웹 애플리케이션이 사용자의 입력값을 그대로 HTML에 출력하는 경우 XSS가 발생할 수 있다.

```text
사용자 입력
    ↓
웹 서버로 전달
    ↓
입력값 검증/필터링 부족
    ↓
HTML 응답에 입력값 포함
    ↓
사용자의 브라우저에서 JavaScript 실행
```

예를 들어 게시판의 댓글 기능에서 사용자가 입력한 내용을 그대로 출력한다고 가정한다.

```html
<input type="text" name="comment" />
```

공격자가 다음과 같은 스크립트를 입력한다.

```html
<script>
  alert("XSS");
</script>
```

서버가 이 값을 그대로 HTML에 출력하면 브라우저는 해당 내용을 단순한 문자열이 아니라 **HTML/JavaScript 코드로 해석**하여 실행할 수 있다.

---

## 3. XSS의 종류

| 종류          | 설명                                                                                |
| ------------- | ----------------------------------------------------------------------------------- |
| Stored XSS    | 악성 스크립트가 서버에 저장된 후 다른 사용자가 해당 페이지를 방문할 때 실행         |
| Reflected XSS | 요청에 포함된 악성 스크립트가 서버에 저장되지 않고 응답에 그대로 포함되어 실행      |
| DOM-based XSS | 서버의 응답과 관계없이 클라이언트 측 JavaScript가 DOM을 안전하지 않게 조작하여 발생 |

---

## 4. Stored XSS

**Stored XSS(저장형 XSS)**는 공격자가 입력한 악성 스크립트가 데이터베이스 등에 저장되고, 해당 데이터를 조회하는 사용자의 브라우저에서 실행되는 방식이다.

대표적인 예시는 게시판의 댓글이다.

```text
공격자
  ↓
악성 스크립트가 포함된 댓글 작성
  ↓
서버/DB에 저장
  ↓
다른 사용자가 게시글 조회
  ↓
저장된 스크립트가 응답에 포함
  ↓
브라우저에서 실행
```

예시:

```html
<script>
  alert(document.domain);
</script>
```

관리자가 게시판을 확인하는 순간 해당 스크립트가 실행될 수 있다.

---

## 5. Reflected XSS

**Reflected XSS(반사형 XSS)**는 공격자가 HTTP 요청에 악성 스크립트를 포함시키고, 서버가 해당 입력값을 검증하지 않은 채 응답에 다시 포함하면서 발생한다.

예를 들어 검색 기능이 다음과 같다고 가정한다.

```text
/search?q=hello
```

서버가 검색어를 그대로 페이지에 출력한다면 공격자가 악성 스크립트가 포함된 요청을 만들어 피해자에게 전달할 수 있다.

```text
사용자 입력
    ↓
HTTP 요청에 악성 스크립트 포함
    ↓
서버가 입력값을 그대로 응답에 포함
    ↓
브라우저에서 스크립트 실행
```

Stored XSS와 달리 악성 코드가 서버에 저장되지 않는다는 차이가 있다.

---

## 6. DOM-based XSS

**DOM-based XSS**는 클라이언트 측 JavaScript가 사용자 입력을 안전하지 않게 DOM에 삽입하면서 발생한다.

예를 들어 다음과 같은 코드가 있다고 가정한다.

```javascript
const value = location.hash.substring(1);

document.getElementById("result").innerHTML = value;
```

URL의 `hash` 값을 가져온 뒤 `innerHTML`을 이용해 그대로 삽입하고 있다.

사용자 입력이 HTML로 해석될 수 있기 때문에 XSS가 발생할 수 있다.

### 주요 원인

```javascript
innerHTML;
outerHTML;
document.write();
```

와 같이 사용자 입력을 HTML로 해석할 수 있는 API를 안전하지 않게 사용하는 경우 발생할 수 있다.

---

## 7. XSS 공격으로 발생할 수 있는 문제

XSS가 발생하면 공격자는 피해자의 브라우저에서 JavaScript를 실행할 수 있다.

대표적인 영향은 다음과 같다.

- 사용자 정보 탈취
- 세션 정보 탈취 시도
- 사용자를 악성 사이트로 이동
- 피싱 페이지 삽입
- 웹 페이지 내용 변조
- 사용자 대신 특정 동작 수행
- 관리자 계정 공격으로 이어질 가능성

단, **HttpOnly 쿠키는 JavaScript의 `document.cookie`를 통한 직접적인 접근이 제한**되므로 XSS가 발생했다고 해서 항상 쿠키를 직접 탈취할 수 있는 것은 아니다.

---

## 8. XSS 방어 방법

### ① 출력값 인코딩

사용자 입력을 HTML로 해석하지 않고 일반 문자열로 출력한다.

```html
<!-- 위험할 수 있는 방식 -->
<div id="result"></div>

<script>
  result.innerHTML = userInput;
</script>
```

가능하다면 HTML을 해석하지 않는 방식으로 출력한다.

```javascript
result.textContent = userInput;
```

---

### ② 입력값 검증

사용자가 입력할 수 있는 값의 형식과 범위를 제한한다.

예:

```text
이름 → 문자만 허용
나이 → 숫자만 허용
전화번호 → 지정된 형식만 허용
```

다만 **입력값 필터링만으로 XSS를 완전히 방어하는 것은 어렵기 때문에 출력 시점의 적절한 인코딩이 중요하다.**

---

### ③ CSP(Content Security Policy)

CSP를 사용하여 브라우저에서 실행할 수 있는 스크립트의 출처를 제한한다.

예:

```http
Content-Security-Policy: default-src 'self'
```

CSP는 XSS 취약점이 존재하더라도 악성 스크립트 실행 가능성을 줄이는 **추가적인 방어 계층**으로 사용할 수 있다.

---

### ④ HttpOnly 쿠키 사용

세션 쿠키 등에 `HttpOnly` 속성을 설정하면 JavaScript에서 해당 쿠키에 직접 접근하는 것을 제한할 수 있다.

```http
Set-Cookie: session=abc123; HttpOnly; Secure
```

---

## 9. XSS 핵심 정리

```text
XSS
→ 신뢰할 수 없는 입력이 웹 페이지에서 코드로 실행되는 취약점

Stored XSS
→ 악성 스크립트가 서버에 저장
→ 사용자가 페이지를 조회할 때 실행

Reflected XSS
→ 악성 입력이 요청에 포함
→ 서버 응답에 반사되어 실행

DOM-based XSS
→ 클라이언트 JavaScript가 DOM을 안전하지 않게 조작
→ 브라우저에서 실행

주요 방어
→ 출력 인코딩
→ 입력값 검증
→ 안전한 DOM API 사용
→ CSP
→ HttpOnly/Secure 쿠키
```
