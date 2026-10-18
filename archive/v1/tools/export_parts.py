#!/usr/bin/env python3
"""Export declared OpenSCAD parts and audit the resulting STL surfaces.

This checks mesh topology only, not clearances, forces or mechanical function.
Uses only Python's standard library and an installed openscad executable.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]


def read_stl(path):
    data = Path(path).read_bytes()
    if len(data) >= 84:
        count = struct.unpack_from('<I', data, 80)[0]
        if len(data) == 84 + 50 * count:
            return [tuple(tuple(row[3 + k * 3:6 + k * 3]) for k in range(3))
                    for row in struct.iter_unpack('<12fH', data[84:])]
    text = data.decode('ascii')
    vertices = [tuple(map(float, m)) for m in
                re.findall(r'vertex\s+(\S+)\s+(\S+)\s+(\S+)', text)]
    if len(vertices) % 3:
        raise ValueError('Invalid ASCII STL vertex count')
    return [tuple(vertices[i:i + 3]) for i in range(0, len(vertices), 3)]


def audit(path):
    triangles = read_stl(path)
    if not triangles:
        raise ValueError('Empty mesh')
    vertices = [p for tri in triangles for p in tri]
    if not all(math.isfinite(v) for p in vertices for v in p):
        raise ValueError('Non-finite coordinate')
    edges, directed = Counter(), Counter()
    parents = {}

    def find(p):
        parents.setdefault(p, p)
        while parents[p] != p:
            parents[p] = parents[parents[p]]
            p = parents[p]
        return p

    volume = 0.0
    degenerate = 0
    for tri in triangles:
        a, b, c = tri
        cross = (b[1]*c[2]-b[2]*c[1], b[2]*c[0]-b[0]*c[2], b[0]*c[1]-b[1]*c[0])
        volume += sum(a[i] * cross[i] for i in range(3)) / 6
        keys = [tuple(round(v, 5) for v in p) for p in tri]
        if len(set(keys)) < 3:
            degenerate += 1
        for j in range(3):
            p, q = keys[j], keys[(j + 1) % 3]
            edges[tuple(sorted((p, q)))] += 1
            directed[(p, q)] += 1
            rp, rq = find(p), find(q)
            if rp != rq:
                parents[rp] = rq
    bad_edges = sum(n != 2 for n in edges.values())
    orientation_errors = sum(directed[(a, b)] != directed[(b, a)] for a, b in edges)
    components = len({find(p) for p in parents})
    low = [min(p[i] for p in vertices) for i in range(3)]
    high = [max(p[i] for p in vertices) for i in range(3)]
    return {
        'file': str(Path(path).relative_to(ROOT)),
        'triangles': len(triangles),
        'components': components,
        'bbox_min_mm': [round(v, 3) for v in low],
        'bbox_max_mm': [round(v, 3) for v in high],
        'size_mm': [round(high[i]-low[i], 3) for i in range(3)],
        'signed_volume_mm3': round(volume, 3),
        'nonmanifold_edges': bad_edges,
        'orientation_errors': orientation_errors,
        'degenerate_triangles': degenerate,
        'mesh_check_passed': bad_edges == 0 and orientation_errors == 0
                             and degenerate == 0 and volume > 0 and components == 1,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parts', nargs='+', help='Default: all // @export declarations')
    parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    source = ROOT / 'pascaline.scad'
    declared = dict((p, int(n)) for p, n in
                    re.findall(r'^// @export (\w+) (\d+)\s*$', source.read_text(), re.M))
    names = args.parts or list(declared)
    if not names or set(names) - declared.keys():
        parser.error('Unknown or missing part declaration')
    executable = shutil.which('openscad')
    if not args.validate_only and not executable:
        parser.error('Install OpenSCAD and add openscad to PATH')
    output = ROOT / 'exports'
    output.mkdir(exist_ok=True)

    def process(name):
        target = output / f'{name}.stl'
        if not args.validate_only:
            command = [executable, '--export-format', 'binstl', '-o', str(target),
                       '-D', f'part="{name}"', str(source)]
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
            result = subprocess.run(command, capture_output=True, text=True,
                                    env=env, timeout=300)
            (output / f'{name}.log').write_text(result.stdout + result.stderr)
            if result.returncode or 'ERROR:' in result.stderr or not target.exists():
                raise RuntimeError(f'{name}: export failed; see exports/{name}.log')
        result = audit(target)
        result['quantity'] = declared[name]
        print(f"{name}: {'PASS' if result['mesh_check_passed'] else 'CHECK'} "
              f"{result['size_mm']} mm, {result['components']} component(s)")
        return result

    with ThreadPoolExecutor(max_workers=max(1, min(args.jobs, 4))) as pool:
        reports = list(pool.map(process, names))
    report = {'scope': 'STL topology only; physical mechanism remains untested',
              'units': 'mm', 'parts': reports}
    report_name = 'mesh_report.json' if not args.parts else 'mesh_report_selected.json'
    (output / report_name).write_text(json.dumps(report, indent=2) + '\n')
    if not all(r['mesh_check_passed'] for r in reports):
        raise SystemExit('One or more parts need mesh inspection')


if __name__ == '__main__':
    main()
