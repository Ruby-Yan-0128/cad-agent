from build123d import *

LENGTH = 60.0
WIDTH = 40.0
THICKNESS = 8.0
HOLE_DIA = 6.0

with BuildPart() as bracket:
    Box(LENGTH, WIDTH, THICKNESS)
    fillet(bracket.edges().filter_by(Axis.Z), radius=5.0)
    with Locations((-20, 0), (20, 0)):
        Hole(radius=HOLE_DIA / 2)

result = bracket.part