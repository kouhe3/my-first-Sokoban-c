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
- Rich header 每条记录是 `(product, build)` 与计数。微构建实验（cl + link、不链 CRT）确认
  `0x0104` = cl、`0x0102` = link，计数 = 该 build 的 obj 数：

  | 文件 | cl 条目 | link 条目 |
  | --- | --- | --- |
  | 原版 | `30034 ×13` | `30133 ×1` |
  | 重建（单 TU） | `30034 ×13`（预编译 CRT 库）+ `30159 ×1`（用户 obj） | `30159 ×1` |

  原版**没有任何 30133/30159 的 cl 条目**，说明用户代码由 **cl 19.29.30034**（VS2019 16.10 时代）编译；
  30133 只出现在链接器条目。同一 build 的计数会把用户 obj 与静态库 obj 合并，不能直接当作源文件数。

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
5. 工程形态与函数排布（2026-10-31 新增，尚未定论）：
   - 本机 `VC\Tools\MSVC\14.29.30133\` 目录内实际是 **30159** 二进制；从 2021-09-03 的频道清单
     （`VisualStudio.16.Release.chman` → `VisualStudio.vsman`）下载的**真 30133** 编译器，
     重建结果与 30159 完全相同 → 补丁版本不是函数排序的原因。
   - cl 30040 / 30133 / 30159 都把每个函数写成**按函数名升序**的独立 `.text$mn` COMDAT
     （zebra/yak/main 的 obj 段序为 main, yak, zebra）；`/ORDER` 在 `/INCREMENTAL` 下被忽略（LNK4075），
     增量链接也不会保留 `.ilk` 中的旧顺序；而多 obj 链接按命令行顺序排布。
   - 因此原版 `.text` 的「源码序」只能来自两种工程形态：单文件 + 编译器不排序（cl 30034），
     或一函数一文件。现有证据偏向**单文件**：原版 `.rdata` `0x2491`、`.msvcjmc` `0x11f`
     小于一函数一文件的实测值（`0x25d1` / `0x161`），更接近单文件值（`0x2581` / `0x10a`）。
   - 用 `tools/split_multi_tu.py` 生成一函数一文件后，cl 30133 构建可复现原版函数顺序，
     首函数 `0x411810` vs 原版 `0x4117F0`，各函数地址差 `0x10–0x30`，但 `.rdata`/`.msvcjmc` 变大。
   - 结论：逐字节对齐需要 **cl 19.29.30034** 及其同期 CRT 库，先验证其是否不排序 COMDAT。

---

## 4. 已还原函数与判据

判据（`tools/verify_rebuild.py`）：

1. **指令流比对（符号化地址）**：capstone 反汇编两侧函数体，以最后一条 `ret` 为边界；
   镜像内地址先解析为「符号 + 偏移」（锚点：9 个用户函数与 5 个全局变量），解析不到才退回 `IMG`；
   分支目标与数据引用必须落到同一符号的同一偏移；
2. **块重排例外**：对标记为 `LAYOUT_ONLY` 的函数（当前仅 `handle_input`），允许前一交付约定的顺序差异——
   比较**去除控制流指令（jmp/jcc）与对齐 nop 后的指令多重集**，相等即判定「仅块重排」；
3. 指令序列长度（最后一条 `ret` 之前）一致；
4. 辅以整节字节比对（`.data` raw 与 `.rsrc` 必须完全相同）、Rich header 指纹（cl/link build 与计数）。

| 函数 | 原 VA | 原尺寸 | 指令数 (原/新) | 结论 |
| --- | --- | --- | --- | --- |
| `init_level1` | `0x4117F0` | 963 | 219 / 219 | ✅ 完全一致 |
| `init_level2` | `0x411CD0` | 932 | 217 / 217 | ✅ 完全一致 |
| `init_level0` | `0x4121B0` | 1205 | 263 / 263 | ✅ 完全一致 |
| `handle_input` | `0x4127C0` | 446 | 146 / 146 | ⚠️ 仅块排布不同（then 块位置） |
| `move_and_push` | `0x412A30` | 151 | 51 / 51 | ✅ 完全一致 |
| `move_player` | `0x412AF0` | 179 | 63 / 63 | ✅ 完全一致 |
| `draw_map` | `0x412BD0` | 111 | 38 / 38 | ✅ 完全一致 |
| `count_remaining_boxes` | `0x412C60` | 147 | 48 / 48 | ✅ 完全一致 |
| `main` | `0x412E00` | 534 | 139 / 139 | ✅ 完全一致 |

另：`.data` raw（512 字节）、`.rsrc`（512 字节）逐字节相同；三个 DLL 的导入函数集合完全相同；
所有用户字面量（含 GBK 中文格式串与 33 条关卡模板串）在原版与重建版中字节一致。

`handle_input` 的唯一差异：`if (space||star)` 的 then 块在原版被放在 else-if 之后（测试指令 `je` 直跳尾部），
重建编译器（30040/30133/30159 行为一致）则内联在测试之后。按最后一条 `ret` 定界后两侧均为 165 条指令，
去控制流指令后的多重集完全相同（多 TU 诊断构建亦同），属 §5 允许的**块顺序重排**。

当前验证输出（`python tools/verify_rebuild.py ...`）：

```
toolchain fingerprint (Rich header, build x count):
  original: cl=30034 (30034x13); link=30133 (30133x1)
  rebuilt : cl=30159 (30034x13, 30159x1); link=30159 (30159x1)
  newest cl build identical: False; link build identical: False

