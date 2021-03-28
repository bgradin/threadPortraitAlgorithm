# This is my first attempt at writing code in Python - please don't judge 😂😭

from PIL import Image, ImageOps, ImageDraw
from skimage.draw import line
import numpy as np
import os
import sys

# TODO: Refactor to use optparse
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

# Section: script arguments
args = sys.argv
IMAGE_PATH = str(args[1])
NUM_COLORS = int(args[2])
BOARD_WIDTH = int(args[3])          #CM
PIXEL_WIDTH = float(args[4])        #ex: 0.1 - suggest keeping this constant and changing board width only
LINE_TRANSPARENCY = float(args[5])  #value between 0 to 1
NUM_NAILS = int(args[6])
MAX_ITERATIONS = int(int(args[7]) / NUM_COLORS)
DEBUG = bool(args[8])

# Section: constants
MINIMUM_NAIL_DISTANCE = 10
OUTPUT_DIRECTORY = "output"
WHITE = (255, 255, 255)

# Section: Functions
def cropToCircle(img):
    mask = Image.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + img.size, fill=255)
    mask = mask.resize(img.size, Image.ANTIALIAS)
    white_canvas = Image.new("RGB", img.size, color=WHITE)
    output = Image.composite(img.convert("RGB"), white_canvas, mask)
    return output

def imgToPaletteArray(img):
    palette = np.array(img.getpalette(), dtype=np.uint8)
    reshaped = palette.reshape(-1, 3).tolist()
    filtered = filter(lambda x: len(x) == 3 and (x[0] != 0 or x[1] != 0 or x[2] != 0), reshaped)
    return list(filtered)

def isolateColor(img, colorStart):
    palette = imgToPaletteArray(img)
    new_palette = [255] * (3 * len(palette))
    new_palette[(colorStart * 3)]     = palette[colorStart][0]
    new_palette[(colorStart * 3) + 1] = palette[colorStart][1]
    new_palette[(colorStart * 3) + 2] = palette[colorStart][2]

    copy = img.copy()
    copy.putpalette(new_palette)
    return copy

def uniqueTuples(l):
    return list(set([i for i in l]))

def getTitle(iteration):
    return OUTPUT_DIRECTORY + "/output" + str(BOARD_WIDTH) + "W-" + str(PIXEL_WIDTH) + "P-" + str(NUM_NAILS) + "N-" + str(iteration) + "-" + str(LINE_TRANSPARENCY) + ".png"

def getStartIndices(l):
    return list(range(len(l)))

def flatten(l):
    return [idx for sub in l for idx in sub]

