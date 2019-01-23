import os.path
import glob
import lxml.etree as ET
import re
import typing
import pprint
import pickle

from collections import namedtuple

import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.patches as patches

sns.set(color_codes=True)

# Constants that changes the directory on which the script is run
DEV = "input"
PROD = "../anthologia/tif"
MODE = PROD
# Constants to read files
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
# Define useful regexes
BBOX = re.compile(r"^bbox (\d+) (\d+) (\d+) (\d+)")
SPACE = re.compile(r"\s+")
TITLE = re.compile(r"^([A-Z0l1 \.]+)( +\d+)?$")  # l = I sometimes...
POEM_NUMBER = re.compile(r"^[IVXCl0-9\.]+[ᵃᵇᶜᵈᵉ]?$")
MANUSCRIPT = re.compile(r"^([A-Z01l]+ )+[0-9]+\.( *\d+)?$")
LEFT_RIGHT_NOTES = re.compile(r"^(([IVlX0-9]+,?) ?|([A-Za-z0-9]{1,3}[\.]) ?)+\.?$")
FOLIO = re.compile(r"^f?ol\.? [l\d]+$")
LINE = re.compile(r"^.*[a-zA-Z]+.*")  # at least one character
LINE_NUMBER = re.compile(r"^[0-9OIl]+$")
MISSING_LINE = re.compile(r"^(\. ?)+$")
PROBABLY_NON_TEXT = re.compile(r"^(\w{1,3}[\. ]{1,2})+$")


_Bbox = namedtuple("Bbox", ["x1", "y1", "x2", "y2"])
_Size = namedtuple("Size", ["width", "height"])
_Line = namedtuple("Line", ["text", "type", "bbox", "size", "centered", "small", "color"])
Regex = namedtuple("Regex", ["regex", "type", "color", "centered"])


class Size(_Size):
    def small_width(self, page_size: "Size") -> bool:
        """ Checks that the current size is very small compared to the page size
        """
        return 0.3 > self.width / page_size.width

    def nearly_same_height_as(self, other_size: "Size") -> bool:
        """ Checks that two boxes are similar heights """
        margin = 0.1
        return (1-margin) < self.height / other_size.height < (1+margin)


class Bbox(_Bbox):
    def contains(self, other_bbox: "Bbox") -> bool:
        """ Checks that this box contains the other box
        """
        return self.x1 <= other_bbox.x1 and self.x2 >= other_bbox.x2 and \
            self.y1 <= other_bbox.y1 and self.y2 >= other_bbox.y2

    def intersect(self, other_bbox: "Bbox") -> bool:
        """ Checks that this box and the other box collides
        """
        pass

    def centered_within(self, page_box: "Bbox") -> bool:
        """ Checks that the current box is centered within the page
        """
        remaining_left = self.x1
        remaining_right = page_box.x2 - self.x2
        # If the left space / right space ratio is nearly equal to one
        # Then it's centered
        return 0.85 < remaining_left / remaining_right < 1.15

    @classmethod
    def merge_bbox(cls, n: "Bbox", m: "Bbox") -> "Bbox":
        """ Merge two Bbox """
        return cls(
            min(n.x1, m.x1),
            min(n.y1, m.y1),
            max(n.x2, m.x2),
            max(n.y2, m.y2)
        )


class Line(_Line):
    def nearly_same_baseline(self, other: "Line") -> bool:
        """ Checks that two items are roughly on the same line """
        # The margin should be equal to a fifth of the size of the line maximum
        ratio_height = 0.20
        margin = ratio_height * self.size.height
        # The baseline or the top line should be in this margin
        return abs(self.bbox.y2 - other.bbox.y2) < margin or \
               abs(self.bbox.y1 - other.bbox.y1) < margin

    @classmethod
    def merge(cls, one, other):
        bbox = Bbox.merge_bbox(one.bbox, other.bbox)
        size = Size(*compute_size_bbox(*bbox))
        return cls(
            text=SPACE.sub("", one.text + " " + other.text),
            bbox=bbox,
            size=size,
            type=one.type,
            centered=False,
            small=False,
            color=one.color
        )

    @classmethod
    def change_type(cls, line, _type):
        attrs = list(line)
        attrs[1] = _type
        return cls(*tuple(attrs))


