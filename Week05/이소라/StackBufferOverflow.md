# 시스템 취약점 분석 스터디 노트 — Stack Buffer Overflow

> CWE-121: Stack-based Buffer Overflow
> 메모리 안전하지 않은 언어(C/C++)에서 가장 고전적이고 대표적인 메모리 손상 취약점이다.

---

## 1. 개념

**스택에 할당된 버퍼에 그 크기보다 큰 데이터를 쓰면서, 인접한 메모리를 덮어쓰는 취약점이다.**

C/C++은 배열 경계를 자동으로 검사하지 않는다.
그래서 길이 검증 없이 입력을 복사하면, 버퍼 뒤에 있는 다른 지역 변수나 함수 호출 정보까지 덮어쓰게 된다.

```
[ 입력 데이터 ] ---> [ buf[16] ][ 다른 지역 변수 ][ SFP ][ Return Address ]
                       ↑ 16바이트를 넘는 순간부터 뒤쪽 영역이 오염된다
```

---

## 2. 배경 지식 — 스택 프레임 구조

함수가 호출되면 스택에 **스택 프레임**이 생성된다. (x86-64 기준, 스택은 높은 주소 → 낮은 주소로 자란다)

```
높은 주소
+--------------------+
| 호출자 프레임       |
+--------------------+
| Return Address     |  ← 함수 종료 후 돌아갈 주소 (call 시 push)
+--------------------+
| Saved RBP (SFP)    |  ← 이전 프레임의 base pointer
+--------------------+
| 지역 변수 / 버퍼    |  ← buf[] 는 여기 위치
+--------------------+
낮은 주소
```

- 버퍼는 **낮은 주소에서 높은 주소 방향으로** 채워진다.
- 따라서 버퍼를 넘치게 쓰면 → 다른 지역 변수 → SFP → **Return Address** 순으로 덮인다.
- 함수가 `ret` 할 때 스택의 Return Address로 점프하므로, 이 값이 오염되면 **프로그램 실행 흐름이 바뀐다.**

---

## 3. 왜 위험한가

| 영향            | 설명                                                             |
| --------------- | ---------------------------------------------------------------- |
| 프로그램 크래시 | 잘못된 주소로 복귀 → Segmentation Fault (DoS)                    |
| 데이터 변조     | 인접한 지역 변수(인증 플래그, 길이 값 등)를 바꿔 로직 우회       |
| 실행 흐름 탈취  | Return Address 조작 → 공격자가 원하는 코드 실행 가능             |
| 권한 상승       | setuid 프로그램, 원격 서비스에서 발생하면 시스템 장악으로 이어짐 |

> 1988년 Morris Worm이 `fingerd`의 `gets()` 스택 오버플로우를 이용했다.
> 1996년 Aleph One의 _"Smashing The Stack For Fun And Profit"_ 이 이 취약점을 널리 알린 고전 문서다.

---

## 4. 취약한 코드 패턴

### (1) 경계 검사가 없는 함수

```c
void vuln() {
    char buf[16];
    gets(buf);          // 입력 길이를 전혀 제한하지 않음 (C11에서 제거됨)
}
```

### (2) 길이 검증 없는 복사

```c
void copy(char *input) {
    char buf[32];
    strcpy(buf, input); // input 길이가 32 이상이면 오버플로우
}
```

### (3) 크기 계산 실수

```c
char buf[64];
read(0, buf, 128);      // 버퍼보다 큰 크기를 읽음
```

```c
char buf[16];
for (int i = 0; i <= 16; i++)   // off-by-one: buf[16]까지 접근
    buf[i] = input[i];
```

### 위험 함수와 대체 함수

| 위험 함수     | 문제점               | 안전한 대안                              |
| ------------- | -------------------- | ---------------------------------------- |
| `gets()`      | 길이 제한 없음       | `fgets(buf, sizeof(buf), stdin)`         |
| `strcpy()`    | 대상 크기 확인 안 함 | `strncpy()` / `strlcpy()` / `snprintf()` |
| `strcat()`    | 대상 크기 확인 안 함 | `strncat()` / `strlcat()`                |
| `sprintf()`   | 출력 길이 제한 없음  | `snprintf()`                             |
| `scanf("%s")` | 길이 제한 없음       | `scanf("%15s")` 처럼 폭 지정             |

