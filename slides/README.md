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

You can run `./slidechecker foo.yml.html` to check for
missing images and show the number of slides in that deck.
It requires `phantomjs` to be installed. It takes some
time to run so it is not yet integrated with the publishing
pipeline.
