"""Typeset current standalone manufacturing meshes, with filenames and quantities."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'exports'
def font(size,bold=False):
    return ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-'+('Bold' if bold else 'Regular')+'.ttc',size)
parts=json.loads((OUT/'mesh_report.json').read_text())['parts']
names={'base':'底座','digit_wheel':'数字轮（含棘轮）','units_cam':'个位凸轮','carry_slider':'进位滑架','drive_pawl':'刚性驱动爪','stop_pawl':'刚性止回爪','shaft_spacer':'下法兰轴套','upper_spacer':'上轴向隔圈','top_cover':'上盖（可选）'}
canvas=Image.new('RGB',(2400,1800),'#edf2f5');d=ImageDraw.Draw(canvas)
ink,muted='#172e3d','#5b6d7a'
d.text((64,36),'两位帕斯卡计算器 V0.2 · OBJ 打印分件',font=font(52,True),fill=ink)
d.text((66,112),'9 种文件 / 完整版 13 件 / 无盖版 12 件 · 金属轴套、螺钉、定位柱及弹簧另备',font=font(30),fill=muted)
for i,p in enumerate(parts):
    key=Path(p['file']).stem;x=64+i%3*770;y=196+i//3*494;w,h=744,470
    d.rounded_rectangle((x,y,x+w,y+h),radius=20,fill='white',outline='#d9e2e8',width=2)
    d.text((x+24,y+19),f'{i+1:02d}  {names[key]}',font=font(33,True),fill=ink)
    d.rounded_rectangle((x+w-110,y+18,x+w-24,y+68),radius=12,fill='#e6f2f1')
    d.text((x+w-95,y+18),f'×{p["quantity"]}',font=font(33,True),fill='#0b6470')
    d.text((x+25,y+74),key+'.obj',font=font(27),fill=muted)
    im=Image.open(OUT/'part_previews'/f'{key}.png').convert('RGBA');im.thumbnail((700,300),Image.Resampling.LANCZOS)
    canvas.paste(im,(x+(w-im.width)//2,y+112),im)
    dims=' × '.join(f'{v:.2f}'.rstrip('0').rstrip('.') for v in p['size_mm'])
    d.text((x+24,y+425),dims+' mm',font=font(25),fill=muted)
d.text((66,1720),'独立实体网格渲染 · 各格独立缩放 · 文件单位毫米，导入比例 100% · 试装时按装配说明调整间隙',font=font(28),fill=muted)
canvas.save(OUT/'print_parts_overview.png')
canvas.save(OUT/'print_parts_overview.pdf','PDF',resolution=150)
print(OUT/'print_parts_overview.png')