class Color:
    """ Color classes for the layout impression """
    SIDE_DATA = "red"
    TEXT = "blue"
    HEADER = "green"
    TITLES = "grey"
    UNCLASSED = "black"

# List of Regexes to run in the best order possible.
REGEXES = [
    Regex(POEM_NUMBER, "Poem Number", Color.TITLES, centered=True),
    Regex(LINE_NUMBER, "Number", Color.SIDE_DATA, centered=False),
    Regex(TITLE, "Poem Title", Color.TITLES, centered=False),
    Regex(LEFT_RIGHT_NOTES, "Notes", Color.SIDE_DATA, centered=False),
    Regex(FOLIO, "Folio", Color.SIDE_DATA, centered=False),
    Regex(MANUSCRIPT, "Mss Number", Color.HEADER, centered=False),
    Regex(MISSING_LINE, "Missing Line", Color.TEXT, centered=False),
    Regex(PROBABLY_NON_TEXT, "Prob non text", Color.UNCLASSED, centered=False),
    Regex(LINE, "Poem Line", Color.TEXT, centered=False)
]
DEFAULT = Regex(None, "NOT MATCHED", Color.UNCLASSED, centered=False)


# Different constants related to the dataset.
#   Headers are often in the 0 0 Page_width 70 BBOX
#   Except for page 0361
# The DPI is a trick to show the image in the exported layout
# See notes.md for the sizes
PageHeaderBboxMaker = lambda page_width: Bbox(0, 0, page_width, 70)
HeaderExceptions = ["0361"]
SMALL_BOX_HEIGHT = 20
DPI = 96


def parse_bbox(element: ET.Element) -> typing.Tuple[int, int, int, int]:
    """ Based on an etree element, get the attribute @title and
    parses it into 4 different pixel number representing the bbox"""
    bbox = element.attrib.get("title")
    return tuple([int(x) for x in BBOX.findall(bbox)[0]])


def compute_size_bbox(x1: int, y1: int, x2: int, y2: int) -> typing.Tuple[int, int]:
    """ Based on a bbox coordinates, computes the size (in pixel) of the bbox"""
    return x2-x1, y2-y1


def get_text(element: ET.Element) -> str:
    """ Retrieves the text from within an etree element and cleans it.
    """
    return SPACE.sub(" ", " ".join(element.xpath('.//text()'))).strip()


