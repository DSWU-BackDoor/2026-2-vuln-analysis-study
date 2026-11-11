# Wargame | SSRF

## 1. 문제 정보

- **분류**: Web
- **취약점**: Server-Side Request Forgery (SSRF)
- **목표**: 내부 서버에 접근하여 `flag.txt`에 저장된 FLAG 확인
- https://dreamhack.io/wargame/challenges/75

---

문제 파일을 다운로드한 후, 파일 구성을 확인했다.
<img width="400" alt="Image" src="https://github.com/user-attachments/assets/a2bff84e-9cee-4c2a-a247-eeb8b0522d42" />
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/8b4df917-d19b-4002-b01f-68d1a192f8b2" />

VM 머신을 통해 접속하면 이미지 URL을 입력할 수 있는 페이지가 나타난다.  
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/4e7a74ec-8baf-418a-ba0a-9c2521872008" />

바로 아래 'View' 버튼을 누를 경우 기본 이미지가 표시된다.
<img width="800" height="1050" alt="Image" src="https://github.com/user-attachments/assets/c932292b-af44-48a8-b59a-e35d9edc49e0" />

url 창에 다음 주소를 입력했을 때는 다른 이미지가 표시된다. 

```text
http://localhost:8000/static/dream.png
```
<img width="800" height="1054" alt="Image" src="https://github.com/user-attachments/assets/3e2cc50f-5336-46b2-b46b-55f5312f601c" />

이를 통해 사용자가 입력한 URL을 서버가 요청하고, 응답 데이터를 이미지 뷰어에 표시하는 구조임을 확인하였다. 

## 2. 문제 분석

문제에서 제공된 `app.py`와 `Dockerfile`을 확인하였다.
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/718c9c39-1344-417b-8000-ec7049d59d5c" />
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/7d4475e5-45f7-4a45-a1de-e2bc96f113ae" />
코드를 전체적으로 살펴보면서 다음 부분을 중심으로 분석하였다.

분석 과정에서 다음 사항을 확인하고자 하였다.

- 사용자가 입력한 URL이 서버에서 어떻게 처리되는가?
- 내부 주소를 차단하는 필터가 존재하는가?
- 내부 HTTP 서버는 어떤 주소와 포트에서 실행되는가?
- 내부 서버를 통해 `flag.txt`에 접근할 수 있는가?

코드 분석 결과, 사용자가 입력한 URL로 서버가 직접 요청을 보내는 구조를 확인하였다. 따라서 URL 필터를 우회해 내부 서버에 접근할 수 있는지 확인하는 방향으로 풀이를 진행하였다.

---

## 3. 코드 분석

### 3.1 `/img_viewer`와 URL 필터링

먼저 Ubuntu 환경에서 이미지 뷰어의 HTML 템플릿인 'img_viewer.html'을 확인하였다. 

```bash
cat ~/261004ex/deploy/templates/img_viewer.html
```

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/8fc90cd1-cc9f-4670-b8c8-74d619ade95d" />

이후 'app.py'에서 사용자가 입력한 URL을 처리하는 부분을 확인하였다. 

```python
@app.route("/img_viewer", methods=["GET", "POST"])
def img_viewer():
    if request.method == "GET":
        return render_template("img_viewer.html")
    elif request.method == "POST":
        url = request.form.get("url", "")
        urlp = urlparse(url)

        if url[0] == "/":
            url = "http://localhost:8000" + url
        elif ("localhost" in urlp.netloc) or ("127.0.0.1" in urlp.netloc):
            data = open("error.png", "rb").read()
            img = base64.b64encode(data).decode("utf8")
            return render_template("img_viewer.html", img=img)
```

각 코드의 역할은 다음과 같다.

- `@app.route("/img_viewer", methods=["GET", "POST"])`: `/img_viewer` 경로에서 GET과 POST 요청을 처리한다.
- `request.form.get("url", "")`: 사용자가 입력한 URL을 가져온다.
- `urlparse(url)`: URL을 구성 요소별로 나눈다.
- `urlp.netloc`: URL의 호스트와 포트 부분을 확인한다.

