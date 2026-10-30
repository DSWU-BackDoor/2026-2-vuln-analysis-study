# Week05 - 강은채

취약점 분석 스터디 5주차 정리 및 실습입니다. (System Hacking / Pwnable)

## 개념 정리
- [Stack Buffer Overflow](Stack-Buffer-Overflow.md) — 스택 구조, 반환 주소 덮어쓰기, 오프셋 계산, ret2win/셸코드/ROP, 완화 기법(Canary/NX/ASLR/PIE)

## WarGame 실습
- [basic_exploitation_001 (Dreamhack)](WarGame/basic_exploitation_001.md) — 스택 BOF ret2win
  - `main`의 `gets(buf)` 오버플로우로 반환 주소를 `read_flag()`(=`system("cat flag")`)로 덮음
  - buf→RET 오프셋 132(0x84), `read_flag=0x080485b9` → `'A'*132 + p32(read_flag)`
  - 스크린샷 + 재현용 익스플로잇(raw 소켓 / pwntools) 포함
