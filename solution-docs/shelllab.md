# Lab6 ShellLab
## 实验准备
- 实验介绍：利用学习的异常控制流机制（进程控制、信号），实现一个 tiny shell。
- 实验获取：https://csapp.cs.cmu.edu/3e/shlab-handout.tar，下载压缩包后，在linux环境使用`tar -xvf shlab-handout.tar`进行解压即可。
- 知识准备：学习教材第8章：异常控制流，尤其是理解其中的示例代码；阅读实验的Writeup, 它会告诉你这个实验如何完成。
- 实验环境：实验可在 WSL2 的 linux 环境运行。VSCODE 作为代码编辑器，通过 SSH 连接到 WSL2。
- 程序运行：解压tar包后，发现这是一个经典的C语言项目结构。你需要在`tsh.c`文件中写代码实现空缺的功能，**每次在`tsh.c`修改代码后，皆需要使用`make`命令进行编译**，以生成新的可执行程序`tsh`，在terminal输入`./tsh`就能运行我们自己的shell了。
- 程序测试：一共16个测试，输入`make test01`,`make test02`,...,`make test16`分别运行这16个测试。每个测试都有参考答案：输入`make rtest01`,`make rtest02`,...,`make rtest16`获得16个测试的参考答案。你需要保证运行16个测试的输出和参考答案完全一致（仅进程编号可以不同）。
## 基础知识整理
- 异常控制流这章内容繁多复杂，且教材中的很多示例代码就是直接可以复制过来用的，可以在实验初期为你形成基本框架，故在此对实验相关的基础知识及示例代码进行梳理。
### 进程
0. **操作系统：** 可以理解为躺在RAM（运行内存）中的内核代码。操作系统分为用户态（CPU执行用户的代码，权限较低）和内核态（CPU执行OS内核代码，权限很高）。操作系统会频繁切换用户态和内核态，以实现中断处理、异常处理、进程调度等功能。粗略地讲，进程（Process）指的是正在运行的程序。在操作系统中，以Android为例，你会打开微信、淘宝、Google等APP，每个APP可以视作一个正在运行的程序，那么每个APP就是一个进程。
1. **进程调度：** 操作系统有大量进程，比如进程A，进程B，进程C...，但是CPU核心数是有限的（此处以单核为例，单核CPU同一时刻只能运行单个进程），为了给用户一种“很多程序在同时流畅运行”的错觉，操作系统内核会实现进程调度，可以快速切换执行不同的进程：先做会儿A，然后做会儿B，再做会儿C，再做会儿B，再做会儿A...
2. **进程上下文切换：** 操作系统中会有多个进程，CPU每隔一段时间触发timer interrupt，从正在CPU上执行的进程中夺回CPU的控制权，CPU陷入内核开始执行操作系统内核代码，内核选择一个新进程（可能和刚刚执行的进程一致），恢复它的运行环境（恢复该进程保存的寄存器，并切换到该进程的页表），然后将CPU控制权交给这个新的用户进程，以实现进程调度。
3. **进程的三种状态：** Running, Stopped, Terminated。Running表示进程正在CPU上执行或者进程是就绪(Runnable)可以被调度的状态。Stopped表示进程被挂起。Terminated表示进程终止，终止分为正常终止和异常终止，正常终止包括：main函数执行完后返回、调用exit；异常终止：接收信号，且进程对该信号的默认行为是终止进程。
### fork 系统调用
1. 通过 fork 系统调用，父进程可以创建一个状态为Running的子进程。
2. 通过 fork 创建的子进程和父进程几乎一致：①子进程和父进程的虚拟地址空间是一致的（但是两个进程的地址空间是相互独立的）；②子进程拷贝父进程的文件描述符。③子进程的pid与父进程不同。
3. fork 调用一次，返回两次，在子进程和父进程分别返回一次。在子进程中，fork 返回 0，在父进程中，fork 返回子进程的 pid。根据fork返回值的差异性，可通过if语句控制父子进程的不同行为。于是有以下经典代码：
```c
int main() {
    pid_t pid;
    int x = 1;
    pid = Fork(); 
    if (pid == 0) {  /* Child */
        printf("child : x=%d\n", ++x); 
        exit(0);
    }
    /* Parent */
    printf("parent: x=%d\n", --x); 
    exit(0);
}
```
### 子进程的回收(Reap)
1. 进程终止后,变为僵尸进程，它依然会占用一些系统资源：①内核进程表条目(每个条目是一个PCB进程控制块结构体)，②进程号pid资源。在一个三年重启一次的服务器中，如果存在持续运行、一直创建进程而不回收进程的垃圾程序，将会造成严重的内存泄露。未回收的进程会占几KB的PCB结构体内存，且始终占用进程号pid。几KB的PCB结构体可能不会造成太大影响，但是占用进程号pid是个很严重的问题，linux系统可能仅支持2^15个进程号，一旦pid耗尽，系统就会报错 No more processes，此时你连执行个 ls 命令都执行不了，整台服务器直接瘫痪。
```c
/* 简化版 PCB(process control block) 块的结构。Simplified representation of 
   the task_struct structure in Linux kernel */
struct task_struct {
    volatile long state;            // Process state (e.g., TASK_RUNNING, TASK_STOPPED, EXIT_ZOMBIE)
    struct thread_info *thread_info;
    struct exec_domain *exec_domain; // Execution domain information (deprecated)
    struct mm_struct *mm;           // Memory management information (address space)
    struct fs_struct *fs;           // Filesystem information
    struct files_struct *files;     // File descriptor table
    struct signal_struct *signal;   // Signal handlers and signals pending
    struct sighand_struct *sighand; // Signal handling information
    ...
    /* Various other fields */
    ...
};
```
2. 回收：父进程使用`wait`或者`waitpid`即可回收子进程。父进程调用wait/waitpid函数只能回收自己的儿子进程(父进程通过`fork/vfork/clone`创建的进程)，孙子进程也是无法回收的。waitpid如果第一个参数指定的pid与调用waitpid的进程非父子关系，系统将会报错。
3. 孤儿进程：父进程终止了而没有回收它的子进程，会使得子进程变为孤儿进程，孤儿进程将会被系统的init进程回收。然而，有些父进程持续运行但是不回收子进程，这会导致子进程无法变成孤儿进程，从而子进程运行结束后一直作为僵尸进程存在，最终造成内存泄露。
### execve 函数
- 加载并运行程序。进程执行该函数后，进程的内存空间将直接被新的可执行程序覆盖，变得焕然一新。函数原型如下：
```
int execve(char *filename, char *argv[], char *envp[]) 
```
- 假设我们使用execve达到命令`/bin/ls –lt /usr/include`的运行效果，你需要填入的参数如下：
```c
char* filename = "/bin/ls";
//! \note execve 两个指针数组的传参皆需以 NULL 作为最后一个元素，从而界定数组的访问边界。
const char* argv[] = {"/bin/ls", "-lt", "/usr/include", NULL};
const char* envp[] = {"PWD=/usr/droh",...,"USER=droh", NULL}; // 如果不想填这个envp，可以直接 envp == NULL。
```
- 上述代码中，/bin/ls 就是一个可执行程序文件。一般而言，filename 和 argv[0] 相等，但二者可以不相等。比如 filename == "/bin/ls"，但是 argv[0] == "hello_world"。此时程序仍然执行 ls，但 ls 程序内部看到自己的名字会是：hello_world。
- execve 这个系统调用不返回，只有执行出错才会返回。
- linux 的 bash 需要用到 execve。比如你在命令行敲击 ls 按下回车，bash 会先通过 fork 创建子进程，然后调用`execve("/bin/ls", NULL, NULL)`加载并运行Linux系统的ls程序(ls是一个可执行文件，路径是/bin/ls)。大致代码如下所示。
```c
  if ((pid = Fork()) == 0) {   /* Child runs program */                                               
      if (execve(myargv[0], myargv, environ) < 0) {                                                        
          printf("%s: Command not found.\n", myargv[0]);                                                 
          exit(1);                                                                                     
      }                                                                                                
  }  
```
### shell
- shell就是你在linux系统中敲击命令按回车的那个黑框。用户通过 shell 与操作系统交互，从而运行用户进程。linux 系统的默认 Shell 是 bash。
- 下面是CSAPP教材实现的simple shell。实现逻辑很朴素：shell程序是一个无限循环，每次读取用户的一行输入，解析用户的输入，分为内置命令和非内置命令，若是非内置命令，就需要fork+execve创建子进程执行。对于非内置命令，若前台执行，则shell需要等待子进程执行完成并回收子进程，在此期间shell阻塞无法读取用户输入；若是后台命令，shell进程直接从eval返回，读取下一个用户输入。
- 然而，这个simple shell并没有回收后台子进程，由于shell进程一直运行使得后台子进程无法成为孤儿进程，这将会导致内存泄露。如何解决这个问题？你需要**信号**机制。
```c
int main() {
    char cmdline[MAXLINE]; /* command line */
    while (1) {
        printf("> ");
        Fgets(cmdline, MAXLINE, stdin);
        if (feof(stdin))
            exit(0);
        eval(cmdline); // evaluate
    }
}

void eval(char *cmdline) {
    char *argv[MAXARGS]; /* Argument list execve() */
    char buf[MAXLINE];   /* Holds modified command line */
    int bg;              /* Should the job run in bg or fg? */
    pid_t pid;           /* Process id */
    strcpy(buf, cmdline);
    bg = parseline(buf, argv);
    if (argv[0] == NULL)
        return;   /* Ignore empty lines */
    if (!builtin_command(argv)) {
        if ((pid = Fork()) == 0) {   /* Child runs user job */
            if (execve(argv[0], argv, environ) < 0) {
                printf("%s: Command not found.\n", argv[0]);
                exit(0);
            }
        }
        /* Parent waits for foreground job to terminate */
        if (!bg) {
            int status;
            if (waitpid(pid, &status, 0) < 0)
                unix_error("waitfg: waitpid error");
        } else {
            printf("%d %s", pid, cmdline);
        }
    }
    return;
}
```
### 进程组
- 每个进程都有一个进程id(记作pid)。而每个进程都属于且仅属于一个进程组(记作pgid)。
- 一般而言，通过shell启动的用户进程，其`pgid == pid`。若该用户进程继续fork子进程（子进程进一步fork孙子进程），那么fork出的子进程、孙进程和这个用户进程皆属于同一个进程组，他们的pgid是相同的。
![alt text](shelllab-images/image.png)
### 信号(Signal)的概念
- 一个信号就是一条小消息，它通知进程系统中发生了一个某种类型的事件。它由操作系统内核向进程发送。信号用id表示不同的信号类型，id是用小整数来表示的(数字1~30)。一条信号携带的信息：①信号id；②信号到达的事实。
- 下表列出了一些常见的信号
| ID | 信号名称 (Name) | 默认动作 (Default Action) | 对应事件 (Corresponding Event) |
| :---: | :--- | :--- | :--- |
| **2** | SIGINT | 终止 (Terminate) | 用户输入了 `ctrl-c` |
| **11** | SIGSEGV | 终止并转储 (Terminate & Dump) | 段错误 / 内存段违规访问 (Segmentation violation) |
| **17** | SIGCHLD | 忽略 (Ignore) | 子进程停止或终止 (Child stopped or terminated) |
- 信号从发出到接收需要经历三个阶段：发送信号(Sending Singal) --> 挂起信号(Pending Signal) --> 接收信号(Receiving Signal)
### 发送信号
- 内核有多种方式向进程发送信号。
- 方式一：一些系统事件发生：①用户进程除以0会导致CPU触发硬件异常使得用户进程陷入内核，内核向这个尝试除以0的用户进程发送SIGFPE信号；②父进程fork出的子进程终止了，内核会向父进程发送SIGCHLD信号。
- 方式二：用户键盘输入。比如用户在进程前台执行时按下Ctrl+C，会发送SIGINT信号给前台进程组。
- 方式三：kill函数/命令，它只是发信号的，未必杀死进程。C语言提供了kill系统调用，linux 中也内置了 /bin/kill 可执行程序，通过指定发送信号的id和目标进程的pid，即可向特定进程发送信号。下面是一些调用示例(目标pid > 0 是发给单个进程，pid < 0 是发给进程组)：
```bash
kill –9 24818 # 向进程24818(pid == 24818)发送id = 9的信号(SIGKILL)
kill -9 -24818 # 向进程组24818(pgid == 24818)的所有进程发送id = 9的信号(SIGKILL)
```
```c
#define	SIGINT 2
kill(24818, SIGINT); // 向进程24818(pid == 24818)发送 SIGINT 信号
kill(-24818, SIGINT); // 向进程组24818(pgid == 24818)的所有进程发送 SIGINT 信号
```
### 挂起信号（待处理信号）
- 待处理信号：信号已经由内核发出，但是目标进程还没有接收（目标进程未对该信号做出反应）。
- 进程上下文会用pending这个bit vector记录待处理信号。当类型为k的信号发送给进程p时，内核会在该进程pending的第k比特位设置为1。由于每个信号是否处于待处理状态是由单个比特位记录的，只能记录0/1，所以**同类型信号至多记录一个待处理信号**，多个同类型待处理信号不会排队等待。例如：若进程p的pending记录了SIGINT信号，内核又向进程p发送了2个SIGINT信号，此时这两个SIGINT信号会被丢弃。
- 进程可以阻塞接收某些类型的信号。进程上下文通过blocked这个bit vector记录阻塞信号。可通过C语言的`sigprocmask`函数设置阻塞哪些信号。
- pending中记录的待处理信号只能被接收一次，即：一旦进程对这个信号做出反应，pending队列中对该信号的记录就会被删去。
### 接收信号
- 当目标进程被内核强迫以某种方式对信号的发送做出反应时，它就接收了信号。
- 进程p接收的信号是**待处理且未被阻塞的信号**，即：`pnb = pending & ~blocked` 
- 进程可以做出的反应：①执行默认行为（忽略信号、终止进程、暂停进程）；②执行自定义的信号处理函数signal_handler（也叫捕获信号）。
- 进程p接收信号的时机（进程做出反应的时机）是：内核的异常处理代码执行完毕，将控制权交给进程p之前。这里的异常处理代码包括：执行系统调用、处理时钟中断（可能触发进程调度，导致上下文切换）、处理IO中断、处理缺页异常、处理除以0异常等。
- 接收信号算法的简化版代码如下：
```c
int get_signal(struct ksignal *ksig)
{
    struct task_struct *tsk = current;
    int sig;

    // Loop through the signal queue until we find a signal to deliver to user space
    for (;;) {
        // 1. Fetch the next unblocked signal pending for this thread/process
        sig = dequeue_signal(tsk, &tsk->blocked, &ksig->info);
        if (sig <= 0)
            return 0; // No pending signals remaining

        // 2. Handle tracing/debugging hooks (e.g., ptrace interception)
        if (unlikely(tsk->ptrace) && ptrace_signal_deliver(sig, ksig)) {
            continue; // Tracer might skip or change the signal
        }

        // 3. Extract the registered disposition (action) for this signal
        ksig->ka = tsk->sighand->action[sig - 1];

        // 4. Case A: The process explicitly requested to ignore this signal
        if (ksig->ka.sa.sa_handler == SIG_IGN) {
            continue; // Drop the signal and fetch the next one
        }

        // 5. Case B: The disposition is set to the default system action
        if (ksig->ka.sa.sa_handler == SIG_DFL) {
            
            // Check default behavior based on standard POSIX specifications
            if (sig_kernel_ignore(sig)) {
                continue; // Drop signal (e.g., default behavior for SIGCHLD/SIGURG)
            }

            if (sig_kernel_stop(sig)) {
                // Halt execution (e.g., SIGSTOP or Ctrl+Z SIGTSTP)
                do_signal_stop(sig);
                continue; // Resume iteration once the process wakes up
            }

            // Severe default actions: Process must terminate (e.g., SIGKILL, SIGSEGV)
            if (sig_kernel_coredump(sig)) {
                // Generate a core dump file before exiting
                do_coredump(&ksig->info);
            }
            
            // Terminate the execution of the entire thread group
            do_group_exit(sig); 
            return 0; 
        }

        // 6. Case C: A valid custom user-space handler exists!
        // Store the signal number and return 1 to inform the architecture code
        //! \note 只要执行用户的 signal handler，这个 get_signal 函数就跳出循环而结束执行了
        ksig->sig = sig;
        return 1; 
    }
}
```
- 信号嵌套执行：假设某进程对信号A和信号B皆设置了signal handler（即：该进程捕获了信号A和信号B）。某个进程在执行信号A的 signal handler 时，该进程处于用户态。若进程执行信号A的 signal handler 时，某次从内核态返回用户态的过程中，内核(执行`get_signal`的过程中)发现该进程有待处理信号B（假设该信号未被屏蔽）且存在signal handler，于是`get_signal`返回1，系统将为执行信号B的 signal handler 准备用户栈。这就发生了信号的嵌套执行。
![alt text](<shelllab-images/nested signal handler.png>)
### 信号的阻塞和解除阻塞
- 隐式阻塞（即：某些情况下会自动阻塞）。当执行信号A的handler时，该进程会阻塞接收信号A。例如：若执行信号A的过程中又收到信号A，那么信号A会在pending队列里面，但是由于blocked队列里面也有信号A,所以信号A不会被接收。
- 显式阻塞：`sigpromask`函数，与之相关的数据结构是信号集`sigset_t`。
- C语言没有集合类型，所以它提供了`sigemptyset`（清空信号集的所有信号，使之变为空集）、`sigfillset`（将所有信号添加到信号集，一般用于阻塞全部信号）、`sigaddset`（向信号集添加某个信号）、`sigdelset`（删除信号集中的某个信号）四个函数帮你操作信号集`sigset_t`。
- 下面是教材中的使用示例：
```c
sigset_t mask, prev_mask;
Sigemptyset(&mask);
Sigaddset(&mask, SIGINT);
/* Block SIGINT and save previous blocked set */
/* SIG_BLOCK: 将 mask 参数包含的信号和进程既有的阻塞的信号取并集 */
/* 第三个参数 prev_mask 用于储存进程原来的阻塞信号集，若传入 NULL，表示无需保留进程原来的阻塞信号集 */
Sigprocmask(SIG_BLOCK, &mask, &prev_mask);
/* Code region that will not be interrupted by SIGINT */
/* Restore previous blocked set, unblocking SIGINT */
/* SIG_SETMASK: 将 mask 参数包含的信号直接覆盖进程既有的阻塞信号集 */
Sigprocmask(SIG_SETMASK, &prev_mask, NULL);
```
### 安全信号处理
- 由于同一进程的**信号处理函数与用户程序、信号处理函数之间**皆为并发运行关系，可能造成类似于多线程环境那样的数据同步问题。如何写出安全的 signal handler？CSAPP列出了6条指引。
```
G0：信号处理程序尽可能简单。
G1：信号处理程序只调用 async-signal-safe 函数，即使发生异步信号递送导致函数执行被中断或重入，其行为仍然是安全的（如 write、_exit、sigprocmask、kill 等）。
G2：保存和恢复errno。若信号处理程序直接exit而非return，则无需该操作。
G3：访问（读/写）共享数据时暂时屏蔽所有信号（类似于多线程访问共享数据时加锁）。注意：实际工程中，为了减少不必要的影响，往往只阻塞可能访问该共享数据的相关信号，而不是无条件阻塞所有信号。
G4：全局变量声明为 volatile。防止程序只读取全局变量的寄存器副本而导致看不到最新值。
G5：全局标志(比如信号处理程序设置全局变量 flag = 1 表示收到了信号)声明为 volatile sig_atomic_t。可以保证对flag的读、写是原子的。当然，flag++和flag+=10这种依然不是原子的，它们涉及多条指令。
```
### 可移植信号处理
- 你的信号处理程序可能应用于不同版本的系统。一些系统的信号处理可能存在的问题是：①在执行某个信号A的handler后就会将信号A的接收方式恢复默认；②一些慢系统调用(比如 accept)会被信号处理中断，信号处理返回后，这些慢系统调用将停止执行并立即返回给用户错误条件。③处理信号时，不自动阻塞接收这个信号。
- 一般而言，使用下面的封装函数实现可移植信号处理。
```c
handler_t *Signal(int signum, handler_t *handler) {
    struct sigaction action, old_action;
    action.sa_handler = handler;
    // sigemptyset表示除了默认临时屏蔽handler对应的信号本身外，不额外屏蔽任何信号
    sigemptyset(&action.sa_mask); /* Block sigs of type being handled */
    action.sa_flags = SA_RESTART; /* Restart syscalls if possible */
    if (sigaction(signum, &action, &old_action) < 0)
        unix_error("Signal error");
    return (old_action.sa_handler);
}
```
### 信号处理函数的同步问题
- 下面的案例，如果fork后，子进程先执行，并且在父进程能再次运行之前，子进程就终止了，使得内核向父进程发送SIGCHLD信号。当内核计划调度父进程执行，准备从内核态返回用户态的过程中，发现父进程有未处理的SIGCHLD信号。于是，父进程会先执行hanlder的`deletejob`，而`addjob`则会靠后执行，从而导致逻辑错误。
```c
int main(int argc, char **argv) {
    int pid;
    sigset_t mask_all, prev_all;
    Sigfillset(&mask_all);
    Signal(SIGCHLD, handler);
    initjobs(); /* Initialize the job list */
    while (1) {
        if ((pid = Fork()) == 0) { /* Child */
            Execve("/bin/date", argv, NULL);
        }
        Sigprocmask(SIG_BLOCK, &mask_all, &prev_all); /* Parent */
        addjob(pid);  /* Add the child to the job list */
        Sigprocmask(SIG_SETMASK, &prev_all, NULL);
    }
}

void handler(int sig) {
    int olderrno = errno;
    sigset_t mask_all, prev_all;
    pid_t pid;
    Sigfillset(&mask_all);
    while ((pid = waitpid(-1, NULL, 0)) > 0) { /* Reap child */
        Sigprocmask(SIG_BLOCK, &mask_all, &prev_all);
        deletejob(pid); /* Delete the child from the job list */
        Sigprocmask(SIG_SETMASK, &prev_all, NULL);
    }
    if (errno != ECHILD)
        Sio_error("waitpid error");
    errno = olderrno;
}
```
- 为了避免这个问题，main函数在fork调用前，先阻塞SIGCHLD信号。父进程直到addjob执行完毕，再解除阻塞SIGCHLD。同时，由于子进程会复制父进程的信号阻塞列表，因此，子进程需要尽早解除对SIGCHLD的阻塞。
```c
int main(int argc, char **argv) {
    int pid;
    sigset_t mask_all, mask_one, prev_one;
    Sigfillset(&mask_all);
    Sigemptyset(&mask_one);
    Sigaddset(&mask_one, SIGCHLD);
    Signal(SIGCHLD, handler);
    initjobs(); /* Initialize the job list */
    while (1) {
        Sigprocmask(SIG_BLOCK, &mask_one, &prev_one); /* Block SIGCHLD */
        if ((pid = Fork()) == 0) { /* Child process */
            Sigprocmask(SIG_SETMASK, &prev_one, NULL); /* Unblock SIGCHLD */
            Execve("/bin/date", argv, NULL);
        }
        Sigprocmask(SIG_BLOCK, &mask_all, NULL); /* Parent process */
        addjob(pid);  /* Add the child to the job list */
        Sigprocmask(SIG_SETMASK, &prev_one, NULL);  /* Unblock SIGCHLD */
    }
    exit(0);
}
```
### 显式等待信号
- 下面的例子是主程序显式等待SIGCHLD的到达。这个程序是正确的，但是`while (!pid)`这种自旋操作会浪费CPU资源。
```c
volatile sig_atomic_t pid;
void sigchld_handler(int s) {
    int olderrno = errno;
    pid = Waitpid(-1, NULL, 0); /* Main is waiting for nonzero pid */
    errno = olderrno;
}

void sigint_handler(int s) {
}

int main(int argc, char **argv) {
    sigset_t mask, prev;
    Signal(SIGCHLD, sigchld_handler);
    Signal(SIGINT, sigint_handler);
    Sigemptyset(&mask);
    Sigaddset(&mask, SIGCHLD);
    while (1) {
        Sigprocmask(SIG_BLOCK, &mask, &prev); /* Block SIGCHLD */
        if (Fork() == 0) /* Child */
            exit(0);
        /* Parent */
        pid = 0;
        Sigprocmask(SIG_SETMASK, &prev, NULL); /* Unblock SIGCHLD */
        /* Wait for SIGCHLD to be received (wasteful!) */
        while (!pid);
        /* Do some work after receiving SIGCHLD */
        printf(".");
    }
    exit(0);
}
```
- 若将自旋语句改为`while (!pid) pause();`可能导致竞争条件：若程序在while测试之后和pause执行之前收到SIGCHLD信号执行sigchld_handler，则pause()无法再被SIGCHLD信号唤醒（除非用户手动按下Ctrl+C向主程序发送SIGINT信号）。
- 若将自旋语句改为`while (!pid) sleep(1);`逻辑上是对的，但问题是sleep多久？不好确定。
- 所以，为了显式等待信号，你需要`sigsuspend`：自旋语句将改为：`while (!pid) sigsuspend(&prev);`。修改后的`main`如下：
```c
int main(int argc, char **argv) {
    sigset_t mask, prev;
    Signal(SIGCHLD, sigchld_handler);
    Signal(SIGINT, sigint_handler);
    Sigemptyset(&mask);
    Sigaddset(&mask, SIGCHLD);
    while (1) {
        Sigprocmask(SIG_BLOCK, &mask, &prev); /* Block SIGCHLD */
        if (Fork() == 0) /* Child */
            exit(0);
        /* Parent */
        pid = 0; // 注意：pid = 0 下方删除了 Unblock SIGCHLD Sigprocmask(SIG_SETMASK, &prev, NULL); 
        /* Wait for SIGCHLD to be received */
        while (!pid)
            Sigsuspend(&prev);
        /* Do some work after receiving SIGCHLD */
        printf(".");
    }
    exit(0);
}
```
这里的`sigsuspend(&prev)`相当于原子化的（不会被打断的）下列语句，相当于延后解除对于SIGCHLD的阻塞。其中，`raw`为临时变量，用于在pause执行结束后恢复进程原有的阻塞信号集：
```c
sigprocmask(SIG_SETMASK, &prev, &raw); // prev 会解除对于 SIGCHLD 的阻塞
pause(); 
sigprocmask(SIG_SETMASK, &raw, NULL); // 恢复对 SIGCHLD 的阻塞
```
- 由于在即将执行pause()时才解除对SIGCHLD的阻塞，且解除SIGCHLD阻塞和调用pause()之间不会被打断。这就消除了竞争条件。
## ShellLab实验
### 测试脚本解读
- 为了防止找不到完成实验的方向，实验文档中提到`Use the trace files to guide the development of your shell.`，你可以面向测试用例编程。输入命令`make test01`就可以运行第一个测试了，这个测试默认是通过的，是赠送的测试用例。它包含两行，一行一个单词：`(line1)CLOSE (line2)WAIT`。
- 那么问题来了，这是什么含义？我们的tiny shell是如何理解这两行的？
- **`sdriver.pl`：** 若要理解测试的运行原理，需要我们对这个脚本有简要理解。它的大致作用：通过`fork()`系统调用启动我们的`tsh`程序，逐行读取`trace{xx}.txt`的内容。测试程序通过`Writer`向`tsh`发送输入内容。每行内容`$line`主要分为三种情况：
1. TSTP\INT\QUIT\KILL：测试程序通过kill系统调用向`tsh`发送对应的信号。
2. CLOSE\WAIT\SLEEP：①CLOSE：关闭Writer，`tsh`将无法接收到任何输入；②WAIT：测试程序等待并回收子进程`tsh`；③SLEEP：测试程序自身调用`sleep(time)`。
3. 其他输入：通过Writer这个管道将`$line`发送到`tsh`，比如`trace2`的`quit`，它不是大写的QUIT，所以测试程序不会向`tsh`发送QUIT信号，而是会转发`quit`到`tsh`作为输入。其效果类似于你在linux的命令行输入`quit`并敲击回车。
- 测试脚本中有很多类似于下面的行，即：第一行是`echo`+命令，第二行是命令本身。以下面两行为例，第一行被测试程序转发到`tsh`后，`tsh`的处理为：`/bin/echo`是回显命令，`-e`：激活转义字符的解析功能，`tsh> ./myspin 1 \046`是回显字符串，由于`-e`的存在，`\046`会被解析为`&`。因此，第一行只有打印功能，不需要`tsh`执行`./myspin`。第二行则是真正需要让`tsh`执行`./myspin`程序。
```
/bin/echo -e tsh> ./myspin 1 \046
./myspin 1 &
```
### 系统调用的错误处理
- 根据CSAPP的建议，系统调用需要处理返回值为-1的情况。这里使用Stevens-style error-handling wrappers风格对fork调用进行包装，形成`Fork()`函数，如下所示。后续创建子进程时，将使用`Fork`调用。
```c
pid_t Fork(void) {
    pid_t pid = 0;
    if ((pid = fork()) < 0) 
        unix_error("vely sad. fork error.\n");
    return pid;
}
```
### 热身：实现内置命令quit, jobs
- 实验文档中有下面一句话，说明内置命令`quit jobs fg bg`皆为前台运行，且直接在`./tsh`这个进程运行，无需fork子进程。
``` 
If the first word is a built-in command, the shell immediately executes the command in the current process. 
```
- 查看`tsh.c`，`main`循环读取用户输入命令和`parseline`解析用户输入命令都已经写好了。你需要在`eval`函数中处理内置命令，并处理这些内置命令。
- **`builtin_cmd`函数：** 实验文档写着：`builtin_cmd: Recognizes and interprets the built-in commands`，所以该函数中会区分四个内置命令，并且由于该函数在`tsh.c`中标出了`return 0; /* not a builtin command */`，所以该函数的返回值可代表bool：是否内置命令，返回1表示是内置命令，返回0表示非内置命令。于是，`builtin_cmd`在`eval`中可写在if判断中。
- **内置命令检测：** C语言需要使用`strcmp`检验字符串相等，使用类似`if (!strcmp(cmdline, "quit"))`的语法判断`cmdline == "quit"`。
- **内置命令quit：** 处理方式就是直接退出进程，使用系统调用`exit(0)`即可。
- **内置命令jobs：** `tsh.c`中有一个全局数据结构`struct job_t jobs[MAXJOBS]; /* The job list */`，管理tiny shell中的所有fork()出的进程。所以你需要访问与jobs相关的函数，`tsh.c`中有一个`listjobs`已经写好了，调用`listjobs(jobs)`即可。另外，根据CSAPP教材中对于写信号处理程序的指引"Protect accesses to shared data structures by temporarily blocking all signals."，`listjobs(jobs)`涉及对全局变量jobs的读操作，所以可暂时阻塞所有信号。于是，在`eval`和`builtin_cmd`中填充下列代码。
```c
void eval(char* cmdline) {
    int bg = 0;
    char* argv[MAXARGS];
    char buf[MAXLINE];
    strcpy(buf, cmdline);
    bg = parseline(buf, argv);
    if (argv[0] == NULL)  return;
    if (!builtin_cmd(argv)) {
        // 待填充的处理非内置命令的情况
    }
    return;
}

int builtin_cmd(char **argv) {
    if (!strncmp(argv[0], "quit", 4)) {
        exit(0);
    }
    if (!strncmp(argv[0], "jobs", 4)) {
        sigset_t full_mask, prev_mask;
        sigfillset(&full_mask);
        sigprocmask(SIG_BLOCK, &full_mask, &prev_mask);
        listjobs(jobs);
        sigprocmask(SIG_SETMASK, &prev_mask, NULL);
        return 1;
    }
    // bg fg 命令的处理方式待填充
    return 0;     /* not a builtin command */
}
```
### 运行前台任务：代码框架
- trace03.txt会测试：`/bin/echo tsh> quit`。这是一个前台任务，需要你的`tsh`运行`echo`程序，回显字符串`tsh> quit`。显然，我们需要在`eval`函数的`if (!builtin_cmd(argv))`分支内填写代码了。
- `/bin/echo tsh> quit`这个命令，在parseline解析后，argv数组中，`argv[0]="/bin/echo" argv[1]="tsh> quit"`。非内置命令皆需要fork子进程，随后在子进程使用`execve`函数，将argv的响应参数传入即可。
- 同时，根据实验文档的提示：默认情况下Ctrl+C会发向前台进程组，`tsh`fork出的子进程默认和`tsh`同属前台进程组，所以在`tsh`执行前台任务时按下Ctrl+C，`tsh`和子进程都会收到SIGINT信号。`tsh`的`sigint_handler`的函数注释表明本实验希望`tsh`捕获sigint然后将它转发给fork出的前台任务，即：子进程**不直接接收SIGINT信号**，所以fork出的子进程需要修改所属进程组。实验文档写道： `After the fork, but before the execve, the child process should call setpgid(0, 0)`，照做即可，将会把子进程的进程组号设置为与进程pid一致。
- 父进程应该负责维护`jobs`全局变量，创建子进程后，父进程应调用`addjob(jobs, pid, FG, cmdline);`将任务信息添加到`jobs`。
- 父进程`tsh`需要在等待前台任务执行完成，所以需要调用`waitfg(pid)`。注意此时我们还没有实现`waitfg`的功能。
```c
// eval 函数内部
if (!builtin_cmd(argv)) {
    volatile pid_t pid;
    pid = Fork();
    if (!pid) {
        if (execve(argv[0], argv, NULL) < 0) {
            setpgid(0, 0);
            printf("%s: Command not found\n", argv[0]);
            exit(0);
        }
    }
    addjob(jobs, pid, FG, cmdline);
    waitfg(pid);
}
```
- 子进程执行结束后，父进程负责回收进程。根据实验文档：`It is simpler to do all reaping in the handler.`所以子进程回收都在sigchld_handler中实现。对于前台任务，父进程只需要写wait和deletejob即可。实验文档写道：`The WUNTRACED and WNOHANG options to waitpid will also be useful.`。这说明：需要把这俩参数加到`waitpid`中。参数解释：①WNOHANG："wait no hang"，即：父进程不挂起。如果父进程发现还没有可回收的子进程，waitpid将不会阻塞，而是返回0。②WUNTRACED：如果子进程处于STOPPED状态，waitpid也返回。
```c
void sigchld_handler(int sig) {
    while ((pid = waitpid(-1, NULL, WNOHANG | WUNTRACED)) > 0) {
        deletejob(jobs, pid);
    }
    return;
}
```
### 运行后台任务
- trace04.txt会测试`./myspin 1 &`。注意trace04.txt的`/bin/echo -e tsh> ./myspin 1 \046`依然是前台任务。
- 后台任务与前台任务的区别在于：父进程无需等待。在`eval`函数的`if (!builtin_cmd(argv))`分支内，沿用执行前台任务的代码，进行少量调整即可。
- 运行`make rtest04`，你会发现，程序会输出一行：`[1] (4287) ./myspin 1 &`，参照该格式，父进程应该执行`print`语句打印出后台任务的`jid`,`pid`(`tsh.c`中提供了接口`int pid2jid(pid_t pid)`),以及执行的命令`cmdline`。字符串模板是`"[%d] (%d) %s"`。需要注意的细节是：cmdline读取的输入本身带有`\n`字符，所以字符串模板中无需以`\n`结尾。
```c
// eval 函数内部
if (!builtin_cmd(argv)) {
    volatile pid_t pid;
    pid = Fork();
    if (!pid) {
        if (execve(argv[0], argv, NULL) < 0) {
            setpgid(0, 0);
            printf("%s: Command not found\n", argv[0]);
            exit(0);
        }
    }
    //! \note 添加判断：bg = parseline(buf, argv); 若 bg = 1 表明为后台任务。
    addjob(jobs, pid, bg ? BG : FG, cmdline);
    if (bg)
        waitfg(pid); // 前台任务需要父进程等待
    else // 打印后台任务的相关信息
        printf("[%d] (%d) %s", pid2jid(pid), pid, cmdline);
}
```
### 信号处理函数：SIGINT
- trace06.txt、trace07.txt 开始测试 SIGINT。`tsh.c`中对`sigint_handler`函数的注释为：Catch it and send it along to the foreground job。所以信号处理函数的作用就是将sigint信号转发给前台进程。即：如果前台进程的进程号是`fg_pid`，调用`kill(fg_pid, SIGINT)`即可。`tsh.c`提供了辅助函数`fg_pid`寻找前台进程的pid：`fg_pid = fgpid(jobs)`。所以信号处理函数的核心逻辑是：
```c
fg_pid = fgpid(jobs);
if (fg_pid != 0) // fg_pid == 0 表示当前没有正在运行的前台进程
    kill(fg_pid, SIGINT);
```
- 考虑到`fgpid(jobs)`会访问全局变量`jobs`，所以需要暂时阻塞全部信号以对全局变量`jobs`进行保护。
- 实验文档中写道`When you type ctrl-c, the shell should catch the resulting SIGINT and then forward it to the appropriate foreground job`，这意味着，我们需要向进程组发送信号，所以kill调用应该写为`kill(-fg_pid, SIGINT)`(在fg_pid前面加个负号)。
- 最终形成的信号处理函数如下：
```c
//! \note sigtstp_handler 的写法与下面的 sigint_handler 基本一致，仅替换函数体内的 kill 函数即可。
void sigint_handler(int sig) {
    pid_t fg_pid;
    sigset_t all_mask, prev_mask;
    sigfillset(&all_mask);
    sigprocmask(SIG_BLOCK, &all_mask, &prev_mask);
    fg_pid = fgpid(jobs);
    if (fg_pid != 0) {
        kill(-fg_pid, SIGINT);
        // 对于函数 sigtstp_handler, 将 kill 语句替换为 kill(-fg_pid, SIGSTP)
    }
    sigprocmask(SIG_SETMASK, &prev_mask, NULL);
    return;
}
```
- 若运行`make rtest06`，你会发现输出语句包含`Job [1] (7058) terminated by signal 2`。所以在父进程回收由SIGINT杀死的子进程时(即：在`sigchld_handler`里)，需要进行`printf`输出，模板字符串是`Job [%d] (%d) terminated by signal %d\n`。另外，该实验中只有SIGINT导致的子进程回收需要`printf`。所以要记录是哪个信号导致子进程停止，需填写`waitpid`的第二个参数，以记录子进程状态改变的具体原因。
- 我们使用`child_status`记录子进程的状态，然后使用一些C语言内置的宏函数来确认子进程是由于收到SIGINT而停止的。
```c
void sigchld_handler(int sig) {
    int child_status = 0, pid = 0;
    while ((pid = waitpid(-1, &child_status, WNOHANG | WUNTRACED)) > 0) {
        // WIFSIGNALED 判定子进程确实是被信号杀死的，然后用 WTERMSIG 去看是哪个信号
        if (WIFSIGNALED(child_status) && WTERMSIG(child_status) == SIGINT)
            printf("Job [%d] (%d) terminated by signal %d\n", pid2jid(pid), pid, WTERMSIG(child_status));    
        deletejob(jobs, pid);
    }
    return;
}
```
### 信号处理函数：SIGSTP 及 STOPPED 进程的处理
- `sigstp_handler`：拷贝上方`sigint_handler`的实现，把`kill(-fg_pid, SIGINT);`替换为`kill(-fg_pid, SIGSTP)`即可。
- 如果运行`make rtest08`，发现对于接收 SIGSTP 的子进程，父进程需要输出类似于`Job [2] (11506) stopped by signal 20`这种。SIGTSTP 会导致子进程进入 STOPPED 状态，而 Child stopped 会给父进程发送 SIGCHLD 信号，因此，依然可以在`sigchld_handler`完成语句输出。
```c
void sigchld_handler(int sig) {
    int child_status = 0, pid = 0;
    while ((pid = waitpid(-1, &child_status, WNOHANG | WUNTRACED)) > 0) {
        if (WIFSTOPPED(child_status)) {
            getjobpid(jobs, pid)->state = ST;
            printf("Job [%d] (%d) stopped by signal %d\n", pid2jid(pid), pid, WSTOPSIG(child_status));               
        } else { 
            if (WIFSIGNALED(child_status) && WTERMSIG(child_status) == SIGINT)
                printf("Job [%d] (%d) terminated by signal %d\n", pid2jid(pid), pid, WTERMSIG(child_status));    
            deletejob(jobs, pid);
        }
    }
    return;
}
```
### 内置命令实现：bg和fg
- 根据`tsh.c`，需要在`do_bgfg`中实现。实验文档中对这两个命令的功能做了详细的说明：`bg <job>: Change a stopped background job to a running background job.`，`fg <job>: Change a stopped or running background job to a running in the foreground.`。
- 可先在`builtin_cmd`完成`bg` `fg`命令的识别、参数初步检验，然后在`builtin_cmd`调用`do_bgfg`函数。完整的`builtin_cmd`函数如下：
```c
int builtin_cmd(char **argv) {
    if (!strncmp(argv[0], "quit", 4)) {
        exit(0);
    }
    if (!strncmp(argv[0], "jobs", 4)) {
        sigset_t full_mask, prev_mask;
        sigfillset(&full_mask);
        sigprocmask(SIG_BLOCK, &full_mask, &prev_mask);
        listjobs(jobs);
        sigprocmask(SIG_SETMASK, &prev_mask, NULL);
        return 1;
    }
    int is_bg = !strncmp(argv[0], "bg", 2);
    int is_fg = !strncmp(argv[0], "fg", 2);
    if (is_bg || is_fg) {
        if (!argv[1]) {
            printf("%s command requires PID or %%jobid argument\n", 
                   is_bg ? "bg" : "fg");
            return 1;
        }
        // 检查第一个是否是数字？
        if (!isdigit(argv[1][0]) && argv[1][0] != '%') {
            printf("%s: argument must be a PID or %%jobid\n", 
                   is_bg ? "bg" : "fg");

            return 1;          
        }
        do_bgfg(argv);
        return 1;
    }
    return 0;     /* not a builtin command */
}
```
- `do_bgfg`需要对bg、fg的参数进行区分，根据实验文档`“%5”denotes JID 5, and “5” denotes PID 5`,参数加百分号是jid，不加百分号是pid。检验参数是否有百分号只需要`argv[1][0] == '%'`。
- `do_bgfg`需要检验传入的jid/pid是否是有效的。可借助`tsh.c`中提供的辅助函数：`getjobjid/getjobpid`。这俩函数如果返回`NULL`，则表明参数的jid/pid是无效的。`do_bgfg`直接返回。
- 无论是`bg`还是`fg`，都需要向目标进程发送`SIGCONT`信号，使用系统调用`kill`对进程`pid`取负值，向目标进程组发送SIGCONT信号即可。
- 若是`bg`命令，将目标进程状态设置为`BG`即可。若为`fg`命令，需将目标进程状态设置为`FG`，由于子进程转为前台运行，因此父进程需要等待子进程结束，所以父进程调用`waitfg`。
- 最后，注意访问全局数据结构`jobs`时暂时阻塞所有信号，并在恰当时机解除阻塞即可。
```c
void do_bgfg(char **argv) {   
    sigset_t full_mask, prev_mask;
    sigfillset(&full_mask);
    sigprocmask(SIG_BLOCK, &full_mask, &prev_mask);
    int is_jid = (argv[1][0] == '%');
    struct job_t* this_job = is_jid ? 
                              getjobjid(jobs, atoi(argv[1] + 1))
                              : getjobpid(jobs, atoi(argv[1]));
    if (!this_job) {
        sigprocmask(SIG_SETMASK, &prev_mask, NULL);  
        is_jid ? printf("%s: No such job\n", argv[1]) 
               : printf("(%s): No such process\n", argv[1]);
        return;
    }
    kill(-this_job->pid, SIGCONT);
    if (!strncmp(argv[0], "bg", 2)) {
        this_job->state = BG;
        printf("[%d] (%d) %s", this_job->jid, this_job->pid, this_job->cmdline);
        sigprocmask(SIG_SETMASK, &prev_mask, NULL);  
        return;
    }
    // handle built-in command fg
    this_job->state = FG;
    sigprocmask(SIG_SETMASK, &prev_mask, NULL);  
    waitfg(this_job->pid);
    return;
}
```
### 显式等待信号：waitfg
- 由于子进程回收都在`sigchld_handler`中进行，所以waitfg只需要阻塞父进程。根据CSAPP教材中“显式等待信号”的代码示例：
```c
sigprocmask(SIG_BLOCK, &mask, &prev); /* Block SIGCHLD */
// ...
while (!pid) // 若子进程在 sigchld_handler被回收，pid将不为 0
    sigsuspend(&prev);
```
- 我们的`waitfg`可直接参考上面的代码。将检测`!pid`替换为调用`fgpid(jobs)`检测是否还存在前台进程。同时，由于要访问全局变量`jobs`，所以要在`fgpid(jobs)`判断前暂时阻塞所有信号。然后在while判断后，调用`sigsuspend(&prev_mask);`，该调用可以原子化地【解除信号阻塞，调用`pause()`，在`pause()`返回后恢复对所有信号的阻塞】。
```c
void waitfg(pid_t pid) {
    sigset_t all_mask, prev_mask;
    sigfillset(&all_mask);
    sigprocmask(SIG_BLOCK, &all_mask, &prev_mask);
    while (fgpid(jobs)) {
        sigsuspend(&prev_mask);
    }
    sigprocmask(SIG_SETMASK, &prev_mask, NULL);
    return;
}
```
### eval和sigchld_handler的同步问题
- 前文为了直观展示处理逻辑，没有对`eval`和`sigchld_handler`屏蔽信号以避免并发问题。
- 其中，`sigchld_handler`由于涉及全局数据结构`jobs`的访问，所以仅需要在访问`jobs`前阻塞所有信号，并在访问后解除阻塞。
```c
void sigchld_handler(int sig) {
    int child_status = 0, pid = 0;
    sigset_t all_mask, prev_mask;
    sigfillset(&all_mask);
    while ((pid = waitpid(-1, &child_status, WNOHANG | WUNTRACED)) > 0) {
        sigprocmask(SIG_BLOCK, &all_mask, &prev_mask);
        if (WIFSTOPPED(child_status)) {
            getjobpid(jobs, pid)->state = ST;
            printf("Job [%d] (%d) stopped by signal %d\n", pid2jid(pid), pid, WSTOPSIG(child_status));               
        } else { 
            if (WIFSIGNALED(child_status) && WTERMSIG(child_status) == SIGINT)
                printf("Job [%d] (%d) terminated by signal %d\n", pid2jid(pid), pid, WTERMSIG(child_status));    
            deletejob(jobs, pid);
        }
        sigprocmask(SIG_SETMASK, &prev_mask, NULL);
    }
    return;
}
```
- `eval`函数除了需要保护`jobs`全局变量外，还需要在创建子进程前阻塞`SIGCHLD`信号，否则可能导致子进程先执行结束，父进程收到SIGCHLD信号后调用`sigchld_handler`中的`deletejob`，使得`deletejob`先于`addjob`执行，造成并发问题。注意：由于父进程在fork调用之前阻塞了`SIGCHLD`信号，因此fork出的子进程需要尽快解除对于SIGCHLD的阻塞。
```c
void eval(char *cmdline) {
    sigset_t old_mask, new_mask, full_mask;
    int bg = 0;
    char* argv[MAXARGS];
    char buf[MAXLINE];
    volatile pid_t pid;
    strcpy(buf, cmdline);
    sigemptyset(&new_mask);
    sigaddset(&new_mask, SIGCHLD);
    sigfillset(&full_mask);
    bg = parseline(buf, argv);
    if (argv[0] == NULL)  return;
    if (!builtin_cmd(argv)) {
        sigprocmask(SIG_BLOCK, &new_mask, &old_mask);
        pid = Fork();
        if (!pid) {
            // puts the child in a new process group whose group ID is identical to the child's PID
            setpgid(0, 0); 
            sigprocmask(SIG_SETMASK, &old_mask, NULL);
            if (execve(argv[0], argv, NULL) < 0) {
                printf("%s: Command not found\n", argv[0]);
                exit(0);
            }
        }
        // G3: Protect accesses to shared data structures by temporarily blocking all signals.  
        sigprocmask(SIG_SETMASK, &full_mask, NULL);
        addjob(jobs, pid, bg ? BG : FG, cmdline);
        sigprocmask(SIG_SETMASK, &old_mask, NULL);

        if (!bg)
            waitfg(pid);
        else 
            printf("[%d] (%d) %s", pid2jid(pid), pid, cmdline);
    }
    return;
}
```
### 自动化测试脚本
- 由于需要逐个核对你的输出和标准输出是否完全一致，可以在实验目录创建`autotest.py`并写入下列代码，批量运行测试。
```python
import os
import subprocess
script_dir = os.path.dirname(os.path.abspath(__file__))
test_seqnums = ["{:02d}".format(elem) for elem in range(1, 17)]
for seqnum in test_seqnums[:16]:
    print(f"===============TEST{seqnum}===============")
    result = subprocess.run(["make", "test" + seqnum], 
                            capture_output=True, text=True, cwd=script_dir)
    print(result.stdout, end = "")
    print()
    ref_result = subprocess.run(["make", "rtest" + seqnum], 
                                capture_output=True, text=True, cwd=script_dir)
    print(ref_result.stdout, end = "")
```
### 参考实现
```c
pid_t Fork(void) {
    pid_t pid = 0;
    if ((pid = fork()) < 0) 
        unix_error("vely sad. fork error.\n");
    return pid;
}

void eval(char *cmdline) {
    sigset_t old_mask, new_mask, full_mask;
    int bg = 0;
    char* argv[MAXARGS];
    char buf[MAXLINE];
    volatile pid_t pid;
    strcpy(buf, cmdline);
    sigemptyset(&new_mask);
    sigaddset(&new_mask, SIGCHLD);
    sigfillset(&full_mask);
    bg = parseline(buf, argv);
    if (argv[0] == NULL)  return;
    if (!builtin_cmd(argv)) {
        sigprocmask(SIG_BLOCK, &new_mask, &old_mask);
        pid = Fork();
        if (!pid) {
            setpgid(0, 0); 
            sigprocmask(SIG_SETMASK, &old_mask, NULL);
            if (execve(argv[0], argv, NULL) < 0) {
                printf("%s: Command not found\n", argv[0]);
                exit(0);
            }
        }
        sigprocmask(SIG_SETMASK, &full_mask, NULL);
        addjob(jobs, pid, bg ? BG : FG, cmdline);
        sigprocmask(SIG_SETMASK, &old_mask, NULL);

        if (!bg)
            waitfg(pid);
        else 
            printf("[%d] (%d) %s", pid2jid(pid), pid, cmdline);
    }
    return;
}

int builtin_cmd(char **argv) {
    if (!strncmp(argv[0], "quit", 4))
        exit(0);
    if (!strncmp(argv[0], "jobs", 4)) {
        sigset_t full_mask, prev_mask;
        sigfillset(&full_mask);
        sigprocmask(SIG_BLOCK, &full_mask, &prev_mask);
        listjobs(jobs);
        sigprocmask(SIG_SETMASK, &prev_mask, NULL);
        return 1;
    }
    int is_bg = !strncmp(argv[0], "bg", 2);
    int is_fg = !strncmp(argv[0], "fg", 2);
    if (is_bg || is_fg) {
        if (!argv[1]) {
            printf("%s command requires PID or %%jobid argument\n", 
                   is_bg ? "bg" : "fg");
            return 1;
        }
        if (!isdigit(argv[1][0]) && argv[1][0] != '%') {
            printf("%s: argument must be a PID or %%jobid\n", 
                   is_bg ? "bg" : "fg");

            return 1;          
        }
        do_bgfg(argv);
        return 1;
    }
    return 0;
}

void do_bgfg(char **argv) {   
    sigset_t full_mask, prev_mask;
    sigfillset(&full_mask);
    sigprocmask(SIG_BLOCK, &full_mask, &prev_mask);
    int is_jid = (argv[1][0] == '%');
    struct job_t* this_job = is_jid ? 
                              getjobjid(jobs, atoi(argv[1] + 1))
                              : getjobpid(jobs, atoi(argv[1]));
    if (!this_job) {
        sigprocmask(SIG_SETMASK, &prev_mask, NULL);  
        is_jid ? printf("%s: No such job\n", argv[1]) 
               : printf("(%s): No such process\n", argv[1]);
        return;
    }
    kill(-this_job->pid, SIGCONT);
    if (!strncmp(argv[0], "bg", 2)) {
        this_job->state = BG;
        printf("[%d] (%d) %s", this_job->jid, this_job->pid, this_job->cmdline);
        sigprocmask(SIG_SETMASK, &prev_mask, NULL);  
        return;
    }
    this_job->state = FG;
    sigprocmask(SIG_SETMASK, &prev_mask, NULL);  
    waitfg(this_job->pid);
    return;
}

void waitfg(pid_t pid) {
    sigset_t all_mask, prev_mask;
    sigfillset(&all_mask);
    sigprocmask(SIG_BLOCK, &all_mask, &prev_mask);
    while (fgpid(jobs)) {
        sigsuspend(&prev_mask);
    }
    sigprocmask(SIG_SETMASK, &prev_mask, NULL);
    return;
}

void sigchld_handler(int sig) {
    int child_status = 0, pid = 0;
    sigset_t all_mask, prev_mask;
    sigfillset(&all_mask);
    while ((pid = waitpid(-1, &child_status, WNOHANG | WUNTRACED)) > 0) {
        sigprocmask(SIG_BLOCK, &all_mask, &prev_mask);
        if (WIFSTOPPED(child_status)) {
            getjobpid(jobs, pid)->state = ST;
            printf("Job [%d] (%d) stopped by signal %d\n", pid2jid(pid), pid, WSTOPSIG(child_status));               
        } else { 
            if (WIFSIGNALED(child_status) && WTERMSIG(child_status) == SIGINT)
                printf("Job [%d] (%d) terminated by signal %d\n", pid2jid(pid), pid, WTERMSIG(child_status));    
            deletejob(jobs, pid);
        }
        sigprocmask(SIG_SETMASK, &prev_mask, NULL);
    }
    return;
}

void sigint_handler(int sig) {
    pid_t fg_pid;
    sigset_t all_mask, prev_mask;
    sigfillset(&all_mask);
    sigprocmask(SIG_BLOCK, &all_mask, &prev_mask);
    fg_pid = fgpid(jobs);
    if (fg_pid != 0) {
        kill(-fg_pid, SIGINT);
    }
    sigprocmask(SIG_SETMASK, &prev_mask, NULL);
    return;
}

void sigstp_handler(int sig) {
    pid_t fg_pid;
    sigset_t all_mask, prev_mask;
    sigfillset(&all_mask);
    sigprocmask(SIG_BLOCK, &all_mask, &prev_mask);
    fg_pid = fgpid(jobs);
    if (fg_pid != 0) {
        kill(-fg_pid, SIGSTP);
    }
    sigprocmask(SIG_SETMASK, &prev_mask, NULL);
    return;
}
```
## 一些问题
### 前台进程组
- 前台进程组指的是可以直接与终端进行交互的进程组，即：只有前台进程组可以从终端（键盘）读取数据；当你按下Ctrl+C，Ctrl+Z，信号会发给（广播给）前台进程组；当后台进程试图读取终端输入，系统会向其发送 SIGTTIN 信号暂停这个后台进程。
- “前台进程组”不是一个一成不变的组织，它更像是一个麦克风。谁在舞台中央说话，终端就把麦克风（前台身份）递给谁的进程组。当你刚启动 Shell 时，Shell 所在的组握着麦克风，所以它们是同一个东西。
- 当你打开一个终端时，linux 的 bash 在前台进程组。我们运行`ps -o pid,pgid,tpgid,comm &`命令即可验证这一事实。从下文可以看出，bash, oh-my-posh（bash美化程序，用户自行安装的） 皆属于前台进程组 TPGID = PGID = 1551。
```
    PID    PGID   TPGID COMMAND
   1551    1551    1551 bash
   1714    1714    1551 ps
   1715    1551    1551 oh-my-posh
```
- 注意：如果上述命令不加 & 让ps后台运行的话，进程列表打印时，ps所在的进程组才是前台进程组。这个过程大概是：①bash 运行 fork 创建子进程(或者是job)；②子进程运行`setpgid(0, 0)`创建并加入新的进程组，这个进程组PGID和子进程的PID一致；③bash运行`tcsetpgrp(STDIN_FILENO, pgid)`将终端前台进程组切换给子进程。④job 结束后 shell 运行`tcsetpgrp(STDIN_FILENO, bash_pgid)`把自己重新设为 foreground process group。
```
    PID    PGID   TPGID COMMAND
   1551    1551    1678 bash
   1678    1678    1678 ps
```
- 同理，当你在bash中输入`./tsh`命令，`./tsh`所在进程组是前台进程组。然而，我们的`./tsh`不要求调用tcsetpgrp，这意味着tsh 始终待在前台进程组。
- writeup 中写明了调用 setpgid 的时机：After the fork, but before the execve, the child process should call setpgid(0, 0)。但是，子进程解SIGCHLD阻塞和setpgid的顺序应该是怎样的？下文给出了两种情况，到底要选哪一个？
```c
// new mask 只添加了 SIGCHLD 阻塞。
//! \note 方案1：先解除阻塞，再setpgid
sigprocmask(SIG_BLOCK, &new_mask, &old_mask);
pid = Fork();
if (!pid) {
    sigprocmask(SIG_SETMASK, &old_mask, NULL);
    setpgid(0, 0); 
    execve(argv[0], argv, NULL);
}
//! \note 方案2：先setpgid，再解除阻塞
sigprocmask(SIG_BLOCK, &new_mask, &old_mask);
pid = Fork();
if (!pid) {
    setpgid(0, 0); 
    sigprocmask(SIG_SETMASK, &old_mask, NULL);
    execve(argv[0], argv, NULL);
}
```
- 两种方案皆不会出现严重的问题。不过，选择方案2更好，即：子进程被创建后应当尽早设置进程组。若setpgid执行比较延迟，那么会出现一个窗口：从子进程创建到setpgid执行之间，子进程和tsh皆属于前台进程组，如果此时按下Ctrl+C，父子进程皆会收到这个信号（假设极端情况下，系统优先调度了父进程，将子进程添加到了jobs结构，且解除了父进程的信号阻塞，而子进程尚未执行setpgid），此时父进程执行sigint_handler的kill(-pid, SIGINT)时，编号为pid进程组可能不存在，从而使得kill函数执行出错。
### C语言字符串的存放位置
- 进程虚拟地址空间的数据区主要存放静态和全局变量，该区域由三个部分组成：.data段 .bss段 .rodata段。
1. .data段存放的是已经赋了初值、且初值不为 0 的全局变量和静态变量
2. .bss段存放的是未初始化，或者显式初始化为 0 的全局变量和静态变量。该段无需根据变量大小实际占据磁盘空间，只需要几个字节保存元数据，记录程序运行时.bss需要多少空间，以及.bss的权限。例如全局声明数组而不初始化：`int arr[10000000]; `，可执行文件中只会记录下列内容。
```
Name: .bss, Size: 40000000 Bytes, Flags: Allocate/Write
```
3. ./rodata段是只读数据段，存放程序运行期间不能被修改的常量。比如：字符串字面量(用双引号写的字符串，比如"hello")，全局常量(如 const int GLOBAL_VAR = 5;)。但是，函数内的const常量依旧会放在栈空间中，只有编译器会检查限制它不能被修改，若能骗过编译器检查，则你在运行时可以随便修改这个局部const常量。
- 情况1：p 指向的地址是字符串字面量 "hell word" 的地址，在 .rodata 段。若使用`p[1] = 'E'`尝试修改这个字符串，程序依然可正常编译生成可执行文件，则由于访问了只读数据，该可执行文件运行时会报错：Segmentation fault (core dumped)。
```c
int main(int argc, char** argv) {
    char* p = "hell word";
    return 0;
}
```
- 情况2：字符串常量池。现代编译器为了节约内存，通常有字符串常量重用机制。下面示例的两个字符串字面量完全一致，所以./rodata只保留一份这个字符串。
```c
int main(int argc, char** argv) {
    char *p1 = "hello world";
    char *p2 = "hello world";
    printf("%d\n", p1 == p2); // p1 == p2 is True
    return 0;
}
```
- 情况3：字符数组构成的字符串。下面的案例中，①编译期：字面量"hell word"会在./rodata中存储一份；②运行时：栈空间中会分配10个字节(包含`\0`)，把 .rodata 里的 "hello" 拷贝（复制）到栈空间。即："hell word"字符串存在两份，一份在只读数据段，另一份在栈空间。运行`str[1] = 'E'`这种修改语句是不会崩溃的，而是修改被拷贝到栈空间的字符串。
```c
int main(int argc, char** argv) {
    char str[] = "hell word";
    return 0;
}
```
- 情况4：字符串数组`char* arr[]`(C++是`std::string arr[];`)。例如下面的envp数组，"PWD=/usr/droh", "USER=droh"这俩字符串字面量会储存在./rodata段，但是不会向情况3那样将这些字符串拷贝到栈空间，栈空间的envp是一个指针数组，共3个元素，前两个元素是字符串字面量在./rodata的地址，第三个元素是0x0。
```c
int main(int argc, char** argv) {
    char* envp[] = {"PWD=/usr/droh", "USER=droh", NULL};
    return 0;
}
```
### linux捕获信号详解
0. CSAPP对内核地址空间的描述非常详尽，如下图所示。对于每个进程而言，它在内核地址空间有页表、`struct task` `struct mm`、内核栈。
![alt text](shelllab-images/image-1.png)
1. 每个进程（假设进程是单线程的）有一个用户栈和一个内核栈。进程在执行过程中会陷入内核，CPU与内核入口代码(entry.S)会将被打断的用户进程的寄存器保存在内核栈中的`pt_regs`。`pt_regs`的结构如下所示。其中，`%rip %rsp`等寄存器是由CPU压入内核栈的，`%rdx %rdi...`是由内核入口代码entry.S压入的。
```
struct pt_regs {
    /* pushed by entry.S */
    unsigned long r15;
    unsigned long r14;
    unsigned long r13;
    unsigned long r12;
    unsigned long rbp;
    unsigned long rbx;
    unsigned long r11;
    unsigned long r10;
    unsigned long r9;
    unsigned long r8;
    unsigned long rcx;
    unsigned long rdx;
    unsigned long rsi;
    unsigned long rdi;

    /* System tracking */
    /* Original syscall number or hardware error code */
    unsigned long orig_ax; 

    /* pushed by hardware (or synthesized) */
    unsigned long rip;
    unsigned long cs;
    unsigned long eflags;
    unsigned long rsp;
    unsigned long ss;
};
```
2. 当操作系统从内核态返回用户态的过程中，对应进程的内核栈将被清空（通过增加内核栈指针的值来释放内核栈空间），内核栈中保存的寄存器从栈中弹出，恢复到CPU的物理寄存器上，为继续执行中断的用户进程恢复环境。
3. 若某次从内核态返回用户态的过程中，内核执行`get_signal`并发现有可捕获的信号A，那么内核会在用户栈构造`rt_sigframe`，其结构如下所示。内核栈的`pt_regs`会被拷贝到用户栈的`rt_sigframe->ucontext`当中，因为后续会修改内核栈上保存寄存器的值。随后，内核代码会修改内核栈中保存的`pt_regs->rip`的值，使它指向信号A的 signal handler 的地址。
```c
struct rt_sigframe {
    char __user *pretcode;              /* 信号蹦床（Trampoline）代码的返回地址 */
    struct siginfo info;                /* 包含信号的详细信息（如信号编号、发送者 PID 等） */
    struct ucontext uc;                 /* 用户态上下文，包含核心的寄存器备份 */
    struct fxregs_state fpstate;        /* 浮点寄存器、FPU/MMX/SSE 等扩展状态的备份（可选） */
    /* 在现代内核中，fpstate 可能作为 uc.uc_mcontext.fpstate 的指针指向这里 */
};
```
4. 内核代码通过CPU物理寄存器`%rdi`传参`signum`，作为 signal handler 函数的参数。`rt_sigframe`可以理解为一个特殊的函数栈帧，栈顶（栈的最低地址）是rt_sigframe的第一个数据成员`char __user *pretcode; `，它指向一段蹦床代码(Trampoline Code)，如下所示，这段蹦床代码包含系统调用`__NR_rt_sigreturn`。此外，由于用户栈有更新，那么储存在内核栈的`pt_regs->rsp`将更新为新的用户栈栈顶地址（指向`sigreturn addr`在用户栈的地址）。
```asm
__restore_rt:
    movq $15, %rax      # 15 是 __NR_rt_sigreturn 的系统调用号
    syscall             # 触发系统调用，陷入内核
    retq                # 理论上不会执行到这里，因为内核在恢复后会直接跳转到原程序的 rip
```
5. 操作系统从内核态返回用户态，该进程内核栈中保存的寄存器恢复到CPU物理寄存器中，并通过移动内核栈指针以逻辑清空内核栈。CPU在用户态，像执行一个用户函数调用那样在用户栈执行信号A的signal handler。
6. 在信号A的signal handler执行`ret`后，位于用户栈顶的`char __user *pretcode`被赋值给`%rip`，运行蹦床代码触发`__NR_rt_sigreturn`系统调用而陷入内核，该系统调用会将用户栈中保存的用户态寄存器`rt_sigframe->ucontext`拷贝到内核栈的`pt_regs`。（注意到：`pt_regs->rsp`会指向用户进程中断时的用户栈顶，相当于逻辑释放了由于接收、捕获信号而占用的用户栈空间）。
7. 最后，若没有其他信号，操作系统从内核态返回至用户态，将内核栈空间的寄存器恢复到CPU物理内存，用户进程继续执行，好像什么都没有发生过。