이후 입력값이 `/`로 시작하는지 확인한다. 예를 들어 `/static/dream.png`를 입력하면 `http://localhost:8000`을 앞에 붙여 전체 URL로 만든다.

그렇지 않으면 URL의 호스트 부분에 `localhost` 또는 `127.0.0.1`이라는 문자열이 포함되어 있는지 검사한다. 해당 문자열이 포함되어 있으면 요청을 차단하고 `error.png`를 반환한다.

처음에는 내부 주소를 차단하는 조건 때문에 접근하기 어려울 것이라고 생각하였다. 하지만 코드를 자세히 살펴보니 실제 IP 주소가 가리키는 대상을 확인하는 것이 아니라, 특정 문자열이 포함되어 있는지만 검사하고 있었다.

따라서 필터에서 검사하는 문자열과 다른 형태로 루프백 주소를 표현하면 우회할 수 있을 것이라고 판단하였다.

### 3.2 서버 요청 및 응답 처리

다음으로 실제 URL 요청과 응답을 처리하는 부분을 확인하였다.

```python
try:
    data = requests.get(url, timeout=3).content
    img = base64.b64encode(data).decode("utf8")
except:
    data = open("error.png", "rb").read()
    img = base64.b64encode(data).decode("utf8")

return render_template("img_viewer.html", img=img)
```

핵심은 다음 코드이다.

```python
data = requests.get(url, timeout=3).content
```

`requests.get()`은 지정한 URL로 HTTP GET 요청을 보내고, `.content`는 응답 데이터를 가져온다.

즉, 사용자가 입력한 주소에 웹 서버가 직접 접근한다. 이때 사용자가 내부 서버의 주소를 입력하면 서버가 대신 내부 자원에 접근하게 될 수 있다. 이러한 동작을 악용하는 취약점이 SSRF(Server-Side Request Forgery, 서버 측 요청 위조) 이다.

요청에 성공하면 응답 데이터를 Base64로 인코딩한다.

```python
img = base64.b64encode(data).decode("utf8")
```

Base64는 데이터를 문자열 형태로 표현하는 인코딩 방식이다. 이 문제에서는 응답 데이터를 이미지 뷰어의 HTML에 전달하기 위해 사용한다.

따라서 요청한 파일이 일반 텍스트라면 브라우저에서 정상적인 이미지로 표시되지 않을 수 있다. 화면에 깨진 이미지가 나타나더라도 요청이 실패했다고 단정할 수는 없다.

### 3.3 내부 HTTP 서버와 포트 확인

`app.py`의 아래쪽에서는 별도의 내부 HTTP 서버를 실행한다.

```python
local_host = "127.0.0.1"
local_port = random.randint(1500, 1800)

local_server = http.server.HTTPServer(
    (local_host, local_port),
    http.server.SimpleHTTPRequestHandler
)

threading._start_new_thread(run_local_server, ())
```

각 코드의 의미는 다음과 같다.

- `local_host = "127.0.0.1"`: 내부 서버가 실행될 루프백 주소를 지정한다.
- `random.randint(1500, 1800)`: 1500부터 1800 사이에서 포트 번호를 무작위로 선택한다.
- `HTTPServer(...)`: 지정한 주소와 포트에서 HTTP 서버를 생성한다.
- `SimpleHTTPRequestHandler`: 현재 작업 디렉터리의 파일을 HTTP 요청으로 제공한다.

여기서 중요한 점은 '내부 서버의 포트 번호가 고정되어 있지 않다'는 것이다. 따라서 포트를 모르는 상태에서는 특정 포트 하나만 요청하는 것으로 파일에 접근하기 어려울 수 있다.

또한 `Dockerfile`을 확인하였다.

<img width="800" alt="Dockerfile 확인" src="https://github.com/user-attachments/assets/7d4475e5-45f7-4a45-a1de-e2bc96f113ae" />

```dockerfile
ADD ./deploy /app
WORKDIR /app
```

