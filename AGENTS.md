# Working in this repository

Container-training course materials: Markdown decks compiled by custom Python
MarkMaker scripts and rendered with Remark (not Slidev).

## Directory map

- `slides/`: deck manifests (`*.yml`), compiler, templates, CSS, and publishing assets.
  - `containers/`, `swarm/`, `k8s/`, `terraform/`, `flux/`: topic-specific slide sources.
  - `shared/`: content reused across decks; edits can affect multiple courses.
  - `images/`, `exercises/`: slide assets and hands-on exercise materials.
  - `autopilot/`: semi-automated exercise testing harness.
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
```

One container builds every deck at startup and serves them at
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

For a one-shot build without Docker, use Python 3 with dependencies from
`slides/requirements.txt`, then run `cd slides && make build` (or `./build.sh once`).
Set `SLIDES_ZIP=1` to also produce `slides.zip` (needs `zip`); Netlify does this.
Edit sources rather than generated `*.yml.html`, `index.html`, `past.html`, or `slides.zip`.

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
