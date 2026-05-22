"""Example FreeCAD model script for the folder-watch agent."""

import FreeCAD as App
import Part


doc = App.ActiveDocument or App.newDocument("AgentExample")

base = Part.makeBox(90, 56, 6)

holes = []
for x in (18, 45, 72):
    holes.append(Part.makeCylinder(6, 12, App.Vector(x, 28, -3)))

rounded_corners = [
    Part.makeCylinder(8, 12, App.Vector(0, 0, -3)),
    Part.makeCylinder(8, 12, App.Vector(90, 0, -3)),
    Part.makeCylinder(8, 12, App.Vector(0, 56, -3)),
    Part.makeCylinder(8, 12, App.Vector(90, 56, -3)),
]

shape = base
for hole in holes:
    shape = shape.cut(hole)

for corner in rounded_corners:
    shape = shape.fuse(corner.common(base))

plate = doc.addObject("Part::Feature", "perforated_plate")
plate.Label = "Perforated Plate"
plate.Shape = shape

rail_left = doc.addObject("Part::Feature", "left_rail")
rail_left.Label = "Left Raised Rail"
rail_left.Shape = Part.makeBox(90, 4, 8, App.Vector(0, 5, 6))

rail_right = doc.addObject("Part::Feature", "right_rail")
rail_right.Label = "Right Raised Rail"
rail_right.Shape = Part.makeBox(90, 4, 8, App.Vector(0, 47, 6))

for obj, color in (
    (plate, (0.72, 0.76, 0.82)),
    (rail_left, (0.2, 0.44, 0.72)),
    (rail_right, (0.2, 0.44, 0.72)),
):
    if hasattr(obj, "ViewObject"):
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.Transparency = 0

doc.recompute()
