# Working in this repository

Container-training course materials: Markdown decks compiled by custom Python
MarkMaker scripts and rendered with Remark (not Slidev).

## Directory map

- `slides/`: deck manifests (`*.yml`), compiler, templates, CSS, and publishing assets.
  - `containers/`, `swarm/`, `k8s/`, `terraform/`, `flux/`: topic-specific slide sources.
  - `shared/`: content reused across decks; edits can affect multiple courses.
  - `images/`, `exercises/`: slide assets and hands-on exercise materials.
  - `labtest/`: runs the `.lab[]` commands of a deck on a lab cluster (`make labtest`).
- `dockercoins/`: microservices demo used throughout orchestration courses.
- `k8s/`: runnable Kubernetes manifests and examples (distinct from `slides/k8s/`).
- `compose/`: Compose-based Kubernetes control-plane and networking labs.
- `stacks/`: Compose application stacks for orchestration demos.
- `efk/`, `elk/`: logging demos; `prom/`, `snap/`: monitoring demos.
- `prepare-labs/`: primary cloud lab provisioning tools; entry point is `labctl`.
  - `settings/`: course settings and provisioning steps; `lib/`: implementation.
  - `terraform/`: provider configurations; `tags/`: per-deployment state/settings.
  - `templates/`, `www/`: student access pages and generated lab information.
- `prepare-eks/`: numbered AWS EKS cluster, IAM, and student-access setup scripts.
- `prepare-local/`: Vagrant/Ansible labs; `prepare-machine/`: legacy Docker Machine guide.
- `bin/`: demo helper scripts; `webhooks/admission/`: Kubernetes admission example.
- `.devcontainer/`: development-container configuration.

## Start the slide server

From the repository root, with Docker and Compose available:

```sh
cd slides
make serve        # same as: docker compose up --build --watch
# Build and rebuild only the workshop deck:
make serve SLIDES_DECK=kube-sec-twodays.yml
```

One container builds the selected deck, or all decks by default, and serves them at
`http://localhost:8080/` (override with `SLIDES_PORT`). Compose watch syncs
edits under `slides/` and `k8s/` into the container and re-runs `./build.sh once`.
Generated HTML stays in the container; open a deck such as `/intro-fullday.yml.html`
and refresh after a rebuild. Build errors appear in the same terminal. Stop with
Ctrl-C, then `make down`. Always use `--build` so the baked-in baseline matches
the checkout.

## Edit and validate slides

1. Read `slides/README.md` for the publishing workflow, then open the target
   `slides/*.yml` manifest. Its `content` list controls chapter inclusion and order.
2. Edit the referenced Markdown files; use `---` between slides and `???` for
   speaker notes. Keep shared content reusable; search manifests for affected decks.
3. For styling, edit `slides/workshop.css`; the HTML template is `slides/workshop.html`.
   Course logistics live in `slides/logistics*.md`; the landing-page catalog is `slides/index.yaml`.
4. Rebuild and inspect every affected deck in the browser for overflow, broken
   images, and exercise formatting. `build.sh` exits non-zero on the first failing deck.

Content rules for every slide you write or edit:

- Do not add speaker notes (`???` sections) inside individual slides unless
  the user specifically requests them.
- Teach current Kubernetes and current tools only. When a newer feature
  replaces an older one, teach the newer one, and give the older one at most
  one line ("X is deprecated; use Y"). Delete history that has no replacement.
  Exception: a topic that a client quote names as legacy (e.g. "PSP (legacy)")
  gets that one line, with what replaced it.
- Test each command, image, and chart version on the current lab before it
  goes on a slide. A slide that reads well but fails on a lab is a bug.

For a one-shot build without Docker, use Python 3 with dependencies from
`slides/requirements.txt`, then run `cd slides && make build` (or `./build.sh once`).
Set `SLIDES_ZIP=1` to also produce `slides.zip` (needs `zip`); Netlify does this.
Edit sources rather than generated `*.yml.html`, `index.html`, `past.html`, or `slides.zip`.

## Create slide diagrams

- Unless specified otherwise, use a 16:9 canvas for all Excalidraw diagrams
  and SVG exports to maximize usable space on slides.
- When creating or editing diagrams, use the `excalidraw-diagram-skill` skill
  if available. Some environments list it as `excalidraw-diagram`.
