"""History-style parametric mounting plate for update-mode testing.

Run with:

    python3 agent_submit.py examples/history_mounting_plate.py --mode update

First run creates a stable FreeCAD object graph. Later runs update the same
objects and recompute the chain instead of clearing the session document.
"""

import json

import FreeCAD as App


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


def get_or_add(doc, type_id, name, label):
    obj = doc.getObject(name)
    if obj is None:
        obj = doc.addObject(type_id, name)
    obj.Label = label
    return obj


def set_visible(obj, visible):
    try:
        obj.ViewObject.Visibility = bool(visible)
    except Exception:
        pass


def set_color(obj, color):
    if hasattr(obj, "ViewObject"):
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.Transparency = 0


def set_box(obj, length, width, height, placement=None):
    obj.Length = length
    obj.Width = width
    obj.Height = height
    if placement is not None:
        obj.Placement = placement


def set_cylinder(obj, radius, height, placement):
    obj.Radius = radius
    obj.Height = height
    obj.Placement = placement


def update_parameter_sheet(doc, params):
    sheet = get_or_add(doc, "Spreadsheet::Sheet", "Parameters", "Parameters")
    sheet.set("A1", "parameter")
    sheet.set("B1", "value")
    for row, key in enumerate(sorted(params), start=2):
        value = params[key]
        sheet.set("A{}".format(row), key)
        sheet.set("B{}".format(row), str(value))
        try:
            sheet.setAlias("B{}".format(row), key)
        except Exception:
            pass
    sheet.set("D1", "json")
    sheet.set("D2", json.dumps(params, sort_keys=True))
    return sheet


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

update_parameter_sheet(doc, params)

base = get_or_add(doc, "Part::Box", "plate_base", "Plate Base")
set_box(base, plate_width, plate_depth, plate_thickness)
set_color(base, (0.68, 0.72, 0.76))
set_visible(base, False)

usable_width = max(0.0, plate_width - (2.0 * hole_margin))
spacing = usable_width / max(1, hole_count - 1)
previous = base
active_cut = None

for index in range(1, hole_count + 1):
    x = hole_margin + (spacing * (index - 1) if hole_count > 1 else usable_width / 2.0)
    cutter = get_or_add(
        doc,
        "Part::Cylinder",
        "hole_cutter_{:02d}".format(index),
        "Hole Cutter {:02d}".format(index),
    )
    set_cylinder(
        cutter,
        hole_diameter / 2.0,
        plate_thickness + 4.0,
        App.Placement(App.Vector(x, plate_depth / 2.0, -2.0), App.Rotation()),
    )
    set_visible(cutter, False)

    cut = get_or_add(
        doc,
        "Part::Cut",
        "plate_cut_{:02d}".format(index),
        "Plate Cut {:02d}".format(index),
    )
    cut.Base = previous
    cut.Tool = cutter
    set_color(cut, (0.68, 0.72, 0.76))
    set_visible(cut, False)
    previous = cut
    active_cut = cut

for obj in list(doc.Objects):
    if obj.Name.startswith("hole_cutter_") or obj.Name.startswith("plate_cut_"):
        suffix = obj.Name.rsplit("_", 1)[-1]
        try:
            index = int(suffix)
        except ValueError:
            continue
        if index > hole_count:
            set_visible(obj, False)

if active_cut is not None:
    active_cut.Label = "Plate With Holes"
    set_visible(active_cut, True)

left_rail = get_or_add(doc, "Part::Box", "left_rail", "Left Rail")
set_box(
    left_rail,
    plate_width,
    rail_width,
    rail_height,
    App.Placement(App.Vector(0, rail_inset, plate_thickness), App.Rotation()),
)
set_color(left_rail, (0.23, 0.44, 0.72))
set_visible(left_rail, True)

right_rail = get_or_add(doc, "Part::Box", "right_rail", "Right Rail")
set_box(
    right_rail,
    plate_width,
    rail_width,
    rail_height,
    App.Placement(
        App.Vector(0, plate_depth - rail_inset - rail_width, plate_thickness),
        App.Rotation(),
    ),
)
set_color(right_rail, (0.23, 0.44, 0.72))
set_visible(right_rail, True)

doc.recompute()
