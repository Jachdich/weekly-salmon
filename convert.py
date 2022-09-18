import re, sys, datetime, os

def get_regional_indicator(char):
    return chr(0x1f1e6 + ord(char.upper()) - ord("A"))

def discord_to_emojis(txt):
    txt = txt.replace(":scotland:", "🏴󠁧󠁢󠁳󠁣󠁴󠁿")
    txt = txt.replace(":england:", "🏴󠁧󠁢󠁥󠁮󠁧󠁿")
    
    flags = re.findall(r":flag_\w\w:", txt)
    for flag in flags:
        code = flag.replace("flag_", "").strip(":")
        newcode = get_regional_indicator(code[0]) +\
                  get_regional_indicator(code[1])

        txt = txt.replace(flag, newcode)

    return txt

class Bold:
    def __init__(self, text):
        self.text = text
    def gen(self, fmt):
        if fmt == "html": return f"<strong>{self.text}</strong>"
        else: return f"**{self.text}**"

class Italic:
    def __init__(self, text):
        self.text = text
    def gen(self, fmt):
        if fmt == "html": return f"<i>{self.text}</i>"
        else: return f"*{self.text}*"

class Normal:
    def __init__(self, text):
        self.text = text
    def gen(self, fmt):
        return self.text

class FmtText:
    def __init__(self, text):
        self.things = []
        pos = 0
        plain_buf = ""
        while pos < len(text):
            if text[pos] == "*":
                if len(plain_buf) != 0:
                    self.things.append(Normal(plain_buf))
                    plain_buf = ""
                pos += 1
                if text[pos] == "*":
                    buf = ""
                    while pos + 1 < len(text) and not (text[pos] == "*" and text[pos + 1] == "*"):
                        buf += text[pos]
                        pos += 1
                    if not pos + 1 < len(text):
                        raise SyntaxError("Unclosed '**'")
                    pos += 2
                    self.things.append(Bold(buf))
                else:
                    buf = ""
                    while pos < len(text) and text[pos] != "*":
                        buf += text[pos]
                        pos += 1
                    if not pos + 1 < len(text):
                        raise SyntaxError("Unclosed '*'")
                    pos += 1
                    self.things.append(Italic(buf))
            else:
                plain_buf += text[pos]
                pos += 1
        if len(plain_buf) > 0:
            self.things.append(Normal(plain_buf))
    def gen(self, fmt):
        return "".join([thing.gen(fmt) for thing in self.things])

class Paragraph:
    def __init__(self, text):
        
        self.text = FmtText(text)
        self.sources = []
        self.author = None

    def gen(pg, fmt):
        if fmt == "html":
            return f"<p class='pgraph'>{pg.text.gen(fmt)}" +\
                   "".join([f"<a class='source' href='{url}'>[{i + 1}]</a>"\
                            for i, url in enumerate(pg.sources)]) +\
                    (("<span class='author'>~" + pg.author + "</span>") if pg.author else "") +\
                    "</p>\n"
        if fmt == "reddit":
            author = ""
            if pg.author:
                author = " ^^~" + " ".join(["^^" + word for word in pg.author.split(" ")])
            return pg.text.gen(fmt) +\
                   "".join([f"^([\\[{i + 1}\\]]({url}))"\
                            for i, url in enumerate(pg.sources)]) +\
                    author + "\n\n"
        if fmt == "discord":
            return pg.text.gen(fmt) + "\n\n"


def cg_subhead(txt, fmt):
    if fmt == "html":
        return f'<div class="subhead">{txt}</div>\n'
    if fmt == "reddit":
        return f"## {txt}\n\n"
    if fmt == "discord":
        return f"__{txt}__\n"

def cg_head(txt, fmt):
    if fmt == "html":
        return f'<div class="head">{txt}</div>\n'
    if fmt == "reddit":
        return f"# {txt}\n\n"
    if fmt == "discord":
        return f"**{txt}**\n"

#TODO rewrite the parser to make a list instead of tree structure, and use polymorphism

