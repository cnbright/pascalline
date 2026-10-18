#!/usr/bin/env python3
"""HISTORICAL FAILED PROPOSAL — never use as current V0.2 validation.

Planar geometric clearance sweep for the original proposed V0.2 rigid pawls.
This archived script is self-contained. Running it writes only an adjacent
historical JSON report; it is not part of the current validation sequence.
Its drive helper had already been updated to the selected tapered nose before
archival, while its stop and standalone sweep retain the rejected proposal.
It therefore does not exactly reproduce the earliest rectangular-drive study.
Current scripts use validation/geometry_helpers.py and do not import this file.

This checks the supplied geometry, not dynamics, spring forces or friction.
Angles are degrees, distances mm. Clockwise pawl opening is positive in output.
"""
import json
from math import cos, sin, radians
from pathlib import Path

import numpy as np
import shapely
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union


def capsule(a, b, width=3.5):
    return LineString([a, b]).buffer(width / 2, quad_segs=32)


def make_pawl(kind):
    if kind == "drive":
        pivot = (48, 22)
        elbow = (69.5, 2)
        tail = (38, 32)
        nose = Polygon([(68, 0), (71.5, 0), (71.0, 3.5), (68, 3.5)])
    else:
        pivot = (-35, -20)
        elbow = (-3, -14.25)
        tail = (-43, -20)
        nose = box(-3, -16, 0, -12.5)
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


def scan(kind, stroke=0, max_opening=25, phase_step=0.05, opening_step=0.05):
    pivot, whole, pieces = make_pawl(kind)

    def posed(geometry, opening):
        geometry = affinity.rotate(geometry, -opening, origin=pivot)
        if kind == "drive":
            return affinity.translate(geometry, xoff=-84, yoff=-stroke)
        return affinity.rotate(geometry, -18, origin=(0, 0))

    phases = np.linspace(0, 36, round(36 / phase_step)+1)
    openings = np.linspace(0, max_opening, round(max_opening / opening_step)+1)
    # Tiny inward offset treats exact face/point contact as admissible.
    gears = np.array([affinity.rotate(ratchet(), p, origin=(0, 0)).buffer(-1e-8)
                      for p in phases], dtype=object)
    pawls = np.array([posed(whole, a) for a in openings], dtype=object)
    blocked = shapely.intersects(gears[:, None], pawls[None, :])
    any_free = np.any(~blocked, axis=1)
    minima = []
    limiting_feature_counts = {k: 0 for k in pieces}
    non_nose_controls = []
    intervals = []
    for i, phase in enumerate(phases):
        if not any_free[i]:
            continue
        first = int(np.flatnonzero(~blocked[i])[0])
        lo = openings[max(first-1, 0)]
        hi = openings[first]
        for _ in range(30):
            mid = (lo+hi)/2
            if posed(whole, mid).intersects(gears[i]):
                lo = mid
            else:
                hi = mid
        minima.append((float(phase), float(hi)))
        if hi > 1e-5:
            touching = []
            for name, geometry in pieces.items():
                if posed(geometry, max(0, hi-1e-5)).intersects(gears[i]):
                    limiting_feature_counts[name] += 1
                    touching.append(name)
            if "outside_nose" in touching:
                non_nose_controls.append((float(phase), float(hi), touching))
        # Any return to collision after the first free opening is recorded.
        if np.any(blocked[i, first:]):
            intervals.append(float(phase))

    worst = max(minima, key=lambda p:p[1]) if minima else None
    jumps = sorted(
        ((minima[i][0], minima[i][1]-minima[i-1][1]) for i in range(1, len(minima))),
        key=lambda p:abs(p[1]), reverse=True,
    )[:5]
    failed = [float(x) for x in phases[~any_free]]
    report = {
        "kind": kind, "stroke_mm": stroke,
        "phase_step_degrees": phase_step, "opening_step_degrees": opening_step,
        "max_allowed_opening_degrees": max_opening,
        "phase_samples": len(phases),
        "no_feasible_opening_phases": failed,
        "worst_minimum_opening": {"gear_phase_degrees":worst[0], "opening_degrees":worst[1]} if worst else None,
        "minimum_opening_at_phase_zero": minima[0][1] if minima and minima[0][0] == 0 else None,
        "maximum_jump_between_adjacent_phase_samples": jumps,
        "nonmonotonic_free_angle_phase_count": len(intervals),
        "limiting_feature_sample_counts": limiting_feature_counts,
        "non_nose_limiting_examples": non_nose_controls[:8],
        "non_nose_limiting_worst": max(non_nose_controls, key=lambda p:p[1]) if non_nose_controls else None,
        "clearance_at_max_opening_mm": float(np.min(shapely.distance(gears, pawls[-1]))),
    }
    return report


def free_intervals(kind, stroke=0, gear_phase=0, opening_step=0.01):
    """Report disconnected angle intervals; a spring cannot jump a blocked gap."""
    pivot, whole, _ = make_pawl(kind)
    gear = affinity.rotate(ratchet(), gear_phase, origin=(0, 0)).buffer(-1e-8)
    angles = np.linspace(0, 25, round(25/opening_step)+1)
    geometries = []
    for a in angles:
        posed = affinity.rotate(whole, -a, origin=pivot)
        if kind == "drive":
            posed = affinity.translate(posed, xoff=-84, yoff=-stroke)
        else:
            posed = affinity.rotate(posed, -18, origin=(0, 0))
        geometries.append(posed)
    free = ~shapely.intersects(gear, np.array(geometries, dtype=object))
    edges = np.diff(np.r_[False, free, False].astype(int))
    intervals = [[float(angles[a]), float(angles[b-1])]
                 for a, b in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1))]
    return {"kind": kind, "stroke_mm": stroke, "gear_phase_degrees": gear_phase,
            "opening_step_degrees": opening_step, "free_opening_intervals_degrees": intervals}


if __name__ == "__main__":
    reports = [scan("stop"), scan("drive", 0), scan("drive", 9.9)]
    result = {
        "status": "HISTORICAL_FAILED_PROPOSAL_NOT_FINAL_V02",
        "scope": "2D rigid geometry only; no contact forces, spring stability, friction, tolerances, or axial checks",
        "ratchet_root_radius_mm": 11.5,
        "ratchet_tip_radius_mm": 17,
        "reports": reports,
        "interpretation": [
            "Existence of a collision-free opening at every gear phase does not prove a continuous reset path.",
            "Stop beam intersects a tooth by about 0.00586 mm^2 at nominal closed zero phase.",
            "At drive stroke 0 and integer gear phase, closed opening 0 is isolated from the opened free interval.",
            "A return spring cannot pass through the intervening blocked angle interval to reset the driver.",
            "This script preserves the original supplied proposal geometry even if the SCAD is subsequently revised.",
        ],
        "closure_examples": [
            free_intervals("stop", gear_phase=p) for p in (0, 0.1, 2, 2.4)
        ] + [
            free_intervals("drive", stroke=s) for s in (1, 0, -0.5, -1, -4)
        ],
    }
    target = Path(__file__).with_suffix(".json")
    target.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