`deploy` 디렉터리의 파일을 `/app`에 복사하고, 작업 디렉터리를 `/app`으로 설정하는 코드이다. 제공된 파일 구성에서 `flag.txt`가 이 디렉터리에 있으므로, 내부 HTTP 서버를 통해 해당 파일에 접근할 수 있는지 확인하기로 하였다.

---

## 4. 취약점 확인

앞에서 확인한 내용을 정리하면 다음과 같다.

1. 사용자가 입력한 URL로 서버가 직접 요청을 보낸다.
2. 내부 주소 필터는 `localhost`와 `127.0.0.1`이라는 문자열을 검사한다.
3. 내부 HTTP 서버의 포트는 1500~1800 사이에서 무작위로 결정된다.
4. 내부 서버는 작업 디렉터리의 파일을 제공할 수 있다.
5. 응답 데이터는 Base64로 인코딩되어 HTML에 포함된다.

따라서 문자열 필터를 우회할 주소를 사용하고, 내부 서버의 포트를 찾은 다음, 응답 데이터를 확인하는 방향으로 풀이를 진행하였다.

### 4.1 `127.1`을 이용한 필터 우회

`127.1`은 `127.0.0.1`을 나타내는 축약된 루프백 주소 표현으로 사용할 수 있다.

기존 필터는 호스트 부분에 `localhost` 또는 `127.0.0.1`이라는 문자열이 포함되어 있는지만 검사한다. 따라서 `127.1`을 사용하면 해당 문자열 검사에 걸리지 않는다.

요청에 사용할 URL 형식은 다음과 같다.

```text
http://127.1:포트/flag.txt
```

- `127.1`: 필터 검사를 우회하기 위해 사용한 루프백 주소 표현
- `포트`: 내부 HTTP 서버가 실행 중인 포트 번호
- `/flag.txt`: 확인하려는 파일 경로


### 4.2 포트 탐색

내부 서버는 1500~1800 사이에서 무작위로 포트를 선택한다. 따라서 처음부터 실제 포트를 알 수 없었다.

먼저 포트 `1500`을 지정하여 요청해 보고, 원하는 응답이 반환되는지 확인하기로 하였다. 해당 요청에서 FLAG를 바로 확인하지 못하면 다른 포트일 가능성을 고려해야 했다.

---

## 5. 풀이

### 5.1 첫 번째 요청 테스트

먼저 `test_ssrf.py`를 작성하여 이미지 뷰어에 요청을 보내고, 응답 상태 코드와 HTML을 확인하였다.

첫 번째 테스트에 사용한 URL은 다음과 같다.

```text
http://127.1:1500/flag.txt
```

먼저 `127.1`을 이용해 로컬 주소 필터를 우회할 수 있는지 확인하기 위해 `test_ssrf.py`를 작성하였다. 내부 서버의 포트를 우선 `1500`으로 설정하고, `/flag.txt`를 요청하도록 하였다.
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/6ca41440-06b8-485b-9905-c42241b86e75" />

스크립트에서는 `requests.post()`로 `/img_viewer`에 URL을 전달하고, 반환된 상태 코드와 응답 HTML을 출력하도록 하였다.

<img width="1276" height="800" alt="Image" src="https://github.com/user-attachments/assets/99ea2d2a-1c73-4448-9dc8-0189ead9ab0e" />

실행 결과 HTTP 상태 코드 `200`이 반환되었고, 응답 HTML에는 `data:image/png;base64,`로 시작하는 문자열이 포함되어 있었다.

하지만 **HTTP 상태 코드 `200`은 웹 페이지 요청에 대한 응답이 반환되었다는 뜻이지, `flag.txt`의 내용을 성공적으로 읽었다는 뜻은 아니다.** 따라서 응답에 실제로 어떤 데이터가 들어 있는지 추가로 확인할 필요가 있었다.

이를 위해 응답 HTML을 `/tmp/ssrf_response.html`에 저장하도록 코드를 수정하였다.

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/18c9b3f3-4589-48d8-8387-7732b2be70a9" />
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/3d6bc88f-a40f-4594-a99c-52703b6db9f2" />

저장된 HTML에서 Base64 이미지 데이터가 포함된 부분을 확인하였다.

