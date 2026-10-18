# 几何验证的运行方式与范围

这里的检查用于复现 V0.2 名义尺寸的几何结果。它们不是动力学仿真，也不证明打印后会可靠进位。弹簧力、摩擦、材料强度、磨损、加工公差和实物装配仍需另行验证。

## 环境

已使用的环境为 Python 3.12.14、NumPy 2.3.5、Shapely 2.2.0、OpenSCAD 2021.01。Shapely 必须为 2.x，脚本使用其向量化接口。`openscad` 须可在命令行调用；这些脚本不需要 Blender、CadQuery 或联网。

```sh
python -m pip install numpy==2.3.5 shapely==2.2.0
openscad --version
```

## 现行运行顺序

从仓库根目录运行以下命令。使用脚本路径调用，不要改成 `python -m validation...`，当前导入方式没有按包配置。脚本会覆盖 `validation/` 下的同名报告和生成文件。

```sh
python validation/cam_contact.py
python validation/driver_reset_path.py
python validation/stop_setback_candidate.py
python validation/working_stroke.py
python validation/section_clearance.py
python validation/pawl_pair_path.py
python validation/manual_tens_pair.py
```

前四项互相独立。`section_clearance.py` 必须先根据当前 `pascaline.scad` 重新导出截面；`pawl_pair_path.py` 随后读取这些 SVG 和 `driver_reset_path.csv`；`manual_tens_pair.py` 也依赖这些 SVG。首次运行、新环境运行或 CAD 修改后，**不得使用 `--reuse-all-sections` 或 `--reuse-fixed-sections`**。

| 入口 | 检查内容及限制 |
| --- | --- |
| `cam_contact.py` | 通过 OpenSCAD 读取实际凸轮函数，检查二维轮廓与随动头的采样接触。 |
| `driver_reset_path.py` | 固定齿轮在 36°，寻找并检查驱动爪回程路径。按旧矩形鼻包络规划，按当前斜切鼻检查节点和中点；12.35°是保守可行路径峰值，并非最小必要开角。 |
| `stop_setback_candidate.py` | 名称虽有 candidate，当前定义是选定的前缘退让 0.25 mm 止回爪。检查离散相位下的自由区间及其相邻连接，不是连续运动或弹簧跟随证明。 |
| `working_stroke.py` | 给定齿轮角度的工作行程与释放行程二维检查；不求解接触力或钢珠定位力。 |
| `section_clearance.py` | 从当前 CAD 提取若干高度的实际截面，检查指定部件在采样姿态下的间隙。不是所有零件的完整三维碰撞检查。 |
| `pawl_pair_path.py` | 使用已保存的驱动爪回程路径以及闭合爪工作行程，检查两爪之间的间隙。 |
| `manual_tens_pair.py` | 在三个固定滑块位置分别检查十位轮手拨的一齿周期；逐相位选择不穿透角度，不证明这些角度能连续到达或由弹簧自动实现。 |

## 结果解释与复现注意

- 脚本正常退出不等于所有检查通过。必须查看报告字段，例如凸轮的 `sampled_geometry_pass`、路径的 `overlap_count`、工作行程的碰撞数量、止回爪的未连接相位、手拨检查的缺失合法角度及两爪重叠数量。
- 当前 `section_clearance.json` 保留 `drive_tens_stop_swept` 这一独立极限姿态组合的相交结果。它不能被改称为全包络无碰撞；实际给定回程及手拨姿态须结合后两项报告判断。未知的新相交不能按这个已知结果忽略。
- `geometry_helpers.py`、止回爪脚本、工作行程及姿态脚本含有显式尺寸和运动参数；它们不会自动随 SCAD 参数更新。改 CAD 后必须逐项同步核对。报告中的 SCAD 哈希不代表这些硬编码值已经自动校验。
- 配对与手拨脚本只读取 SVG，不自行验证 SVG 是否由当前 CAD 生成。因此仅给报告写入当前源文件哈希，不能防止误用旧截面；运行顺序和禁用复用标志很重要。
- `mechanism_evidence.json` 是设计阶段汇总索引，不是自动运行器。重新运行或换路径后，报告哈希可能变化，需要重新生成或核对索引。`cam_contact.json` 的 `source` 字段会记录本机绝对路径；这个路径不是执行依赖。
- 中途失败可能留下先前报告。自动化重建应使用干净的输出目录或检查本次生成记录，不能把存在的旧 JSON 当作本次成功结果。适合 CI 的统一入口应显式检查结果字段及输入哈希。

## 历史方案

`archive/history/rigid_pawl_contact.py` 保存混合历史脚本：其主入口和止回爪是被否决的方案，驱动爪定义在归档前已更新。**不得把它作为现行验证运行，也不得把重跑结果当作最早方案的严格复现。** 当前依赖已抽出为 `geometry_helpers.py`。

旧项目中的 `rigid_pawl_reset_candidates.*`、`pre_*`、`tail_25deg_*` 等候选分析和快照也不属于现行验证链。历史报告中出现的 `current_source_matches: true` 只描述生成当时，不能说明与当前 CAD 相同。保留历史材料时应放在归档目录并保留原有失败结论。
