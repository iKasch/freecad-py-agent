"""Second example model for testing session document reuse."""

import FreeCAD as App
import Part


doc = DOC

base = doc.addObject("Part::Feature", "base")
base.Label = "Marker Base"
base.Shape = Part.makeBox(42, 42, 5)

post = doc.addObject("Part::Feature", "center_post")
post.Label = "Center Post"
post.Shape = Part.makeCylinder(8, 46, App.Vector(21, 21, 5))

cap = doc.addObject("Part::Feature", "top_cap")
cap.Label = "Top Cap"
cap.Shape = Part.makeCylinder(14, 6, App.Vector(21, 21, 51))

if hasattr(base, "ViewObject"):
    base.ViewObject.ShapeColor = (0.68, 0.72, 0.76)
if hasattr(post, "ViewObject"):
    post.ViewObject.ShapeColor = (0.25, 0.47, 0.75)
if hasattr(cap, "ViewObject"):
    cap.ViewObject.ShapeColor = (0.9, 0.56, 0.18)

doc.recompute()
