# my-first-Sokoban-c
 我的第一个用 c  写的 推箱子



这是我看完了[慕课网上的C语言教程](https://www.imooc.com/learn/249)和[啊哈c语言](https://archive.org/details/aha-c_202108)之后写出来的。

激励我的是书里最后一节那句话

> 如果你是认认真真地一节一节读到这里的，我想你应该可以顺利地完成这个游戏，开启自己独立思考的编程之路

然后，我花了 2 天时间，终于写出来了！

本来想把代码 push 到 GitHub 上做纪念，但因为不当操作被删掉了 qwq .

只留下了这个 exe.

直到我写完这个 README , 我还在质疑：

这真的是小学生计算机兴趣书吗？

---

最初使用 DeepSeek 反编译，当前源码已替换为按原始 EXE 指令流还原的版本。

## 构建与比对

`ConsoleApplication1.c` 使用 **GBK/cp936** 编码，编辑时请保留编码。
需要 MSVC v142 x86 工具集、Windows SDK 和 Python（比对依赖 `capstone`）。
`build.bat` 中的 `vcvarsall.bat` 路径对应当前机器，其他安装位置需调整该路径。

```bat
build.bat
uv run --with capstone python tools\verify_rebuild.py --orig ConsoleApplication1.exe --rebuilt Debug\ConsoleApplication1.exe --map Debug\ConsoleApplication1.map
```

构建产物位于 `Debug/`，不会覆盖根目录的原始 `ConsoleApplication1.exe`。
还原进度及验证边界见 [Reverse.md](Reverse.md)；验证器的 `PASS` 不代表控制流或整文件字节完全一致。
