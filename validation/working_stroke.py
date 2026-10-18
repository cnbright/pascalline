"""Prescribed rigid work/release path; this is not a contact-force simulation."""
import json, math, hashlib
from pathlib import Path
import numpy as np
from shapely.affinity import rotate, translate
from geometry_helpers import make_pawl, ratchet
ROOT=Path(__file__).resolve().parents[1]
_,pawl,_=make_pawl('drive')
work_bad=[];release_bad=[];areas=[]
for s in np.linspace(0,10.4,1041):
    theta=math.degrees(math.atan2(s,12.5))
    gear=rotate(ratchet(),theta,origin=(0,0))
    moved=translate(pawl,xoff=-84,yoff=-s)
    area=moved.intersection(gear).area;areas.append(area)
    if area>1e-6:work_bad.append([float(s),theta,area])
for s in np.linspace(8.3,10.4,211):
    theta=max(36,math.degrees(math.atan2(s,12.5)))
    area=translate(pawl,xoff=-84,yoff=-s).intersection(rotate(ratchet(),theta,origin=(0,0))).area
    if area>1e-6:release_bad.append([float(s),theta,area])
r={'scope':'Nominal prescribed 2D work/release path; no spring, friction or detent-force simulation',
   'source_sha256':hashlib.sha256((ROOT/'pascaline.scad').read_bytes()).hexdigest(),
   'work_samples':1041,'release_samples':211,'maximum_work_overlap_mm2':max(areas),
   'work_collision_count':len(work_bad),'release_collision_count':len(release_bad),
   'overlap_examples':(work_bad+release_bad)[:5],
   'nominal_peak_angle_deg':math.degrees(math.atan2(10.4,12.5)),
   'assumed_max_contact_radius_mm':12.75,'assumed_total_stroke_loss_mm':.7,
   'minimum_angle_under_assumptions_deg':math.degrees(math.atan2(9.7,12.75)),
   'tolerance_note':'Conditional geometry budget only; actual aggregate play/loss must be measured.'}
Path(__file__).with_suffix('.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
assert not work_bad and not release_bad
