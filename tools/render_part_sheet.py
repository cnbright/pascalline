"""Render individual, unchanged STL parts for a labeled manufacturing overview.

blender -b -t 6 --python tools/render_part_sheet.py
python3 tools/compose_part_sheet.py
"""
import json
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'exports' / 'part_previews'
OUT.mkdir(exist_ok=True)
parts = json.loads((ROOT / 'exports/mesh_report.json').read_text())['parts']

for part in parts:
    name = Path(part['file']).stem
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.wm.stl_import(filepath=str(ROOT / part['file']))
    model = bpy.context.object
    model.name = name
    colors = {'base': (.08, .34, .39), 'digit_wheel': (.48, .60, .67),
              'units_cam': (.75, .43, .12), 'carry_slider': (.70, .45, .15),
              'drive_pawl': (.78, .24, .10), 'stop_pawl': (.78, .24, .10),
              'shaft_spacer': (.37, .46, .53), 'upper_spacer': (.37, .46, .53), 'top_cover': (.08, .34, .39)}
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*colors[name], 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*colors[name], 1)
    shader.inputs['Roughness'].default_value = .48
    model.data.materials.append(mat)
    corners = [model.matrix_world @ Vector(p) for p in model.bound_box]
    low = Vector([min(p[i] for p in corners) for i in range(3)])
    high = Vector([max(p[i] for p in corners) for i in range(3)])
    center = (low + high) / 2
    span = max(high - low)
    bpy.ops.object.camera_add(location=center + Vector((.6, -.9, 1.65)) * span)
    camera = bpy.context.object
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    rotation = camera.rotation_euler.to_quaternion().inverted()
    projected = [rotation @ (p-center) for p in corners]
    xmin, xmax = min(p.x for p in projected), max(p.x for p in projected)
    ymin, ymax = min(p.y for p in projected), max(p.y for p in projected)
    ratio = 900 / 420
    camera.data.ortho_scale = max(xmax-xmin, (ymax-ymin)*ratio) * 1.13
    scene = bpy.context.scene
    scene.camera = camera
    for offset, energy, size in [((-1,-1,2),65,1.5),((1,.6,1.2),40,1.3)]:
        bpy.ops.object.light_add(type='AREA', location=center + Vector(offset)*span)
        light = bpy.context.object
        light.data.energy = energy * span * span
        light.data.shape = 'DISK'
        light.data.size = size * span
        light.rotation_euler = (center-light.location).to_track_quat('-Z', 'Y').to_euler()
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.7,.75,.8,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .45
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.cycles.use_denoising = False
    scene.render.film_transparent = True
    scene.render.resolution_x = 900
    scene.render.resolution_y = 420
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.filepath = str(OUT / f'{name}.png')
    scene.view_settings.view_transform = 'AgX'
    bpy.ops.render.render(write_still=True)
    print('PART_DONE', name, flush=True)
