#!/usr/bin/env python3
# transforms a YAML manifest into a HTML workshop file

import glob
import logging
import os
import re
import string
import subprocess
import sys
from collections import Counter
from typing import NamedTuple
import yaml


logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))

# Dev mode (SLIDES_DEV=1, set by compose.yaml): each slide footer shows its
# source file name and its "#anchor" (a "name:" property, or a generated
# title or TOC anchor), and the footer is always visible.
dev = os.environ.get("SLIDES_DEV") == "1"
toc_exclude = []


class SlideTOCEntry(NamedTuple):
    label: str
    target: str
    filename: str


class ContentsTOCEntry(SlideTOCEntry):
    """A link to generated contents, without a lecture title slide."""


def anchor(title):
    title = title.lower().replace(' ', '-')
    title = ''.join(c for c in title if c in string.ascii_letters+'-')
    return "toc-" + title


class Interstitials(object):

    def __init__(self):
        self.index = 0
        self.images = [url.strip() for url in open("interstitials.txt") if url.strip()]

    def next(self):
        index = self.index % len(self.images)
        self.index += 1
        return self.images[index]


interstitials = Interstitials()


def insertslide(markdown, title):
    title_position = markdown.find("\n# {}\n".format(title))
    slide_position = markdown.rfind("\n---\n", 0, title_position+1)
    logging.debug("Inserting title slide at position {}: {}".format(slide_position, title))

    before = markdown[:slide_position]

    toclink = "toc" if single_toc else "toc-section-{}".format(title2part[title])
    _titles_ = [""] + all_titles + [""]
    currentindex = _titles_.index(title)
    # The first and last title slides link back to the TOC.
    previouslink = anchor(_titles_[currentindex-1]) if _titles_[currentindex-1] else toclink
    nextlink = anchor(_titles_[currentindex+1]) if _titles_[currentindex+1] else toclink
    interstitial = interstitials.next()

    extra_slide = """
---

class: pic

.interstitial[![Image separating from the next section]({interstitial})]

---

name: {anchor}
class: title

 {title}

.nav[
[Previous lecture](#{previouslink})
|
[Table of Contents](#{toclink})
|
[Next lecture](#{nextlink})
]

.debug[{debug}]
""".format(anchor=anchor(title), interstitial=interstitial, title=title, toclink=toclink, previouslink=previouslink, nextlink=nextlink,
           debug="(title slide) · #" + anchor(title) if dev else "(automatically generated title slide)")
    after = markdown[slide_position:]
    return before + extra_slide + after


def flatten(titles):
    for title in titles:
        if isinstance(title, dict):
            yield from flatten(title["content"])
        elif isinstance(title, list):
            for t in flatten(title):
                yield t
        else:
            yield title


def generatefromyaml(manifest, filename):
    global single_toc, toc_exclude
    single_toc = manifest.get("toc") == "single"
    toc_exclude = manifest.get("exclude", [])
    markdown, titles = processcontent(manifest["content"], filename)
    logging.debug("Found {} titles.".format(len(titles)))
    toc = gentoc(titles)
    markdown = markdown.replace("@@TOC@@", toc)
    for title in flatten(titles):
        if isinstance(title, str):
            markdown = insertslide(markdown, title)

    exclude = manifest.get("exclude", [])
    logging.debug("exclude={!r}".format(exclude))
    if not exclude:
        logging.warning("'exclude' is empty.")
    markdown = removeexcluded(markdown, exclude)
    markdown = removetitleonly(markdown)
    # Validate against retained source slides and generated TOC/title anchors.
    names = Counter(slideproperties(s).get("name") for s in markdown.split("\n---\n"))
    for entry in flatten(titles):
        if isinstance(entry, SlideTOCEntry) and names[entry.target] != 1:
            raise ValueError("{}: toc target {!r} must name exactly one retained slide (found {})".format(
                entry.filename, entry.target, names[entry.target]))
    exclude = ",".join('"{}"'.format(c) for c in exclude)

    # Published decks keep build details in the hidden first footer.
    # Dev footers stay one line so they do not cover slide content.
    if not dev:
        markdown = markdown.replace(
            ".debug[",
            ".debug[\n```\n{}\n```\n\nThese slides have been built from commit: {}\n\n".format(dirtyfiles, commit),
            1)

    html = open("workshop.html").read()
    html = html.replace("@@TITLE@@", manifest["title"].replace("\n", " "))
    html = html.replace("@@MARKDOWN@@", markdown)
    html = html.replace("@@EXCLUDE@@", exclude)
    html = html.replace("@@SLIDENUMBERPREFIX@@", manifest.get("slidenumberprefix", ""))
    # CSS classes on <body>; workshop.html enables features from them.
    bodyclass = []
    if dev:
        bodyclass.append("dev")
    # Image path label on mouse hover: always in dev mode, and in production
    # when the manifest has "imagelabels: true".
    if dev or manifest.get("imagelabels"):
        bodyclass.append("image-labels")
    # "Ask AI" button (Claude, ChatGPT) on text slides: "askai: true" in the
    # manifest. It links to the public chapter file, under the "slides" URL.
    if manifest.get("askai"):
        bodyclass.append("ask-ai")
    html = html.replace("@@SLIDESURL@@", manifest.get("slides", ""))
    html = html.replace("@@BODYCLASS@@", " ".join(bodyclass))
    return html