def getPointsOnLine(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    if (x1 > x2 or (x1 == x2 and y1 > y2)):
        x1, y1 = p2
        x2, y2 = p1
    if (x1 == x2 and y1 == y2):
        return [(x1, y1)]
    elif (x1 == x2):
        return [(x1, y) for y in range(y1, y2 + 1)]
        
    slope = (y2 - y1) / float(x2 - x1)
    return [(x + x1, int(round(x * slope + y1))) for x in range(0, x2 - x1 + 1)]

def getPossibleLines(startIndex):
    return list(map(lambda x: (startIndex, x % NUM_NAILS), list(range(startIndex + MINIMUM_NAIL_DISTANCE, startIndex + NUM_NAILS - (MINIMUM_NAIL_DISTANCE * 2)))))

def getAllPossibleLines(nails):
    return flatten(list(map(getPossibleLines, getStartIndices(nails))))

def getAllUniquePossibleLines(nails):
    return uniqueTuples(list(map(lambda pair: (pair[0], pair[1]) if pair[0] <= pair[1] else (pair[1], pair[0]), getAllPossibleLines(nails))))

def getLine(l, nails):
    startNailIndex, endNailIndex = l
    return getPointsOnLine(nails[startNailIndex], nails[endNailIndex])

def getLineScore(l, imageArray):
    return len(list(filter(lambda x: imageArray[l[x][0], l[x][1]] != WHITE, range(len(l))))) / len(l)

def sortByLineScore(lines, imageArray):
    return sorted(lines, key=lambda l: getLineScore(l, imageArray), reverse=True)

def findBestLine(allPossibleLines, imageArray):
    return sortByLineScore(allPossibleLines, imageArray)[0]

# Section: script
if not os.path.exists(OUTPUT_DIRECTORY):
    os.makedirs(OUTPUT_DIRECTORY)

pixels = int(BOARD_WIDTH / PIXEL_WIDTH)
size = (pixels + 1, pixels + 1)

finalImage = Image.new("RGB", size, color=WHITE)
angles = np.linspace(0, 2 * np.pi, NUM_NAILS)  # angles to the dots
halfway = BOARD_WIDTH / 2 / PIXEL_WIDTH
nail_x_coords = halfway + (BOARD_WIDTH / 2) * (np.cos(angles) / PIXEL_WIDTH)
nail_y_coords = halfway + (BOARD_WIDTH / 2) * (np.sin(angles) / PIXEL_WIDTH)
nails = list(map(lambda x, y: (int(x), int(y)), nail_x_coords, nail_y_coords))
allPossibleLines = list(map(lambda l: getPointsOnLine(nails[l[0]], nails[l[1]]), getAllUniquePossibleLines(nails)))

sourceImage = Image.open(IMAGE_PATH).resize(size).convert("P", palette=Image.ADAPTIVE, colors=NUM_COLORS)
sourceImagePalette = imgToPaletteArray(sourceImage)

if (DEBUG):
    sourceImage.save(OUTPUT_DIRECTORY + "/segmented.png")
    rawmode = sourceImage.palette.rawmode    # Backup
    sourceImage.palette.rawmode = None       # idk why tf this is necessary but it is, trust me
    sourceImage.palette.save(OUTPUT_DIRECTORY + "/palette.txt")
    sourceImage.palette.rawmode = rawmode    # Restore

# Segment source image by color
segmentedImages = []
segmentedImageColors = []
for x in range(NUM_COLORS):
    segmentedImages.append(cropToCircle(isolateColor(sourceImage, x)))
    segmentedImageColors.append(tuple(sourceImagePalette[x]))
    
    if (DEBUG):
        segmentedImages[x].save(OUTPUT_DIRECTORY + "/segmented-color-" + str(x) + ".png")

# Draw each segmented image as lines of segmented color
output = ""
for iteration in range(MAX_ITERATIONS):
    if (iteration % 10 == 0):
        output += "\n --- " + str(iteration) + " --- \n"

        if (DEBUG):
            title = getTitle(iteration)
            print(title)
            finalImage.save(title)

    for index in range(len(segmentedImages)):
        segmentedImage = segmentedImages[index]
        segmentedImageArray = segmentedImage.load()

        bestLine = findBestLine(allPossibleLines, segmentedImageArray)
        startNail, endNail = (bestLine[0], bestLine[len(bestLine) - 1])
        lineCoordinates = (startNail[0], startNail[1], endNail[0], endNail[1])

        # Remove line from source
        segmentedImageCanvas = ImageDraw.Draw(segmentedImage)
        segmentedImageCanvas.line(lineCoordinates, fill=WHITE)

        # Add line to canvas
        finalImageCanvas = ImageDraw.Draw(finalImage)
        finalImageCanvas.line(lineCoordinates, fill=segmentedImageColors[index])

        output += "(" + str(index + 1) + "::" + str(nails.index(startNail)) + "->" + str(nails.index(endNail)) + ") "
    
    print("Iteration " , iteration + 1 , " complete")

print("Iteration " , MAX_ITERATIONS , " complete")

# Save everything
results = open(OUTPUT_DIRECTORY + "/results.txt", "w")
results.write(output)
results.close()
finalImage.save(getTitle(MAX_ITERATIONS))