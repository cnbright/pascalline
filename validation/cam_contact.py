#!/usr/bin/env python3
"""Sample the actual OpenSCAD cam functions and check planar roller clearance.

This is a geometric check, not a spring, friction, strength or durability test.
OpenSCAD, NumPy and Shapely are required. Nothing is uploaded.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

import numpy as np
from shapely.geometry import Point, Polygon
from shapely.validation import explain_validity


def run():
    scad = Path(__file__).resolve().parents[1] / "pascaline.scad"
    source = scad.read_bytes()
    with tempfile.TemporaryDirectory(prefix="pascaline_cam_") as directory:
        probe = Path(directory) / "probe.scad"
        probe.write_text(
            f"include <{scad}>;\n"
            "echo(verification_profile=[for(i=[0:cam_samples-1])cam_point(i*360/cam_samples)]);\n"
            "echo(verification_motion=[for(j=[0:3599])[j/10,cam_lift(j/10),lift_derivative(j/10)]]);\n"
            "echo(verification_constants=[cam_base_r,follower_r,cam_samples]);\n",
            encoding="utf-8",
        )
        completed = subprocess.run(
            ["openscad", "-D", 'part="units_cam"', "-o", str(Path(directory)/"probe.csg"), str(probe)],
            text=True, capture_output=True, check=True,
        )
        log = completed.stdout + completed.stderr

    def echoed(name):
        match = re.search(r"ECHO: " + name + r" = (\[[^\n]*\])", log)
        if not match:
            raise RuntimeError(f"OpenSCAD did not emit {name}")
        return np.asarray(json.loads(match.group(1)), dtype=float)

    profile = echoed("verification_profile")
    motion = echoed("verification_motion")
    base_r, follower_r, sample_count = echoed("verification_constants")
    polygon = Polygon(profile)
    angles = np.deg2rad(270-motion[:, 0])
    pitch_r = base_r + follower_r + motion[:, 1]
    centers = np.column_stack((pitch_r*np.cos(angles), pitch_r*np.sin(angles)))
    distances = np.asarray([Point(p).distance(polygon) for p in centers])
    pressure = np.degrees(np.arctan(np.abs(motion[:, 2]/pitch_r)))
    # Finite-difference estimate, excluding negative (concave) pitch curvature.
    r_prime = -motion[:, 2]
    r_second = np.gradient(motion[:, 2], np.deg2rad(0.1))
    denominator = pitch_r*pitch_r + 2*r_prime*r_prime - pitch_r*r_second
    curvature = (pitch_r*pitch_r + r_prime*r_prime)**1.5 / denominator
    positive_curvature = curvature[curvature > 0]
    error = np.abs(distances-follower_r)
    result = {
        "scope": "Actual SCAD functions; planar geometric samples only. No friction, spring forces, strength, or physical validation.",
        "source": str(scad),
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "profile_samples": int(sample_count),
        "motion_samples": len(motion),
        "motion_step_degrees": 0.1,
        "polygon_valid": bool(polygon.is_valid),
        "polygon_validity_detail": explain_validity(polygon),
        "cam_min_radius_mm": float(np.linalg.norm(profile, axis=1).min()),
        "cam_max_radius_mm": float(np.linalg.norm(profile, axis=1).max()),
        "lift_min_mm": float(motion[:, 1].min()),
        "lift_max_mm": float(motion[:, 1].max()),
        "follower_radius_mm": float(follower_r),
        "follower_center_to_cam_min_mm": float(distances.min()),
        "follower_center_to_cam_max_mm": float(distances.max()),
        "maximum_sampled_contact_error_mm": float(error.max()),
        "maximum_pressure_angle_degrees": float(pressure.max()),
        "maximum_pressure_angle_input_phase_degrees": float(motion[np.argmax(pressure), 0]),
        "estimated_min_convex_pitch_curvature_radius_mm": float(positive_curvature.min()),
        "estimated_min_convex_cam_curvature_radius_mm": float(positive_curvature.min()-follower_r),
        "sampled_geometry_pass": bool(polygon.is_valid and error.max() < 0.01),
        "interpretation": "A pass establishes sampled roller contact within 0.01 mm, not manufacturability or working carry reliability.",
    }
    target = Path(__file__).with_suffix(".json")
    target.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    run()
