#!/usr/bin/env python3
"""Engineering illustrations from the existing OpenSCAD SVG projections.

SVG paths preserve the actual model outlines; arrows illustrate prescribed
motion and do not represent a solved elastic-contact simulation.
"""
from pathlib import Path
import math
import re
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch, Circle, Arc, Rectangle, FancyArrowPatch
from matplotlib.transforms import Affine2D
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

ROOT = Path(__file__).resolve().parent
font = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
font_manager.fontManager.addfont(font)
plt.rcParams.update({'font.family': font_manager.FontProperties(fname=font).get_name(),
                     'axes.unicode_minus': False, 'svg.fonttype': 'path',
                     'pdf.fonttype': 42, 'font.size': 11})
INK='#163544'; MUTED='#617683'; LIGHT='#dce5e9'; BG='#f8fafb'
CAM='#ebbc59'; SLIDER='#8abed7'; DRIVE='#e87548'; STOP='#399584'; WHEEL='#e4e9eb'


def load_path(name):
    tree=ET.parse(ROOT/'source'/f'{name}.svg')
    vertices=[]; codes=[]
    for node in tree.iter('{http://www.w3.org/2000/svg}path'):
        tokens=re.findall(r'[MLZmlz]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?',node.attrib['d'])
        i=0; command=None; first=None
        while i<len(tokens):
            if tokens[i] in ('M','L','z','Z'):
                command=tokens[i]; i+=1
                if command.lower()=='z':
                    vertices.append(first); codes.append(MPath.CLOSEPOLY)
                    continue
            x,y=float(tokens[i]),-float(tokens[i+1]); i+=2  # OpenSCAD SVG reverses Y
            vertices.append((x,y)); codes.append(MPath.MOVETO if command=='M' else MPath.LINETO)
            if command=='M': first=(x,y); command='L'
    return MPath(vertices,codes)


PATHS={name:load_path(name) for name in ['ratchet_section','units_cam','carry_slider','drive_pawl','stop_pawl']}


def part(ax,name,color,x=0,y=0,angle=0,lw=1.1,alpha=1,z=3):
    patch=PathPatch(PATHS[name],facecolor=color,edgecolor=INK,lw=lw,alpha=alpha,
                    transform=Affine2D().rotate_deg(angle).translate(x,y)+ax.transData,zorder=z)
    ax.add_patch(patch)
    return patch


def arrow(ax,a,b,color=INK,width=1.3,style='-|>',size=11):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle=style,mutation_scale=size,
                                color=color,lw=width,zorder=20))


def arc_arrow(ax,center,r,a1,a2,color=INK):
    theta=np.deg2rad(np.linspace(a1,a2,70))
    points=np.column_stack((center[0]+r*np.cos(theta),center[1]+r*np.sin(theta)))
    ax.plot(points[:,0],points[:,1],color=color,lw=1.7,zorder=20)
    arrow(ax,points[-5],points[-1],color,width=1.7,size=12)


def note(ax,text,xy,xytext,align='left',color=INK):
    ax.annotate(text,xy,xytext=xytext,ha=align,va='center',fontsize=10,color=color,
                arrowprops=dict(arrowstyle='-',lw=.95,color=color,
                                connectionstyle='angle,angleA=0,angleB=90,rad=0'),zorder=21)


def dimh(ax,x1,x2,y,label,base_y=0):
    ax.plot([x1,x1],[base_y,y+1],color=MUTED,lw=.7)
    ax.plot([x2,x2],[base_y,y+1],color=MUTED,lw=.7)
    arrow(ax,(x1,y),(x2,y),color=MUTED,style='<->',width=.9,size=10)
    ax.text((x1+x2)/2,y+1,label,ha='center',va='bottom',color=INK,fontsize=11,
            bbox=dict(facecolor=BG,edgecolor='none',pad=1))


def setup(ax,lim):
    ax.set_xlim(lim[0],lim[1]); ax.set_ylim(lim[2],lim[3]); ax.set_aspect('equal'); ax.axis('off')


