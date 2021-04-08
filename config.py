import os
import sys
from pathlib import Path
from argparse import ArgumentParser
from path import is_path_exists_or_creatable

parser = ArgumentParser(description="Given an input image path and a number of lines, create line art of the image.")
parser.add_argument("file_path",
    metavar="PATH",
    help="path of the image to redraw as lines")
parser.add_argument("lines",
    metavar="INTEGER",
    type=int,
    help="number of lines to draw in the output image")
parser.add_argument("-o", "--output",
    dest="output_path",
    default="",
    metavar="DIRECTORY",
    help="output directory path [default: parent directory path of input file]")
parser.add_argument("-c", "--colors",
    dest="colors",
    metavar="INTEGER",
    type=int,
    default=1,
    help="number of colors [default: %(default)s]")
parser.add_argument("-w", "--width",
    dest="width",
    metavar="INTEGER",
    type=int,
    default=80,
    help="board width, in centimeters [default: %(default)s]")
parser.add_argument("-n", "--nails",
    dest="nails",
    metavar="INTEGER",
    type=int,
    default=300,
    help="number of nails to place evenly around the board [default: %(default)s]")
parser.add_argument("-q", "--quiet",
    action="store_false",
    dest="verbose",
    default=True,
    help="quiet output mode")

class Config:
    def __init__(self):
        args = parser.parse_args()

        file_path = Path(args.file_path)
        if (not(file_path.exists()) or not(file_path.is_file())):
            self.__report_parse_error("invalid input file path")

        output_path = Path(args.output_path) if args.output_path != "" else file_path.parent
        if (output_path.exists() and not(output_path.is_dir())):
            self.__report_parse_error("invalid output directory path")

        if (not(output_path.exists())):
            os.makedirs(output_path.absolute())

        self.file_path = file_path
        self.lines = args.lines
        self.output_path = output_path
        self.colors = args.colors
        self.width = args.width
        self.nails = args.nails
        self.verbose = args.verbose

    def __report_parse_error(self, error: str):
        sys.stderr.write("error: " + error + "\n\n")
        parser.print_help()
        sys.exit(1)
