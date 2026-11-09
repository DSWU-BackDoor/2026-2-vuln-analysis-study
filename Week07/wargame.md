# Shellcode

## 1. 문제 정보

- **문제명:** Shell Free (Dreamhack)
- **문제 링크:** https://dreamhack.io/wargame/challenges/2608


## 2. 소스 코드 분석

문제에서 제공하는 `out_of_bound.c` 파일을 확인하였다.
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/8d20c540-7a0f-4988-9a27-8b2360ca1ce3" />

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/3d194700-f5dd-4618-a7ef-5814a764cbbd" />

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/c3acc0c4-f736-4bcc-a12c-d6662f362bce" />

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/3fdd010a-7933-4516-9327-8abbef2d08d7" />

main 실행 파일이 열리지 않는 상태였다.

### 2-1. 파일 정보 확인

```bash
file main
```
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/b3623621-aacd-4b7d-bf56-322153ae9219" />

리눅스 64비트 실행파일, 리틀 엔디안, PIE 활성화(실행 시 코드 주소 무작위로 변경됨), not stripped(함수 이름 등 심볼 유지) 등을 확인하였다. 이어서 보호 기법을 확인했다. 

```bash
checksec --file=main
```
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/ce6c67cc-d5b0-4222-8796-74e8cef5545e" />

NX Enabled로 NX 활성화 되어 있었다. 이는 스택에서 셸코드 실행을 방지하기 때문에 스택에 셸코드 넣고 주소로 점프하는 방식이 차단되어있다고 볼 수 있다. 따라서 워게임 풀이 시 우회가 필요함을 확인하였다. 

Canary Enabled로 오버플로우 발생 시 프로그램이 종료될 수 있기에 이 부분도 우회가 필요하며, PIE Enabled로 바이너리 주소 바뀌니까 고정 주소를 사용하지 못하는 문제임을 확인하였다. 

### 2-2. 함수 목록 확인

```bash
nm -n main
```

- 심볼: 함수나 전역 변수처럼 프로그램 내부에 존재하는 요소들의 이름과 관련 정보
해당 명령어는 실행파일의 심볼 정보를 확인하는 명령어이며, `-n` 명령어는 심볼을 주소 순으로 정렬해서 보여준다. 

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/89eeb091-d242-46fe-828b-23bfbe6da570" />
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/84dd32a3-b974-462c-a946-2fb848a72b35" />

- `T` 실행 코드가 저장되는 Text 영역
- `B` 초기값이 지정되지 않은 전역 변수 등이 저장되는 BSS 영역
- `D` 초기값이 지정된 전역 변수 등이 저장되는 Data 영역

따라서

- `T main` : 프로그램 시작 함수
- `T get_flag` : 플래그 관련 함수
- `B flag` : 전역 변수
- `B fp` : 전역 변수


## 3. main() 분석

```bash
strings main
```
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/849fd55c-89bc-4b50-8878-11b14c40d902" />

바이너리 내부의 문자열을 추출해보았다. 

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/44c45c21-dba7-4aef-a37d-5d707b19760e" />

이 부분에서 입력을 받고, 플래그를 출력하는 것을 확인할 수 있다. 

GDB로 넘어가 분석을 이어갔다. 

우선 `info functions`을 통해 현재 분석 중인 프로그램에 존재하는 함수 목록을 확인하였다. 

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/a15759bf-b47e-42f6-ae5b-3e02cdce678c" />

이 부분에서 `main()` 함수와 `get_flag()` 함수가 존재한다는 사실과, 이들의 시작 주소를 확인할 수 있었다.


## 4. main() 어셈블리 코드 분석

GDB를 실행한 후 `main` 함수의 어셈블리 코드를 확인하였다.

```bash
disassemble main
```
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/0ed9186e-b5d9-4492-9b7d-fd5767fdce23" />

중요한 구간별로 나누어서 보면

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/c8a24e45-17b3-4303-87b2-773165620899" />

먼저 스택에 특정 바이트 값을 저장하고

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/a5dc5c87-1bbe-4192-af8e-3141bae92359" />

이후에 비슷한 작업을 반복하는 것을 확인할 수 있다. 
(movabs는 큰 상수값을 레지스터에 직접 저장하는 명령어이다. )

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/7ad3e8be-0356-4a28-b21d-eefe83d00050" />

이 부분은 mmap를 호출하는 부분이다. 64비트 Linux의 함수 호출 규약 하에서는 함수 인자를 레지스터에 전달한다. 

따라서 `mov edx, 0x7` prot 인자 값이 0x7이란 뜻이고,

0x7 권한은 읽기(1), 쓰기(2), 실행(4) 권한을 모두 가진다. 

