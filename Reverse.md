# 逆向重建进展

目标：由 `ConsoleApplication1.exe`（2021-09-02 链接，PDB 已丢失）还原出**可字节对齐重建**的 C 源码与工程配置。

当前为**第 1 次交付**：函数级指令流已对齐；允许「重建导致的顺序重排」差异（见 §5）。

- 原始文件：`ConsoleApplication1.exe`（47104 字节）
  - SHA-256 `ca890eacb4ecc4e431f0c690215b29481221c0a8b4d3c52d6a752967e51391e5`
- 重建工程目录：本仓库根目录（已从 `D:\VS2019\HELLO\ConsoleApplication1` 迁回；旧路径与原版 PDB 内嵌路径一致）
- 重建源码：`ConsoleApplication1.c`（**GBK/cp936 存盘**，原始字节复制）
- 构建入口：`build.bat`，产物写入 `Debug/`；新构建路径与原版不同，可能影响调试信息及布局
- 验证脚本：`tools/verify_rebuild.py`

---

## 1. 源 EXE 事实

### 1.1 PE 结构

| 项 | 值 |
| --- | --- |
| 格式 | PE32 (`0x10b`)，machine `0x14c` (x86)，9 个节 |
| 链接器版本 | **14.29**（VS2019 v142 工具集） |
| 时间戳 | `1630551553` = 2021-09-02 02:59:13 UTC |
| 子系统 | 3 (console)，子系统版本 6.0 |
| DllCharacteristics | `0x8140`（DYNAMIC_BASE / NX_COMPAT / TERMINAL_SERVER_AWARE） |
| ImageBase | `0x400000` |
| 入口点 | `0x00011023` → ILT thunk（增量链接的 `j_start`） |

| 节 | VA | VirtualSize | RawSize | 说明 |
| --- | --- | --- | --- | --- |
| `.textbss` | `0x1000` | `0x10000` | 0 | **/ZI (Edit and Continue) + /INCREMENTAL 的特征** |
| `.text` | `0x11000` | `0x6dd2` | `0x6e00` | 代码 + ILT thunk 区 |
| `.rdata` | `0x18000` | `0x2491` | `0x2600` | 字符串/跳转表 |
| `.data` | `0x1b000` | `0x349c` | `0x200` | 初始化数据 + bss |
| `.idata` | `0x1f000` | `0xb30` | `0xc00` | 导入表 |
| `.msvcjmc` | `0x20000` | `0x11f` | `0x200` | **/JMC 特征** |
| `.00cfg` | `0x21000` | `0x109` | `0x200` | CFG 函数表 |
| `.rsrc` | `0x22000` | `0x43c` | `0x600` | 仅 manifest |
| `.reloc` | `0x23000` | `0x7a2` | `0x800` | 重定位 |

### 1.2 资源

- 仅一项：`RT_MANIFEST`，ID 1，语言 `0x409`，381 字节。
- 内容为链接器默认 manifest（`asInvoker`，379 字节 XML），无图标、无版本信息。
- 重建产物的 `.rsrc` **整节 512 字节逐字节相同**。

### 1.3 导入（Debug 动态 CRT）

| DLL | 函数数 | 关键项 |
| --- | --- | --- |
| `KERNEL32.dll` | 23 | `GetModuleHandleW`、`VirtualQuery`、`QueryPerformanceCounter`… |
| `VCRUNTIME140D.dll` | 8 | `__current_exception`、`memset`、`__vcrt_LoadLibraryExW`… |
| `ucrtbased.dll` | 42 | `strcpy`、`strcpy_s`、`system`、`puts`、`printf` 族、`_getch`、`_initterm`… |

→ **/MDd**；`ucrtbased` 中出现 `strcpy` 说明用户代码用的是不安全版 `strcpy`（不是 `strcpy_s`）。
重建产物导入集合完全一致（23 / 8 / 42，函数名逐一相同）。

