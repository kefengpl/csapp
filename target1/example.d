
example.o:     file format elf64-x86-64


Disassembly of section .text:

0000000000000000 <.text>:
   0:	48 b8 35 39 62 39 39 	movabs $0x6166373939623935,%rax
   7:	37 66 61 
   a:	48 89 44 24 08       	mov    %rax,0x8(%rsp)
   f:	48 8d 7c 24 08       	lea    0x8(%rsp),%rdi
  14:	68 fa 18 40 00       	push   $0x4018fa
  19:	c3                   	ret
