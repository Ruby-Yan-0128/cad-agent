from build123d import *


LEG_50 = 50.0
LEG_40 = 40.0
WIDTH = 30.0
THICKNESS = 5.0
INSIDE_FILLET = 3.0
HOLE_DIA = 6.6
HOLE_RADIUS = HOLE_DIA / 2
GUSSET_THICKNESS = 4.0
GUSSET_LENGTH = 25.0
GUSSET_HEIGHT = 25.0
OUTER_CHAMFER = 1.5


with BuildPart() as bracket:
    with Locations((LEG_50 / 2, 0, THICKNESS / 2)):
        Box(LEG_50, WIDTH, THICKNESS)

    with Locations((THICKNESS / 2, 0, LEG_40 / 2)):
        Box(THICKNESS, WIDTH, LEG_40)

    inside_edges = [
        edge
        for edge in bracket.edges().filter_by(Axis.Y)
        if abs(edge.position_at(0.5).X - THICKNESS) < 0.01
        and abs(edge.position_at(0.5).Z - THICKNESS) < 0.01
    ]
    if len(inside_edges) != 1:
        raise ValueError("Could not identify the bracket's inside fillet edge")
    fillet(inside_edges, radius=INSIDE_FILLET)

    chamfer(bracket.edges().filter_by(GeomType.LINE), length=OUTER_CHAMFER)

    with BuildSketch(Plane.XZ):
        Polygon(
            (THICKNESS, THICKNESS),
            (GUSSET_LENGTH, THICKNESS),
            (THICKNESS, GUSSET_HEIGHT),
        )
    extrude(amount=GUSSET_THICKNESS, both=True)

    with Locations((LEG_50 / 2, 0, THICKNESS / 2)):
        Hole(radius=HOLE_RADIUS)

    with Locations((THICKNESS / 2, 0, LEG_40 / 2)):
        Cylinder(
            radius=HOLE_RADIUS,
            height=THICKNESS + 2,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
            rotation=(0, 90, 0),
            mode=Mode.SUBTRACT,
        )

result = bracket.part