### 1.4 全局变量布局（.data）

| 符号 | VA | 初值 | 说明 |
| --- | --- | --- | --- |
| `g_rows` | `0x41B000` | 1 | 行数 |
| `g_player_y` | `0x41B004` | 1 | 玩家 y |
| `g_player_x` | `0x41B008` | 1 | 玩家 x |
| `g_map` | `0x41B150` | 0 | `char[100][100]`，占 `0x2710` 字节 |
| `g_level` | `0x41D860` | 0 | 关卡号 |

- 初始化数据段共 `0x150` 字节；其后是 bss（`g_map`、`g_level`）。
- 重建源码写成 `int g_rows = 1; int g_player_y = 1; int g_player_x = 1;`，`.data` 前 512 字节与原版**完全一致**。
- 三个 int 在 `g_map` 之前、`g_level` 在 `g_map` 之后，与源码声明顺序一致。

### 1.5 字符串 / 格式串（GBK）

| VA | 内容 |
| --- | --- |
| `0x418B30` | `人的坐标 ： %d %d \n\n` |
| `0x418B4C` | `\n 未归位箱子还有 %d 个 \n` |
| `0x418B78` | `你已经玩了3关了`（无换行） |
| `0x418B88` | `pause` |
| `0x419864` | `\n\n 完成！ 按 enter 进入下一关 \n` |
| — | `cls` |

关卡模板为**函数内局部数组** `char tpl[100][100]` 的字面量，`.rdata` 中按 16 字节对齐排布（`0x18B98` 起为关卡 1，`0x18C60` 起为关卡 2，`0x18F10`/`0x19048`… 为关卡 0）。

### 1.6 调试目录 / 工具链指纹

- CodeView (type 2, 90 字节)：`RSDS`，GUID `cbb2294a-2896-4edc-9b01-ea596b77aa64`，age **114**，
  PDB 路径 `D:\VS2019\HELLO\ConsoleApplication1\Debug\ConsoleApplication1.pdb`。
- type 12 `VC_FEATURE`，20 字节。
- Rich header 解出的工具集 build 为 **30133**，部分库为 30034 → VS2019 16.11 v142。

---

## 2. 重建配置

```
cl /nologo /c /ZI /Od /RTC1 /GS /MDd /JMC /W3 ^
   /D WIN32 /D _DEBUG /D _CONSOLE ^
   /FoDebug\ConsoleApplication1.obj ConsoleApplication1.c

link /nologo /DEBUG /INCREMENTAL /MANIFEST:EMBED /subsystem:console ^
     /out:Debug\ConsoleApplication1.exe /pdb:Debug\ConsoleApplication1.pdb ^
     /map:Debug\ConsoleApplication1.map Debug\ConsoleApplication1.obj
```

依据：

- `.textbss` + 入口点为 ILT thunk → `/ZI` + `/INCREMENTAL`；
- `.msvcjmc` 段 + `__CheckForDebuggerJustMyCode` 调用 → `/JMC`；
- `ucrtbased`/`VCRUNTIME140D` → `/MDd`；
- 每个函数都有 `__RTC_CheckStackVars`/`0xCC` 栈填充、`__security_cookie` → `/RTC1` + `/GS`；
- 函数体无优化痕迹（逐语句 load/store）→ `/Od`。

**源码必须以 GBK(cp936) 保存**，否则中文字面量字节与 `.rdata` 对不上（本机系统代码页 936）。

---

## 3. 还原出的源码形态（关键结论）

1. 关卡初始化是**三个独立函数**（不是一份模板 + 参数）：
   `init_level1 / init_level2 / init_level0`，签名均为
   `(char map[][100], int *rows, int *player_y, int *player_x)`；
   函数内部各自持有 `char tpl[100][100]` 局部模板，逐行 `strcpy(map[i], tpl[i])`，
   并把 `*rows / *player_y / *player_x` 写成常量。
   - 关卡 1：11 行，y=5，x=6；关卡 2：10 行（模板有 11 个字面量，第 11 行未使用），y=4，x=3；关卡 0：11 行，y=5，x=8。
   - 循环边界是 `i < *rows`（解引用），不是常量。
