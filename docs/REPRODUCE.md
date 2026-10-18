# 在新环境恢复与重建

所有命令从含有 `pascaline.scad`、`AGENTS.md` 的项目目录执行。若项目存放于仓库子目录，先进入该子目录。不要依赖旧机器的 `/workspace/pascaline-v2` 路径；旧报告中的绝对路径仅为历史诊断信息。

## 1. 原样恢复交付文件

```bash
git clone https://github.com/cnbright/pascalline.git
cd pascalline
```

克隆 GitHub 仓库即可得到全部源码、9 个 OBJ、9 个 STL、预览、原交付 ZIP、装配说明、五金清单和证据。没有 Git LFS、外部网格、云端建模服务或私有子模块依赖。私有仓库需新环境登录有读取权限的 GitHub 账号。

```bash
python3 tools/verify_baseline.py
python3 -m unittest discover -s software -v
```

校验器只读：检查 `baseline_manifest.json` 的文件 SHA-256、实际 OBJ 网格、STL/OBJ 精确对应、数量及交付 ZIP 的 CRC 和 OBJ 内容。Python 3.12 为已测试版本。算术测试仅使用标准库，14 项含全部 100×100 两位加法。

## 2. 安装生成依赖

已测试：Python 3.12.14、OpenSCAD 2021.01、NumPy 2.3.5、Shapely 2.2.0、Pillow 12.3.0、Blender 4.3.2。Ubuntu/Debian 可用：

```bash
sudo apt-get update
sudo apt-get install -y openscad python3-venv fonts-noto-cjk fonts-liberation
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
openscad --version
```

无 sudo 时使用环境管理员提供的包安装途径。预览需要额外安装官方 Blender 4.x 并加入 PATH；先运行 `blender --version`。某些发行版 `apt install blender` 仍为 3.x，不适用本预览脚本的 STL 导入 API。Blender 只用于渲染，生成 OBJ 不需要它。中文排版使用 `/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc` 和 `NotoSansCJK-Bold.ttc`。Windows/macOS 可安装同版本工具，但预览字体路径需按系统调整；本次复现验证在 Linux 完成。

CAD 的数字刻字采用 OpenSCAD 默认字体；保留 Liberation Sans，避免缺字或字体替代引起刻字网格差异。

## 3. 在独立目录生成

以下输出目录必须尚不存在；更换路径即可重复运行，不要删除未知用户目录。

```bash
# 九种 STL/OBJ + 七组几何证据
python tools/rebuild.py --output /tmp/pascaline-rebuild --meshes --geometry

# 如果 Blender 4.x 已安装，也可一次性包括分件图
python tools/rebuild.py --output /tmp/pascaline-rebuild-with-preview --meshes --geometry --preview
```

入口会复制当前项目到新目录，记录每一步日志并执行生成脚本；原 checkout 和 `dist` 原交付包不会被重写。结果入口：

- `exports/obj/`：新 OBJ；`exports/parts.csv`：数量；`exports/obj_report.json`：新网格结果。
- `exports/print_parts_overview.png`、`.pdf`：若选 `--preview` 则新生成，否则仍是复制的原预览。
- `rebuild_report.json`：本次真正执行的阶段、依赖、退出状态。
- `geometry_verdict.json`：若选 `--geometry` 则生成的结果摘要及已知独立极限姿态碰撞。
- `saved_baseline/`：移走的原摘要/哈希清单，仅作原版记录，不是本次报告。
- `dist/`：原交付 ZIP，不会自动变成此次新网格的打包文件。

只选 `--preview` 会渲染保存的 STL；只选 `--meshes` 不代表几何验证或预览重画。底层脚本可单独使用，但会原地写文件，且有依赖顺序，见 `validation/README.md`。

## 4. 如何判断复现成功

原样恢复的文件应逐字节匹配清单。重新网格化时，不同 OpenSCAD/CGAL 版本可能改变三角形排列、浮点序列和文件哈希；必须比较尺寸、体积、单体封闭网格、数量及实际几何，不以新文件 SHA 不同直接判定设计改变。报告包含运行时间或本地路径，也可能自然变化。

几何入口会解析 JSON，而不只检查脚本是否退出成功。它保留一项已知限制：驱动爪和止回爪在独立极限开角/高位移组合下可相交，规定路径及手动十位采样另行检查。不得将此写成“全部姿态无碰撞”。

当前几何 helper 含独立尺寸，只对应 CAD SHA-256 `938b2e7983265af279ef11afa5ffce0bac8022f535ac9fe8ba747e4faf517040`。修改 CAD 后，先同步并审查 helper、运动路径和检查范围，才可更新 `tools/rebuild.py` 中支持的哈希；不能只替换哈希来取得通过。

全部检查通过仍不代表已实物打印、无需修孔装配或寿命达标。当前状态始终是未完成实物验证的工程打样文件。