def run_stats():
    sizes = []
    xs = []
    pages = {}
    # Change MODE to change direction
    for file in glob.glob(os.path.join(DIRECTORY, MODE, "*.hocr")):
        # Parse the XML file
        with open(file) as io:
            xml = ET.parse(io)

        # Get a simple string representing the file, basically what's before .hocr in the
        # filename
        index = os.path.basename(file).split(".")[0]
        # Set-up an empty list for this page in the pages dictionary
        pages[index] = []

        # Compute and store the BBOX of the page
        page_bbox = Bbox(*parse_bbox(xml.findall("//div[@class='ocr_page']")[0]))
        # Compute the size of the page
        page_size = Size(*compute_size_bbox(*page_bbox))

        # Compute the Bbox of the header for the current page (See PageHeaderBboxMaker up there)
        header_boundaries = PageHeaderBboxMaker(page_size.width)

        # Retrieve each line
        for line in xml.findall('//span[@class="ocr_line"]'):
            # Compute the bbox for the current line
            bbox = Bbox(*parse_bbox(line))
            # Compute the size of the Bbox
            size = Size(*compute_size_bbox(*bbox))
            # Get the text of the line and clean it
            text = get_text(line)
            # If we have a square that is not empty
            # Store some statistics. Feelin is the ratios based on the page size
            # are good indicators but not perfect.
            # Hence using mostly regexes
            if text and size.width and size.height:
                sizes.append((size.height/size.width, len(text)))
                xs.append((bbox.x1/page_size.width, len(text)))
            # Other wise, skip this element in the loop and go to the next line
            else:
                continue

            # We compute if the line is centered
            centered = bbox.centered_within(page_bbox)

            # If this lines is part of the header
            # Then class it as Header
            #   Except if it has been manually marked as a page that has something else in
            #       this bbox
            if header_boundaries.contains(bbox) and index not in HeaderExceptions:
                t = "Header"
                color = Color.HEADER
            # If this is really small in height, it ought to be a side note
            elif size.height <= SMALL_BOX_HEIGHT:
                t = "Side note"
                color = Color.SIDE_DATA
            # Otherwise, let's go use some loops
            else:
                for regex in REGEXES:
                    # If the regex class matches
                    if regex.regex.match(text):
                        # If the regex class require the text to be centered
                        #   but the text is not, then it moves to the next regex class
                        if regex.centered and not centered:
                            continue
                        t = regex.type
                        color = regex.color
                        break
                # if it was not found, we move it to default
                else:
                    t = DEFAULT.type
                    color = DEFAULT.color

            # We save the line into the dictionary
            pages[index].append(
                Line(text, t, bbox, size, centered=centered,
                     small=size.small_width(page_size), color=color)
            )

        # This part is responsible for producing a color layout
        # based on the classification we just made

        # We create a figure
        # matplotlib does not accept pixels as figsize, so we divide our pixel by the DPI
        # of the output we want. Here, our screen is 96 dpi so we did set up the DPI constant to 96
        # It is important to note that
        #       Pixels / DPI = Inch
        fig = plt.figure(figsize=(page_size.width/DPI, page_size.height/DPI), dpi=DPI)
        # We add an axes from 0 0 to 1 1
        ax = fig.add_axes([0, 0, 1, 1])
        # We sort the items first by vertical position and then by horizontal position
        sorted_items = sorted(pages[index], key=lambda l: (l.bbox.y1, l.bbox.x1))
        pages[index] = sorted_items
        # We keep an index for later purposes
        for index_item, item in enumerate(sorted_items):
            # We compute the left bottom coordinate of the bbox
            #   because this is the starting point for Rectangle in matplotlib
            # Coordinates needs to be divided by the page width and height
            #   to fit the [0,1] range of Xs and Ys of the axes
            # Because matplotlib starts from the left-bottom
            #   but hocr starts from the left-top, we need to substract to 1 (the max Y)
            #   the calculated y
            left_bottom = (item.bbox.x1/page_size.width, 1-item.bbox.y2/page_size.height)
            # We create a rectangle fitting once more the xs and ys based on the [0,1] ranges
            # We assign a color based on the line color class
            p = patches.Rectangle(
                left_bottom,
                item.size.width/page_size.width, item.size.height/page_size.height,
                color=item.color
            )
            # We add some text aligned on the left bottom point.
            # Currently, the text is the index in which it was sorted
            ax.text(*left_bottom, str(index_item),
                    horizontalalignment='left',
                    verticalalignment='bottom',
                    transform=ax.transAxes)
            # We add this rectangle to the axes
            ax.add_patch(p)

            # Check that we should merge with the next line
            # We check we have a next item
            if index_item + 1 < len(sorted_items):
                # We store the next item in a variable for conveniance
                next_item = sorted_items[index_item + 1]

                # If the items have roughly the same size
                #   and start or end on the same vertical line, and have
                #   the same time, they are probably the same line.
                if item.size.nearly_same_height_as(next_item.size) and \
                    item.nearly_same_baseline(next_item) and item.type == next_item.type:
                    # We merge the Bbox-es
                    new_bbox = Bbox.merge_bbox(item.bbox, next_item.bbox)
                    # We compute the new size of the Bbox
                    new_size = Size(*compute_size_bbox(*new_bbox))
                    # We generated the new left_bottom point for our dear matplotlib
                    left_bottom = (new_bbox.x1/page_size.width, 1-new_bbox.y2/page_size.height)
                    # We generated the rectangle but only with a border
                    p = patches.Rectangle(
                        left_bottom,
                        new_size.width / page_size.width, new_size.height / page_size.height,
                        color=item.color, fill=False
                    )
                    ax.add_patch(p)

        # We save the fig
        plt.savefig("output/layout_{}.png".format(index))
        # We close the fig
        plt.close(fig)
    with open("analysis.pickle", "wb") as target_file:
        pickle.dump(pages, target_file)


if __name__ == "__main__":
    run_stats()
