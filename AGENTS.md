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

## Create slide diagrams

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

## Current project: two-day Kubernetes security workshop

Deck: `slides/kube-sec-twodays.yml` ("Kubernetes Architecture and Security").
Day 1 is Kubernetes fundamentals; day 2 is platform and workload security.
The client quote in the manifest header is the source of truth for topics.
The `REVIEW:`, `ADD EXISTING FILES`, and `NET NEW SLIDES` comments in the
manifest hold the per-file reasons; this section holds the order of work.

The goal is a **tested** workshop: every `.lab[]` block runs clean on the
student lab environment, in deck order, from a fresh lab. A slide that reads
well but fails on a lab is a bug. When a phase is done, tick its box here and
delete its comments from the manifest.

### Decisions

- Deck file: `slides/kube-sec-twodays.yml`. Make workshop changes there, not in
  `kube-twodays.yml`.
- Lab platform: kubeadm clusters on AWS VMs, not EKS. Provision with
  `labctl create --provider aws --settings settings/kubernetes.env`. Test every
  exercise on this platform. This keeps `user-cert.md`, `control-plane-auth.md`,
  and encryption at rest hands-on, because they need `/etc/kubernetes` and the
  cluster CA.
- GitOps: `gitworkflows.md` is the last lecture of day 1, after `cert-manager.md`.
  `flux.md`, `argocd.md`, and `argocd-advanced.md` stay in the manifest as
  commented-out lines, marked as potential after-hours labs. Bret uncomments
  one to offer students self-paced hands-on outside class time. Keep both chapters runnable on the lab, and
  do not split them: `kube-twodays`, `kube-fullday`, and `kube-selfpaced` also
  use them. Known self-paced gaps: `flux.md:193` has no `blue.yaml` content,
  `argocd admin dashboard` listens on the VM's localhost, and both chapters ask
  for two clusters but use one.
- EKS: students get no EKS access. The class has 100+ students whose names are
  known only on the day, so per-student IAM setup (`prepare-eks/`,
  `access-eks-cluster.md`) cannot work. Bret gives instructor-only EKS demos
  that compare EKS with the students' kubeadm clusters. Students watch.

### Open decisions (ask Bret)

- EKS scope: which `aws-eks.md` slides stay, where they go (day 1 or day 2
  next to `authn-authz.md`), and which demos Bret gives.
- OpenID Connect demo: which OIDC provider the students use.

### Plan

1. [ ] **Manifest match.** Apply every `REVIEW:` comment and move each
   `ADD EXISTING FILES` line into its `(ADD HERE: ...)` group. Move `netpol.md`
   below the auth chapters to match the quote order. Done when each quote topic
   maps to one active file or sub-chapter and `./build.sh once` passes.
2. [ ] **Day 1 time budget.** Day 1 has 33 quote topics plus EKS, GitOps, and
   cert-manager. Trim the Helm chart-authoring files (`helm-create-basic-chart`,
   `helm-create-better-chart`, `helm-dependencies`,
   `helm-values-schema-validation`). Done when Bret approves the day 1 list.
3. [ ] **Existing hands-on test.** Run every exercise in deck order on one
   lab. Record each failure with file, slide title, command, and output. Known
   risk: `pod-security-policies.md` edits API server flags and fails on 1.25+;
   teach it as history and remove its exercises. Done when all exercises pass
   or each failure has a fix or a removal.
4. [ ] **Net new slides.** Write the seven files in `NET NEW SLIDES`, in this
   order: `pod-hardening`, `encryption-at-rest`, `external-secrets`,
   `kyverno-security-policies`, `linting`, `gitops-pr-gating`,
   `supply-chain-security`. Each hands-on uses dockercoins, so it builds on the
   day 1 app. Done per file when its exercises pass on a fresh lab.
5. [ ] **Lab setup.** Pre-install on the lab image each tool that the day 2
   exercises need (Kyverno CLI, kubeconform, kube-linter, cosign, trivy, syft,
   kubeseal) so students spend class time on security, not installs. Done when
   a fresh `labctl create` lab runs phase 3 and 4 exercises with no manual step.
6. [ ] **Full dry run.** Run both days end to end on a fresh lab with the
   final deck, and note the time per chapter. Inspect the built deck in the
   browser for overflow and broken images. Done when no exercise fails and the
   time fits two days.

### Test exercises

Use `slides/labtest/` (read its README for directives and result files).
From `slides/`:

- `make labtest-plan DECK=<deck>.yml [ONLY="k8s/a.md k8s/b.md"]`: no lab
  needed. Lists commands per file and the commands that will probably hang.
  Fix those first: add `wait`/`keys`/`key` directives after them.
- `make labtest DECK=<deck>.yml TAG=<tag> [ONLY=... | FROM=file[:line] TO=file]`:
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
