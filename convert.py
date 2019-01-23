import os.path
import glob
import lxml.etree as ET
import re
import typing
import pprint

from collections import defaultdict

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt



DIRECTORY = os.path.dirname(os.path.abspath(__file__))
BBOX = re.compile("^bbox (\d+) (\d+) (\d+) (\d+)")
SPACE = re.compile("\s+")
TITLE = re.compile("^([A-Z0l1 \.]+)( +\d+)?$")  # l = I sometimes...
SUBNUMBER = re.compile("^[IVXl1\.]+$")
MANUSCRIPT = re.compile("^([A-Z01l]+ )+[0-9]+\.( *\d+)?$")
LEFT_RIGHT_NOTES = re.compile("^(([IVlX0-9]+,?) ?|([A-Za-z0-9]{1,3}[\.]) ?)+\.?$")
FOLIO = re.compile("^f?ol\.? [l\d]+$")
LINE = re.compile("^.*[a-zA-Z]+.*")  # at least one character
LINE_NUMBER = re.compile("^[0-9O]+$")
MISSING_LINE = re.compile("^(\. ?)+$")
PROBABLY_NON_TEXT = re.compile("^(\w{1,3}[\. ]{1,2})+$")
sns.set(color_codes=True)
REGEXES = [
    (SUBNUMBER, "Poem Number"),
    (TITLE, "Poem Title"),
    (LEFT_RIGHT_NOTES, "Notes"),
    (FOLIO, "Folio"),
    (LINE_NUMBER, "Line Number"),
    (MANUSCRIPT, "Mss Number"),
    (MISSING_LINE, "Missing Line"),
    (PROBABLY_NON_TEXT, "Prob non text"),
    (LINE, "Poem Line")
]
DEFAULT = "NOT MATCHED"


def parse_bbox(element: ET.Element) -> typing.Tuple[int, int, int, int]:
    bbox = element.attrib.get("title")
    return tuple([int(x) for x in BBOX.findall(bbox)[0]])


def compute_size_bbox(x1: int, y1: int, x2: int, y2: int) -> typing.Tuple[int, int]:
    return x2-x1, y2-y1


def get_text(element: ET.Element) -> str:
    return SPACE.sub(" ", " ".join(element.xpath('.//text()'))).strip()


def run_stats():
    sizes = []
    xs = []
    pages = {}
    for file in glob.glob(os.path.join(DIRECTORY, "input", "*.hocr")):
        with open(file) as io:
            xml = ET.parse(io)

        index = os.path.basename(file)
        pages[index] = defaultdict(list)

        p_width, p_height = compute_size_bbox(
            *parse_bbox(xml.findall("//div[@class='ocr_page']")[0])
        )

        for line in xml.findall('//span[@class="ocr_line"]'):
            x1, y1, x2, y2 = parse_bbox(line)
            width, height = compute_size_bbox(x1, y1, x2, y2)
            text = get_text(line)
            if text and width and height:
                sizes.append((height/width, len(text)))
                xs.append((x1/p_width, len(text)))
                #pages[index].append((height/width, x1/p_width, text))
            else:
                continue
                # print("Weird bbox [{}] {}".format(text, (x1, y1, x2, y2)))

            x_ratio = x1 / p_width
            for reg, title in REGEXES:
                if reg.match(text):
                    pages[index][title].append(text)
                    break
            else:
                pages[index][DEFAULT].append(text)

    df = pd.DataFrame(xs, columns=["Partition", "Text Length"])
    plot = sns.jointplot(x="Partition", y="Text Length", data=df)
    df = pd.DataFrame(sizes, columns=["BBox Ration h/W", "Text Length"])
    plot = sns.jointplot(x="BBox Ration h/W", y="Text Length", data=df)
    plt.show()

    pprint.pprint(pages)
run_stats()