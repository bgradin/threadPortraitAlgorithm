# This is my first attempt at writing code in Python - please don't judge 😂😭

from PIL import Image, ImageOps, ImageDraw
from skimage.draw import line
import numpy as np
import os
import sys

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

def getTitle(iteration):
    return OUTPUT_DIRECTORY + "/output" + str(BOARD_WIDTH) + "W-" + str(PIXEL_WIDTH) + "P-" + str(NUM_NAILS) + "N-" + str(iteration) + "-" + str(LINE_TRANSPARENCY) + ".png"

def findBestNailPair(nails, imageArray):
    bestStartNailIndex = None
    bestEndNailIndex = None
    maxHitRatio = 0
    for startNailIndex in range(len(nails)):
        startNail = nails[startNailIndex]

        for endNailIndex in range(startNailIndex + MINIMUM_NAIL_DISTANCE, startNailIndex + len(nails) - MINIMUM_NAIL_DISTANCE):
            endNailIndex = endNailIndex % NUM_NAILS
            testLine = line(nails[startNailIndex][0], nails[startNailIndex][1], nails[endNailIndex][0], nails[endNailIndex][1])
            testLineLength = len(testLine[0])

            # Calculate number of points line hits
            lineScore = 0
            for i in range(testLineLength):
                pixelColor = imageArray[int(testLine[0][i]), int(testLine[1][i])]
                if (pixelColor[0] != 255 or pixelColor[1] != 255 or pixelColor[2] != 255):
                    lineScore += 1

            # Use the nail which hits the most colored pixels
            hitRatio = lineScore / testLineLength
            if hitRatio > maxHitRatio:
                bestStartNailIndex = startNailIndex
                bestEndNailIndex = endNailIndex
                maxHitRatio = hitRatio

    return (bestStartNailIndex, bestEndNailIndex) if maxHitRatio > 0 else None

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
    if (iteration % 100 == 0):
        output += "\n --- " + str(iteration) + " --- \n"

        if (DEBUG):
            title = getTitle(iteration)
            print(title)
            finalImage.save(title)

    for index in range(len(segmentedImages)):
        segmentedImage = segmentedImages[index]
        segmentedImageArray = segmentedImage.load()

        pair = findBestNailPair(nails, segmentedImageArray)
        if (pair != None):
            startNail = nails[pair[0]]
            endNail = nails[pair[1]]
            lineCoordinates = (startNail[0], startNail[1], endNail[0], endNail[1])

            # Remove line from source
            segmentedImageCanvas = ImageDraw.Draw(segmentedImage)
            segmentedImageCanvas.line(lineCoordinates, fill=WHITE)

            # Add line to canvas
            finalImageCanvas = ImageDraw.Draw(finalImage)
            finalImageCanvas.line(lineCoordinates, fill=segmentedImageColors[index])

            output += "(" + str(index + 1) + "::" + str(pair[0]) + "->" + str(pair[1]) + ") "
    
    print("Iteration " , iteration + 1 , " complete")

print("Iteration " , MAX_ITERATIONS , " complete")

# Save everything
results = open(OUTPUT_DIRECTORY + "/results.txt", "w")
results.write(output)
results.close()
finalImage.save(getTitle(MAX_ITERATIONS))
