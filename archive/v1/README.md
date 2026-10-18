# 帕斯卡计算器 · 两位工程原型 V0.1

目标是先做一个可观察、可打样的 **00–99 机械加法器**，再扩展位数。当前交付包括参数化 OpenSCAD 模型、独立 STL 零件、Python 计算参考程序，以及把计算结果转换为 CAD 显示状态的配套程序。

本版采用帕斯卡计算器的十进制累加思路，进位机构使用现代简化的凸轮、滑块和棘爪。它不是历史 Pascaline 的等比例复刻。**它是待打样的工程原型：算术程序与 STL 检查不能证明实体能可靠进位。**

2026-10-12 打印适配复查：发现滑块支承高度、细导柱紧固及进位行程余量仍需修正；现版不宜直接全套选择普通树脂下单。详见 [嘉立创适配审查与省钱计划](JLC_PRINT_REVIEW.md)。此次审查未修改 CAD。

## 首版范围

| 项目 | 本版约定 |
| --- | --- |
| 数值范围 | 显示 00–99，个位和十位各 10 档，每档 36° |
| 输入 | 个位前进一档加 1；十位前进一档加 10 |
| 进位 | 设计目标是在个位 9→0 时推动十位前进一档 |
| 溢出 | 99+1 显示 00；程序记录溢出，实体尚无百位或溢出旗 |
| 运算 | 首版只做正向加法；不设计反向借位 |
| 材料假设 | 常见 FDM，0.4 mm 喷嘴；刚性零件 PLA/PETG，弹性爪优先 PETG |
| 五金假设 | 允许少量金属轴、螺钉和外加弹簧/橡皮筋 |
| 扩展 | 软件支持 1–12 位；机械 CAD 当前限定两位，多位传动需另行设计 |

## 文件入口

- `pascaline.scad`：建模源代码，含装配、爆炸、打印排布和独立零件模式。
- `exports/*.stl`：毫米单位的零件网格；装配 STL 只供查看，不整机一体打印。
- `exports/preview.png`：由实际 CAD 网格渲染的预览。
- `exports/exploded.png`：分层爆炸预览。
- `exports/assembly.glb`：可在支持 glTF 的 3D 查看器中旋转查看的装配模型，单位已转为米；制造仍使用毫米单位 STL。
- `exports/mesh_report.json`：各零件尺寸、封闭边、方向和连通性检查。
- `exports/validation_summary.json`：已执行检查、尚未验证项目及源码校验值。
- `simulator.py`：可扩展的十进制计算/进位状态模型。
- `model_pose.py`：计算加法并导出结果对应的两位 CAD 静态姿态。
- `test_simulator.py`：逻辑测试，含全部 100×100 两位加法。
- `tools/export_parts.py`：批量导出 STL 并检查网格，仅依赖 Python 标准库和 OpenSCAD。
- `ASSEMBLY.md`：零件、装配、调试和后续扩展说明。

## 打开和导出模型

安装 OpenSCAD 2021.01 或更新版本，打开 `pascaline.scad`。默认显示装配图，按 F5 预览；F6 完成几何运算后可导出。

在文件顶部或自定义面板切换 `part`：`assembly` 为装配图，`exploded` 为爆炸图，`print` 为打印排布。需要单独导出时使用文件顶部 `// @export` 中列出的零件名称。

命令行批量导出：

```bash
cd pascaline-v1
python3 tools/export_parts.py
```

例如只重新导出凸轮与滑块：

```bash
python3 tools/export_parts.py --parts units_cam carry_slider
```

从顶部观察，程序的正向角度为逆时针；两轮使用相同方向。数字沿相反方向排布，以保证每次正转 36° 读数增加一。改变 `units_angle`、`tens_angle` 可观察不同姿态。装配视图中的十位角度是显示状态输入，**不会通过刚体接触自动求解**。

## 运行配套程序

Python 3.10 或更新版本，无第三方依赖。

```bash
python3 simulator.py --digits 2 --start 8 --add 7
python3 simulator.py --digits 2 --start 99 --add 1
python3 simulator.py --digits 3 --start 99 --add 1
python3 -m unittest -v test_simulator.py
```

结果分别为 `15`、`00`（溢出 1 次）和 `100`。JSON 中的 `wheel_step` 是一档拨动，`carry` 是实际 9→0 引发的进位，`overflow` 表示超过当前最高位。轮位索引 0=个位，1=十位。`overflow_count` 是本次操作的溢出次数，`total_overflow_count` 是自构造或最近一次 `reset` 以来的累计次数。

`add` 接受 0–9999 的整数，按十进制分轮输入；例如两位版加 127，相当于个位拨 7 档，再拨十位 12 档。程序会保留每一次实际进位事件。负数、小数和越界初值会被拒绝。

程序与 CAD 的连接：

```bash
python3 model_pose.py --start 8 --add 7 --output exports/pose_15.csg
```

用 OpenSCAD 打开生成的 `pose_15.csg`，可查看带盖板指针的读数 15 装配状态；同名 JSON 保存输入、结果和进位事件。首版试验台左轮是个位 UNITS，右轮是十位 TENS，应先读十位再读个位；此例左 5、右 1。这是**最终显示姿态**，不包含摩擦、接触、弹性或连续运动求解。机械 CAD 仍为两位，因此 `model_pose.py` 固定使用两位。

Python API：

```python
from simulator import Pascaline

machine = Pascaline(digits=2, start=9)
step = machine.advance(wheel=0)
assert step.display == "10"
print(step.to_dict()["events"])
```

`reset()` 是软件状态装载，不代表实体有一键归零机构。实体应继续正向拨到 00；不要强行反转止回棘轮。

## 验证边界

已经执行的算术测试覆盖 10,000 组两位加法、连锁进位、溢出、单轮拨动、非法参数和事件回放。网格检查检查每个打印件是否封闭、边是否成对、法向方向是否一致，以及是否为单个连通实体。

未执行实际打印、力学仿真、寿命试验和实物进位试验。装配尺寸和凸轮运动采用设计值，拨爪能否在负载下完成一档推进且不重复进位，须依照 `ASSEMBLY.md` 的步骤验证。应先验证单次进位，再考虑外壳美化、缩小尺寸与多位扩展。
