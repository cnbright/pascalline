#!/usr/bin/env python3
"""Read-only audit of the saved V0.2 delivery. Standard library only."""
import hashlib
import json
from pathlib import Path
import zipfile

from export_obj import inspect_mesh, read_obj, read_stl, weld

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((ROOT / 'baseline_manifest.json').read_text())
    for name, expected in manifest['files_sha256'].items():
        path = (ROOT / name).resolve()
        require(path.is_relative_to(ROOT), f'Unsafe manifest path: {name}')
        require(path.is_file() and sha(path) == expected, f'Baseline changed/missing: {name}')
    summary = json.loads((ROOT / 'validation_summary.json').read_text())
    require(sha(ROOT / 'pascaline.scad') == summary['source_sha256'], 'CAD hash mismatch')
    report = json.loads((ROOT / 'exports/obj_report.json').read_text())
    require(report['part_types'] == 9 and report['validation_passed'], 'Invalid OBJ report')
    quantity = sum(part['quantity'] for part in report['parts'])
    require(quantity == 13, 'Unexpected BOM quantity')
    for part in report['parts']:
        name = part['part']
        obj = ROOT / 'exports' / part['obj_file']
        require(sha(obj) == summary['obj_files_sha256'][obj.name], f'{name}: delivery hash')
        object_name, vertices, faces = read_obj(obj)
        require(object_name == name, f'{name}: object name')
        require(inspect_mesh(vertices, faces)['mesh_check_passed'], f'{name}: topology')
        source_vertices, source_faces = weld(read_stl(ROOT / part['source_stl']))
        require(vertices == source_vertices and faces == source_faces, f'{name}: STL/OBJ mismatch')
        print(f'{name}: closed oriented mesh, exact STL/OBJ geometry')
    for name, expected in summary['evidence_reports_sha256'].items():
        require(sha(ROOT / 'validation' / name) == expected, f'Evidence changed: {name}')
    with zipfile.ZipFile(ROOT / 'dist/pascaline-v2-print-obj.zip') as archive:
        require(archive.testzip() is None, 'Delivery ZIP CRC failure')
        for name, expected in summary['obj_files_sha256'].items():
            require(hashlib.sha256(archive.read('obj/' + name)).hexdigest() == expected,
                    f'Delivery ZIP OBJ mismatch: {name}')
    print(f'PASS: {len(manifest["files_sha256"])} saved files; 9 OBJ types / 13 pieces (12 without cover).')
    print('This verifies saved data and mesh topology, not physical operation or supplier acceptance.')


if __name__ == '__main__':
    main()