2. 地图指针通过参数传递：`handle_input / move_player / move_and_push / draw_map / count_remaining_boxes` 都以 `map` 为首参。
3. `main`：三个独立 `if`（顺序 1 → 2 → 0），没有 `else`；通关用 `getchar()`（不是 `system("pause")`），全局结束才 `system("pause")`。
4. `handle_input`：
   - 先 `char ch = _getch();`，再读 `*player_y / *player_x`（顺序影响 /Od 代码生成）；
   - `switch` 的 case 顺序为 **w, a, s, d**；
   - `beyond_y = new_y + new_y - *player_y;`（`x + x` 形式；写 `2 * x` 会被 30159 编成 `shl`）；
   - `if (map[new_y][new_x] != '#') { ... }` 正条件嵌套（`if (== '#') return;` 会生成 `jne` + 额外 `jmp`）。

---

## 4. 已还原函数与判据

判据（`tools/verify_rebuild.py`）：

1. **指令流归一化比对**：capstone 反汇编两侧函数体，把落在镜像内的绝对地址/跳转目标统一归一为 `IMG`，逐指令比较助记符与操作数结构；
2. **块重排例外**：对标记为 `LAYOUT_ONLY` 的函数（当前仅 `handle_input`），允许前一交付约定的顺序差异——
   比较**去除控制流指令（jmp/jcc）与对齐 nop 后的指令多重集**，相等即判定「仅块重排」；
3. 期望的指令序列长度一致；
4. 辅以整节字节比对（`.data` raw 与 `.rsrc` 必须完全相同）、导入集合比对、字面量字节比对。

| 函数 | 原 VA | 原尺寸 | 指令数 (原/新) | 结论 |
| --- | --- | --- | --- | --- |
| `init_level1` | `0x4117F0` | 963 | 219 / 219 | ✅ 完全一致 |
| `init_level2` | `0x411CD0` | 932 | 217 / 217 | ✅ 完全一致 |
| `init_level0` | `0x4121B0` | 1205 | 263 / 263 | ✅ 完全一致 |
| `handle_input` | `0x4127C0` | 446 | 146 / 147 | ⚠️ 仅块排布不同（多 1 条 `jmp`） |
| `move_and_push` | `0x412A30` | 151 | 51 / 51 | ✅ 完全一致 |
| `move_player` | `0x412AF0` | 179 | 63 / 63 | ✅ 完全一致 |
| `draw_map` | `0x412BD0` | 111 | 38 / 38 | ✅ 完全一致 |
| `count_remaining_boxes` | `0x412C60` | 147 | 48 / 48 | ✅ 完全一致 |
| `main` | `0x412E00` | 534 | 139 / 139 | ✅ 完全一致 |

另：`.data` raw（512 字节）、`.rsrc`（512 字节）逐字节相同；三个 DLL 的导入函数集合完全相同；
所有用户字面量（含 GBK 中文格式串与 33 条关卡模板串）在原版与重建版中字节一致。

`handle_input` 的唯一差异：`if (space||star)` 的 then 块在原版被放在 else-if 之后（测试指令 `je` 直跳尾部），
30159 编译器则内联在测试之后，导致多一条 `jmp`（146 → 147 条）。去控制流指令后的指令多重集完全相同，
语义与指令对应关系一致，属 §5 允许的**块顺序重排**。

当前验证输出（`python tools/verify_rebuild.py ...`）：

