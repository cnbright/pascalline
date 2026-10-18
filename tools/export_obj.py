#!/usr/bin/env python3
"""Convert declared standalone STLs to welded, material-free triangle OBJs.

Usage: python3 tools/export_obj.py
Run tools/export_parts.py first whenever CAD changes. Sources and quantities
come from exports/mesh_report.json. OBJ has no enforced unit system: coordinates
are preserved in millimetres, and every file explicitly comments that unit.

Validation checks the STL/OBJ geometry round trip, closed oriented 2-manifold
topology (including vertex links), and one connected surface. It does not check
self-intersections, mechanical clearances, printability, or physical operation.
Only Python's standard library is required.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import struct


ROOT = Path(__file__).resolve().parents[1]
NAMES_ZH = {
    "base": "底座",
    "digit_wheel": "数字轮（含棘轮）",
    "units_cam": "个位凸轮",
    "carry_slider": "进位滑架",
    "drive_pawl": "驱动拨爪",
    "stop_pawl": "止回爪",
    "shaft_spacer": "下法兰轴套",
    "upper_spacer": "上轴向隔圈",
    "top_cover": "上盖",
}


def read_stl(path: Path) -> list[tuple]:
    data = path.read_bytes()
    if len(data) >= 84:
        count = struct.unpack_from("<I", data, 80)[0]
        if len(data) == 84 + 50 * count:
            return [tuple(tuple(row[3 + 3*k:6 + 3*k]) for k in range(3))
                    for row in struct.iter_unpack("<12fH", data[84:])]
    try:
        source = data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("Invalid binary size or non-ASCII STL") from exc
    vertices = [tuple(map(float, match)) for match in re.findall(
        r"^\s*vertex\s+(\S+)\s+(\S+)\s+(\S+)\s*$", source, re.M)]
    facets = len(re.findall(r"^\s*facet\s+normal\b", source, re.M))
    if not facets or len(vertices) != 3 * facets:
        raise ValueError("Invalid ASCII STL facet/vertex count")
    return [tuple(vertices[i:i+3]) for i in range(0, len(vertices), 3)]


def weld(triangles: list[tuple]) -> tuple[list[tuple], list[tuple]]:
    """Weld exactly equal coordinates; never round, scale, or move a vertex."""
    vertices, faces, lookup = [], [], {}
    for triangle in triangles:
        face = []
        for point in triangle:
            if not all(math.isfinite(value) for value in point):
                raise ValueError("Non-finite STL coordinate")
            if point not in lookup:
                lookup[point] = len(vertices)
                vertices.append(point)
            face.append(lookup[point])
        faces.append(tuple(face))
    return vertices, faces


def inspect_mesh(vertices: list[tuple], faces: list[tuple]) -> dict:
    if not vertices or not faces:
        raise ValueError("Empty mesh")
    edge_faces = defaultdict(list)
    directed = Counter()
    links = defaultdict(list)
    duplicate_faces = 0
    degenerate_faces = 0
    seen_faces = set()
    volume_terms = []
    parents = list(range(len(faces)))

    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def join(a, b):
        a, b = find(a), find(b)
        if a != b:
            parents[a] = b

    for face_index, face in enumerate(faces):
        if len(face) != 3 or any(i < 0 or i >= len(vertices) for i in face):
            raise ValueError("Invalid triangular face index")
        a, b, c = (vertices[i] for i in face)
        ab = tuple(b[i] - a[i] for i in range(3))
        ac = tuple(c[i] - a[i] for i in range(3))
        cross = (ab[1]*ac[2]-ab[2]*ac[1], ab[2]*ac[0]-ab[0]*ac[2],
                 ab[0]*ac[1]-ab[1]*ac[0])
        if len(set(face)) != 3 or all(value == 0 for value in cross):
            degenerate_faces += 1
        key = tuple(sorted(face))
        duplicate_faces += key in seen_faces
        seen_faces.add(key)
        volume_terms.append((
            a[0]*(b[1]*c[2]-b[2]*c[1])
            + a[1]*(b[2]*c[0]-b[0]*c[2])
            + a[2]*(b[0]*c[1]-b[1]*c[0])) / 6)
        for i in range(3):
            p, q = face[i], face[(i+1) % 3]
            edge_faces[tuple(sorted((p, q)))].append(face_index)
            directed[(p, q)] += 1
            links[p].append((q, face[(i+2) % 3]))

    nonmanifold_edges = sum(len(incident) != 2 for incident in edge_faces.values())
    orientation_errors = 0
    for (a, b), incident in edge_faces.items():
        if directed[(a, b)] != 1 or directed[(b, a)] != 1:
            orientation_errors += 1
        for face_index in incident[1:]:
            join(incident[0], face_index)

    # A closed 2-manifold requires each vertex link to be one cycle, not two
    # shells touching only at a point. Edge incidence alone would miss that.
    nonmanifold_vertices = 0
    for vertex in range(len(vertices)):
        adjacency = defaultdict(set)
        degrees = Counter()
        for a, b in links[vertex]:
            adjacency[a].add(b)
            adjacency[b].add(a)
            degrees[a] += 1
            degrees[b] += 1
        if not degrees or any(degree != 2 for degree in degrees.values()):
            nonmanifold_vertices += 1
            continue
        visited, pending = set(), [next(iter(degrees))]
        while pending:
            node = pending.pop()
            if node not in visited:
                visited.add(node)
                pending.extend(adjacency[node] - visited)
        if len(visited) != len(degrees):
            nonmanifold_vertices += 1

    low = [min(vertex[i] for vertex in vertices) for i in range(3)]
    high = [max(vertex[i] for vertex in vertices) for i in range(3)]
    components = len({find(i) for i in range(len(faces))})
    volume = math.fsum(volume_terms)
    closed = not (nonmanifold_edges or nonmanifold_vertices or degenerate_faces or duplicate_faces)
    return {
        "vertices": len(vertices), "triangles": len(faces),
        "bbox_min_mm": low, "bbox_max_mm": high,
        "size_mm": [high[i] - low[i] for i in range(3)],
        "signed_volume_mm3": volume, "components": components,
        "nonmanifold_edges": nonmanifold_edges,
        "nonmanifold_vertices": nonmanifold_vertices,
        "orientation_errors": orientation_errors,
        "degenerate_triangles": degenerate_faces, "duplicate_faces": duplicate_faces,
        "closed_2_manifold": closed,
        "mesh_check_passed": closed and not orientation_errors and components == 1 and volume > 0,
    }


def write_obj(path: Path, name: str, vertices: list[tuple], faces: list[tuple]) -> None:
    with path.open("w", encoding="ascii", newline="\n") as target:
        target.write("# Units: mm (millimetres); OBJ itself does not enforce units.\n")
        target.write("# Exact-coordinate welded vertices; triangles; no material dependencies.\n")
        target.write("# Local part coordinates and print orientation preserved from source STL.\n")
        target.write(f"o {name}\n")
        for vertex in vertices:
            target.write("v " + " ".join(format(value, ".17g") for value in vertex) + "\n")
        for face in faces:
            target.write("f " + " ".join(str(index + 1) for index in face) + "\n")


def read_obj(path: Path) -> tuple[str, list[tuple], list[tuple]]:
    objects, vertices, faces = [], [], []
    for number, line in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
        fields = line.split()
        if not fields or fields[0].startswith("#"):
            continue
        if fields[0] == "o" and len(fields) == 2:
            objects.append(fields[1])
        elif fields[0] == "v" and len(fields) == 4:
            point = tuple(map(float, fields[1:]))
            if not all(math.isfinite(value) for value in point):
                raise ValueError(f"Non-finite OBJ coordinate at line {number}")
            vertices.append(point)
        elif fields[0] == "f" and len(fields) == 4:
            if not all(re.fullmatch(r"[1-9][0-9]*", value) for value in fields[1:]):
                raise ValueError(f"Expected positive plain vertex indices at line {number}")
            faces.append(tuple(int(value) - 1 for value in fields[1:]))
        else:
            raise ValueError(f"Unexpected OBJ record at line {number}: {fields[0]}")
    if len(objects) != 1:
        raise ValueError(f"Expected one OBJ object, got {len(objects)}")
    return objects[0], vertices, faces


def confirm_source_report(entry: dict, measured: dict) -> None:
    """Catch stale source reports, allowing their documented 0.001-mm rounding."""
    if entry.get("mesh_check_passed") is not True or entry["triangles"] != measured["triangles"]:
        raise ValueError("STL report failed or stale; rerun tools/export_parts.py")
    for field in ("bbox_min_mm", "bbox_max_mm", "size_mm"):
        if any(abs(a-b) > 0.00051 for a, b in zip(entry[field], measured[field])):
            raise ValueError(f"STL/report {field} mismatch; re-export source parts")
    if not math.isclose(entry["signed_volume_mm3"], measured["signed_volume_mm3"],
                        rel_tol=1e-12, abs_tol=0.00051):
        raise ValueError("STL/report volume mismatch; re-export source parts")


def convert_part(entry: dict, output: Path) -> dict:
    source = (ROOT / entry["file"]).resolve()
    if not source.is_relative_to(ROOT) or source.suffix.lower() != ".stl":
        raise ValueError("Source must be an STL inside the project")
    name = source.stem
    if not re.fullmatch(r"[A-Za-z0-9_]+", name):
        raise ValueError("Unsafe/unsupported part identifier")
    quantity = entry["quantity"]
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
        raise ValueError("Quantity must be a positive integer")
    vertices, faces = weld(read_stl(source))
    original = inspect_mesh(vertices, faces)
    confirm_source_report(entry, original)
    if not original["mesh_check_passed"]:
        raise ValueError("STL fails exact-weld topology validation: " + json.dumps(original))
    destination = output / f"{name}.obj"
    temporary = destination.with_suffix(".obj.tmp")
    try:
        write_obj(temporary, name, vertices, faces)
        object_name, result_vertices, result_faces = read_obj(temporary)
        converted = inspect_mesh(result_vertices, result_faces)
        bbox_delta = max(abs(a-b) for field in ("bbox_min_mm", "bbox_max_mm")
                         for a, b in zip(original[field], converted[field]))
        volume_delta = abs(original["signed_volume_mm3"] - converted["signed_volume_mm3"])
        exact = vertices == result_vertices and faces == result_faces
        if not (exact and object_name == name and converted["mesh_check_passed"]
                and bbox_delta <= 1e-9
                and math.isclose(original["signed_volume_mm3"], converted["signed_volume_mm3"],
                                 rel_tol=1e-12, abs_tol=1e-6)):
            raise ValueError("OBJ round-trip geometry/topology validation failed")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "part": name, "name_zh": NAMES_ZH.get(name, name), "quantity": quantity,
        "optional": name == "top_cover", "source_stl": entry["file"],
        "obj_file": f"obj/{destination.name}", "object_count": 1, "units": "mm",
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "obj_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "source_stl_metrics": original, "obj_metrics": converted,
        "roundtrip_geometry_exact": exact, "bbox_max_delta_mm": bbox_delta,
        "volume_delta_mm3": volume_delta, "validation_passed": True,
    }


def write_parts_csv(path: Path, reports: list[dict]) -> None:
    # BOM is one row per object type. Quantities are NOT baked into each OBJ.
    with path.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.writer(target)
        writer.writerow(["文件", "中文名称", "数量", "可选", "单位", "X尺寸_mm",
                         "Y尺寸_mm", "Z尺寸_mm", "单件体积_cm3", "备注"])
        for part in reports:
            metrics = part["obj_metrics"]
            writer.writerow([part["obj_file"], part["name_zh"], part["quantity"],
                             "是" if part["optional"] else "否", "mm",
                             *(f"{value:.3f}" for value in metrics["size_mm"]),
                             f"{metrics['signed_volume_mm3']/1000:.6f}",
                             "每文件仅一个零件；请按数量生产" + ("；盖板可省略" if part["optional"] else "")])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh-report", type=Path, default=ROOT / "exports/mesh_report.json")
    parser.add_argument("--output-root", type=Path, default=ROOT / "exports",
                        help="Bundle directory containing obj/, obj_report.json and parts.csv")
    args = parser.parse_args(argv)
    try:
        source_bytes = args.mesh_report.read_bytes()
        source_report = json.loads(source_bytes)
        entries = source_report["parts"]
        if source_report["units"] != "mm" or not entries:
            raise ValueError("Expected a non-empty source report in mm")
        names = [Path(entry["file"]).stem for entry in entries]
        if len(set(names)) != len(names):
            raise ValueError("Duplicate part identifiers in source report")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    output = args.output_root / "obj"
    output.mkdir(parents=True, exist_ok=True)
    reports = []
    for entry in entries:
        try:
            report = convert_part(entry, output)
            print(f"{report['part']}: PASS; {report['obj_metrics']['vertices']} welded vertices; "
                  f"{report['obj_metrics']['triangles']} triangles; quantity {report['quantity']}")
        except (OSError, KeyError, TypeError, ValueError) as exc:
            report = {"source_stl": entry.get("file"), "validation_passed": False,
                      "error": str(exc), "existing_obj_not_refreshed": True}
            print(f"{entry.get('file')}: FAIL: {exc}")
        reports.append(report)
    passed = all(part["validation_passed"] for part in reports)
    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "STL-to-OBJ geometry and closed oriented 2-manifold topology only; "
                 "self-intersections, physical fit and printability are not validated",
        "units": "mm", "welding": "Exact coordinate equality; no tolerance welding",
        "source_report": str(args.mesh_report.resolve()),
        "source_report_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "part_types": len(entries), "validation_passed": passed, "parts": reports,
    }
    if passed:
        result["total_quantity_with_cover"] = sum(part["quantity"] for part in reports)
        result["total_quantity_without_cover"] = sum(part["quantity"] for part in reports if not part["optional"])
        write_parts_csv(args.output_root / "parts.csv", reports)
    else:
        result["parts_csv_not_refreshed"] = True
    (args.output_root / "obj_report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not passed:
        print("Export incomplete. Do not package existing OBJ/CSV files as a validated new bundle.")
        return 1
    print(f"Validated {len(reports)} OBJ types / {result['total_quantity_with_cover']} pieces "
          f"({result['total_quantity_without_cover']} without optional cover).")
    print(f"Report: {args.output_root / 'obj_report.json'}")
    print(f"BOM: {args.output_root / 'parts.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