months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
def generate_document(inp, fmt, infile_name, outfile_name, root_path):
    if fmt != "discord":
        inp = discord_to_emojis(inp)
    inp = inp.split("\n")
    raw_date = inp[0]
    date = datetime.datetime.strptime(raw_date, "%d/%m/%Y")
    date_text = "Issue " + infile_name.split(".")[0] + "<br>" + \
                date.strftime("%A, %-d of %B, %Y")
    inp = inp[1:]
    
    pgraphs = {}
    heading = None
    subheading = None
    for line in inp:
        if len(line) == 0: continue
        if line.startswith("**"):
            heading = line.strip("* ")
            subheading = None
            pgraphs[heading] = {None: []}
        elif line.startswith("__"):
            subheading = line.strip("_ ")
            pgraphs[heading][subheading] = []
        elif line.startswith("[["):
            source_urls = line.strip("[]").split(" ")
            pgraphs[heading][subheading][-1].sources = source_urls
        elif line.startswith("{{"):
            author = line.strip("{}")
            pgraphs[heading][subheading][-1].author = author
        else:
            pgraphs[heading][subheading].append(Paragraph(line))

    out = ""
    for head in pgraphs:
        if fmt != "discord" and head == "Server News":
            continue
        if fmt == "html":
            out += "<div class='section'>\n"
        out += cg_head(head, fmt)
        for subhead in pgraphs[head]:
            if subhead is not None:
                out += cg_subhead(subhead, fmt)
            for pgraph in pgraphs[head][subhead]:
                out += pgraph.gen(fmt)
        if fmt == "reddit":
            out += "---\n\n"
        elif fmt == "html":
            out += "</div>\n"

    if fmt == "html":
        issues = get_issues(root_path)
        if not infile_name.split(".")[0] in [i[0] for i in issues]:
            issues.append((infile_name.split(".")[0], raw_date, outfile_name.split("/")[-1]))
        issue_dict = {}
        for i_num, i_date, i_file in issues:
            parsed_date = datetime.datetime.strptime(i_date, "%d/%m/%Y")
            #TODO surely there's a better way of doing this
            if issue_dict.get(parsed_date.year) == None: issue_dict[parsed_date.year] = {}
            if issue_dict[parsed_date.year].get(parsed_date.month) == None: issue_dict[parsed_date.year][parsed_date.month] = []
            issue_dict[parsed_date.year][parsed_date.month].append((i_num, i_date, i_file, parsed_date.day))

        salmon_sidebar = "<ul class='sidebar_list'>\n"
        sorted_list = sorted(issue_dict.keys())
        sorted_list.reverse()
        for year in sorted_list:
            salmon_sidebar += f"    <li><span class='list_arrow'>{year}</span>\n"
            salmon_sidebar += "        <ul class='list_nested'>\n"
            for month in issue_dict[year]:
                salmon_sidebar += f"            <li><span class='list_arrow'>{months[month - 1]}</span>\n"
                salmon_sidebar += f"                <ul class=list_nested>\n"
                for issue in issue_dict[year][month]:
                    salmon_sidebar += f"                    <li><a href='./{issue[2]}'>{issue[3]} (issue {issue[0]})</a></li>\n"
                salmon_sidebar += "                </ul>\n"
                salmon_sidebar += "            </li>\n"
                
            salmon_sidebar += "        </ul>\n"
            salmon_sidebar += "    </li>\n"
        salmon_sidebar += "</ul>\n"
            
        with open("issue_template.html", "r") as f:
            template = f.read()
        
        document = template.format(salmon_text=out,
                                   salmon_date=date_text,
                                   raw_date=date.strftime("%d/%m/%Y"),
                                   salmon_sidebar=salmon_sidebar)
        return document
    else:
        return out

def get_issues(root_path):
    files = os.listdir(root_path)
    issue_files = filter(lambda f: re.match("\\d+\\.html", f) is not None, files)
    issue_files = sorted(issue_files, key=lambda file: int(file.replace(".html", "")))
    ret = []
    for file in issue_files:
        issue_num = file.replace(".html", "")
        with open(root_path + file, "r") as f:
            issue_date = f.read().split("\n")[0].strip("<!->")
        ret.append((issue_num, issue_date, file))

    return ret

