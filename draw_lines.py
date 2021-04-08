from config import Config
from constants import PIXEL_WIDTH, WHITE
from segmentation import SegmentedImage
from tuples import Size
from PIL import Image, ImageDraw

# TODO: Refactor data structures:
# 1. Right now I have a list of lines, which are each a list of points.
#    First, create a structure to represent a segmented color, which has
#    a copy of the possible lines
# 2. For each color, store a 2d array of points to lines, and a "rank", which is just
#    the number of non-white pixels. Finally, store a sorted list of lines,
#    using a new structure:
# 3. Create a line class, which stores a list of points, and exposes a "score",
#    which is the number of non-white pixels.
# 4. Every time a segmented color calculates a best fit line, use the 2d point
#    array to recalculate the score of each line containing every point on the line.
#    Then re-sort the lines. This should be much quicker, because none of the scores
#    need to be calculated, and most of the lines should already be in the right place.
#
# Note: Exposing the segmented color rank would allow me to weight the colors during
#   rendering (right now they're weighted equally).
#
# If I wanted to be really cool I could thread the rendering in a coroutine, and
#   implement locking on certain things so that I could save the current render on
#   demand. Maybe even see if I abuse output buffering to display a render progress
#   that updates instead of printing a new line.
#
# Another idea - maybe output line scores as the rendering progresses, and base
#   script termination off of that instead of number of iterations.
#
# Open question - Right now big blotches are prioritized. How can I feature smaller
#   details?
#   - Maybe consider progressively larger concentric circles?
#
# Another random thought - I should check to make sure the resolution of the sources
#   is high enough to keep lines from overlapping too often. There's probably a
#   fairly small window I need to be in.
#
# Another random thought - I should try to do a pass on the segmented input image
#   to increase the minimum blob size. In other words, I don't want a single
#   isolated color pixel within a different color.

# Parse args
_config = Config()

def _get_title(iteration: int) -> str:
    return _config.output_path.absolute() + "/output" + str(_config.width) + "W-" + str(_config.nails) + "N-" + str(iteration) + ".png"

print("Initializing...")

# Get board size
_pixel_width = int(_config.width / PIXEL_WIDTH)
_pixel_size = Size._make((_pixel_width,) * 2)

_segmented_image = SegmentedImage(_config, _pixel_size)
_canvas = Image.new("RGB", _pixel_size, color=WHITE)
_output = ""

print("Rendering...")

for iteration in range(_config.lines):
    if (iteration % (int(_config.lines / 10)) == 0):
        output += "\n --- " + str(iteration) + " --- \n"

        if (_config.verbose):
            title = _get_title(iteration)
            print(title)
            _canvas.save(title)

    segmented_color = _segmented_image.next_color()
    if (segmented_color == None):
        print("Ran out of pixels in the source image!")
        break

    line = segmented_color.next_line()
    ImageDraw.Draw(_canvas).line((*line[0], *line[-1]), fill=segmented_color.color())
    
    startIndex, endIndex = (_segmented_image.nails().index(line[0]), _segmented_image.nails().index(line[-1]))

    output += "(" + str(_segmented_image.index(segmented_color) + 1) + "::" + str(startIndex) + "->" + str(endIndex) + ") "
    print("Iteration " , iteration + 1 , " complete")

print("Iteration " , _config.lines , " complete")