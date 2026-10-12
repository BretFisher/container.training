<!-- verified: 2026-10-09 -->
# Teaching AI agents about new Kubernetes

- Many of us use AI agents to write manifests, Helm charts, and kubectl commands

- A model knows only what was in its training data

- Kubernetes has 3 releases each year:

  - 1.35: December 17, 2025
  - 1.36: April 22, 2026
  - 1.37: August 26, 2026

- If the training data stops before a release, the model does not know its features

- Result: YAML that is old, deprecated, or wrong for our cluster

---

## What goes wrong

- Removed or deprecated features:

  `gitRepo` volumes, `service.spec.externalIPs`, kube-proxy `ipvs` mode

- Old workarounds for problems that Kubernetes solves now:

  - an init container to copy files, instead of an `image` volume

  - a webhook, instead of a `MutatingAdmissionPolicy` (stable in 1.36)

- Security settings that it does not know are stable:

  - `hostUsers: false` (stable in 1.36)

  - Pod Security changes for user namespaces (1.35)

- The YAML looks correct, so it is easy to miss these problems!

---

## Agent skills

- A *skill* is a directory of instructions for an AI agent

  (Claude Code, and other agents that read the same format)

- `SKILL.md`: a name and a description, then the instructions

- The agent reads the description at start

- It loads the rest only when a task matches the description

  (this keeps the context of the model small)

- A skill can have more files: `references/` (details), `scripts/` (tools)

---

## The `k8s-catch-up` skill

- In [github.com/BretFisher/skills](https://github.com/BretFisher/skills)

- Covers the features that became beta or stable in Kubernetes 1.35, 1.36, and 1.37

- `SKILL.md` has an index: 12 categories (pods, DRA, auth and security...)

- 96 files, one for each feature, about 300 tokens each:

  - the status (beta or stable, the feature gate, the version)

  - the exact field or flag, with a short example

  - a link to the docs and to the KEP

- A table of removals and deprecations, with what to use instead

---

## One feature file

```markdown
# User namespaces

**Status:** Beta since v1.30 (gate `UserNamespacesSupport` off), on by default
since v1.33. GA in v1.36.
**Where:** `pod.spec.hostUsers`

Setting `spec.hostUsers: false` maps container UIDs into a host range no other
Pod shares, so root in the container is unprivileged on the host (...)

Docs: <https://kubernetes.io/docs/concepts/workloads/pods/user-namespaces/>
```

- The agent opens only the files that match its task

---

## What the skill tells the agent to do

- Before it writes a manifest, open the feature files for that area

- Give the stage of a beta feature, and its feature gate

- Compare the cluster version with the version of the feature

  (a field from 1.37 fails on a 1.35 API server)

- Check the output against the removals table

- Alpha features are not in the skill (they can change or go away)

---

## Does it work?

- Tested with evals: a task, then checks on the answer

- 14 evals, with Claude Haiku 4.5 (its training data stops before 1.35)

| | Without the skill | With the skill |
|-|-|-|
| Pass rate | 22% | 100% |
| Time | 72 seconds | 99 seconds |
| Tokens | 36,000 | 50,000 |

- More time and tokens, but correct YAML

.footnote[Source: `evals/k8s-catch-up/benchmark.md` in the skills repo (September 2026)]

---

## Keeping it current

- `scripts/k8s-features.py` makes the feature table from:

  - the KEP metadata (`kep.yaml`)

  - the feature gate docs

  - the release blog posts

- `make k8s-verify` checks each feature file against these sources

- After each Kubernetes release, we run the update procedure

  (`references/how-to-update.md` in the skill)

---

## Installing the skill

- As a Claude Code plugin (all of the skills in the repo):

```
/plugin marketplace add bretfisher/skills
/plugin install bretfisher-skills@bretfisher
```

- As separate skills, for many agents:

```bash
npx skills add bretfisher/skills
```

- Add `-g` to install it for all of your projects

---

## A skill is not a control

- A skill gives the agent knowledge; it does not enforce anything

- Check the output of an agent as we check the YAML of a person:

  - schema and linters in CI (kubeconform, kube-linter)

  - policies in CI and at admission (Kyverno, Pod Security)

  - a test on a cluster with the same Kubernetes version

- Give the agent a restricted identity (RBAC), not our admin kubeconfig

???

:EN:- Keeping AI agents current with new Kubernetes features
:FR:- Mettre à jour les agents IA avec les nouveautés de Kubernetes
