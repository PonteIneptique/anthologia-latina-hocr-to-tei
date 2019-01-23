from analyze_layout import *
from copy import deepcopy

with open("analysis.pickle", "rb") as f:
    data = pickle.load(f)


FULL = """<TEI>
    <teiHeader>
    </teiHeader>
    <body>
        {content}
        </div>
    </body>
</TEI>"""
PAGE = """<pb type="image" n="{pb_id}" />
"""
content = ""

tab = ""
first_div = True
last_how_many = 10
last_types = [None] * last_how_many

number_mistakes = r"[0-9Ol]"
LINE_NUMBER_IN_TEXT = re.compile(r"^("+number_mistakes+"+) (.*)$|^([A-Za-z].+) ("+number_mistakes+"+)$")
PAGE_NUMBER_IN_TEXT = re.compile(r"^(p\. [0-9Ol]+) (.*)$|^([A-Za-z].+) (p\. [0-9Ol]+)$")


def merge_lines(cursor: Line, nexts: typing.List[Line]) -> typing.Tuple[Line, typing.List[int]]:
    """ Merge lines if they should (baseline + type checking).

    :param cursor: Current line
    :param nexts: Few next lines to check
    :return: Merged lines and index to pop (desc)
    """
    to_pop = []
    for index_line, line in enumerate(nexts):
        if cursor.type == line.type and \
                cursor.nearly_same_baseline(line):
            cursor = Line.merge(cursor, line)
            to_pop.append(index_line)
    return cursor, to_pop[::-1]


# We do some post-correction of typing first
for page in sorted(data.keys()):
    lines = [deepcopy(x) for x in data[page]]
    news = []
    # As long as I have lines
    while lines:
        # I get the first of the lines from the list
        current = lines.pop(0)

        # First of all, if there is at least " . ." once in there, it is probably a line
        if " . ." in current.text and current.type != "Poem Line":
            current = Line.change_type(current, "Poem Line")

        news.append(current)
    data[page] = news

# For each page
for page in sorted(data.keys()):
    lines = [] + data[page]
    content += tab+PAGE.format(pb_id=page)
    # As long as I have lines
    while lines:
        # I get the first of the lines from the list
        current = lines.pop(0)

        # If this is a header
        if current.type == "Header":
            # And if this is a line number
            if LINE_NUMBER.match(current.text):
                # We treat it as a page beginning
                content += tab+"""<pb type="page" n="{}" />\n""".format(current.text)
            else:
                # Otherwise, it's a fw
                content += tab+"<fw>{}</fw>\n".format(current.text)
        # If it's a poem number
        elif current.type == "Poem Number":
            # If it is not the first div
            #   we close it
            if not first_div:
                content += "</div>\n"
            # We create a new div and use the number as @n
            content += """<div type="textpart" subtype="poem" n="{}">\n""".format(current.text)
            tab = "\t"
            first_div = False
        # Ignore lines numbers
        # If it is a line number, we defintely ignore it
        elif current.type == "Number":
            continue
        # If this is a title
        elif current.type == "Poem Title":
            # If we did not have a title for a long time
            # We create a div
            if "Poem Number" not in last_types:
                if not first_div:
                    content += "</div>\n"
                first_div = False
                content += """<div type="textpart" subtype="poem">\n"""

            # Whatever happens, we create a <head>
            content += tab + """<head>{text}</head>\n""".format(text=current.text)

        # If it is not a line, it's probably a note
        elif current.type != "Poem Line":
            content += tab+"""<note type="{type}">{text}</note>\n""".format(
                type=current.type, text=current.text
            )
        # If it is a line
        else:
            # We first check that the line number or a note did not go inside here
            nexts = lines[:10]
            while nexts:
                current, to_pop = merge_lines(current, nexts)
                if to_pop:
                    for index_to_pop in to_pop:
                        lines.pop(index_to_pop)
                    nexts = []
                else:
                    nexts = False
            text = current.text
            attribs = ""
            # If we have a page number or so, we separate it
            if PAGE_NUMBER_IN_TEXT.match(text):
                page1, text1, text2, page2 = PAGE_NUMBER_IN_TEXT.findall(text)[0]
                text = text1 + text2
                content += tab+"""<milestone n="{}" unit="page" />\n""".format(page1+page2)
            # If we have a line number ending or starting the line, we set it as attribute
            if LINE_NUMBER_IN_TEXT.match(text):
                ln1, text1, text2, ln2 = LINE_NUMBER_IN_TEXT.findall(text)[0]
                text = text1 + text2
                attribs = """ n="{}" """.format(ln1+ln2)

            content += tab+"""<l{attribs}>{text}</l>\n""".format(text=text, attribs=attribs)

        last_types = [current.type] + last_types[:-1]

with open("output.xml", "w") as f:
    f.write(FULL.format(content=content.replace("\n", "\n        ")))
