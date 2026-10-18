from pathlib import Path
import re,xml.etree.ElementTree as ET,json,hashlib
from math import cos,sin,radians
import numpy as np
import shapely
from shapely.geometry import Polygon,GeometryCollection
from shapely.affinity import rotate,translate
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
ratchet=Polygon([(84+r*cos(radians(a)),r*sin(radians(a))) for k in range(10) for r,a in [(11.5,36*k),(17,36*k),(11.5,36*(k+1)-1)]])
phases=np.linspace(0,36,361)
stopangles=np.linspace(0,25,501);driveangles=np.linspace(0,15,301)
def stop(a):return translate(rotate(rotate(s,-a,origin=(-38,-13.5)),-18,origin=(0,0)),xoff=84)
def drive(a,lift):return translate(rotate(p,-a,origin=(48,22)),yoff=-lift)
stopshapes=np.array([stop(a) for a in stopangles],dtype=object)
def minimum_clear(gear,angles,shapes,poser):
 free=~shapely.intersects(gear,shapes)
 if not np.any(free):return None,None
 index=int(np.flatnonzero(free)[0]);hi=angles[index]
 if index==0:return 0.,shapes[0]
 lo=angles[index-1]
 for _ in range(25):
  mid=(hi+lo)/2
  if poser(mid).intersects(gear):lo=mid
  else:hi=mid
 return float(hi),poser(hi)
results=[]
for lift in [8.3,-4.5,0.0]:
 drivshapes=np.array([drive(a,lift) for a in driveangles],dtype=object)
 nodes=[];fail=[];overlap=[];best={'gap_mm':float('inf')}
 for phase in phases:
  gear=rotate(ratchet,float(phase),origin=(84,0)).buffer(-1e-8)
  sa,st=minimum_clear(gear,stopangles,stopshapes,stop)
  da,dr=minimum_clear(gear,driveangles,drivshapes,lambda a:drive(a,lift))
  if sa is None or da is None:
   fail.append({'phase':float(phase),'stop_angle':sa,'drive_angle':da});continue
  gap=dr.distance(st);area=dr.intersection(st).area
  node={'gear_phase':float(phase),'drive_cw_angle':da,'stop_cw_angle':sa,'gap_mm':gap}
  nodes.append(node)
  if gap<best['gap_mm']:best=node
  if area>1e-4:overlap.append({**node,'area_mm2':area})
 results.append({'fixed_slider_lift_mm':lift,'sample_count':len(phases),'missing_legal_angle_count':len(fail),'missing_legal_angle_examples':fail[:12],'max_drive_cw_angle':max([n['drive_cw_angle'] for n in nodes],default=None),'max_stop_cw_angle':max([n['stop_cw_angle'] for n in nodes],default=None),'minimum_pair_gap':best,'pair_overlap_count':len(overlap),'pair_overlap_examples':overlap[:12]})
 (D/f'manual_tens_lift_{lift}.json').write_text(json.dumps({'nodes':nodes,'missing_legal_angles':fail,'pair_overlaps':overlap},indent=2))
report={'source_sha256':hashlib.sha256((D.parent/'pascaline.scad').read_bytes()).hexdigest(),'scope':'SCAD-cut actual pawl footprints; tens manually advances 0..36deg at fixed units lift8.3/-4.5/0. Each pawl uses its minimum nonpenetrating CW opening for each tooth angle. Not a spring/force/continuity proof.','phase_step_deg':.1,'angle_search_step_deg':.05,'angle_refinement_iterations':25,'stop_limit_deg':25,'drive_limit_deg':15,'results':results}
(D/'manual_tens_pair.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
