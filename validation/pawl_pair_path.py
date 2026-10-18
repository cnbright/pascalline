from pathlib import Path
import xml.etree.ElementTree as ET
import re,json,csv,hashlib
import numpy as np
from shapely.geometry import Polygon,GeometryCollection
from shapely.affinity import rotate,translate
from shapely.ops import unary_union
D=Path(__file__).resolve().parent
G=D/'section_clearance'
def geom(n):
 g=GeometryCollection()
 for el in ET.parse(G/f'{n}.svg').iter():
  if el.tag.endswith('path'):
   for c in re.split('[Mm]',el.attrib['d'])[1:]:
    nums=[float(s) for s in re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?',c)]
    g=g.symmetric_difference(Polygon([(nums[i],-nums[i+1]) for i in range(0,len(nums),2)]))
 return g
p=geom('drive');s=geom('stop')
stops={float(a):translate(rotate(rotate(s,-a,origin=(-38,-13.5)),-18,origin=(0,0)),xoff=84) for a in np.linspace(0,25,101)}
sweep=unary_union(list(stops.values()))
checks={}
for mode,static in [('stop_closed',stops[0.]),('stop_swept_0_to_25',sweep)]:
 best={'gap_mm':float('inf')};hits=[]
 with (D/'driver_reset_path.csv').open() as f:
  for row in csv.DictReader(f):
   lift=float(row['stroke_mm']);a=float(row['cw_opening_degrees'])
   drive=translate(rotate(p,-a,origin=(48,22)),yoff=-lift)
   gap=drive.distance(static);area=drive.intersection(static).area
   if gap<best['gap_mm']:best={'gap_mm':gap,'lift':lift,'cw_opening_degrees':a,'sequence':int(row['sequence'])}
   if area>1e-4:hits.append({**row,'area_mm2':area})
 checks[mode]={'minimum':best,'overlap_count':len(hits),'overlap_examples':hits[:8]}
# Working stroke and release have driver closed; allow all stop angles conservatively.
best={'gap_mm':float('inf')};hits=[]
for lift in np.linspace(0,10.4,1041):
 drive=translate(p,yoff=-lift);gap=drive.distance(sweep);area=drive.intersection(sweep).area
 if gap<best['gap_mm']:best={'gap_mm':gap,'lift':float(lift)}
 if area>1e-4:hits.append({'lift':float(lift),'area_mm2':area})
checks['working_and_release_driver_closed']={'minimum':best,'overlap_count':len(hits),'overlap_examples':hits[:8]}
result={'source_sha256':hashlib.sha256((D.parent/'pascaline.scad').read_bytes()).hexdigest(),'driver_path_sha256':hashlib.sha256((D/'driver_reset_path.csv').read_bytes()).hexdigest(),'scope':'SCAD-exported pawls at Z14.5. Actual sampled driver return CSV; working and release closed driver. Stop considered both closed and conservative full 0..25deg sweep. No forces/dynamics/tolerances.','checks':checks}
(D/'pawl_pair_path.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