# Remove the slides that have an excluded class, with all their "--" steps.
# Remark also excludes them (excludedClasses), but it checks each "--" step
# on its own, and a step has no class of its own. So Remark shows the steps
# after the first "--" of an excluded slide (with the content of an earlier
# slide). Removing the whole slide here prevents that.
def removeexcluded(markdown, exclude):
    def excluded(slide):
        # Slide properties ("key: value") are the first lines of the slide.
        for line in slide.lstrip("\n").split("\n"):
            m = re.match(r"(\w+):\s*(.*)$", line)
            if not m:
                return False
            if m.group(1) == "layout" and m.group(2).strip() == "true":
                return False
            if m.group(1) == "class":
                classes = re.split(r"[,\s]+", m.group(2).strip())
                return any(c in exclude for c in classes)
        return False
    slides = markdown.split("\n---\n")
    kept = [s for s in slides if not excluded(s)]
    logging.debug("Removed {} excluded slides.".format(len(slides) - len(kept)))
    return "\n---\n".join(kept)

# Remove the slides that have only a section title ("# Title") and no other
# content. insertslide() already adds a title slide for each section title,
# so a title-only slide would show as an empty slide after it. With this,
# a chapter can start with "# Title" alone, and its first slide can have
# its own "## " title (or be excluded).
def removetitleonly(markdown):
    def titleonly(slide):
        if "toc" in slideproperties(slide):
            return False
        lines = [l.strip() for l in slide.strip("\n").split("\n")]
        # Ignore slide properties (the first "key: value" lines), footers
        # (.debug[...]), and empty lines.
        while lines and re.match(r"\w+:\s", lines[0]):
            lines.pop(0)
        content = [l for l in lines if l
                   and not (l.startswith(".debug[") and l.endswith("]"))]
        return len(content) == 1 and content[0].startswith("# ")
    slides = markdown.split("\n---\n")
    kept = [s for s in slides if not titleonly(s)]
    logging.debug("Removed {} title-only slides.".format(len(slides) - len(kept)))
    return "\n---\n".join(kept)

def processAtAtStrings(text):
    text = text.replace("@@CHAT@@", manifest["chat"])
    text = text.replace("@@GITREPO@@", manifest["gitrepo"])
    text = text.replace("@@GITBRANCH@@", manifest["gitbranch"])
    text = text.replace("@@SLIDES@@", manifest["slides"])
    text = text.replace("@@ZIP@@", manifest["zip"])
    text = text.replace("@@HTML@@", manifest["html"])
    text = text.replace("@@TITLE@@", manifest["title"].replace("\n", "<br/>"))
    # Process @@LINK[file] and @@INCLUDE[file] directives
    local_anchor_path = ".."
    # FIXME use dynamic repo and branch?
    online_anchor_path = "https://{}/tree/{}".format(
        manifest["gitrepo"] or "github.com/jpetazzo/container.training",
        manifest["gitbranch"] if explicit_branch else "main")
    for atatlink in re.findall(r"@@LINK\[[^]]*\]", text):
        logging.debug("Processing {}".format(atatlink))
        file_name = atatlink[len("@@LINK["):-1]
        text = text.replace(atatlink, "[{}]({}/{})".format(file_name, online_anchor_path, file_name ))
    for atatinclude in re.findall(r"@@INCLUDE\[[^]]*\]", text):
        logging.debug("Processing {}".format(atatinclude))
        file_name = atatinclude[len("@@INCLUDE["):-1]
        file_path = os.path.join(local_anchor_path, file_name)
        text = text.replace(atatinclude, open(file_path).read())
    return text