def update_index(root_path):
    issue_files = get_issues(root_path)
    index_list = ""
    for num, date, file in issue_files:
        index_list += f"<a href='./{file}' class='issue_link'>Issue {num}, {date}</a><br>\n"

    with open("index_template.html", "r") as f:
        template = f.read()

    document = template.format(salmon_issues=index_list)
    return document

def sanetise(text):
    return text.replace("“", "\"").replace("”", "\"")

def usage():
    print(f"Usage: {sys.argv[0]} [-hdr] [-o <file>] <filename>")
    print("\t\t-h --html\t\tOutput format in html")
    print("\t\t-d --discord\t\tOutput format in discord markdown")
    print("\t\t-r --reddit\t\tOutput format in reddit markdown")
    print("\t\t-o --output <file>\tOutput to <file>, or stdout if <file> is -")
    print("\t\t-p --path <path>\tOutput html to directory <path>")
    print("\t\t-a --all <dir>\tConvert all files in <dir> following the format %d.txt into corrosponding HTML files")
    sys.exit(1)
    

def main():
    root_path = "/var/www/html/weekly-salmon/"
    infile_name = None
    out_format = None
    outfile_name = None
    path = None
    i = 1
    argv = sys.argv
    while i < len(argv):
        if argv[i]   == "--html":    out_format = "html"
        elif argv[i] == "--discord": out_format = "discord"
        elif argv[i] == "--reddit":  out_format = "reddit"
        elif argv[i] == "--all":
            if len(argv) < i + 2:
                print("Missing required field <dir> for '--all' option")
        elif argv[i] == "--out":
            if not outfile_name is None:
                print("Only one output file is supported")
                usage()
            if len(argv) < i + 2:
                print("Missing required field <file> for '--out' option")
                usage()
            outfile_name = argv[i + 1]
            i += 1
        elif argv[i] == "--path":
            if not path is None:
                print("Only one output path is supported")
                usage()
            if len(argv) < i + 2:
                print("Missing required field <path> for '--path' option")
                usage()
            path = argv[i + 1]
            i += 1
        elif argv[i].startswith("--"):
            print(f"Invalid argument '{argv[i]}'")
            usage()
        elif argv[i].startswith("-"):
            for letter in argv[i][1:]:
                if   letter == "h": out_format = "html"
                elif letter == "d": out_format = "discord"
                elif letter == "r": out_format = "reddit"
                elif letter == "o":
                    if not outfile_name is None:
                        print("Only one output file is supported")
                        usage()
                    if len(argv) < i + 2:
                        print("Missing required field <file> for '--out' option")
                        usage()
                    outfile_name = argv[i + 1]
                    i += 1
                elif letter == "p":
                    if not path is None:
                        print("Only one output path is supported")
                        usage()
                    if len(argv) < i + 2:
                        print("Missing required field <path> for '--path' option")
                        usage()
                    path = argv[i + 1]
                    i += 1
                else:
                    print(f"Invalid option '-{letter}'")
                    usage()
        else:
            if not infile_name is None:
                print("Only one input file is supported")
                usage()
            else:
                infile_name = argv[i]
        i += 1

    if path is not None:
        root_path = path
        if not root_path.endswith("/"):
            root_path += "/"

    if outfile_name is None and out_format != "html":
        print("Cannot figure out what file to output to. Specify filename or STDOUT")
        usage()
    if outfile_name is None:
        print(infile_name)
        outfile_name = root_path + infile_name.replace(".txt", ".html")

    if infile_name is None:
        print("Input filename required")
        usage()

    with open(infile_name, "r") as f:
        inp = sanetise(f.read())

    document = generate_document(inp, out_format, infile_name, outfile_name, root_path)
    if outfile_name == "-":
        print(document)
    else:
        with open(outfile_name, "w") as f:
            f.write(document)

        if out_format == "html":
            new_index = update_index(root_path)
            with open(root_path + "index.html", "w") as f:
                f.write(new_index)

if __name__ == "__main__":
    main()