- Base64 데이터 확인

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/c7e6732f-5bc3-4eda-b928-2a6b751bab01" />

응답 HTML을 저장한 뒤, HTML 전체에서 Base64 이미지 데이터가 시작되는 부분을 확인하였다.

```bash
grep -o 'data:image[^"]*' /tmp/ssrf_response.html | head -c 200
```
명령어의 의미는 다음과 같다.

- `grep -o`: 검색한 부분만 출력한다.
- `'data:image[^"]*'`: `data:image`로 시작해 큰따옴표가 나오기 전까지의 문자열을 찾는다.
- `head -c 200`: 출력 결과의 앞부분 200바이트만 보여 준다.

실행 결과 Base64 데이터가 포함되어 있는 것을 확인하였다. 다만 이 명령어는 데이터의 일부를 출력할 뿐, Base64를 디코딩하거나 FLAG를 확인하는 명령어는 아니다.

첫 번째 요청에서는 FLAG를 바로 확인하지 못했으므로, 내부 서버가 실제로 사용 중인 포트가 `1500`이 아닐 가능성을 고려하였다. 이에 따라 포트 범위를 탐색하기로 하였다.

### 5.2 'scan.py'를 이용한 포트 스캔

내부 서버의 포트를 찾기 위해 `scan.py`를 작성하였다.

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/1da799e8-876c-4c7d-ad65-44b7f5ba1903" />

스크립트는 1500부터 1800까지 포트를 바꾸어 가며 다음 형식의 URL로 요청하도록 구성하였다.

```text
http://127.1:{port}/flag.txt
```

각 포트에 요청한 뒤 응답 HTML에 포함된 Base64 데이터를 추출하고, 이를 디코딩하여 실제 응답 내용을 확인하도록 하였다.

```python
decoded = base64.b64decode(img_data)
```

`base64.b64decode()`는 Base64로 인코딩된 문자열을 원래 데이터로 변환한다. 이를 통해 브라우저에서 이미지 형태로 표시되던 응답을 실제 내용으로 확인할 수 있다.

이 과정에서 중요한 것은 HTTP 상태 코드만 확인하는 것이 아니라, **응답 데이터가 실제로 `flag.txt`의 내용을 포함하고 있는지 확인하는 것**이었다.

### 5.3 FLAG 획득

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/640f4b3d-9a94-460e-8dde-767bff547209" />

포트 탐색 결과, 해당 실행 환경에서 내부 HTTP 서버가 사용 중인 포트는 `1705`로 확인되었다.

해당 포트로 요청한 결과 `flag.txt`의 내용을 확인할 수 있었다.

```text
DH{43dd2189056475a7f3bd11456a17ad71}
```

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/8da17e44-2a14-4adb-993e-ec21cc0d6fac" />

이로써 URL 필터를 우회하고 내부 서버의 포트를 찾아 `flag.txt`에 접근하는 데 성공하였다.

참고로 `1705`는 당시 실행 환경에서 확인한 포트 번호이다. 서버가 다시 실행되면 포트가 달라질 수 있다.

---

## 6. 정리 및 고찰

이번 문제에서는 사용자가 입력한 URL로 서버가 직접 요청을 보내는 구조를 이용해 SSRF 취약점을 확인하였다.

처음에는 `localhost`와 `127.0.0.1`을 차단하는 필터 때문에 내부 서버에 접근하기 어려울 것이라고 생각했다. 하지만 필터가 특정 문자열의 포함 여부만 검사하고 있었기 때문에 `127.1`을 이용해 우회할 수 있었다.

또한 내부 서버의 포트가 무작위로 지정되어 있어 포트 스캔을 통해 실행 중인 포트를 찾아야 했다. 응답 데이터가 Base64로 인코딩되어 있었기 때문에 이를 추출하고 디코딩하여 최종적으로 FLAG를 확인하였다.

이번 문제를 통해 SSRF 취약점은 사용자 입력 URL에 대한 검증이 충분하지 않을 때 발생할 수 있으며, 단순한 문자열 필터링만으로는 다양한 주소 표현을 이용한 우회를 막기 어렵다는 점을 확인하였다.