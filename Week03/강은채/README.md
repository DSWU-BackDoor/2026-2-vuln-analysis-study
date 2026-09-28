# Week03 - 강은채

취약점 분석 스터디 3주차 정리 및 실습입니다.

## 개념 정리
- [XSS (Cross-Site Scripting)](XSS.md) — 발생 원리, Source→Sink, 출력 문맥, 유형, 방어
- [CSRF (Cross-Site Request Forgery)](CSRF.md) — 발생 원리, 성립 조건, CSRF 토큰, XSS와의 관계

## WarGame 실습
- [XSS - Dreamhack #2061](WarGame/XSS-2061.md) — 필터/새니타이저 우회 XSS
  - 블랙리스트 + bleach(`<script>`만 허용) 우회
  - `document.write("<img>")` 실패(`<` 이스케이프) → **동적 `import()`** 로 전환해 쿠키 탈취
  - 스크린샷 기반 상세 보고서 + 재현용 페이로드/URL 포함
