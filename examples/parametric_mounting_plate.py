"""Parametric mounting plate example for iterative agent work.

The folder-watch macro injects job parameters as PARAMS. Running this script
with different PARAMS rebuilds the same stable object set in the current
agent session document.
"""

import FreeCAD as App
import Part


DEFAULT_PARAMS = {
    "plate_width": 110.0,
    "plate_depth": 64.0,
    "plate_thickness": 6.0,
    "hole_count": 4,
    "hole_diameter": 9.0,
    "hole_margin": 18.0,
    "rail_width": 5.0,
    "rail_height": 12.0,
    "rail_inset": 7.0,
}


def merged_params():
    params = DEFAULT_PARAMS.copy()
    params.update(globals().get("PARAMS", {}))
    return params


def as_float(params, key):
    return float(params[key])


def as_int(params, key):
    return int(params[key])


def set_color(obj, color):
    if hasattr(obj, "ViewObject"):
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.Transparency = 0


params = merged_params()
doc = DOC

plate_width = as_float(params, "plate_width")
plate_depth = as_float(params, "plate_depth")
plate_thickness = as_float(params, "plate_thickness")
hole_count = max(1, as_int(params, "hole_count"))
hole_diameter = as_float(params, "hole_diameter")
hole_margin = as_float(params, "hole_margin")
rail_width = as_float(params, "rail_width")
rail_height = as_float(params, "rail_height")
rail_inset = as_float(params, "rail_inset")

plate_shape = Part.makeBox(plate_width, plate_depth, plate_thickness)
usable_width = max(0.0, plate_width - (2.0 * hole_margin))
spacing = usable_width / max(1, hole_count - 1)

for index in range(hole_count):
    x = hole_margin + (spacing * index if hole_count > 1 else usable_width / 2.0)
    cutter = Part.makeCylinder(
        hole_diameter / 2.0,
        plate_thickness + 4.0,
        App.Vector(x, plate_depth / 2.0, -2.0),
    )
    plate_shape = plate_shape.cut(cutter)

plate = doc.addObject("Part::Feature", "parametric_plate")
plate.Label = "Parametric Plate"
plate.Shape = plate_shape
set_color(plate, (0.68, 0.72, 0.76))

left_rail = doc.addObject("Part::Feature", "left_rail")
left_rail.Label = "Left Rail"
left_rail.Shape = Part.makeBox(
    plate_width,
    rail_width,
    rail_height,
    App.Vector(0, rail_inset, plate_thickness),
)
set_color(left_rail, (0.23, 0.44, 0.72))

right_rail = doc.addObject("Part::Feature", "right_rail")
right_rail.Label = "Right Rail"
right_rail.Shape = Part.makeBox(
    plate_width,
    rail_width,
    rail_height,
    App.Vector(0, plate_depth - rail_inset - rail_width, plate_thickness),
)
set_color(right_rail, (0.23, 0.44, 0.72))

doc.recompute()