- Create `.excalidraw` JSON files directly; MCP access is not required. Use
  editable shapes, text, and connectors so contributors can edit the diagrams
  with the free Excalidraw editor.
- Before creating a diagram, read `slides/images/k8s-arch3-2026.excalidraw`.
  Use it as the template for the color palette and design standards, including
  rounded shapes, clean lines, typography, spacing, and resource panels.
  These project standards take precedence over a skill's default style.
- Store all slide image assets in `slides/images/`. Save the editable source
  and SVG export with the exact same base filename: `<name>.excalidraw` and
  `<name>.svg`. For example, `k8s-arch3-2026.excalidraw` exports to
  `k8s-arch3-2026.svg`.
- Export the SVG from the latest Excalidraw source after each edit. Make the
  canvas outside the diagram transparent (`appState.exportBackground: false`)
  so it displays cleanly on dark backgrounds. Keep the shapes' intended fills.
- Reference the SVG in slide Markdown. Keep the `.excalidraw` source beside
  it for future edits. Create a PNG export only when requested.
- Inspect the exported SVG for clipped text, connector placement, and
  readability on light and dark backgrounds before completing the change.

## Provision lab infrastructure

Read `prepare-labs/README.md` before provisioning for provider credentials, modes,
and Terraform layout. Root README references to `prepare-vms/workshopctl` are stale;
use `prepare-labs/labctl` instead.

Provisioning incurs cloud costs. Obtain explicit approval for the provider/account,
region, student count, and cluster size before creating or destroying resources.
Install Terraform and the dependencies checked in `prepare-labs/labctl`; configure
provider credentials and a loaded SSH agent. Review the chosen `settings/*.env`
(including `CLUSTERSIZE`, `STEPS`, and credentials) before running it.

Example: one student's Docker lab on DigitalOcean, after approval:

```sh
cd prepare-labs
./labctl                          # list commands and report missing dependencies
./labctl create --students 1 --settings settings/docker.env --provider digitalocean
```

For Kubernetes VMs, select `settings/kubernetes.env`; for managed Kubernetes,
consult the README's `--mode mk8s` workflow and provider support.
Record the deployment tag printed by `create`; connect with `./labctl ssh <tag>`.
After confirming the exact deployment to remove, use `./labctl destroy <tag>`
(Terraform destruction is auto-approved by the script).
Keep cloud credentials, generated access cards, SSH keys, and Terraform state out
of commits; preserve deployment state until cleanup is complete.

## Current project plan

If `PLAN.md` exists in the repository root, read it before you work on the
current project. It holds the deck we focus on, the decisions, the open
questions, and the plan. It is a local file (in `.gitignore`), so it is not
in every checkout. When you finish a phase, tick its box in `PLAN.md`.

## Test exercises

Use `slides/labtest/` (read its README for directives and result files).
From `slides/`:

- `make labtest-plan SLIDES_DECK=<deck>.yml [ONLY="k8s/a.md k8s/b.md"]`: no lab
  needed. Lists commands per file and the commands that will probably hang.
  Fix those first: add `wait`/`keys`/`key` directives after them.
- `make labtest SLIDES_DECK=<deck>.yml TAG=<tag> [ONLY=... | FROM=file[:line] TO=file]`:
  runs on node1 of `prepare-labs/tags/<tag>` as the student user. Use
  `ONLY` to re-test one chapter after a fix. Run it in the background for
  long selections.
- Read `slides/labtest/runs/latest/summary.md` first. Open
  `steps/NNNN.log` only for the failures and `PASS*` warnings in it.

When a step fails, decide which case it is, and say so in the report:

- Slide bug: the command or the expected output on the slide is wrong. Fix
  the Markdown, then re-test that file.
- Missing directive: the command is interactive or fails on purpose. Add a
  hidden directive (`wait`, `keys`, `key`, `expect-fail`, `timeout`, `skip`).
- Cluster state: the failure comes from state of an earlier test on a used
  lab (an object that exists, a removed node). Confirm it before you blame
  the slide; a fresh lab gives the reference result.
- Lab setup: a tool or setting is missing on the lab image. Fix it in
  `prepare-labs/`.

Commands that must succeed need a clean exit code. Output the student reads
must match the slide text.
