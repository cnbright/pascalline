#!/usr/bin/env python3
"""Compute an addition and export the matching two-wheel CAD display pose.

The pose shows the final state; it is not a contact/force simulation.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from simulator import Pascaline

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', type=int, default=8)
    parser.add_argument('--add', type=int, default=7)
    parser.add_argument('--output', type=Path, default=Path('exports/pose.csg'))
    args = parser.parse_args()
    try:
        result = Pascaline(digits=2, start=args.start).add(args.add)
    except (TypeError, ValueError) as exc:
        parser.error(str(exc))
    if args.output.suffix.lower() not in {'.csg', '.stl', '.3mf'}:
        parser.error('Choose .csg (view), .stl or .3mf (assembly reference only)')
    executable = shutil.which('openscad')
    if not executable:
        parser.error('Install OpenSCAD and add openscad to PATH')
    target = args.output.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [executable, '-o', str(target), '-D', 'part="assembly"',
               '-D', 'show_cover=true',
               '-D', f'units_angle={result.digit_values[0] * 36}',
               '-D', f'tens_angle={result.digit_values[1] * 36}',
               str(ROOT / 'pascaline.scad')]
    subprocess.run(command, check=True,
                   env=dict(os.environ, QT_QPA_PLATFORM='offscreen'))
    target.with_suffix('.json').write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + '\n')
    print(f'{args.start:02d} + {args.add} -> {result.display}; '
          f'overflow_count={result.overflow_count}')
    print(f'CAD final-state pose: {target}')
    print('This is a state illustration, not a physical simulation.')


if __name__ == '__main__':
    main()
