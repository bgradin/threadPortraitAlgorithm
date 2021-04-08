from collections import namedtuple

Point_ = namedtuple("Point", ["x", "y"])
class Point(Point_):
    """A point in on the cartesian plane."""
    pass

Size_ = namedtuple("Size", ["width", "height"])
class Size(Size_):
    """A two-dimensional size (width and height)."""
    pass

Color_ = namedtuple("Color", ["r", "g", "b"])
class Color(Color_):
    """An RGB color."""
    pass