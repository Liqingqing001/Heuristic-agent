# AVL 树插入与旋转

## 题目

向 AVL 树插入结点并保持平衡，实现 LL/RR/LR/RL 四种旋转。

## 解题思路（引导，非完整代码）

**递归插入框架**

```
insert(root, key):
    if root == NULL: return 新建结点(key)      // 基线
    if key < root.val: root.left = insert(root.left, key)
    else: root.right = insert(root.right, key)
    更新 root 的高度
    平衡因子 = 左高 - 右高
    若失衡（|平衡因子| > 1）：做对应旋转并返回新根
    return root
```

**四种旋转的伪代码**

- 右旋（LL）：把 `root.left` 上提为新根，`root.left.right` 交接给原根当左孩子。
- 左旋（RR）：把 `root.right` 上提为新根，`root.right.left` 交接给原根当右孩子。
- LR：先对 `root.left` 左旋，再对 `root` 右旋。
- RL：先对 `root.right` 右旋，再对 `root` 左旋。

## 关键点

- 递归写法天然把「旋转后的新根」通过返回值接回父结点，避免断链（见 buglib「树旋转失衡」）。
- 旋转后必须更新高度，顺序是：先更新子结点、再更新当前根。
- 判断用哪个旋转，看失衡方向与插入去向的组合（LL/RR/LR/RL）。
