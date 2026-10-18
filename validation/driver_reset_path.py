#!/usr/bin/env python3
"""Construct a continuous collision-free sampled return/prestroke path.

Selected driver geometry: P=(48,22), E=(69.5,2), tapered nose polygon
[(68,0), (71.5,0), (71,3.5), (68,3.5)].
Planning uses the enclosing old rectangular nose [68,71.5]x[0,3.5]; every
saved node and midpoint is then checked against the actual tapered nose.
The resulting maximum opening is a conservative feasible bound, not the
minimum opening required by the tapered shape.
Gear stays at exactly 36 degrees. Start is s=8.3, opening=0; the drive opening
is limited to 15 degrees. The path is a geometric existence witness, not a
prediction of spring-controlled motion or contact forces. Other assembly parts
are not included in this ratchet-to-driver check.
"""
import csv
import json
from math import ceil
from pathlib import Path
import numpy as np
import shapely
from shapely import affinity
from shapely.geometry import box
from shapely.ops import unary_union
from geometry_helpers import make_pawl, ratchet

OPENING_LIMIT=15.
GEAR_PHASE=36.
ANGLES=np.linspace(0,OPENING_LIMIT,3001)
PIVOT,WHOLE,_=make_pawl('drive')
PLANNER_WHOLE=unary_union([WHOLE,box(68,0,71.5,3.5)])
assert WHOLE.difference(PLANNER_WHOLE).area < 1e-12
GEAR=affinity.rotate(ratchet(),GEAR_PHASE,origin=(0,0)).buffer(-1e-8)
PAWLS=np.array([affinity.translate(affinity.rotate(PLANNER_WHOLE,-a,origin=PIVOT),xoff=-84)
                for a in ANGLES],dtype=object)


def free_intervals(stroke):
    free=~shapely.intersects(affinity.translate(GEAR,yoff=stroke),PAWLS)
    edges=np.diff(np.r_[False,free,False].astype(int))
    return [(float(ANGLES[a]),float(ANGLES[b-1])) for a,b in
            zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1))]


def posed(stroke,opening):
    return affinity.translate(affinity.rotate(WHOLE,-opening,origin=PIVOT),xoff=-84,yoff=-stroke)


if __name__=='__main__':
    lo,hi=3,4.5
    for _ in range(25):
        mid=(lo+hi)/2
        if len(free_intervals(-mid))>1:lo=mid
        else:hi=mid
    path=[(8.3,0.)]
    def append_motion(target_stroke,target_opening):
        start_s,start_a=path[-1]
        count=max(1,ceil(abs(target_stroke-start_s)/.02),ceil(abs(target_opening-start_a)/.05))
        for j in range(1,count+1):
            t=j/count
            path.append((start_s+(target_stroke-start_s)*t,start_a+(target_opening-start_a)*t))
    previous=(0.,OPENING_LIMIT)
    strokes=np.r_[np.linspace(8.3,-4.5,641),np.linspace(-4.5,0,226)[1:]]
    for s in strokes[1:]:
        possible=[iv for iv in free_intervals(float(s))
                  if max(iv[0],previous[0]) <= min(iv[1],previous[1])+.005]
        if not possible:
            raise RuntimeError(f'Disconnected path at stroke {s}')
        current=min(possible,key=lambda iv:iv[0])
        old_s,old_a=path[-1]
        new_a=current[0]
        # Open first, then translate when the clearance requirement increases.
        # Otherwise translate first, then close within the connected free interval.
        if new_a>old_a:
            append_motion(old_s,new_a)
            append_motion(float(s),new_a)
        else:
            append_motion(float(s),old_a)
            append_motion(float(s),new_a)
        previous=current
    # Check every recorded node plus each segment midpoint. Exact tangencies
    # are admitted by the 1e-8 mm inward gear offset used throughout these checks.
    checks=list(path)
    checks.extend(((s0+s1)/2,(a0+a1)/2) for (s0,a0),(s1,a1) in zip(path,path[1:]))
    overlaps=[]
    for i,(s,a) in enumerate(checks):
        if posed(s,a).intersects(GEAR):
            overlaps.append({'sample':i,'stroke_mm':s,'opening_degrees':a})
    csv_path=Path(__file__).with_suffix('.csv')
    with csv_path.open('w',newline='') as stream:
        writer=csv.writer(stream)
        writer.writerow(['sequence','stroke_mm','cw_opening_degrees'])
        writer.writerows((i,s,a) for i,(s,a) in enumerate(path))
    result={
        'status':'TAPERED_DRIVER_VERIFIED_WITH_CONSERVATIVE_RECTANGULAR_PLANNER_15_DEGREE_LIMIT',
        'scope':'Driver-to-ratchet geometric existence path only; other assembly parts, force, friction, springs and tolerances not simulated',
        'actual_nose_polygon_mm':[[68,0],[71.5,0],[71,3.5],[68,3.5]],
        'planner_envelope':'Actual pawl union old rectangular nose [68,71.5] x [0,3.5]',
        'actual_outside_planner_area_mm2':float(WHOLE.difference(PLANNER_WHOLE).area),
        'planner_contains_actual_pawl':bool(WHOLE.difference(PLANNER_WHOLE).area < 1e-12),
        'collision_check_geometry':'Actual tapered pawl WHOLE at every recorded path node and segment midpoint',
        'opening_result_interpretation':'Conservative feasible opening bound; not a minimum required opening for the tapered nose',
        'gear_phase_degrees':GEAR_PHASE,
        'drive_opening_limit_degrees':OPENING_LIMIT,
        'planner_envelope_minimum_extra_return_mm_sampled':hi,
        'selected_home_stroke_mm':-4.5,
        'nominal_extra_return_margin_mm':4.5-hi,
        'opening_search_resolution_degrees':float(ANGLES[1]),
        'path_start':path[0],'path_finish':path[-1],
        'path_node_count':len(path),'checked_nodes_and_midpoints':len(checks),
        'maximum_planned_opening_degrees':max(a for s,a in path),
        'nominal_opening_margin_degrees':OPENING_LIMIT-max(a for s,a in path),
        'maximum_adjacent_opening_change_degrees':max(abs(a1-a0) for (s0,a0),(s1,a1) in zip(path,path[1:])),
        'maximum_adjacent_stroke_change_mm':max(abs(s1-s0) for (s0,a0),(s1,a1) in zip(path,path[1:])),
        'overlap_count':len(overlaps),'overlap_examples':overlaps[:10],
        'path_csv':csv_path.name,
    }
    Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if overlaps:raise SystemExit(1)
