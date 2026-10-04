문제 설명
flask로 작성된 image viewer 서비스 입니다.

SSRF 취약점을 이용해 플래그를 획득하세요. 플래그는 /app/flag.txt에 있습니다.

풀이과정

1. 사이트 접속
   ![alt text](image-1.png)
   url을 입력받고, 그에 대한 이미지를 출력해주는 사이트임을 알 수 있다.
   혹시 url에 flag가 있을 수도 있을 것 같아, url에 flag가 있다는 /app/flag.txt 를 입력해보았지만
   ![alt text](image.png)
   풀리지 않는 것을 확인했다.

2. app.py 코드 확인

````py
elif ("localhost" in urlp.netloc) or ("127.0.0.1" in urlp.netloc):
            data = open("error.png", "rb").read()
            img = base64.b64encode(data).decode("utf8")
            return render_template("img_viewer.html", img=img)
            ```

```py
local_host = "127.0.0.1"
````

local_host가 내부에서만 접근 가능한 127.0.0.1로 설정되어 있고, url에 localhost나 127.0.0.1가 포함되면 무조건 에러 이미지를 띄운다는걸 알 수 있었다. 즉, 외부에서 접근하는것은 불가능함을 알 수 있었고, 이를 우회해야한다.

3. 127.0.0.1를 우회하기 위해 값을 10진수인 2130706433로 바꾸어보았다.
   http://2130706433:8000/static/dream.png
   얘를 입력해도 동일하게 사진이 출력된다!
   이는 브라우저에서는 주소나 주소를 10진수로 변환한 것이나 똑같은 주소라고 생각을 해 정상적으로 접속이 가능하고, 필터에서는 127.0.0.1라는 숫자가 아니기에 통과가 되는 것이다.

4. 코드 확인

```py
local_port = random.randint(1500, 1800)
```

로컬 포트는 1500과 1800 사이 숫자에 있다고 한다. http://2130706433:8000/static/dream.png
에서 8000을 1500과 1800사이의 로컬 호스트 포트번호로 변경해주면 된다.

5. 로컬호스트 포트번호를 찾기위해 burp suite를 사용해 무차별 대입 공격을 해준다.
   프록시로 웹사이트를 intercept하고, url에 url=http://2130706433:8000/flag.txt를 입력 후 veiw를 누른 상태로 request 값을 우클릭해 Send to Intruder 해준다.