init_level1   219/219  MATCH
init_level2   217/217  MATCH
init_level0   263/263  MATCH
handle_input  146/146  LAYOUT-ONLY (block reordered)
move_and_push  51/51   MATCH
move_player    63/63   MATCH
draw_map       38/38   MATCH
count_remaining_boxes 48/48 MATCH
main          139/139  MATCH
symbol-resolved references: 147 branches, 80/81 operands resolved, 278/277 unresolved
.data raw identical: True
.rsrc raw identical: True
RESULT: PASS (layout reordering accepted: handle_input)
```

---

## 5. 已知差异（第 1 次交付允许）

| 差异 | 现象 | 原因 |
| --- | --- | --- |
| 函数在 `.text` 中的位置 | 原版按源码序（init1, init2, init0, handle, push, player, draw, count, main）；重建版按符号名排序 | 原版由 **cl 19.29.30034**（VS2019 16.10）编译；cl 30040/30133/30159 都把 COMDAT 按文件名排序 |
| 所有绝对地址 / `rel32` 位移 | `.text` 差 18962 字节、`.rdata` 差 3192 字节 | 由上一行的重排引起（地址漂移），非代码差异 |
| 节大小 | `.text` `0x6e2a` vs `0x6dd2`；`.rdata` `+0x100`；`.idata` `+0x13`；`.data` `+0x38`；`.reloc` `+0xF` | 重排 + 地址漂移 + 跳转表/字面量池排布 |
| Rich header | cl `30034`（原版）vs `30159`（重建）；link `30133` vs `30159` | 本地 VS2019 的 `14.29.30133` 目录实为 30159 二进制；真 30133 行为相同，故非补丁版本所致 |
| PE 时间戳 / RSDS GUID / age | 每次链接都不同 | 链接期字段 |
| `.msvcjmc` / `.00cfg` 少量字节 | 共 17 / 2 字节不同 | 内含函数地址（JMC 数据、CFG 表） |

这些差异均不含语义变化；`handle_input` 的块顺序已在 §4 说明。

---

## 6. 复现与验证

```bat
rem 1) 在仓库根目录用 v142 (14.29) 工具集编译
rem    注意：本机 VC\Tools\MSVC\14.29.30133 内实际是 30159 二进制
build.bat

rem 2) 指令流 + 符号化引用 + 工具链指纹
uv run --with capstone python tools\verify_rebuild.py ^
  --orig ConsoleApplication1.exe ^
  --rebuilt Debug\ConsoleApplication1.exe ^
  --map Debug\ConsoleApplication1.map

rem 3) 可选：一函数一文件诊断构建（复现原版函数顺序）
python tools\split_multi_tu.py --src ConsoleApplication1.c --out .build\multi

rem 4) 可选：按 build 分组的 Rich header 明细
python tools\msvc_version.py ConsoleApplication1.exe Debug\ConsoleApplication1.exe
```

所需 Python 包：`capstone`。

验证器不再把镜像内地址一律抹成 `IMG`：可解析的引用必须落到同一符号同一偏移，
分支目标与数据引用同时受检；未解析的镜像操作数会计数并标为 `IMG`
（当前实测 147 条分支、两侧 80/81 个操作数被锚定，278/277 个镜像操作数无锚点）。

**获取真 14.29.30133（用于排除补丁版本影响）**：
- Wayback 快照 `aka.ms/vs/16/release/channel`（2021-09-03）返回
  `VisualStudio.16.Release.chman`；其中 `Microsoft.VisualStudio.Manifests.VisualStudio`
  的 payload 即 `VisualStudio.vsman`（约 20 MB）；
- 按包 ID `Microsoft.VC.14.29.16.11.Tools.HostX86.TargetX86.base` 从 `payloads[].url`
  直接下载 `payload.vsix`；另需 `...Res.base,language=en-US`（`clui.dll`）、
  `CRT.Headers.base`、`CRT.x86.Desktop.base`、`CRT.x86.Store.base`（导入库 `msvcrtd.lib` 等）。

实测（2026-10-31）：真 30133 与 30159 的验证结果逐项相同（函数仍按字母序），
确认工具集补丁版本不是差异来源；原版差异指向 cl 19.29.30034 与 16.10 时代的 CRT 库。

验证器升级（2026-10-31）：地址解析改为符号化 + 分支目标检查，函数边界改为「最后一条 `ret`」，
并加入 Rich header 指纹输出。旧版把镜像内地址统一为 `IMG` 且按原函数尺寸硬切窗口，
会把填充区当作代码（多 TU 构建曾因此误报 DIFF）；升级后单文件与一函数一文件构建
在 `handle_input` 上都稳定判为 `LAYOUT-ONLY`。`LAYOUT_ONLY` 判定本身仍会忽略跳转顺序，
因此 `MATCH` / `LAYOUT-ONLY` 只说明代码与引用目标对应，不等于整节字节一致。

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

1. **取得 cl 19.29.30034**（VS2019 16.10.0 初版，2021-05；16.11.2 清单只提供 30040），
   验证它是否**不排序** COMDAT。若成立，单文件源码即可复现原版函数顺序，再处理 `.rdata`/`.idata`；
   当前公开渠道（微软 CDN 旧清单、archive.org ISO）未找到 30034 payload。
2. 若 30034 仍排序，则原工程是一函数一文件：用 `tools/split_multi_tu.py` 搜索文件划分，
   以 `.rdata` / `.msvcjmc` 大小收敛为准。
3. `handle_input` 的块排布：在全函数 165 条指令范围内尝试不同条件写法（合并条件、调整 `else if`），
   复现原版 then 块后置布局。
4. 回填 PE 时间戳与 RSDS GUID/age，核对整文件 SHA-256。
5. 已完成：源码迁回仓库、`build.bat`、符号化验证器、一函数一文件诊断工具。
