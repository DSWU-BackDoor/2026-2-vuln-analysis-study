# Week02 - 강은채

취약점 분석 스터디 2주차 정리 및 실습

## 개념 정리
- [Command Injection](Command-Injection.md) — 명령어 삽입의 원리, 공격 기법, 방어법
- [SQL Injection](SQL-Injection.md) — SQL 삽입의 원리, 인증 우회 / UNION / Blind, 방어법

## WarGame 실습
- [Blind SQL Injection](WarGame/Blind-SQL-Injection.md) — Dreamhack
  - Boolean-based Blind SQLi로 admin 비밀번호(FLAG)를 한 글자씩 추출
  - 자동화 스크립트: [solve_blind.py](WarGame/solve_blind.py)
  - 분석 대상 소스: [app.py](WarGame/app.py)