def header(fig,title,subtitle):
    fig.text(.045,.951,title,fontsize=24,color=INK,weight='bold')
    fig.text(.046,.910,subtitle,fontsize=11.5,color=MUTED)
    fig.add_artist(plt.Line2D([.045,.955],[.891,.891],transform=fig.transFigure,color=LIGHT,lw=1))


def top_view():
    fig=plt.figure(figsize=(15,10),facecolor=BG)
    header(fig,'进位棘轮 · 俯视剖示','依据现有 V0.1 模型导出轮廓｜隐藏上方数字盘，在棘轮底面以上 1 mm 处剖切｜单位 mm')
    ax=fig.add_axes([.03,.22,.65,.65]); setup(ax,(-30,33,-24,25))
    part(ax,'ratchet_section',WHEEL,lw=1.6)
    for radius in (11.5,16): ax.add_patch(Circle((0,0),radius,fill=False,ec=MUTED,lw=.8,ls=(0,(4,4)),zorder=4))
    ax.plot([-18,18],[0,0],color=MUTED,lw=.55,ls='-.',zorder=4); ax.plot([0,0],[-18,18],color=MUTED,lw=.55,ls='-.',zorder=4)
    dimh(ax,-16,16,20,'齿顶圆 Ø32')
    note(ax,'齿根圆 Ø23',(-9,-7),(-26,-14))
    note(ax,'轴孔 Ø4.4',(1.5,1.5),(20,10))
    note(ax,'传动销盲孔 Ø3.8',(-7,1.9),(-27,11.5))
    ax.plot([11.5,16],[0,0],color=DRIVE,lw=3.5,zorder=10)
    note(ax,'径向工作齿面',(14.2,0),(20,-8),color=DRIVE)
    ax.plot([16,9.42024],[0,6.59612],color=STOP,lw=3,zorder=10)
    note(ax,'回程让齿斜面',(12.8,3.2),(20,2),color=STOP)
    for a in (72,108):
        p=np.array([math.cos(math.radians(a)),math.sin(math.radians(a))]); ax.plot([p[0]*4,p[0]*10],[p[1]*4,p[1]*10],color=MUTED,lw=.8,zorder=4)
    ax.add_patch(Arc((0,0),15,15,theta1=72,theta2=108,ec=INK,lw=1.1,zorder=4))
    ax.text(0,8.7,'36°',ha='center',fontsize=11,color=INK)
    arc_arrow(ax,(0,0),19,204,261,DRIVE)
    ax.text(-5,-21,'正转：俯视逆时针',ha='center',color=DRIVE,fontsize=11)
    fig.text(.714,.821,'当前模型尺寸',fontsize=15,weight='bold',color=INK)
    rows=[('齿数 / 单步角度','10 齿 / 36°'),('棘轮厚度','4 mm'),('齿顶 / 齿根','Ø32 / Ø23 mm'),('中心轴孔','Ø4.4 mm'),('上层数字盘','Ø70 mm'),('一体轮件总厚度','11 mm')]
    for i,(key,val) in enumerate(rows):
        y=.772-i*.048
        fig.text(.714,y,key,fontsize=11,color=MUTED)
        fig.text(.951,y,val,fontsize=11,color=INK,ha='right')
    side=fig.add_axes([.705,.255,.258,.21]); setup(side,(-44,48,-3,17))
    side.text(-39,15,'层叠位置示意',fontsize=12,color=INK,weight='bold')
    outline=[(-16,0),(16,0),(16,4),(9,4),(9,7),(35,7),(35,11),(-35,11),(-35,7),(-9,7),(-9,4),(-16,4),(-16,0)]
    side.add_patch(PathPatch(MPath(outline,[1]+[2]*11+[79]),facecolor=WHEEL,edgecolor=INK,lw=1.1))
    side.add_patch(Rectangle((-2.2,0),4.4,11,fc=BG,ec=INK,lw=.8))
    side.add_patch(Rectangle((-16,0),32,4,fc=CAM,ec=INK,lw=.8))
    side.add_patch(Rectangle((-2.2,0),4.4,4,fc=BG,ec=INK,lw=.8))
    arrow(side,(40,0),(40,11),MUTED,style='<->',width=.8,size=8)
    side.text(43,5.5,'11',va='center',fontsize=9,color=MUTED)
    side.text(-34,8.5,'数字盘',fontsize=9,color=INK)
    side.text(20,1.2,'棘轮 4',fontsize=9,color=INK)
    fig.text(.714,.226,'棘轮、轮毂、数字盘为同一个打印件。',fontsize=10,color=MUTED)
    fig.text(.047,.152,'读图说明',fontsize=13,color=INK,weight='bold')
    fig.text(.047,.110,'• 本图不是完整轮件外观；真正从上方看，Ø70 数字盘会遮住棘轮。',fontsize=11,color=INK)
    fig.text(.047,.074,'• 两个 Ø3.8 盲孔深 3.6 mm，用于个位凸轮连接；十位共用同一轮件，销孔不使用。',fontsize=11,color=INK)
    fig.text(.047,.032,'PASCALINE V0.1  ·  工程原型  ·  轮廓来自 pascaline.scad，尺寸标注不代表实物验证',fontsize=9,color=MUTED)
    return fig


