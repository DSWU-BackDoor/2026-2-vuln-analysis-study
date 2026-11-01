# Ubuntu 22.04를 베이스 이미지로 사용 (SHA256 Digest로 이미지 지정)
FROM ubuntu:22.04@sha256:b6b83d3c331794420340093eb706a6f152d9c1fa51b262d9bf34594887c2c7ac

# 패키지 업데이트 및 socat 설치
RUN apt update && apt-get install -y socat

# 사용자 생성 및 홈 디렉토리 생성
RUN adduser --disabled-login --gecos '' -- "oob"

# 작업 디렉토리 설정 및 사용자 변경
WORKDIR /home/oob
USER oob

# 파일 복사
COPY ./deploy/flag ./flag
COPY ./deploy/oob ./oob

# 파일 권한 설정 (root 사용자로)
USER root
RUN chmod 444 ./flag
RUN chmod 755 ./oob

# 다시 oob 사용자로 변경
USER oob

# 포트 노출 및 socat으로 9090 포트에서 oob 바이너리 실행
EXPOSE 9090
CMD socat TCP-LISTEN:9090,reuseaddr,fork EXEC:./oob,stderr

