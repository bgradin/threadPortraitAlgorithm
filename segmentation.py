import json
from typing import Iterable, List, Tuple
from config import Config
from constants import PIXEL_WIDTH, WHITE
from tuples import Color, Point, Size
from util import flatten
from PIL import Image, ImageDraw
import numpy as np

class Line:
    """A linear set of points on the cartesian plane."""
    def __init__(self, points: List[Point]):
        self.__points = points

    def rescore(self, colored_points: Iterable[Point]):
        self.__score = len(p for p in self.__points if p in colored_points) / len(self.__points)

    def points(self) -> List[Point]:
        return self.__points

    def score(self) -> float:
        return self.__score

class LineEncoder(json.JSONEncoder):
    def default(self, line):
        return line.__dict__

class LineDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.hook, *args, **kwargs)

    def hook(self, dct):
        if (not("__points" in dct)):
            raise TypeError("Invalid json")
        
        return json.loads(dct["__points"])

def _get_all_indices(size: Size) -> Iterable[Tuple]:
    return flatten([list(range(size.height))] * size.width)

def _get_all_points(img: Image) -> Iterable[Point]:
    return (map(Point._make, _get_all_indices(Size._make(img.size))))

def _get_all_colored_points(img: Image) -> Iterable[Point]:
    pixels = img.load()
    return (point for point in _get_all_points(img) if pixels[point.x, point.y] != WHITE)

class SegmentedColor:
    """A single color within an image."""
    def __init__(self, img: Image, lines: List[Line], color: Color):
        self.__image = img
        self.__lines = json.loads(json.dumps(lines))
        self.__color = color

        self.__update()

    def __update(self):
        colored_points = _get_all_colored_points(self.__image)
        self.__score = len(colored_points)

        for line in self.__lines:
            line.rescore()

        self.__lines = sorted((line for line in self.__lines if line.score > 0), key=lambda line: line.score(), reverse=True)
        self.__points_to_lines = {point:set(line for line in self.__lines if point in line.points()) for point in colored_points}

    def next_line(self) -> Line:
        return self.__lines[0] if self.__lines else None

    def remove(self, line: Line):
        ImageDraw.Draw(self.__image).line((*line.points()[0], *line.points()[-1]), fill=WHITE)
        self.__lines.remove(line)
        self.__update()

    def color(self) -> Color:
        return self.__color

    def image(self) -> Image:
        return self.__image

    def score(self) -> int:
        return self.__score

def _sort_points(p1: Point, p2: Point) -> Tuple[Point, Point]:
    """Sort two points based on which one is closer to (0, 0) on the cartesion plane."""
    return (p2, p1) if ((p1.x > p2.x) or ((p1.x == p2.x) and (p1.y > p2.y))) else (p1, p2)

def _get_all_points_on_line(p1: Point, p2: Point) -> Iterable[Point]:
    """Inclusively return all points between two points."""

    # Make sure we don't negatively iterate or divide by zero
    p1, p2 = _sort_points(p1, p2)

    # Special cases for equal points or vertical lines
    if ((p1.x == p2.x) and (p1.y == p2.y)):
        return [Point(p1.x, p1.y)]
    elif (p1.x == p2.x):
        return [Point(p1.x, y) for y in range(p1.y, p2.y + 1)]

    slope = (p2.y - p1.y) / float(p2.x - p1.x)
    return list(map(Point._make, [(x + p1.x, int(round(x * slope + p1.y))) for x in range(p2.x - p1.x + 1)]))

def _get_palette(img: Image) -> List[Color]:
    return list(map(Color._make, np.array(img.getpalette(), dtype=np.uint8).reshape(-1, 3).tolist()))

def _crop_to_circle(img: Image) -> Image:
    mask = Image.new('L', img.size, 0).resize(img.size)
    ImageDraw.Draw(mask).ellipse((0, 0) + img.size, fill=255)
    return Image.composite(img.convert("RGB"), Image.new("RGB", img.size, color=WHITE), mask)

def _isolate_color(img: Image, palette: Iterable[Color], palette_index: int) -> Image:
    new_palette = [255] * (3 * len(palette))
    new_palette[palette_index:palette_index + 3] = palette[palette_index]

    copy = img.copy()
    copy.putpalette(new_palette)
    return copy

def _calculate_distance(p1: Point, p2: Point) -> float:
    return (((p2.x - p1.x) ** 2) + ((p2.y - p1.y) ** 2)) ** 0.5

def _get_all_ending_points(point: Point, points: Iterable[Point]) -> Iterable[Tuple[Point, Point]]:
    return ((point, end) for end in points if _calculate_distance(point, end) > 20)

def _get_all_point_pairs(points: Iterable[Point]) -> Iterable[Tuple[Point, Point]]:
    return flatten(_get_all_ending_points(point, points) for point in points)

def _get_all_unique_point_pairs(points: Iterable[Point]) -> Iterable[Tuple[Point, Point]]:
    return set(_sort_points(*pair) for pair in _get_all_point_pairs(points))

def _get_all_lines(points: Iterable[Point]) -> Iterable[Line]:
    return (Line(list(_get_all_points_on_line(*pair))) for pair in _get_all_unique_point_pairs(points))

def _float_to_int(iterable: Iterable[float]) -> Iterable[int]:
    return (int(i) for i in iterable)

class SegmentedImage:
    """An image, segmented by color."""
    def __init__(self, config: Config, size: Size):
        if (not(isinstance(config, Config))):
            raise TypeError("Invalid configuration object passed to SegmentedImage")

        # Calculate all possible lines between nails
        center = (size.width / 2, size.height / 2)
        radius = min(size) / 2
        angles = np.linspace(0, 2 * np.pi, config.nails)
        xs = _float_to_int(center[0] - np.cos(angles) * radius)
        ys = _float_to_int(center[1] - np.sin(angles) * radius)
        self.__nails = list(map(Point._make, zip(xs, ys)))
        lines = list(_get_all_lines(self.__nails))

        # Load image
        image = Image.open(config.file_path).resize(size).convert("P", palette=Image.ADAPTIVE, colors=config.colors + 1)
        self.__image_palette = _get_palette(image)[0:config.colors + 1]

        # Segment colors
        self.__colors = []
        for x in range(len(self.__image_palette)):
            cropped_isolated_color = _crop_to_circle(_isolate_color(image, self.__image_palette, x))
            self.__colors.append(SegmentedColor(cropped_isolated_color, lines, self.__image_palette[x]))

        if (config.verbose):
            image.save(config.output_path.absolute() + "/segmented.png")
            rawmode = image.palette.rawmode    # Backup
            image.palette.rawmode = None       # not sure why this is necessary but it is
            image.palette.save(config.output_path.absolute() + "/palette.txt")
            image.palette.rawmode = rawmode    # Restore

            for index, color in enumerate(self.__colors):
                color.image().save(config.output_path.absolute() + "/segmented-color-" + str(index) + ".png")

    def next_color(self) -> SegmentedColor:
        self.__colors = sorted((color for color in self.__colors if color.score() > 0), key=lambda color: color.score(), reverse=True)
        return self.__colors[0] if self.__colors else None

    def index(self, color: SegmentedColor):
        return self.__image_palette.index(color.color())

    def nails(self) -> List[Point]:
        return self.__nails
