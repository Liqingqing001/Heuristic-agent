# free/delete 后未置 NULL

## 现象

`free(p)` 之后又对 `p` 判空或再次 `free(p)`，导致重复释放（double free）崩溃；或释放后误以为 `p` 还是空指针继续使用。

## 原因

`free` 只释放内存，**不会改变指针变量的值**。释放后 `p` 仍指向原地址（此时已是悬空指针）。`if (p != NULL)` 这种判断对已释放的 p 依然为真，导致后续误用或二次释放。

## 如何定位

1. 搜索重复的 `free` 调用，看中间是否缺少 `p = NULL`。
2. 检查释放后是否又用 `p == NULL` 做守卫条件。
3. 用 AddressSanitizer 捕获 double-free。

## 预防

养成 `free(p); p = NULL;`（C++ 用 `delete p; p = nullptr;`）的固定习惯；封装析构函数时把指针成员置空。