즉, NX가 활성화된 바이너리지만 mmap로 별도의 RWX 메모리 공간을 확보하고 있음을 알 수 있다. 

다음으로 `printf()`를 호출하는 부분이다. 
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/de2ca85c-061f-4d40-9b53-c9408927c0e6" />

`read()` 호출하는 부분이다.
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/f897a92e-d50a-45fe-b3ef-64dddc695c34" />

buf 에 `mmap 주소 + 0x2d` 값 (=입력 저장 위치를 메모리 시작 주소 아닌 45바이트 뒤부터 입력) 입력됨.
count는 0x400(=1024)바이트 임.


이후 입력값을 검사하는데

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/66e0c28c-6aa1-4731-b3df-d794d13406cc" />

입력값 검사 시작 위치를 45(0x2d)로 설정한다. 

<img width="680" height="62" alt="Image" src="https://github.com/user-attachments/assets/c1757cd5-bcf7-427b-a4be-2ed7924cb518" />

이후 입력값에서 1바이트를 가져오고

<img width="774" height="110" alt="Image" src="https://github.com/user-attachments/assets/7f3301f2-02bb-4971-89cf-ab7b73c22d3a" />

입력값과 미리 저장해 둔 17개의 바이트를 비교한다. 

이 때, 일치하는 값이 발견되면
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/583cbf3e-2e53-4b27-9293-c039647f4150" />

`No Hack ~ ^_^` 출력 후 프로그램 종료된다. 
즉, 특정 바이트가 포함된 셸코드를 차단하는 필더가 존재하고 볼 수 있었다. 

이어서 일치하는 값이 없다면, 
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/b2f0f3bf-767b-487b-a26e-083b978f7a0e" />

반복문을 시작하기 위한 인덱스를 0으로 초기화하고

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/e5389139-e4ec-4024-ab76-145977c55df5" />

스택에 저장해 둔 45바이트를 mmap로 할당한 메모리에 복사한다. 

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/f456a3dd-71e3-4e82-b13b-1b59044346d1" />

이후 `call rdx` 로 `rdx` 에 저장된 mmap 주소를 호출 = 메모리에 복사된 코드가 실행되는 구조이다.

main() 분석을 마친 후 우선 필터링 하고 있는 금지 바이트가 무엇인지 확인해서 프로그램이 종료되지 않게 해야하며, 미리 복사되는 45바이트 코드가 무엇인지 알아내는 과정이 필요하다고 생각했다. 

## 5. get_flag() 어셈블리 코드 분석

```bash
disassemble get_flag
```

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/f0d1c4e7-5fef-4ac1-ae94-c8992de2b7d3" />


`disassemble get_flag`를 통해 확인한 `get_flag` 함수는 간단히 말하자면 flag.txt 파일을 열고, 그 내용을 전역변수 flag에 읽어온 뒤 출력하는 함수였다. 

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/3c78c27b-1050-4221-b586-58277b2e18e2" />

이 부분에서는 `fopen()`을 호출하기 위한 인자를 준비하고, 첫번째 인자를 rdi, 두번째 인자를 rsi에 전달한다. 
따라서 rdi에 파일 이름이, rsi에 어떤 모드로 열지(r)가 들어가게 된다. 

<img width="962" height="138" alt="Image" src="https://github.com/user-attachments/assets/5441bdf0-4f11-45a8-9c1b-15a0bcaa6b9f" />

이후, `fopen()`의 반환값은 rax에 들어온다. 
파일이 열리면 파일 포인터를 반환하고, 파일을 열지 못하면 NULL을 반환하게 되며, 이 값을 `fp`에 저장하고  `text rax, rax`로 NULL인지 검사한다. 

`jne`는 결과가 0이 아닐 때 지정 주소로 이동한느 명령어다. 따라서 파일이 정상적으로 열린다면, `0x14a8`로 이동하게 된다. 

만약 파일을 열지 못하면 아래 코드에 따라 오류 메시지가 출력된다. 

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/ef3c9d47-19f1-46fc-bf28-2439429fa9c5" />



이 부분은 `fscanf()`호출 부분이다. 

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/e4cc9651-a6f5-4b53-925b-86c0a67eacda" />

- rdi: 파일포인터 fp
- rsi: 읽기 형식 문자열 %s
- rdx: 읽은 내용 저장할 flag 인자를 전달받음

이후 마지막으로 `printf()`를 호출한다. 
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/4685a422-04b6-4a51-8896-1c255640e29e" />



## 6. 45바이트의 코드 정체 알아내기

```bash
break *main+150
run
```

