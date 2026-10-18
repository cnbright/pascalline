#!/usr/bin/env python3
"""Regenerate artifacts in a NEW external directory, preserving the saved delivery."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
# The planar helper dimensions are independently encoded, not extracted from CAD.
SUPPORTED_GEOMETRY_SHA256 = '938b2e7983265af279ef11afa5ffce0bac8022f535ac9fe8ba747e4faf517040'


def geometry_verdict(destination, source_hash):
    def read(name):
        return json.loads((destination / 'validation' / (name + '.json')).read_text())
    reports = {n: read(n) for n in ['cam_contact', 'driver_reset_path', 'stop_setback_candidate',
                                  'working_stroke', 'section_clearance', 'pawl_pair_path', 'manual_tens_pair']}
    for name, report in reports.items():
        if 'source_sha256' in report and report['source_sha256'] != source_hash:
            raise RuntimeError(f'Stale geometry report: {name}')
    cam, driver, stop = (reports[n] for n in ['cam_contact', 'driver_reset_path', 'stop_setback_candidate'])
    work, sections, pair, manual = (reports[n] for n in ['working_stroke', 'section_clearance', 'pawl_pair_path', 'manual_tens_pair'])
    checks = {
        'cam_sampled_contact': cam['sampled_geometry_pass'],
        'driver_return_path': driver['overlap_count'] == 0,
        'stop_sampled_connected_path': stop['all_phases_have_free_opening'] and not stop['connected_path_unconnected_phases'],
        'work_and_release_path': work['work_collision_count'] == 0 and work['release_collision_count'] == 0,
        'fixed_body_sections': sections['current_source_matches'] and all(c['pair'] == 'drive_tens_stop_swept' for c in sections['collisions']),
        'prescribed_pawl_pair_path': len(pair['checks']) == 3 and all(c['overlap_count'] == 0 and math.isfinite(c['minimum']['gap_mm']) for c in pair['checks'].values()),
        'manual_tens_sampled_angles': len(manual['results']) == 3 and all(c['sample_count'] == 361 and c['missing_legal_angle_count'] == 0 and c['pair_overlap_count'] == 0 and math.isfinite(c['minimum_pair_gap']['gap_mm']) for c in manual['results']),
    }
    verdict = {'source_sha256': source_hash, 'checks': checks,
               'prescribed_sampled_geometry_pass': all(checks.values()),
               'independent_extreme_envelope_collisions': sections['collisions'],
               'physical_tests_performed': False,
               'limitation': 'Geometric evidence only. Independent extreme pawl combinations may collide; passive spring path selection, friction, fit and life remain unverified.'}
    (destination / 'geometry_verdict.json').write_text(json.dumps(verdict, indent=2) + '\n')
    if not all(checks.values()):
        raise RuntimeError('Geometry checks failed; see geometry_verdict.json')
    return verdict


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='New, nonexisting directory outside this checkout')
    parser.add_argument('--meshes', action='store_true', help='Regenerate nine STL and OBJ files')
    parser.add_argument('--geometry', action='store_true', help='Rerun the current V0.2 geometric evidence')
    parser.add_argument('--preview', action='store_true', help='Render actual STL previews using Blender >=4 and CJK fonts')
    args = parser.parse_args()
    if not any((args.meshes, args.geometry, args.preview)):
        parser.error('Choose --meshes, --geometry and/or --preview')
    destination = args.output.resolve()
    if destination.exists() or destination.is_relative_to(ROOT) or ROOT.is_relative_to(destination):
        parser.error('--output must be a new external directory; existing data is never overwritten')
    source_hash = hashlib.sha256((ROOT / 'pascaline.scad').read_bytes()).hexdigest()
    if args.geometry and source_hash != SUPPORTED_GEOMETRY_SHA256:
        parser.error('CAD changed: first reconcile the independently encoded geometry helpers/limits, then update their supported hash. Do not just relabel old evidence.')
    if (args.meshes or args.geometry) and not shutil.which('openscad'):
        parser.error('OpenSCAD CLI is required')
    if args.preview and not shutil.which('blender'):
        parser.error('Blender >=4 is required')
    packages = {}
    for name in (['numpy', 'shapely'] if args.geometry else []) + (['Pillow'] if args.preview else []):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            parser.error(f'Install requirements.txt; missing {name}')
    shutil.copytree(ROOT, destination, ignore=shutil.ignore_patterns(
        '.git', '.venv', '__pycache__', '*.log', '*.pyc', 'section_clearance', 'clearance_snapshot.scad'))
    # Saved evidence remains at the original checkout. Remove stale summaries in the rebuild copy.
    saved = destination / 'saved_baseline'
    saved.mkdir()
    for name in ['baseline_manifest.json', 'validation_summary.json', 'validation/mechanism_evidence.json']:
        path = destination / name
        shutil.move(str(path), saved / path.name)
    metadata = {'source_sha256': source_hash, 'started_at_utc': datetime.now(timezone.utc).isoformat(),
                'python': sys.version, 'python_packages': packages, 'stages': [],
                'physical_tests_performed': False, 'status': 'RUNNING'}
    log_dir = destination / 'rebuild_logs'
    log_dir.mkdir()
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', PYTHONDONTWRITEBYTECODE='1')
    def run(name, command):
        print(f'Running {name} ...', flush=True)
        log = log_dir / (name + '.log')
        with log.open('w') as stream:
            completed = subprocess.run(command, cwd=destination, env=env, stdout=stream, stderr=subprocess.STDOUT)
        metadata['stages'].append({'name': name, 'exit_code': completed.returncode, 'log': str(log.relative_to(destination))})
        if completed.returncode:
            print(log.read_text()[-4000:])
            raise RuntimeError(f'{name} failed; see {log}')
    try:
        if args.meshes:
            run('export_stl', [sys.executable, 'tools/export_parts.py', '--jobs', '4'])
            run('export_obj', [sys.executable, 'tools/export_obj.py'])
        if args.geometry:
            sequence = ['cam_contact', 'driver_reset_path', 'stop_setback_candidate', 'working_stroke',
                        'section_clearance', 'pawl_pair_path', 'manual_tens_pair']
            for name in sequence:
                (destination / 'validation' / (name + '.json')).unlink(missing_ok=True)
            (destination / 'validation/driver_reset_path.csv').unlink(missing_ok=True)
            for name in sequence:
                run(name, [sys.executable, f'validation/{name}.py'])
            metadata['geometry'] = geometry_verdict(destination, source_hash)
        if args.preview:
            previews = destination / 'exports/part_previews'
            if previews.exists():
                shutil.rmtree(previews)
            for suffix in ['png', 'pdf']:
                (destination / 'exports' / ('print_parts_overview.' + suffix)).unlink(missing_ok=True)
            run('render_parts', ['blender', '-b', '-t', '4', '--python-exit-code', '1', '--python', 'tools/render_part_sheet.py'])
            parts = json.loads((destination / 'exports/mesh_report.json').read_text())['parts']
            for part in parts:
                expected = previews / (Path(part['file']).stem + '.png')
                if not expected.is_file() or expected.stat().st_size == 0:
                    raise RuntimeError(f'Missing newly rendered preview: {expected.name}')
            run('compose_preview', [sys.executable, 'tools/compose_part_sheet.py'])
        metadata['status'] = 'COMPLETED_REQUESTED_STAGES'
    except Exception as error:
        metadata['status'] = 'FAILED'
        metadata['error'] = str(error)
        raise
    finally:
        metadata['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        (destination / 'rebuild_report.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(f'Rebuilt artifacts: {destination}')
    print('Use rebuild_report.json / geometry_verdict.json for this run; saved_baseline and dist retain original historical files.')


if __name__ == '__main__':
    main()
