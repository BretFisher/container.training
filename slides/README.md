# MarkMaker

General principles:

- each slides deck is described in a YAML manifest;
- the YAML manifest lists a number of Markdown files
  that compose the slides deck;
- a Python script "compiles" the YAML manifest into
  a HTML file;
- that HTML file can be displayed in your browser
  (you don't need to host it), or you can publish it
  (along with a few static assets) if you want.


## Getting started

Look at the YAML file corresponding to the deck that
you want to edit. The format should be self-explanatory.

*I (Jérôme) am still in the process of fine-tuning that
format. Once I settle for something, I will add better
documentation.*

### Name TOC sections

Use a `title` and a `content` list to name a section:

```yaml
toc: single
content:
- shared/toc.md
- title: Kubernetes basics
  content:
    - k8s/concepts-k8s.md
    - k8s/kubectlget.md
- title: Deploying our application
  content:
    - shared/sampleapp.md
    - k8s/shippingimages.md
```

The group title is only a TOC label. It adds no lecture, title slide, or
interstitial slide. Lecture names still come from Markdown `# Heading` lines.
The name stays with its group when you move the group.

Names work with `toc: single` and with separate TOC slides (omit `toc: single`).
Existing strings and nested lists keep their behavior. Unnamed groups use
`Section N`; a single unnamed group in separate-slide mode uses
`Table of contents`. A standalone file with `# Heading` lines also forms a
TOC group. Wrap that file in a named group to set its TOC label.

Deeper groups are flattened in source order. Only the outer group's name is
displayed; inner names add no TOC level. Titles must be non-empty, single-line
strings, and `content` must be a list. Explicit names appear even when the
group has no lecture headings or has an empty `content` list. Unnamed groups
without headings or explicit slide links stay omitted. Labels without lecture links do not consume
a section number or change navigation anchors. In separate-slide mode, they
share the preceding TOC slide, or the first following slide if they come first.
A deck with only explicit labels gets one TOC slide. Names add no title or
interstitial slides.

### Link directly to a slide from the TOC

Add these properties before the slide's heading and content:

```markdown
name: getting-started
toc: Getting started

## Getting started: Do these now

Existing slide content.
```

`toc` supplies the link label; `name` supplies its stable target. The link
appears under the containing YAML section, in source order with lecture
links. It opens the existing slide, keeps its heading and style, and adds no
lecture title or interstitial slide. Only Markdown `#` lecture headings
participate in the Previous lecture and Next lecture links. One Markdown
file can contain several lectures and direct slide links.

This works in both TOC modes and with named or unnamed sections. Sections
with only direct slide links share an existing TOC slide in separate-slide
mode, as label-only sections do. A deck with only those sections gets one
TOC slide. Existing lecture navigation anchors stay unchanged.

Set `toc` and `name` once, in the initial Remark property block. An
incremental `--` step does not create another entry. Code and speaker notes
do not supply properties. Excluded slides do not add direct links. A `toc`
label must be non-empty; its `name` must start with a letter and contain only
letters, digits, hyphens, or underscores. The target must be unique among
retained and generated slide names. Invalid entries fail the build. Layout
slides cannot define direct TOC entries because their properties repeat.

From `slides/`, run `make test-markmaker` to test names, direct slide links,
legacy groups, and navigation in both TOC modes. This needs Python 3 and `requirements.txt`.
Set `PYTHON=/path/to/python3` to use another existing Python environment.

Make changes in the YAML file, and/or in the referenced
Markdown files. If you have never used Remark before:

- use `---` to separate slides,
- use `.foo[bla]` if you want `bla` to have CSS class `foo`,
- define (or edit) CSS classes in [workshop.css](workshop.css).

After making changes, run `make build` (or `./build.sh once`);
it will compile each `foo.yml` file into `foo.yml.html`.
It needs Python 3 with the packages in `requirements.txt`.
It exits non-zero if any deck fails to build.

For a live dev server that rebuilds on every save, run `make serve` in this
directory. It runs `docker compose up --build --watch` in the foreground.
Build and watch output stays in that terminal. The slide image supplies
Python and build dependencies; no extra host tool is needed.

```sh
make serve                            # Build all decks and watch source edits
make serve SLIDES_DECK=kube-sec-twodays.yml    # Build and rebuild only this deck
# Press Ctrl+C to stop; then remove the containers:
make down
```

The container serves slides at http://localhost:8080/ (override with
`SLIDES_PORT`). Compose watch syncs source edits under `slides/` and `k8s/`
into the container and runs `./build.sh once`. Generated HTML stays in the
container. Refresh the browser after a rebuild. Each deck keeps its previous
HTML until its next build succeeds.

`SLIDES_DECK` must name an existing `.yml` file in `slides/`, without a path.
Pass it to Make or export it in the shell. An empty or unset value builds all
decks; lab commands default to `kube-sec-twodays.yml` when it is empty.
Before Compose starts, Make prints `Serving deck: <filename>` or
`Serving all decks.` so the selection is visible before image-build output.
The terminal prints `Building deck: <filename>` for a selection, or
`Building all decks.` otherwise. The selection applies to startup and every
rebuild, including edits to shared content, templates, images, and `k8s/`.
Open the deck directly, for example
`http://localhost:8080/kube-sec-twodays.yml.html`. Selected builds skip the
catalog (`index.html` and `past.html`); existing catalog and other deck HTML
can remain and may be out of date. Builds do not delete them. Container
recreation can replace old outputs.