# Maps a title (the string just after "^# ") to its position in the TOC
# (to which section it belongs).
title2part = {}
all_titles = []


def slideproperties(slide):
    properties = {}
    duplicates = []
    for line in slide.lstrip("\n").split("\n"):
        match = re.match(r"^(\w+):[ \t]*(.*)$", line)
        if not match:
            break
        key, value = match.groups()
        if key in properties and key in ("toc", "name"):
            duplicates.append(key)
        properties[key] = value.strip()
    if "toc" in properties and duplicates:
        raise ValueError("Duplicate {!r} slide property".format(duplicates[0]))
    return properties


def contententries(content, filename):
    entries = []
    for slide in content.split("\n---\n"):
        # Lecture detection keeps its existing behavior. Slide links only
        # use initial Remark properties, never code, notes, or -- steps.
        properties = slideproperties(slide)
        if "toc" in properties and removeexcluded(slide, toc_exclude) == slide and properties.get("exclude") != "true":
            label = properties["toc"]
            target = properties.get("name", "")
            if not label:
                raise ValueError("{}: toc needs a non-empty label".format(filename))
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", target):
                raise ValueError("{}: toc needs an explicit name using letters, digits, '-' or '_'".format(filename))
            if properties.get("layout") == "true":
                raise ValueError("{}: toc cannot be set on a layout slide".format(filename))
            entries.append(SlideTOCEntry(label, target, filename))
        if re.search(r"^@@TOC@@$", slide, re.MULTILINE) and removeexcluded(slide, toc_exclude) == slide and properties.get("exclude") != "true":
            entries.append(ContentsTOCEntry("Table of contents",
                "toc" if single_toc else "toc-section-1", filename))
        entries.extend(re.findall("^# (.*)", slide, re.MULTILINE))
    return entries


def tocitem(entry, section):
    if isinstance(entry, SlideTOCEntry):
        label = re.sub(r"([\\\[\]])", r"\\\1", entry.label)
        return "- [{}](#{})\n".format(label, entry.target)
    title2part[entry] = section
    all_titles.append(entry)
    return "- [{}](#{})\n".format(entry, anchor(entry))

# Set from the manifest ("toc: single"): one TOC slide for all sections.
single_toc = False

# Generate the table of contents for a tree of titles.
# "tree" is a list of titles, potentially nested.
# Each list or named group is one TOC section. Its TOC entries are flattened.
# Nested group names do not add TOC levels; only the outer name is displayed.
def gentoc(tree):
    tree = [(entry["title"], list(flatten(entry["content"])))
            if isinstance(entry, dict) else (None, list(flatten(entry)))
            for entry in tree if isinstance(entry, (list, dict))]
    tree = [(name, part) for name, part in tree if name or part]
    # A standalone TOC placeholder is an entry at its manifest position,
    # not a new section. Keep it in the preceding group, or the next at the start.
    groups = []
    pending_contents = []
    for name, part in tree:
        if name is None and part and all(isinstance(entry, ContentsTOCEntry) for entry in part):
            if groups:
                groups[-1][1].extend(part)
            else:
                pending_contents.extend(part)
        else:
            groups.append((name, pending_contents + part))
            pending_contents = []
    tree = groups or ([(None, pending_contents)] if pending_contents else [])
    # Now, process each section.
    if single_toc:
        return gentoc_single(tree)
    parts = []
    pending_labels = []
    section_count = sum(any(not isinstance(entry, ContentsTOCEntry) for entry in part)
                        for name, part in tree)
    display_section = 0
    for name, part in tree:
        if any(not isinstance(entry, ContentsTOCEntry) for entry in part):
            display_section += 1
        if not any(isinstance(entry, str) for entry in part):
            label = "## {}\n\n".format(name or "Section {}".format(display_section))
            label += "".join(tocitem(entry, None) for entry in part)
            if part:
                label += "\n"  # End the link list before the next section heading.
            if parts:
                parts[-1] += "\n" + label
            else:
                pending_labels.append(label)
            continue
        # Labels without lecture links do not consume an anchor or a slide.
        i = len(parts)
        slide = "name: toc-section-{}\n\n".format(i+1) + "".join(pending_labels)
        pending_labels = []
        if name:
            slide += "## {}\n\n".format(name)
        elif section_count == 1:
            slide += "## Table of contents\n\n"
        else:
            slide += "## Section {}\n\n".format(display_section)
        for title in part:
            logging.debug("Generating TOC, section {}, title {}.".format(i+1, title))
            slide += tocitem(title, i+1)
            # If we don't have too many subsections, add some space to breathe.
            # (Otherwise, we display the titles smooched together.)
            if len(part) < 10:
                slide += "\n"
        parts.append(slide)
    # A deck with only labels or direct slide links still needs one TOC slide.
    if pending_labels:
        parts.append("name: toc-section-1\n\n" + "".join(pending_labels))
    parts = [slide + "\n.debug[{}]".format("toc.md · #toc-section-{}".format(i+1)
             if dev else "(auto-generated TOC)") for i, slide in enumerate(parts)]
    return "\n---\n".join(parts)


