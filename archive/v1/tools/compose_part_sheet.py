"""Typeset actual STL renderings; no geometry or manufacturing dimensions changed."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'exports'
font_path = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
bold_path = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
def font(size, bold=False):
    return ImageFont.truetype(bold_path if bold else font_path, size)

parts = json.loads((OUT/'mesh_report.json').read_text())['parts']
labels = ['底座', '数字轮（含棘轮）', '个位凸轮', '进位滑块',
          '驱动拨爪', '止回爪', '法兰轴套', '上盖（可选）']
canvas = Image.new('RGB', (1800, 2200), '#edf2f5')
draw = ImageDraw.Draw(canvas)
ink, muted, accent = '#172e3d', '#5b6d7a', '#0b6470'
draw.text((66,36), '两位帕斯卡计算器 · 打印分件预览', font=font(48,True), fill=ink)
draw.text((68,109), '8 种 STL · 完整版共 11 件 · 去掉上盖为 10 件', font=font(29), fill=muted)
card_w, card_h = 822, 466
for i, (part, label) in enumerate(zip(parts,labels)):
    x = 64 + (i%2)*850
    y = 178 + (i//2)*488
    draw.rounded_rectangle((x,y,x+card_w,y+card_h),radius=20,fill='white',outline='#d9e2e8',width=2)
    draw.text((x+25,y+21), f'{i+1:02d}  {label}', font=font(33,True), fill=ink)
    draw.rounded_rectangle((x+card_w-119,y+19,x+card_w-25,y+70),radius=12,fill='#e6f2f1')
    draw.text((x+card_w-101,y+20),f'×{part["quantity"]}',font=font(33,True),fill=accent)
    draw.text((x+26,y+75),Path(part['file']).name,font=font(26),fill=muted)
    render=Image.open(OUT/'part_previews'/f'{Path(part["file"]).stem}.png').convert('RGBA')
    render.thumbnail((786,300),Image.Resampling.LANCZOS)
    canvas.paste(render,(x+(card_w-render.width)//2,y+110),render)
    def number(n):return f'{n:.2f}'.rstrip('0').rstrip('.')
    dims=' × '.join(number(v) for v in part['size_mm'])
    draw.text((x+26,y+418),f'{dims} mm',font=font(25),fill=muted)
    if i==1:draw.text((x+390,y+418),'盘面朝下，棘轮朝上',font=font(22),fill=muted)
draw.text((68,2147),'当前 V0.1 STL 实际渲染 · 各卡片独立缩放 · 非打印床排版 · 结构修订尚未完成',font=font(25),fill=muted)
canvas.save(OUT/'print_parts_overview.png')
canvas.save(OUT/'print_parts_overview.pdf','PDF',resolution=150)
print(OUT/'print_parts_overview.png')
