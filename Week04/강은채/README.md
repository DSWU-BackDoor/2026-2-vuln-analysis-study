# Week04 - 강은채

취약점 분석 스터디 4주차 정리 및 실습입니다.

## 개념 정리
- [SSRF (Server-Side Request Forgery)](SSRF.md) — 서버가 요청 주체, 내부망/메타데이터, URL 검증 우회(DNS 리바인딩·리다이렉트)
- [Access Control / Broken Access Control](Access-Control.md) — 인증 vs 인가, IDOR, 수평·수직 권한 상승

## WarGame 실습
- [SSRF - Dreamhack #1412](WarGame/SSRF-1412.md) — URL 파싱 차이를 이용한 SSRF 필터 우회
  - `http://www.google.com:80@127.0.0.1/admin` 으로 필터("호스트=google")와 실제 접속(127.0.0.1)을 분리
  - 서버가 자기 `/admin`을 localhost로 호출하게 만들어 flag 세팅 → FLAG 획득
  - 스크린샷 기반 보고서 + 재현용 명령 포함
