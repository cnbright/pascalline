"""Selected V0.2 planar geometry shared by current validation scripts.

These dimensions are explicit copies of the selected CAD geometry, not an
OpenSCAD parser. After changing the CAD, check these definitions too. The
selected stop is defined separately in stop_setback_candidate.py; the obsolete
stop from archive/history/rigid_pawl_contact.py is intentionally absent here.
"""
from math import cos, sin, radians

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union


def capsule(a, b, width=3.5):
    return LineString([a, b]).buffer(width / 2, quad_segs=32)


def make_pawl(kind):
    if kind != "drive":
        raise ValueError("Only the selected drive pawl is defined in this helper")
    pivot = (48, 22)
    elbow = (69.5, 2)
    tail = (38, 32)
    nose = Polygon([(68, 0), (71.5, 0), (71.0, 3.5), (68, 3.5)])
    pieces = {
        "beam": capsule(pivot, elbow),
        "pivot": Point(pivot).buffer(5.5, quad_segs=32),
        "tail": unary_union([capsule(pivot, tail), Point(tail).buffer(3, quad_segs=32)]),
        "nose": nose,
    }
    whole = unary_union(list(pieces.values()))
    pieces["outside_nose"] = whole.difference(nose)
    return pivot, whole, pieces


def ratchet():
    vertices = []
    for k in range(10):
        for r, a in ((11.5, 36*k), (17, 36*k), (11.5, 36*(k+1)-1)):
            vertices.append((r*cos(radians(a)), r*sin(radians(a))))
    return Polygon(vertices)
