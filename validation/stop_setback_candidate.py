#!/usr/bin/env python3
"""Planar check for the selected stop with 0.25 mm front-face setback."""
import json
from pathlib import Path
import numpy as np
import shapely
from shapely import affinity
from shapely.geometry import Point, box
from shapely.ops import unary_union
from geometry_helpers import ratchet, capsule

p=(-38,-13.5)
tail=(-45,-13.5)
pieces={
    'nose':box(-3,-21.75,-.25,-12.5),
    'beam':unary_union([capsule(p,(-20,-20)),capsule((-20,-20),(-3,-20))]),
    'pivot':Point(p).buffer(5.5,quad_segs=32),
    'tail':unary_union([capsule(p,tail),Point(tail).buffer(3,quad_segs=32)]),
}
whole=unary_union(list(pieces.values()))


def pose(g,a):
    return affinity.rotate(affinity.rotate(g,-a,origin=p),-18,origin=(0,0))


if __name__=='__main__':
    angles=np.linspace(0,25,1251)
    phases=np.linspace(0,36,721)
    pawls=np.array([pose(whole,a) for a in angles],dtype=object)
    gear=ratchet().buffer(-1e-8)
    gears=np.array([affinity.rotate(gear,a,origin=(0,0)) for a in phases],dtype=object)
    free=~shapely.intersects(gears[:,None],pawls[None,:])
    minima=[]
    nonmonotonic=[]
    non_nose=[]
    previous=(0.,25.)
    disconnected=[]
    path_minima=[]
    for i,phase in enumerate(phases):
        indices=np.flatnonzero(free[i])
        if not len(indices):
            raise RuntimeError(f'No free opening at phase {phase}')
        first=int(indices[0])
        minima.append(float(angles[first]))
        if np.any(~free[i,first:]):
            nonmonotonic.append(float(phase))
        if first:
            for name,g in pieces.items():
                if name!='nose' and pose(g,angles[first-1]).intersects(gears[i]):
                    non_nose.append((float(phase),name))
                    break
        edges=np.diff(np.r_[False,free[i],False].astype(int))
        intervals=[(float(angles[a]),float(angles[b-1])) for a,b in
                   zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1))]
        candidates=[iv for iv in intervals if max(iv[0],previous[0])<=min(iv[1],previous[1])+.02]
        if not candidates:
            disconnected.append(float(phase))
        else:
            previous=min(candidates,key=lambda iv:iv[0])
            path_minima.append(previous[0])
    reverse_low,reverse_high=0.,3.
    for _ in range(50):
        reverse_mid=(reverse_low+reverse_high)/2
        if affinity.rotate(gear,-reverse_mid,origin=(0,0)).intersects(pawls[0]):
            reverse_high=reverse_mid
        else:
            reverse_low=reverse_mid
    result={
        'scope':'2D nominal rigid geometry only; forces, springs, friction, tolerances and axial clearances untested',
        'candidate':'stop P(-38,-13.5), Q(-20,-20), E(-3,-20), tail(-45,-13.5), nose[-3,-0.25]x[-21.75,-12.5]',
        'phase_step_degrees':.05,'opening_step_degrees':.02,
        'all_phases_have_free_opening':bool(np.all(np.any(free,axis=1))),
        'all_openings_clear_at_integer_phase':bool(np.all(free[0])),
        'worst_minimum_opening_degrees':max(minima),
        'worst_phase_degrees':float(phases[int(np.argmax(minima))]),
        'nonmonotonic_phases_degrees':nonmonotonic,
        'non_nose_limiting_count':len(non_nose),
        'non_nose_limiting_examples':non_nose[:10],
        'minimum_clearance_at_integer_phase_all_openings_mm':float(np.min(shapely.distance(gears[0],pawls))),
        'connected_path_unconnected_phases':disconnected,
        'connected_path_maximum_lowest_opening_degrees':max(path_minima),
        'connected_path_final_lowest_opening_degrees':path_minima[-1],
        'closed_stop_nominal_reverse_contact_degrees':reverse_high,
    }
    Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