def lift(angle):
    phase=angle%360; h=12.5*math.tan(math.radians(36)); ease=lambda t:t*t*(3-2*t)
    return h*(1-ease(phase/36)) if phase<=36 else h*ease((phase-324)/36) if phase>=324 else 0


def mechanism(ax,units_angle,tens_angle,stage):
    h=lift(units_angle)
    setup(ax,(-50,125,-64,49))
    part(ax,'units_cam',CAM,angle=units_angle,z=2)
    part(ax,'carry_slider',SLIDER,y=-h,z=3)
    # Only the tens ratchet is shown; the units wheel is rigidly joined to the cam.
    part(ax,'ratchet_section',WHEEL,x=84,angle=tens_angle,z=4)
    part(ax,'drive_pawl',DRIVE,y=-h,z=6)
    part(ax,'stop_pawl',STOP,x=84,angle=-18,z=5)  # omit the units stop pawl for clarity
    for x in (28,48):
        ax.add_patch(Circle((x,-34-12.5*math.tan(math.radians(36))/2),1.7,fc=BG,ec=MUTED,lw=.8,zorder=8))
    # Hardware spring is diagrammatic, as in the CAD assembly.
    ax.plot([61,61],[24-h,36],color=STOP,lw=1.6,ls=(0,(2,2)),zorder=9)
    for y in (24-h,36): ax.add_patch(Circle((61,y),1.3,fc=STOP,zorder=9))
    for x in (0,84):
        ax.plot([x-3,x+3],[0,0],color=MUTED,lw=.6,zorder=12)
        ax.plot([x,x],[-3,3],color=MUTED,lw=.6,zorder=12)
    ax.text(0,42,'个位凸轮',ha='center',color=INK,fontsize=11)
    ax.text(84,42,'十位棘轮',ha='center',color=INK,fontsize=11)
    ax.text(60,39,'复位弹簧',ha='center',color=STOP,fontsize=8)
    if stage==0:
        note(ax,'驱动拨爪',(68,11),(91,26),color=DRIVE)
        note(ax,'止回爪',(80,-12),(95,-30),color=STOP)
        ax.text(25,-59,'滑架处于原位',color='#33789b',ha='center',fontsize=10)
    elif stage==1:
        arc_arrow(ax,(0,0),35,116,152,DRIVE)
        ax.text(-23,32,'+36°',ha='center',color=DRIVE,fontsize=10)
        arc_arrow(ax,(84,0),21,68,104,DRIVE)
        ax.text(84,28,'+36°＝+1',ha='center',color=DRIVE,fontsize=11)
        arrow(ax,(112,3),(112,-11),DRIVE,width=2,size=14)
        ax.text(115,-4,'9.08\nmm',va='center',fontsize=10,color=DRIVE)
        ax.add_patch(Circle((71.5,-h),1.5,fill=False,ec=DRIVE,lw=1.6,zorder=20))
        ax.text(26,-59,'工作行程：滑架向下',color=DRIVE,ha='center',fontsize=10)
    else:
        arrow(ax,(112,-11),(112,3),STOP,width=2,size=14)
        ax.text(114,-4,'复位',va='center',fontsize=10,color=STOP)
        arrow(ax,(66,8),(58,8),DRIVE,width=1.8,size=12)
        ax.text(57,14,'外挠',fontsize=9,ha='center',color=DRIVE)
        ax.text(89,27,'十位保持 1',fontsize=11,ha='center',color=STOP)
        ax.text(25,-59,'回程：滑架向上',color=STOP,ha='center',fontsize=10)


