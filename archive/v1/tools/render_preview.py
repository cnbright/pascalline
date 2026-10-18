"""Render the actual assembly STL with Blender; colors aid part recognition.

Usage: blender -b -t 4 --python tools/render_preview.py -- assembly.stl preview.png
The camera and illustrative colors do not modify the exported CAD geometry.
"""
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
source, destination = map(lambda s: Path(s).resolve(), args[:2])
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.wm.stl_import(filepath=str(source))
model = bpy.context.object
model.name = 'Pascaline_V1_Actual_CAD'


def material(name, color, roughness=.38, metallic=0):
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    shader = result.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metallic
    return result


palette = [material('Base / deep teal', (.026, .16, .18)),
           material('Cam / brass', (.8, .45, .13), metallic=.25),
           material('Transmission / orange', (.88, .24, .10)),
           material('Display / warm ivory', (.84, .82, .71)),
           material('Floor', (.08, .115, .14), roughness=.8)]
for mat in palette[:4]:
    model.data.materials.append(mat)
for face in model.data.polygons:
    z = face.center.z
    face.material_index = 0 if z <= 5.05 else 1 if z < 11.5 else 2 if z < 17 else 3

points = [model.matrix_world @ Vector(corner) for corner in model.bound_box]
low = Vector([min(p[i] for p in points) for i in range(3)])
high = Vector([max(p[i] for p in points) for i in range(3)])
center = (low + high) / 2
span = max(high.x - low.x, high.y - low.y)
bpy.ops.mesh.primitive_plane_add(size=span*200, location=(center.x, center.y, low.z-.25))
bpy.context.object.data.materials.append(palette[4])

bpy.ops.object.camera_add(location=center + Vector((span*.65, -span*.92, span*1.23)))
camera = bpy.context.object
camera.rotation_euler = (center-camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.type = 'ORTHO'
view_rotation = camera.rotation_euler.to_quaternion().inverted()
projected = [view_rotation @ (p-center) for p in points]
width = max(p.x for p in projected) - min(p.x for p in projected)
height = max(p.y for p in projected) - min(p.y for p in projected)
camera.data.ortho_scale = max(width, height*1600/1100)*1.12
bpy.context.scene.camera = camera


def light(name, offset, energy, size):
    bpy.ops.object.light_add(type='AREA', location=center + Vector(offset))
    lamp = bpy.context.object
    lamp.name = name
    lamp.data.energy = energy * span * span
    lamp.data.shape = 'DISK'
    lamp.data.size = size
    lamp.rotation_euler = (center-lamp.location).to_track_quat('-Z', 'Y').to_euler()


light('Key', (-span*.5, -span*.6, span*1.7), 80, span)
light('Fill', (span, span*.5, span), 50, span*.9)
scene = bpy.context.scene
scene.world.color = (.35, .35, .35)
scene.render.engine = 'CYCLES'
scene.cycles.samples = 64
scene.cycles.use_denoising = False
scene.render.resolution_x = 1600
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = str(destination)
scene.view_settings.view_transform = 'AgX'
destination.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(destination.with_suffix('.blend')))
bpy.ops.render.render(write_still=True)
