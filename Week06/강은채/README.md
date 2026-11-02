# Week06 - 강은채

취약점 분석 스터디 6주차 정리입니다. (System Hacking / Pwnable)

## 개념 정리
- [OOB (Out-of-Bounds)](OOB.md) — OOB Read/Write, 발생 원인(인덱스·길이 검증, 정수 오버플로우, 포인터 연산), 관련 CWE, 보안 영향, 다른 메모리 취약점과의 차이, 대응 방법, ASan 탐지 예제

## WarGame 실습
- [oob (Dreamhack #1415)](WarGame/oob.md) — 전역 배열 인덱스 검증 누락 → OOB Read/Write