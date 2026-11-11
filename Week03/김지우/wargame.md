# Wargame | CSRF-1

## 1. 문제 정보

- **분류**: Web
- **취약점**: Cross-Site Request Forgery (CSRF)
- **목표**: 관리자 기능을 호출하여 `memo`에 저장된 FLAG 확인

---

## 2. 문제 분석

문제에서 제공된 `app.py`를 확인하였다.

코드를 전체적으로 살펴보면서 다음 함수와 라우트를 중심으로 분석하였다.

- `check_csrf()`
- `/vuln`
- `/flag`
- `/admin/notice_flag`
- `/memo`

처음에는 `/flag`에서 입력한 값이 실제로 어떻게 처리되는지 확인하는 것이 중요하다고 생각했다.

코드의 흐름을 따라가 보면 다음과 같다.

```text
/flag
  ↓
check_csrf()
  ↓
Selenium 브라우저가 /vuln 접속
  ↓
입력값이 HTML로 반환
  ↓
브라우저가 HTML을 해석하며 추가 요청 발생
  ↓
/admin/notice_flag 호출
  ↓
FLAG가 memo_text에 저장
  ↓
/memo에서 FLAG 확인
```

---

## 3. 코드 분석

### 3.1 `check_csrf()`

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/973c21a5-5d2b-488e-8d8a-4b9b435dc1e8" />

사용자가 입력한 `param`을 `/vuln`의 Query String으로 만들어 `read_url()`에 전달한다.

`read_url()`에서는 Selenium을 이용해 Chrome 브라우저를 실행하고 해당 URL에 접속한다.

즉, 단순히 서버에서 입력값을 확인하는 것이 아니라 사용자가 입력한 값이 실제 브라우저에서 렌더링되는 구조이다.

따라서 `/vuln`에서 입력값이 어떻게 처리되는지를 확인할 필요가 있었다.

---

### 3.2 `/vuln`

<img width="800"  alt="Image" src="https://github.com/user-attachments/assets/e80a575f-1673-4148-8672-0290434282f4" />

먼저 URL의 `param` 값을 가져온 후 `frame`, `script`, `on` 문자열을 `*`로 치환한다.

```python
xss_filter = ["frame", "script", "on"]
```

처음에는 XSS 필터가 있기 때문에 JavaScript를 실행하는 방식으로 접근해야 하는지 생각했지만, 모든 HTML 태그를 차단하는 것은 아니었다.

특히 마지막에 입력값을 그대로 반환하고 있기 때문에 HTML 태그를 포함한 값을 전달할 수 있다.

따라서 반드시 JavaScript를 실행하지 않더라도 브라우저가 자동으로 요청을 발생시키는 HTML 태그를 사용할 수 있는지 확인해보았다.

---

### 3.3 `/flag`

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/a958f6e5-c815-4d4d-84f0-ede15a8e7f1b" />

`/flag`에 POST 요청을 보내면 입력한 `param`을 가져온다.

```python
param = request.form.get("param", "")
```

이후 해당 값을 `check_csrf()`에 전달한다. 전달된 값은 Selenium 브라우저에서 `/vuln`에 접속할 때 사용된다.

따라서 `/flag`의 입력창에 브라우저에서 해석될 수 있는 HTML을 넣는 것이 이번 워게임 payload 작성의 핵심이라 생각했다. 

---

### 3.4 `/admin/notice_flag`

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/65544da1-dcde-4d75-96b7-668ddf5aeadd" />

이 부분이 실제로 FLAG를 `memo_text`에 저장하는 관리자 기능이다.

먼저 요청의 출발지가 `127.0.0.1`인지 확인한다. 
```python
if request.remote_addr != "127.0.0.1":
```

이후 userid가 admin인지 확인한다. 
```python
if request.args.get("userid", "") != "admin":
```

두 조건을 만족하면 다음 코드가 실행된다.

```python
memo_text += f"[Notice] flag is {FLAG}\n"
```

처음에는 단순히 /admin/notice_flag에 접근하면 되는 것처럼 보였지만, 외부에서 직접 접근하면 127.0.0.1 조건 때문에 막히게 된다. 이에  Selenium 브라우저가 로컬 서버에 접속하는 과정에서 해당 URL로 요청을 보내도록 만들어야 한다고 생각하였다.

---

## 4. 취약점 확인

앞에서 확인한 내용을 정리하면 다음과 같다.

1. /flag에서 입력한 값이 check_csrf()로 전달됨.
2. check_csrf()는 Selenium 브라우저를 이용해 /vuln을 방문함.
3. /vuln은 입력값을 HTML로 그대로 반환함.
4. payload에 HTML 태그를 넣으면 Selenium 브라우저에서 해당 태그가 렌더링됨.
5. HTML 태그 중 외부 리소스를 요청하는 태그를 이용하면 별도의 GET 요청을 발생시킬 수 있음.

위 사항을 참고해 payload를 작성하였다. payload 구성은 `<img>` 태그를 사용하였다.

처음에는 CSRF라고 해서 JavaScript를 실행해야 하는지 생각했지만, `/vuln`에서 `script`와 `on`이 필터링되고 있었다.

```python
xss_filter = ["frame", "script", "on"]
```

CSRF의 핵심은 반드시 JavaScript를 실행하는 것이 아니라 사용자의 브라우저를 이용해 원하는 요청을 발생시키는 것이기에, JavaScript를 사용하지 않고도 브라우저가 자동으로 요청을 보내는 html 태그를 이용하고자 하였다. 

```html
<img src="/admin/notice_flag?userid=admin">
```

`<img>` 태그는 브라우저가 페이지를 로드할 때 `src`에 지정된 URL로 GET 요청을 자동으로 보낸다. 브라우저가 위 HTML을 렌더링하면 다음과 같은 요청이 발생한다.

```text
GET /admin/notice_flag?userid=admin
```

이 요청에는 `userid=admin`이 포함되어 있기 때문에 `/admin/notice_flag`의 두 번째 조건을 만족한다.

또한 Selenium 브라우저가 문제 서버의 로컬 환경에서 실행되므로 127.0.0.1 조건도 만족할 수 있다.

---

## 5. 풀이

`/flag`의 `param` 입력창에 다음 값을 입력하였다.

```html
<img src="/admin/notice_flag?userid=admin">
```

이후 쿼리 전송을 클릭하였다.

정상적으로 요청이 발생하여 `good` 메시지가 출력된다.

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/c3725c32-9e45-43d2-9bf2-8b6203239a16" />

이후 `/memo`에 접속하면 다음과 같이 FLAG가 저장된 것을 확인할 수 있다.

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/45506331-6605-4140-9a4b-9c8edc47428f" />

---

## 6. 정리 및 고찰

이번 문제에서는 /vuln에서 사용자 입력값을 HTML로 반환하고, 해당 값을 Selenium 브라우저에서 렌더링한다는 점을 이용하였다.

코드를 처음 확인했을 때 script, on 등이 필터링되고 있어서 JavaScript를 사용하는 XSS 방식은 어렵다고 생각했다.

하지만 CSRF는 반드시 JavaScript를 실행해야 하는 것이 아니기 때문에, 브라우저가 자동으로 요청을 발생시키는 <img> 태그를 이용하였다.

```HTML
<img src="/admin/notice_flag?userid=admin">
```

해당 payload가 Selenium 브라우저에서 렌더링되면서 /admin/notice_flag?userid=admin으로 GET 요청이 발생하고, 관리자 기능이 실행되어 FLAG가 memo_text에 저장된다.

최종적으로 /memo에서 저장된 FLAG를 확인할 수 있었다.
