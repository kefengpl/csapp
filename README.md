# CSAPP LAB
## LAB1 DataLab
1. **bitXor 使用&、~符号实现按位异或**
- ~x & y 可以得到 y 是 1 且 x 是 0 的部分；x & ~y 可以得到 x 是 1 且 y 是 0 的部分，让二者取并集即可。
- 取并集方法：根据 $\overline{A∪B} = \bar{A}∩\bar{B} ⇒ A∪B = \overline{\bar{A}∩\bar{B}} $，让 (~x & y) 和 (x & ~y) 各自取反，然后取交(&)，最后整体取反即可。
```c
int bitXor(int x, int y) {
  return ~(~(~x & y) & ~(x & ~y));
}
```
2. **tmin 获得INT_MIN**
- 根据补码原理，INT_MIN 符号位是1，其余31位数值位是0。
```c
int tmin(void) {
  return 1 << 31;
}
```
3. **isTmax 检查是否是INT_MAX**
- 补码加法是闭环的，加减法会在可表示范围内回绕。
- INT_MAX + INT_MAX 得到 -2，再 +2 得到 0。
- 与此同时 (-1) + (-1) 也等于 -2，所以需要排除这种情况。
- 即：返回条件是 x + x + 2 等于 0，并且 x + 1 不等于 0。
```c
int isTmax(int x) {
  int is_zero = x + x + 2;
  int is_minus1 = !(x + 1);
  return !is_zero & !is_minus1;
}
```
4. **allOddBits 奇数位全1则返回1**
- 构造出一个 1010....1010，170 的表示是 10101010，所以将它左移0/8/16/24位的结果按位或拼接起来即可。
- x & 1010....1010 将x的所有偶数位变为0，仅剩下x的奇数位，若 x & 1010....1010 和 1010....1010 相等，则 x 的奇数位全1。
```c
int allOddBits(int x) {
  int oddbits_mask = (170 << 24) | (170 << 16) | (170 << 8) | 170;
  return !((oddbits_mask & x)  ^ oddbits_mask) ;
}
```
5. **negate 获取一个数字的相反数** 
- 课件有写：$-x = \sim x + 1$
```c
int negate(int x) {
  return ~x + 1;
}
```
6. **isAsciiDigit 检测x是否在[48, 57]范围内**
- 48 的二进制表示 110000，57 的二进制表示 111001
- 48~57：4~5位是两个1(位索引范围0~31)，0~3位是0000~1001。
- 条件1：检测x是否符合 110XXX，从而得知x是否在范围 48-55。
- 条件2：56，57单独拿出来检测。
- 条件1，条件2满足一个即可。
```c
int isAsciiDigit(int x) {
  int condition1 = !((x & (~15)) ^ 48) & !(x & 8);
  int condition2 = !(x ^ 57) | !(x ^ 56);
  return condition1 | condition2;
}
```
7. **conditional 实现三目表达式**
- 其实只需要判断x是否是0。
- !x 将x映射到 0 和 1 上。只要通过变换，x != 0 的时候 y & -1 并且 z & 0；x == 0 的时候 y & 0 并且 z & -1即可。
```c
int conditional(int x, int y, int z) {
  return (y & (~(!(!x)) + 1)) + (z & (~(!x) + 1));
}
```
8. **isLessOrEqual 检测是否有 x <= y?**
- 分类讨论：
- ①符号位是否相异？相异则直接看x的符号位是否是1。
- ②若符号位相同，则计算 y - x ，若结果 >= 0，则 x <= y。y - x = y + (~x) + 1。两个符号位相同的数据做减法不会溢出，所以看结果的符号位即可。
```c
int isLessOrEqual(int x, int y) {
  int sign_x = (x >> 31) & 1;
  int sign_y = (y >> 31) & 1;
  int diff_sign = !(!(sign_x ^ sign_y));
  int same_sign = !diff_sign;
  int diff_sign_xneg = !(sign_x ^ 1);
  int same_sign_cond = !(((y + (~x) + 1) >> 31) & 1);
  return (diff_sign & diff_sign_xneg) | (same_sign & same_sign_cond);
}
```
9. **logicalNeg 实现c语言逻辑运算符 !**
- !的逻辑是检测x是否为0，所以实现逻辑也是围绕检测 x 是否为 0 展开的。
- 对于 int 范围内的数字取相反数，根据数学知识，只有0取相反数等于它本身。但是对于32位补码表示，INT_MIN 取相反数也是它本身。(将1000...0000取~再加1得到的还是1000...0000)
- 所以对于除了0和INT_MIN外的数，取相反数检测符号位是否相反即可。对于INT_MIN，直接检测符号位即可，即：符号位是1者必定不为0。所以合并的检测逻辑是：x 是负值 或者 x 取相反数后符号位与原来相反。不符合这个逻辑的数就是 0。
```c
int logicalNeg(int x) {
  int sign_bit = (x >> 31) & 1;
  return ~(sign_bit | ((((~x + 1) >> 31) & 1) ^ sign_bit)) + 2;
}
```
10. **howManyBits 补码表示某个数据所需的最少比特位**
- 补码环境下，n比特位可以表示的范围是 $[-2^{n - 1}, 2^{n - 1} - 1]$，例如：1比特表示范围[-1, 0]，2比特表示范围是[-2, 1], 3比特可表示范围[-4, 3]，4比特表示范围[-8, 7]，依次类推。
- 对于一个32比特位的数字，从左往右找找从符号位开始，连续相同比特位的个数（或者连续相同比特位的最低索引，索引范围是0~31）。
```
1. INT_MIN = 1000....0000(省略号中间皆为0，共32位)，符号位起连续相同的比特位只有1个，最低索引是31，所以需要 31 + 1 = 32个比特位表示该数据。
2. 5 = 0000....0101，符号位起连续相同比特位有29个，最低索引是3，所以需要3 + 1 = 4个比特位表示该数据。
3. 0 = 0000....0000，符号位起连续相同比特位有32个，最低索引是0，所以需要0 + 1 = 1个比特位表示该数据。
```
- 为了统一处理，将把负数转化为正数(负数直接取反(~x)即可)，问题则转化为：自符号位开始，从左往右找连续的0的个数，等价转换为**寻找最高位1的索引**，最高位1的索引 + 2得到函数返回结果。对于0，认为其最高位1的索引是 -1。
```c
int sign_bit = (x >> 31) & 1;
int sign_mask = ~sign_bit + 1;
x = x ^ sign_mask;
```
- 如何寻找最高位1的索引？
- 最简单的思路是顺序检验：从高位往低位逐个比特验证是否为1。但是运算符数量会超过90个。例如：取单个bit (x >> 30) & 1需要消耗两个操作符，验证其是否为0至少需要消耗1个操作符，即便不验证符号位，31个比特位检验至少需要 31 * 3 = 93 个操作符，会超出题目要求。因此，顺序检验的思路在此处不可行。
- 为了满足操作符个数限定，此处需要使用二分法。
```
1. 对于32位的数据，将其分为高16位和低16位：若高16位皆为0，则最高位1索引在低16位；若高16位不全为0，则在高16位。由此将查找范围缩小为16位。
2. 对于上步选出的16位数据，将其分为高8位和低8位：若高8位皆为0，则最高位1索引在低8位；若高8位不全为0，则在高8位。由此将查找范围缩小为8位。
依次类推，直到查找范围缩小为1位，即确定了最高位1的索引。
```
- 根据上述思路，写出下列直观的代码（不满足本题目的操作符限定和禁止使用分支的限定）。
```c
int howManyBits(int x) {
  int sign_bit = (x >> 31) & 1;
  int sign_mask = ~sign_bit + 1;
  x = x ^ sign_mask;
  int mask = ~(1 << 31);
  int idx = -1; // 寻找的最高位1的索引，初始对应 x == 0 的情况
  if(x != 0) idx = 0; // 此时可以将 idx 理解为查找范围是 [0, 32)
  // 判断高16位是否全为0。mask == INT_MAX。
  if ((((mask >> 15) & x) ^ x) == 0) idx = idx; else idx = idx + 16;
  // 对于筛选出来存在最高位1的那16位，判断其高8位是否全为0。
  // 若在高16位中检验其高8位(此时idx = 16，对应查找范围 [16, 32))，则 mask >> 7；若在低16位中检验其高8位(此时idx = 0，对应查找范围[0, 16))，则 mask >> (7 + 16)。
  // mask 向右侧移动位数与 idx 的关系是：idx 越大，mask 向右侧移动的位数越少。具体而言，mask 向右侧移动的位数 = 32 - idx - 8 - 1，8 指的是这次需要验证的比特长度是8。
  // 若验证的比特长度为 bit_length，则 mask 向右侧移动的位数 = 32 - idx - bit_length - 1
  if ((((mask >> (32 - idx - 8 - 1)) & x) ^ x) == 0) idx = idx; else idx = idx + 8;
  if ((((mask >> (32 - idx - 4 - 1)) & x) ^ x) == 0) idx = idx; else idx = idx + 4;
  if ((((mask >> (32 - idx - 2 - 1)) & x) ^ x) == 0) idx = idx; else idx = idx + 2;  
  // ⬇ 此步结束后，idx 表示的查找范围长度是 1，所以最高位1的索引得以确定
  if ((((mask >> (32 - idx - 1 - 1)) & x) ^ x) == 0) idx = idx; else idx = idx + 1; 
  return idx + 2;    
}
```
- 现在需要做的，是将上述代码改写为符合题目要求的形式。主要任务是将 if 分支用合法的操作符表达出来。
- 观察下面的表达式，发现两个分支可以合并为 idx = idx + (0 或者 8)。(0 或者 8) 可以通过if 内部表达式的运算结果是否非0决定。若if内表达式为0，则 idx = idx + 0。若if内表达式不为0，则 idx = idx + 8。
```c
if ((((mask >> (32 - idx - 8 - 1)) & x) ^ x) == 0) idx = idx; else idx = idx + 8;
```
- 表达式exp = (((mask >> (32 - idx - 8 - 1)) & x) ^ x) 可以通过加 ! 映射到 [0, 1] 范围内。并且由于表达式不为0时，idx要发生变化，所以希望表达式不为0的情况映射到1。所以使用 !!exp，当 exp 结果不为0时，!!exp = 1，要实现 idx = idx + 8，则需要将 !!exp * 8。由此，上面的 if 表达式优化为：
```c
int exp = ((mask >> (32 - idx - 8 - 1)) & x) ^ x;
idx = idx + !!exp * 8;
```
- 最后，将加减法合并，将乘法改为算术左移，得到此题解决方案。
```c
int howManyBits(int x) {
  int sign_bit = (x >> 31) & 1;
  int sign_mask = ~sign_bit + 1;
  int mask = ~(1 << 31);
  int idx = ~0;
  int shift = 0;
  x = x ^ sign_mask;
  idx = !(!(x ^ 0))+ (~0);
  idx = (!(!(((mask >> 15) & x) ^ x)) << 4) + idx;
  shift = 24 + (~idx);
  idx = (!(!(((mask >> shift) & x) ^ x)) << 3) + idx;
  shift = 28 + (~idx);
  idx = (!(!(((mask >> shift) & x) ^ x)) << 2) + idx;
  shift = 30 + (~idx);
  idx = (!(!(((mask >> shift) & x) ^ x)) << 1) + idx;    
  shift = 31 + (~idx);
  idx = !(!(((mask >> shift) & x) ^ x)) + idx;
  return idx + 2;
}
```

- 测试通过展示
```bash
>> ./dlc bits.c
>> ./btest
Score   Rating  Errors  Function
 1      1       0       bitXor
 1      1       0       tmin
 1      1       0       isTmax
 2      2       0       allOddBits
 2      2       0       negate
 3      3       0       isAsciiDigit
 3      3       0       conditional
 3      3       0       isLessOrEqual
 4      4       0       logicalNeg
 4      4       0       howManyBits
 4      4       0       floatScale2
 4      4       0       floatFloat2Int
 4      4       0       floatPower2
Total points: 36/36
```