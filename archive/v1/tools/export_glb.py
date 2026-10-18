"""Export a meter-scaled view-only GLB from the rendered CAD Blender scene.

blender -b exports/preview.blend --python tools/export_glb.py -- exports/assembly.glb
"""
from pathlib import Path
import sys

import bpy

target = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
bpy.ops.object.select_all(action='DESELECT')
model = bpy.data.objects['Pascaline_V1_Actual_CAD']
model.select_set(True)
bpy.context.view_layer.objects.active = model
model.scale = (.001, .001, .001)  # CAD uses mm; glTF uses meters.
model.location.x = -.042
bpy.ops.export_scene.gltf(filepath=str(target), export_format='GLB',
                          use_selection=True, export_yup=True)