45바이트 코드를 스택에 준비시켜두기 위해서 `main()` 시작 지점에서 150 바이트 떨어진 위치에 중단점을 설정하고 실행하였다. 이 과정을 거치고 나면, main에서 초기화한 45바이트 코드가 스택에 준비된 상태가 될 것이다.

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/b447fe28-8e54-4c6e-88e5-69ad04861d16" />

처음 실행했을 때, main 파일에 실행 권한이 없어 실행이 되지 않는 문제가 발생하였다. 이에 실행 권한을 부여하고 다시 시도해보기로 하였다. 

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/b5722a7d-6500-405e-98da-f118db299abe" />

- `chmod` 파일의 권한을 변경하는 명령어

`+x`를 통해 실행 권한을 추가하였다. 

<img width="400" alt="Image" src="https://github.com/user-attachments/assets/3f08e9b6-8c7f-45a1-bc7f-72523ca18308" />

참고로 Docker 컨테이너 내부의 main 파일에는 실행 권한을 부여하는 설정은 확인되어 내가 풀이하는 곳에서만 추가를 진행하였다. 

다시 실행해보면

<img width="400" alt="Image" src="https://github.com/user-attachments/assets/25e711a6-f1cd-450b-87a7-211a7de89103" />
<img width="800" alt="Image" src="https://github.com/user-attachments/assets/e47cec8f-5c96-4224-ac02-94012e279fa2" />

 `main()` 의 시작 주소: 0x555555555269

 + 0x96(150)

 = 0x5555555552ff

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/215e6c89-67b8-46c7-8d58-a9d2ca200eab" />

 RBP: 현재 함수의 스택 프레임 기준 주소

 RSP: 현재 스택의 가장위쪽 주소

 따라서 확인하려는 데이터 시작은 `RBP-0x40`

임을 확인할 수 있다. 

이어서 `RBP-0x40` 부터 45바이트를 확인해보았다. 

```bash
x/45bx $rbp-0x40
```

이 명령어는 `rbp-0x40`부터 45바이트를 16진수로 출력시킨다. 

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/e3b6cf77-5078-48b6-a808-a18c4ba66de6" />

결과를 3개씩 끊어서 어셈블리 명령어로 변환하면 다음과 같다. 

`xor rax, rax`
`xor rbx, rbx`
.
.
.
`xor r9, r9`
.
.
.

이런 식으로 총 15개의 명령어가 있고, 총 45바이트이므로 각 3바이트이다. xor로 같은 값을 연산하면 결과가 항상 0이 나오기 때문에 초기화하는 것이라 해석이 가능하다. 

45바이트 초기화 코드를 실행한 후, RAX 부터 R15까지 초기화하고, 초기화 코드가 끝나면 바로 뒤에 있는 사용자 셸코드를 실행하는 흐름이다. 

중요한 점은 rsp는 초기화하지 않는다는 것이다.
따라서 call rdx 실행 시 스택에 저장된 반환 주소를 활용할 수 있다.

사용자 셸코드는 레지스터가 초기화된 상태에서 실행된다고 볼 수 있다. 

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/4ddae7ad-6262-42e9-8052-475b0111a3ca" />

그리고 앞부분에서, 총 17개의 바이트가 금지되어 있다고 볼 수 있다. 
0f 05 ff e8 e9 ea eb 9a cc 5e 5f 58 59 5a 5b f3 aa
이 중 하나라도 걸리면 실행 차단 필터에 의해 필터링이 진행되고 실행이 종료된다. 
특히  0f 05는 syscall 명령어를 나타내는 바이트인데 이 부분도 필터링이 되고 있다.  

즉, 셸코드의 최종 목적은 직접 syscall을 사용하는 것이 아니라 이미 프로그램에 존재하는 get_flag() 함수를 실행하는 것이다.




## 7. 익스플로잇 설계

### 7-1. 반환 주소 활용

`main()`에서 다음 명령어가 실행된다. 

```bash 
call rdx
```

CALL 명령어는 다음에 실행할 명령어의 주소를 스택에 저장한 뒤 지정된 주소로 이동한다.

따라서 초기화 코드가 실행되는 동안에도 rsp가 변경되지 않았으므로 스택 최상단에는 CALL 명령어의 반환 주소가 남아 있다.

GDB에서 확인한 주소는 다음과 같다.

- CALL 명령어 다음 주소 : 0x55555555544a
- get_flag() 주소 :	0x555555555465
- 두 주소의 차이 : 0x1b

따라서 스택에 저장된 반환주소에 0x1b를 더하면 `get flag()`의 주소를 구할 수 있다. 

### 7-2. PIE 우회
PIE가 활성화되어 있기 때문에 프로그램이 실행될 때마다 코드의 실제 메모리
주소가 달라질 수 있다. 따라서 get_flag()의 절대 주소를 셸코드에 직접
입력하면 안정적으로 동작하지 않는다.