# Single-slide TOC: every section on one slide, in small columns.
# Each section keeps its number, so the slide shows which titles belong to it.
def gentoc_single(tree):
    slide = "name: toc\n\n## Table of contents\n\n.toc-single[\n"
    section = 0
    lecture_section = 0
    for name, part in tree:
        if any(not isinstance(entry, ContentsTOCEntry) for entry in part):
            section += 1
        if any(isinstance(entry, str) for entry in part):
            lecture_section += 1
        slide += "\n**{}**\n\n".format(name or "Section {}".format(section))
        for title in part:
            slide += tocitem(title, lecture_section)
    slide += "\n]\n\n.debug[{}]".format("toc.md · #toc" if dev else "(auto-generated TOC)")
    return slide


# Arguments:
# - `content` is a string; if it has multiple lines, it will be used as
#   a markdown fragment; otherwise it will be considered as a file name
#   to be recursively loaded and parsed
# - `filename` is the name of the file that we're currently processing
#   (to generate inline comments to facilitate edition)
# Returns expanded Markdown and a title tree (lists or named groups).
def processcontent(content, filename):
    if isinstance(content, str):
        if "\n" in content:
            titles = contententries(content, filename)
            if dev:
                slides = content.split("\n---\n")
                slides = [addfooter(s, devfooter(s, filename)) for s in slides]
                return ("\n---\n".join(slides), titles)
            slidefooter = ".debug[{}]".format(makelink(filename))
            content = content.replace("\n---\n", "\n{}\n---\n".format(slidefooter))
            content += "\n" + slidefooter
            return (content, titles)
        if os.path.isfile(content):
            markdown = open(content).read()
            # Line 1 can be "<!-- verified: YYYY-MM-DD -->", the date of the
            # last fact check of this file (see README.md). Remove it: slide
            # properties ("class: ...") must be the first lines of a slide.
            markdown = re.sub(r"\A<!-- verified: [^\n]*-->\n", "", markdown)
            markdown = processAtAtStrings(markdown)
            fragmentfile = os.path.join("fragments", content)
            fragmentdir = os.path.dirname(fragmentfile)
            os.makedirs(fragmentdir, exist_ok=True)
            with open(fragmentfile, "w") as f:
                f.write(markdown)
            return processcontent(markdown, content)
        logging.warning("Content spans only one line (it's probably a file name) but no file found: {}".format(content))
    if isinstance(content, dict):
        title = content.get("title")
        if not isinstance(title, str) or not title.strip() or "\n" in title:
            raise ValueError("A named content group needs a non-empty, single-line title")
        if not isinstance(content.get("content"), list):
            raise ValueError("A named content group needs a content list")
        markdown, titles = processcontent(content["content"], filename)
        return markdown, {"title": title, "content": titles}
    if isinstance(content, list):
        subparts = [processcontent(c, filename) for c in content]
        # A label-only group has a title tree but no slide content. Do not
        # insert a blank slide for it. Keep legacy empty-list behavior.
        markdown = "\n---\n".join(m for m, t in subparts if m or not t)
        titles = [t for (m,t) in subparts if t]
        return (markdown, titles)
    logging.warning("Invalid content: {}".format(content))
    return "```\nInvalid content: {}\n```\n".format(content), []

# Try to figure out the URL of the repo on GitHub.
# This is used to generate "edit me on GitHub"-style links.
# Each value can be set with an environment variable (REPOSITORY_URL, BRANCH,
# COMMIT) for builds that run without a git checkout, e.g. in a container
# where Compose watch syncs only the source files.
def git(*args):
    return subprocess.check_output(["git"] + list(args),
        stderr=subprocess.DEVNULL).decode("ascii").strip()