```
init_level1   219/219  MATCH
init_level2   217/217  MATCH
init_level0   263/263  MATCH
handle_input  146/147  LAYOUT-ONLY (block reordered)
move_and_push  51/51   MATCH
move_player    63/63   MATCH
draw_map       38/38   MATCH
count_remaining_boxes 48/48 MATCH
main          139/139  MATCH
.data raw identical: True
.rsrc raw identical: True
RESULT: PASS (layout reordering accepted: handle_input)
```

---

## 5. 已知差异（第 1 次交付允许）

| 差异 | 现象 | 原因 |
| --- | --- | --- |
| 函数在 `.text` 中的位置 | 原版按源码序（init1, init2, init0, handle, push, player, draw, count, main）；重建版按符号名排序 | 本机 v142 实际为 **19.29.30159**；/ZI 下 COMDAT 按名字排序。原版为 **30133** |
| 所有绝对地址 / `rel32` 位移 | `.text` 差 18962 字节、`.rdata` 差 3197 字节 | 由上一行的重排引起（地址漂移），非代码差异 |
| 节大小 | `.text` `0x6e2a` vs `0x6dd2`；`.rdata` `+0x100`；`.idata` `+0x13`；`.data` `+0x38`；`.reloc` `+0xF` | 重排 + 地址漂移 + 跳转表/字面量池排布 |
| Rich header | build 30159 vs 30133 | 工具集补丁版本不同 |
| PE 时间戳 / RSDS GUID / age | 每次链接都不同 | 链接期字段 |
| `.msvcjmc` / `.00cfg` 少量字节 | 共 17 / 2 字节不同 | 内含函数地址（JMC 数据、CFG 表） |

这些差异均不含语义变化；`handle_input` 的块顺序已在 §4 说明。

---

## 6. 复现与验证

```bat
rem 1) 在仓库根目录用 v142 (14.29) 工具集编译
build.bat

rem 2) 归一化指令流比对
uv run --with capstone python tools\verify_rebuild.py ^
  --orig ConsoleApplication1.exe ^
  --rebuilt Debug\ConsoleApplication1.exe ^
  --map Debug\ConsoleApplication1.map
```

所需 Python 包：`capstone`。

迁回说明（2026-10-30）：源码与构建入口现已在仓库内。上文 §4 的数字为旧路径产物的历史结果。
现有验证器把镜像内地址统一为 `IMG`，`LAYOUT_ONLY` 判定会删除跳转并忽略指令顺序，
因此 `MATCH` / `LAYOUT-ONLY` 不足以证明引用目标正确或控制流等价；此次迁回未改动验证器逻辑。

迁回后实测：源码与外部版本 SHA-256 均为
`851d6c0a7eb1eaa30f52e7abd269f2848b0d02624659b0149c865b2c9ccf6aa9`。
根目录 `build.bat` 输出 `BUILD_OK`（保留原版 `strcpy`，有三条 C4996 警告）；
上述比对命令输出 8 个 `MATCH`、`handle_input` 为 `146/147 LAYOUT-ONLY`，
`.data` / `.rsrc` raw 均相同，最终 `PASS`。迁回后 `.rdata` rawdiff 为 3192，
其余表中计数与旧路径运行结果相同；此处只记录现有验证器的输出，不提升为等价性证明。
实际运行 `Debug/ConsoleApplication1.exe`：初始坐标 `(5,8)`，未归位箱子为 2；
输入 `w` 后坐标为 `(4,8)`，再输入 `s,d,d` 后坐标为 `(5,10)`，
右侧箱子向右移动一格，尚未到目标点，未归位箱子仍为 2；中文与地图显示正常。

---

## 7. 下一步

1. 取得 **MSVC 14.29.30133**（VS2019 16.11.0）工具集，消除函数排序、Rich header 与少量代码生成差异；
2. 目标：`.text` / `.rdata` 全节字节一致；
3. 回填链接期字段（PE 时间戳、RSDS GUID/age），完成整文件 SHA-256 对齐；
4. 已完成：重建源码迁回本仓库，替换 DeepSeek 反编译版本，并加入根目录 `build.bat`。