> `strncpy()`는 길이가 꽉 차면 NULL 종료를 보장하지 않으므로 직접 `buf[n-1] = '\0'` 처리가 필요하다.

---

## 5. 보호 기법 (Mitigation)

현대 시스템은 여러 보호 기법을 **겹겹이** 적용한다. 각 기법이 막는 지점이 다르다.

### (1) Stack Canary (SSP)

- 버퍼와 SFP/Return Address 사이에 **임의의 값(canary)** 을 넣어둔다.
- 함수 종료 직전에 canary가 바뀌었는지 검사 → 바뀌었으면 `__stack_chk_fail`로 즉시 종료한다.
- GCC 옵션: `-fstack-protector`, `-fstack-protector-strong`, `-fstack-protector-all`

```
[ buf ][ canary ][ SFP ][ RET ]
          ↑ 오버플로우가 RET까지 가려면 반드시 여기를 지나야 한다
```

### (2) NX / DEP (No-eXecute)

- 스택, 힙 같은 데이터 영역을 **실행 불가**로 표시한다.
- 스택에 코드를 넣어도 실행되지 않는다.
- 쓰기 가능한 영역과 실행 가능한 영역을 분리하는 원칙(W^X).

### (3) ASLR (Address Space Layout Randomization)

- 실행할 때마다 스택, 힙, 공유 라이브러리의 **주소를 무작위화**한다.
- 공격자가 점프할 주소를 예측하기 어렵게 만든다.
- 확인: `cat /proc/sys/kernel/randomize_va_space` (2 = 전체 적용)

### (4) PIE (Position Independent Executable)

- 실행 파일 자체(코드 영역)의 주소도 무작위화한다.
- ASLR과 함께 써야 효과가 완전해진다.
- GCC 옵션: `-fPIE -pie`

### (5) RELRO (RELocation Read-Only)

- GOT 등 재배치 관련 영역을 읽기 전용으로 만들어 덮어쓰기를 막는다.
- Partial RELRO / Full RELRO (`-Wl,-z,relro,-z,now`)

### (6) 기타

- **FORTIFY_SOURCE** (`-D_FORTIFY_SOURCE=2`): 컴파일 시 크기를 알 수 있는 버퍼에 대해 위험 함수를 검사 버전으로 치환한다.
- **Shadow Stack / CET**: Return Address를 별도의 보호된 스택에 저장해 비교한다 (Intel CET).

### 보호 기법 확인

```bash
checksec --file=./binary
```

```
RELRO           STACK CANARY      NX            PIE
Full RELRO      Canary found      NX enabled    PIE enabled
```

---

## 6. 안전한 코딩 (근본적인 방어)

보호 기법은 **피해를 줄이는 장치**일 뿐, 근본 해결은 코드에서 오버플로우가 발생하지 않게 하는 것이다.

1. **모든 입력의 길이를 검증한다.** 복사 전에 대상 버퍼 크기와 비교한다.
2. **위험 함수를 쓰지 않는다.** 크기를 인자로 받는 함수를 사용한다.
3. **`sizeof`를 활용한다.** 크기를 하드코딩하지 않는다.
4. **off-by-one에 주의한다.** NULL 종료 문자 1바이트를 항상 고려한다.
5. **컴파일러 경고와 보호 옵션을 켠다.** `-Wall -Wextra -fstack-protector-strong -D_FORTIFY_SOURCE=2`
6. **정적/동적 분석 도구를 활용한다.** AddressSanitizer(`-fsanitize=address`), Valgrind, 정적 분석기
7. **가능하면 메모리 안전 언어를 사용한다.** Rust, Go 등은 경계 검사를 기본으로 한다.

```c
// 개선 예시
void safe_copy(const char *input) {
    char buf[32];
    snprintf(buf, sizeof(buf), "%s", input);  // 항상 NULL 종료, 크기 초과 시 잘림
}
```

---

## 7. 정리

| 구분      | 내용                                               |
| --------- | -------------------------------------------------- |
| 원인      | 경계 검사 없는 스택 버퍼 쓰기                      |
| 핵심 대상 | 인접 지역 변수, SFP, **Return Address**            |
| 결과      | 크래시, 로직 우회, 실행 흐름 탈취                  |
| 완화      | Canary, NX, ASLR, PIE, RELRO, FORTIFY_SOURCE       |
| 근본 대책 | 입력 길이 검증, 안전한 함수 사용, 메모리 안전 언어 |

---
