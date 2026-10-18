from pathlib import Path
import subprocess, re, json, hashlib, sys
from concurrent.futures import ThreadPoolExecutor
import xml.etree.ElementTree as ET
import numpy as np
from shapely.geometry import Polygon, GeometryCollection
from shapely.affinity import translate,rotate
D=Path(__file__).resolve().parent
S=D.parent/'pascaline.scad'
SNAP=D/'clearance_snapshot.scad'
SNAP.write_bytes(S.read_bytes())
OUT=D/'section_clearance'
OUT.mkdir(exist_ok=True)
jobs=[]
levels=[6.5,9.5,11.5,13.75,14.5,17.25,19.5]
for z in levels:
 jobs.extend([(f'base_{z}',f'translate([0,0,{-z}])base();'),(f'slider_{z}',f'translate([0,0,{6-z}])carry_slider();')])
jobs.extend([('drive','translate([0,0,-1])drive_pawl();'),('stop','translate([0,0,-1])stop_pawl();')])
def export(job):
 name,body=job
 scad=OUT/f'{name}.scad';svg=OUT/f'{name}.svg'
 scad.write_text('use <../clearance_snapshot.scad>\nprojection(cut=true) '+body+'\n')
 # Reuse flags are only valid after independently verifying unchanged section geometry.
 if '--reuse-all-sections' not in sys.argv and ('--reuse-fixed-sections' not in sys.argv or name.startswith('slider_') or not svg.exists()):
  p=subprocess.run(['openscad','-o',str(svg),str(scad)],capture_output=True,text=True)
  (OUT/f'{name}.log').write_text(p.stdout+p.stderr)
 if not svg.exists():
  if 'empty' in p.stderr.lower():return name,GeometryCollection()
  raise RuntimeError((name,p.stderr))
 polys=[]
 for el in ET.parse(svg).iter():
  if not el.tag.endswith('path'):continue
  for contour in re.split('[Mm]',el.attrib.get('d',''))[1:]:
   nums=[float(s) for s in re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?',contour)]
   points=[(nums[i],-nums[i+1]) for i in range(0,len(nums),2)]
   if len(points)>2:polys.append(Polygon(points))
 result=GeometryCollection()
 for p in polys:result=result.symmetric_difference(p)
 if (name in ('drive','stop') or name.startswith('base_')) and (result.is_empty or not result.is_valid):
  raise RuntimeError(f'Empty/invalid required section: {name}')
 return name,result
geoms=dict(ThreadPoolExecutor(max_workers=4).map(export,jobs))
collisions=[]; mins={}
lifts=np.linspace(-4.5,10.4,299)
angles=np.linspace(0,-25,51)
def check(key,a,b,meta):
 dist=a.distance(b)
 if key not in mins or dist<mins[key]['gap_mm']:mins[key]={'gap_mm':dist,**meta}
 area=a.intersection(b).area
 if area>1e-4:
  old=next((x for x in collisions if x['pair']==key),None)
  if old is None:collisions.append({'pair':key,'max_overlap_area_mm2':area,**meta,'bounds':a.intersection(b).bounds})
  elif area>old['max_overlap_area_mm2']:old.update({'max_overlap_area_mm2':area,**meta,'bounds':a.intersection(b).bounds})
for z in levels:
 base=geoms[f'base_{z}'];slider=geoms[f'slider_{z}']
 for lift in lifts:
  sl=translate(slider,yoff=-lift)
  check(f'base_slider_z{z}',base,sl,{'lift':float(lift),'z':z})
 if 14<=z<17:
  for a in angles:
   drive=rotate(geoms['drive'],a,origin=(48,22))
   st=rotate(geoms['stop'],a,origin=(-38,-13.5))
   for i,x in enumerate([0,84]):
    stop=translate(rotate(st,-18,origin=(0,0)),xoff=x)
    check(f'base_stop{i}',base,stop,{'open_angle':float(a),'z':z})
    for lift in lifts:
     check(f'slider_stop{i}',translate(slider,yoff=-lift),stop,{'open_angle':float(a),'lift':float(lift),'z':z})
   if a>=-15:
    check('drive_slider',drive,slider,{'drive_angle':float(a),'z':z})
    for lift in lifts:
     check('base_drive',base,translate(drive,yoff=-lift),{'open_angle':float(a),'lift':float(lift),'z':z})
from shapely.ops import unary_union
stops_sweep=unary_union([translate(rotate(rotate(geoms['stop'],a,origin=(-38,-13.5)),-18,origin=(0,0)),xoff=84) for a in angles])
for a in np.linspace(0,-15,31):
 for lift in lifts:
  check('drive_tens_stop_swept',translate(rotate(geoms['drive'],a,origin=(48,22)),yoff=-lift),stops_sweep,{'drive_angle':float(a),'lift':float(lift),'z':14.5})
report={'source_sha256':hashlib.sha256(SNAP.read_bytes()).hexdigest(),'current_source_matches':S.read_bytes()==SNAP.read_bytes(),'scope':'SCAD horizontal sections at constant topology layers; samples cover independent drive angles 0..15deg and stop angles 0..25deg and lifts -4.5..10.4. Geometry only, intended tangent contacts use 1e-4 mm2 overlap tolerance.','collisions':collisions,'minimum_distances':mins}
report['independent_envelope_note']='The drive/stop swept-envelope collision combines independently maximal opening and lift. See pawl_pair_path.json and manual_tens_pair.json for the actual prescribed path and manual tens checks; no claim is made that arbitrary manual pawl opening is collision-free.'
report['prescribed_path_evidence']='pawl_pair_path.json'
report['manual_tens_evidence']='manual_tens_pair.json'
(D/'section_clearance.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