To switch decks, press Ctrl+C and run `make serve SLIDES_DECK=another-deck.yml`.
Run `make serve SLIDES_DECK=` to build all decks again. `make zip` and
`SLIDES_ZIP=1` always build all decks and catalogs. Direct `./build.sh once`
builds all decks unless `SLIDES_DECK` is set. Run `make test-markmaker` for
compiler and selection tests.

The dev server builds in dev mode (`SLIDES_DEV=1`): the footer of each
slide shows its source file name and its `name:` anchor, for example
`install.md · #install`. Dev footers omit Git status and build details so
they do not cover slide content. Dev builds skip all Git metadata lookups,
so a container without `.git` does not emit Git metadata warnings.
Published decks keep those details in the
hidden first footer. Open `deck.yml.html#install` to go back to that
slide. For a local build in dev mode, run `make build-dev`. To turn dev
mode off in the container, run `SLIDES_DEV=0 make serve`. Netlify does not
set `SLIDES_DEV`, so published slides keep the hidden footer.

To create `slides.zip` like Netlify does (all decks, no dev footers), run
`make zip`. It builds in the same Docker image and copies only `slides.zip`
to this directory. Unzip it and open a `foo.yml.html` file in a browser.

Stop with Ctrl+C, then run `make down` to remove the container.
`make clean` also deletes generated files from a local, non-Docker build.
`make help` lists all targets.


## Publishing pipeline

Each time we push to `master`, a webhook pings
[Netlify](https://www.netlify.com/), which will pull
the repo, build the slides (by running `build.sh once` with
`SLIDES_ZIP=1`, which also creates `slides.zip`), and publish them to http://container.training/.

Pull requests are automatically deployed to testing
subdomains. I had no idea that I would ever say this
about a static page hosting service, but it is seriously awesome. ⚡️💥


## Search a deck

Press `/` or click the search button above the theme button to search all
slides in the open deck. The Remark help screen (`?`) lists this shortcut.
Search matches text without case sensitivity, including code. It treats
punctuation as plain text. It excludes speaker notes, slide properties,
and slide controls. In chapter view (`workshop.html?k8s/helm-intro`), it
searches only that chapter.

Results show slide titles and displayed numbers. Use Up/Down and Enter,
or click a title to open a result. Close with X, Escape, or a click outside
the popup. Dismissal restores focus and keeps the current slide and reveal.
A match in a later incremental step opens that step; each slide
appears once. Cmd/Ctrl+F keeps the browser's normal search behavior.
Search runs in the browser and needs no extra dependency or service.

## Open the table of contents

Press `o` or click the contents button to open the deck's generated section
slides with their original columns, text styles, and chapter links. Each
preview trims blank slide margins and scales the content to fit the window. Select **Table of contents** in the generated
list to open the TOC slide. The compiler adds this entry at the manifest
position of `toc.md`. Multi-page TOCs link to their first page.
Decks with multiple TOC slides show each section preview in a scrollable
popup. The four buttons form a vertical stack at the
bottom right: contents, search, theme, and Help. This shortcut also appears
in Help (`?`). Select a chapter to close the popup and open its first step. Use Tab and Enter for
keyboard selection.

Close with X, Escape, or a click outside. Dismissal keeps the current slide,
reveal, and URL hash. Both popups keep slide navigation keys inside the popup
and use the current theme. Chapter-only views have no generated contents.

## Extra bells and whistles

To test the hands-on labs of a deck on a lab cluster, use
`make labtest-plan` and `make labtest`. See [labtest/README.md](labtest/README.md).

You can run `./slidechecker foo.yml.html` to check for
missing images and show the number of slides in that deck.
It requires `phantomjs` to be installed. It takes some
time to run so it is not yet integrated with the publishing
pipeline.

## Helm workshop validation

The security workshop uses Helm 4.3.0 and the examples in
[`../k8s/helm-labs/`](../k8s/helm-labs/README.md). The component-chart and
chart-dependency chapters are optional in `kube-sec-twodays.yml`.

From `slides/`, run `make helm-labs-check` to build local chart dependencies,
lint the three checked-in charts, and render them without a cluster.
This needs the existing Helm CLI. It does not install tools.

Plan the core chapters before a lab run:

```sh
make labtest-plan SLIDES_DECK=kube-sec-twodays.yml \
  ONLY="k8s/helm-intro.md k8s/helm-chart-format.md k8s/helm-create-basic-chart.md k8s/helm-values-schema-validation.md k8s/helm-secrets.md"
```

Then use the same selection with `make labtest` and the approved `TAG`.
Read `labtest/runs/latest/summary.md` and check every failure and warning.

Student VMs need this checkout's `k8s/dockercoins.yaml` and
`k8s/helm-labs/` under `~/container.training/`. Use a clean working directory
and the lab namespaces named in the slides. Do not use production clusters.