하지만 반환 주소와 get_flag()의 주소 사이의 상대적인 차이는 동일하다.
이를 이용하면 실행 시점의 반환 주소를 기준으로 get_flag()의 실제
주소를 계산할 수 있다.

### 7-3. 금지된 명령어 우회
일반적인 방식으로 JMP 명령어를 사용하면 금지 바이트 검사에 걸릴 수 있다.
따라서 JMP 대신 push와 ret을 이용해 원하는 주소로 실행 흐름을
이동시키기로 했다.

ret은 스택 최상단에 저장된 주소를 꺼내 해당 주소로 이동하는 명령어다.

## 8. 최종 셸코드 작성

최종적으로 작성한 셸코드는 다음과 같다. 

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/06c52747-a8ab-49ff-89b9-71310d3fa751" />

- `mov rax, [rsp]`   스택 최상단에 저장된 반환 주소를 RAX에 저장
- `add rax, 0x1b`    반환 주소에 0x1b를 더해 get_flag() 주소 계산
- `push rax`        계산한 주소를 스택에 저장
- `ret`              스택에 저장된 주소로 실행 흐름 이동

rsp에 저장된 반환 주소를 가져온 후, 반환주소에 0x1b를 더한다. 
더한 get_flag() 주소를 스택에 넣는다.
retㅇ르 실행해 get_flag()로 이동한다.
flag()가 flag를 출력한다. 

이렇게 작성한 어셈블리 코드를 바이너리로 변환한다. 
```bash
nasm -f bin shellcode.asm -o shellcode.bin
```

이후 생성된 바이너리를 확인한다. 
```bash
xxd -g 1 shellcode.bin
```

결과는 다음과 같았다. 

48 8b 04 24 48 83 c0 1b 50 c3

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/6d00ac34-2a33-43da-9efd-3273afda80c8" />
(아래에 있는 실행)

총 10바이트이며, 금지된 바이트가 포함되어 있지 않은 것을 확인했다.

로컬 환경 내에서 정상적으로 실행되는지 확인해보았다. 
```bash
b *get_flag
run < shellcode.bin
continue
```

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/776ae209-99f6-42ab-9411-7f5c6275f0d3" />

<img width="800"  alt="Image" src="https://github.com/user-attachments/assets/77f512ce-6672-4c9f-a804-200b3d2d1755" />

실행 결과 get_flag() 함수에 정상적으로 도달하는 것을 확인했다. 이후
flag가 출력되었다.

다만 flag 출력 이후 프로그램이 SIGSEGV로 종료되는 현상이 발생했다. 이는
초기화 코드에서 rbp까지 0으로 초기화했기 때문이다.

get_flag() 실행이 끝나면 원래 실행 흐름으로 돌아가는데, 이후
main()에서 rbp를 사용하는 과정에서 잘못된 메모리 주소에 접근하게
된다.

따라서 flag가 출력된 이후 발생하는 SIGSEGV는 익스플로잇 실패가
아니다. 목표인 get_flag() 실행과 flag 획득은 정상적으로 이루어진
것으로 확인하였다. 



로컬 환경 내에서 셸코드가 정상적으로 실행되는 것을 확인했으므로, 이를 드림핵 VM 서버와 연동하여 FLAG를 획득해보고자 하였다. 

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/591d5e36-409b-49e2-be83-e038fe0c1bf8" />

<img width="800" alt="Image" src="https://github.com/user-attachments/assets/4e081f54-2af0-4b8d-9142-f3d1946c0886" />

실행 결과 FLAG를 획득할 수 있었다. 



## 9. 결론 및 느낀 점

이번 문제에서는 syscall과 특정 분기 명령어에 해당하는 바이트가 금지되어
있어 일반적인 셸코드 작성 방식으로는 풀이하기 어려웠다. 하지만 다음과
같은 방법으로 문제를 해결할 수 있었다.
1. mmap()으로 RWX 메모리 영역이 할당된다는 점을 확인했다.
2. 초기화 코드가 레지스터를 0으로 초기화하지만 rsp는 유지한다는 점을
   이용했다.
3. call rdx가 스택에 저장한 반환 주소를 가져왔다.
4. 반환 주소에 0x1b를 더해 get_flag()의 실제 주소를 계산했다.
5. 금지된 JMP 대신 push와 ret을 이용해 실행 흐름을 이동시켰다.
이를 통해 syscall이나 직접적인 JMP 명령어를 사용하지 않고도 프로그램
내부의 get_flag() 함수를 실행할 수 있었다.
