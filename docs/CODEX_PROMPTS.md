# 可复制的 Codex 接续提示词

先把 `<仓库URL>` 替换为最终上传的仓库地址，把 `<项目目录>` 替换为检出后包含 `AGENTS.md` 与 `pascaline.scad` 的项目目录。若项目位于现有仓库子目录，保留该层目录。远端目标确定后再填写，不假定仓库名称或地址。

以下四段可分别整段复制。重建统一写到独立输出目录；示例 `/tmp/pascaline-rebuild` 已存在时，选择新的空目录，保留其中已有结果。

## 1. 恢复项目并核对基线

```text
请接续帕斯卡两位计算器 V0.2 项目。已有检出时使用当前工作副本；否则先克隆 <仓库URL>，进入 <项目目录>。读取 AGENTS.md、docs/PROJECT_CONTEXT.md、docs/REPRODUCE.md 和 ASSEMBLY.md，先检查当前 Git 状态并保留已有改动。

按仓库说明准备依赖，然后从项目根目录依次运行：
python3 tools/verify_baseline.py
python3 -m unittest discover -s software -v

核对根目录 CAD、保存的 OBJ/STL、验证报告和交付快照的对应关系；archive/v1 仅是历史。若检查失败，查明是环境依赖、文件损坏还是源码变化，报告具体差异，不用重新生成覆盖基线来掩盖失败。给出当前版本、执行结果和接下来可做的工作。分别说明算术、网格、名义几何与实物验证状态；不得将软件或几何通过写成实体运行通过。
```

## 2. 重建独立 OBJ 与零件预览

```text
请在当前检出的 <项目目录> 继续；没有检出时先克隆 <仓库URL> 再进入项目目录。先读 AGENTS.md、docs/PROJECT_CONTEXT.md、docs/REPRODUCE.md，按 requirements.txt 与复现说明准备依赖，并先运行：
python3 tools/verify_baseline.py
python3 -m unittest discover -s software -v

从当前 V0.2 CAD 重建独立打印网格与真实零件预览，使用：
python3 tools/rebuild.py --output /tmp/pascaline-rebuild --meshes --preview

若输出目录已存在，改用新的空目录。重建在副本输出，不覆盖保存的 exports、validation 或 dist 基线。核对九种单零件 OBJ/STL 的毫米尺寸、封闭性和数量，再检查预览是否清楚：数字轮须显示其一体棘轮，标明盘面朝下的打印姿态；图版附文件名、中文名、数量和尺寸，独立缩放时注明非统一比例。交付新输出路径与差异结论，不能把网格预览当成实体照片，也不能宣称已实物验证。
```

## 3. 继续两位机构验证

```text
请使用当前检出的 <项目目录>；没有检出时先克隆 <仓库URL>。读取 AGENTS.md、docs/PROJECT_CONTEXT.md、docs/REPRODUCE.md、ASSEMBLY.md 以及 validation_summary.json，从项目根目录先运行：
python3 tools/verify_baseline.py
python3 -m unittest discover -s software -v

按依赖说明准备几何工具，在独立空目录重建当前几何证据：
python3 tools/rebuild.py --output /tmp/pascaline-rebuild --geometry

结合报告核对 08→09 不提前进位、09→10 只进一档、10→11 不倒退、99→00 正确回绕，以及个位固定升程 −4.5、0、+8.3 mm 时手拨十位的情况。保留独立极限开角可能相碰的记录，区分它与指定工作/回程路径。发现问题时定位具体零件、姿态和源码参数，在新工作版本中修正并只补做受影响的检查；涉及 CAD 改动时再组合 --meshes --geometry --preview 生成新结果，不覆盖交付基线。

根据已有实物记录分析装配和进位可靠性；若没有实物记录，准备按 ASSEMBLY.md 进行的 100 次慢速进位记录表与判定项，明确实测仍未完成。禁止把预设姿态、算术测试或几何可行路径写成实际弹簧机构已经可靠运行。
```

## 4. 可选：开展多位扩展

```text
请在当前检出的 <项目目录> 开展三位机械原型研究；没有检出时先克隆 <仓库URL>。先读 AGENTS.md、docs/PROJECT_CONTEXT.md、docs/REPRODUCE.md 和现有两位装配、验证报告，并运行：
python3 tools/verify_baseline.py
python3 -m unittest discover -s software -v

保留 V0.2 两位交付，在独立的新版本目录开展设计。先检查新增百位后凸轮、滑架、爪和轴向层的空间安排，再明确进位时序、复位和负载假设；不要直接复制两位布局并声称可用。实现可审查的三位 CAD 草案与所需程序改动，重点验证 099→100、199→200、999→000 的连续进位及单轮操作。

按 docs/REPRODUCE.md 在副本中使用 tools/rebuild.py，依据改动选择或组合 --meshes、--geometry、--preview，输出到 /tmp/pascaline-rebuild 或另一个空目录。核对验证脚本确实覆盖新位数，不能拿原两位检查当成三位通过证明。软件已有多位算术能力不代表机械已支持；最终分别交付设计、实际运行的检查、未解决的问题与实体打样验收项目，不宣称物理验证通过。
```