# Development footers need only source filenames and slide anchors. Do not
# discover Git metadata here: development containers have no .git directory.
urltemplate = "file://{pwd}/{filename}".format(pwd=os.getcwd(), filename="{}")
commit = "??????"
dirtyfiles = ""
if not dev:
    try:
        repo = os.environ.get("REPOSITORY_URL") or git("config", "remote.origin.url")
        repo = repo.replace("git@github.com:", "https://github.com/").removesuffix(".git")
        branch = os.environ.get("BRANCH") or git("rev-parse", "--abbrev-ref", "HEAD")
        try:
            base = git("rev-parse", "--show-prefix").strip("/")
        except Exception:
            base = os.path.basename(os.getcwd())
        urltemplate = ("{repo}/tree/{branch}/{base}/{filename}"
            .format(repo=repo, branch=branch, base=base, filename="{}"))
    except Exception:
        logging.warning("Could not determine repository URL or branch; generating local URLs instead.")
        urltemplate = "file://{pwd}/{filename}".format(pwd=os.getcwd(), filename="{}")
    try:
        commit = os.environ.get("COMMIT") or git("rev-parse", "--short", "HEAD")
    except Exception:
        logging.warning("Could not determine HEAD commit.")
        commit = "??????"
    try:
        dirtyfiles = git("status", "--porcelain")
    except Exception:
        dirtyfiles = "(git status unavailable in this build environment)"

def makelink(filename):
    if os.path.isfile(filename):
        url = urltemplate.format(filename)
        return "[{}]({})".format(filename, url)
    else:
        return filename

# Dev footer: "file.md · #anchor", as plain text (the dev server runs in a
# container, so a file link would not open). The anchor comes from the
# slide's "name:" property; Remark properties are the "key: value" lines at
# the top of a slide.
# Remark shows an incremental slide ("--") as several copies, each holding
# only the content up to its step. A footer at the end would appear only at
# the last step, so put it right after the slide properties (top of the slide).
# The footer is absolutely positioned, so it still renders at the bottom.
def addfooter(slide, footer):
    if not footer:
        return slide
    lines = slide.split("\n")
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    while i < len(lines) and re.match(r"^\w+:\s*.*$", lines[i]):
        i += 1
    return "\n".join(lines[:i] + ["", footer, ""] + lines[i:])


def devfooter(slide, filename):
    # TOC slides are generated later and carry their own footer (file name
    # and anchor in one line), so don't add a second one that would overlap.
    if "@@TOC@@" in slide:
        return ""
    # The path (e.g. k8s/netpol.md), not only the name: the "Ask AI" button
    # in workshop.html reads it to find the chapter file (as in production).
    text = filename
    for line in slide.lstrip("\n").split("\n"):
        match = re.match(r"^(\w+):\s*(.*)$", line)
        if not match:
            break
        if match.group(1) == "name":
            text += " · #" + match.group(2).strip()
    # Escape Markdown emphasis characters, e.g. in Container_Networking_Basics.md.
    text = re.sub(r"([_*])", r"\\\1", text)
    return ".debug[{}]".format(text)

if len(sys.argv) != 2:
    logging.error("This program takes one and only one argument: the YAML file to process.")
else:
    filename = sys.argv[1]
    if filename == "-":
        filename = "<stdin>"
        manifest = sys.stdin
    else:
        manifest = open(filename)
    logging.info("Processing {}...".format(filename))

    manifest = yaml.safe_load(manifest)
    for k in manifest:
        override = os.environ.get("OVERRIDE_"+k)
        if override:
            manifest[k] = override
    for k in ["chat", "gitrepo", "slides", "title"]:
        if k not in manifest:
            manifest[k] = ""
    # Branch used in generated GitHub links; decks that don't set it keep "master".
    explicit_branch = "gitbranch" in manifest
    manifest.setdefault("gitbranch", "master")
    if "zip" not in manifest:
        if manifest["slides"].endswith('/'):
            manifest["zip"] = manifest["slides"] + "slides.zip"
        else:
            manifest["zip"] = manifest["slides"] + "/slides.zip"
    if "html" not in manifest:
        manifest["html"] = filename + ".html"

    sys.stdout.write(generatefromyaml(manifest, filename))
    logging.info("Processed {}.".format(filename))