def principle():
    fig=plt.figure(figsize=(21,11),facecolor=BG)
    header(fig,'进位机构 · 工作原理','示例：09 → 10 → 11｜左轴为个位，右轴为十位｜俯视；隐藏数字盘与底座，叠合显示不同高度的零件')
    for i,(label,color) in enumerate([('个位凸轮',CAM),('滑架 / 圆头从动件',SLIDER),('驱动拨爪',DRIVE),('止回爪',STOP),('十位棘轮',WHEEL)]):
        x=.045+i*.18
        fig.add_artist(Rectangle((x,.857),.012,.016,transform=fig.transFigure,fc=color,ec=INK,lw=.6))
        fig.text(x+.017,.859,label,fontsize=11,color=INK)
    stages=[('01  进位前 · 09',324,0,
             '个位停在 9，凸轮处于低位。\n驱动拨爪准备抵住十位的工作齿面。'),
            ('02  个位 9→0 · 变为 10',360,36,
             '凸轮推动滑架下移约 9.08 mm。\n驱动拨爪推齿，十位逆时针转 36°。'),
            ('03  个位 0→1 · 变为 11',396,36,
             '弹簧拉回滑架；驱动拨爪需外挠越齿。\n止回爪阻止倒转，十位保持不动。')]
    for i,(title,u,t,caption) in enumerate(stages):
        x=.033+i*.325
        fig.text(x+.01,.801,title,fontsize=17,weight='bold',color=INK)
        ax=fig.add_axes([x,.337,.307,.429]); mechanism(ax,u,t,i)
        fig.text(x+.01,.286,caption,fontsize=12,color=INK,linespacing=1.8)
        if i<2: fig.add_artist(plt.Line2D([x+.315,x+.315],[.278,.82],transform=fig.transFigure,color=LIGHT,lw=1))
    fig.add_artist(plt.Line2D([.045,.955],[.238,.238],transform=fig.transFigure,color=LIGHT,lw=1))
    fig.text(.046,.191,'关键分工',fontsize=14,weight='bold',color=INK)
    fig.text(.143,.192,'驱动拨爪负责“向前推一齿”；止回爪负责“回程时不倒转”。',fontsize=14,color=INK)
    fig.text(.046,.133,'省略个位止回爪。层高：凸轮 Z=6–10，棘轮 Z=12–16，棘爪 Z=12–15 mm；投影重叠不表示同层。',fontsize=11,color=MUTED)
    fig.text(.046,.090,'第三幅显示回程终点；橙色箭头表示回程期间需要的外挠方向，并非已求解的弹性形状。',fontsize=11,color=MUTED)
    fig.text(.046,.046,'原理示意 · 9.08 mm 为设计行程；弹性越齿、摩擦与连续进位可靠性仍需实体打样验证。',fontsize=11,color=INK)
    return fig


if __name__=='__main__':
    figures=[('ratchet_top_view',top_view()),('carry_principle',principle())]
    with PdfPages(ROOT/'ratchet_and_carry_drawings.pdf') as pdf:
        for name,fig in figures:
            fig.savefig(ROOT/f'{name}.png',dpi=180,facecolor=BG)
            fig.savefig(ROOT/f'{name}.svg',facecolor=BG)
            pdf.savefig(fig,facecolor=BG)
            plt.close(fig)
    print('Saved two PNG/SVG drawings and a two-page PDF.')
