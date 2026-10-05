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

For a live dev server that rebuilds on every save, run `make serve`
(or `docker compose up --build --watch`) in this directory. It runs one
container that:

- is built from `Dockerfile` with Python, the build dependencies, and a
  baseline copy of `slides/` and `k8s/` (slides pull manifests from `k8s/`
  with `@@INCLUDE[...]`),
- builds every deck at startup and serves this directory on
  http://localhost:8080/ (set `SLIDES_PORT` in `.env` or the environment
  to change the port),
- receives each source edit through Compose watch (file sync, no bind
  mount) and re-runs `./build.sh once`. Build errors show in the same
  terminal, and the previous HTML stays served until the build passes.

Generated files stay inside the container. Always start with `--build`
(which `make serve` does) so the baseline matches your checkout; the sync
only carries edits made while the watcher runs.

The dev server builds in dev mode (`SLIDES_DEV=1`): the footer of each
slide shows its source file name and its `name:` anchor, for example
`install.md · #install`. Dev footers omit Git status and build details so
they do not cover slide content. Published decks keep those details in the
hidden first footer. Open `deck.yml.html#install` to go back to that
slide. For a local build in dev mode, run `make build-dev`. To turn dev
mode off in the container, run `SLIDES_DEV=0 make serve`. Netlify does not
set `SLIDES_DEV`, so published slides keep the hidden footer.

To create `slides.zip` like Netlify does (all decks, no dev footers), run
`make zip`. It builds in the same Docker image and copies only `slides.zip`
to this directory. Unzip it and open a `foo.yml.html` file in a browser.

Stop with Ctrl-C, then `make down` to remove the container.
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
make labtest-plan DECK=kube-sec-twodays.yml \
  ONLY="k8s/helm-intro.md k8s/helm-chart-format.md k8s/helm-create-basic-chart.md k8s/helm-values-schema-validation.md k8s/helm-secrets.md"
```

Then use the same selection with `make labtest` and the approved `TAG`.
Read `labtest/runs/latest/summary.md` and check every failure and warning.

Student VMs need this checkout's `k8s/dockercoins.yaml` and
`k8s/helm-labs/` under `~/container.training/`. Use a clean working directory
and the lab namespaces named in the slides. Do not use production clusters.
