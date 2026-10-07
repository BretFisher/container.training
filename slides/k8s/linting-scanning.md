<!-- verified: 2026-10-07 -->
# Linting and scanning

- Admission control (Pod Security, Kyverno) stops bad resources *at the API server*

- We also want to find problems:

  - **before** they get to the cluster (in the editor, in CI)

  - **after** they get to the cluster (resources and images that are already there)

- Linters and scanners do this

- They read YAML, Helm charts, Kustomize overlays, a live cluster, or a node

---

## Where each tool runs

| Where | What it checks | Tools (2026) |
|-|-|-|
| Editor, CI | YAML schema | kubeconform |
| Editor, CI | Security and best practices | kube-linter, Trivy, Kubescape, Polaris, Checkov |
| Editor, CI | *Our own* rules | Kyverno CLI, conftest (OPA), kube-linter custom checks |
| API server | Our own rules | Pod Security Admission, Kyverno, ValidatingAdmissionPolicy |
| Live cluster | Resources, RBAC, image CVEs | Trivy, Kubescape, Polaris |
| Nodes | CIS Benchmark | kube-bench, Trivy, Kubescape |
| Upgrades | Deprecated API versions | Pluto |

- Kyverno policies can run in two places: in CI (`kyverno apply`) and in the cluster

---

## Helm charts and Kustomize

- Scan what we *apply*, not only the source files

- Most tools read a chart directory or YAML from stdin:

```bash
helm template ./mychart | kubeconform -summary -
kubectl kustomize overlays/prod | kube-linter lint -
```

- Some tools read charts or overlays directly:

  - kube-linter: a chart directory, or a Kustomize directory (since 0.8)

  - Trivy: `trivy config ./mychart` (but not Kustomize overlays: render them first)

  - Kubescape: `kubescape scan ./mychart`

- `helm lint` checks the chart format, not security

---

## Project status in 2026

- Active: Trivy, Kubescape (CNCF incubating), Kyverno (CNCF graduated),
  <br/>kubeconform, kube-linter, Polaris, Checkov, conftest, Pluto, kube-bench

- Low activity: kube-score, Popeye, kubent (use Pluto for deprecated APIs)

- Gone: kubeval (use kubeconform), Datree (the company closed in 2023)

- The CIS Kubernetes Benchmark is at version 2.x in 2026

  (scanners lag: Trivy has CIS 1.23, Kubescape has CIS 1.12)

---

## Lab: schema and best practices

- Our lab nodes have `kubeconform`, `kube-linter`, `trivy`, and `kyverno`

.lab[

- Go to the directory of our manifests:
  ```bash
  cd ~/container.training/k8s
  ```

- Check the YAML against the Kubernetes API schemas:
  ```bash
  kubeconform -summary dockercoins.yaml
  ```

- Check it for security and best-practice problems:
  ```bash
  kube-linter lint dockercoins.yaml
  ```

<!-- ```expect-fail``` -->

]

- The YAML is valid, but kube-linter finds 21 problems (root user, no limits...)

---

## Lab: our own lint rules

- @@LINK[k8s/kube-linter-config.yaml] changes the default checks for our team:

  - removes a check, adds the `latest-tag` check, adds a custom check (`owner` label)

.lab[

- Run kube-linter with our config, then count the problems by check:
  ```bash
    kube-linter lint --config kube-linter-config.yaml dockercoins.yaml 2>&1 |
      grep -oE "check: [a-z-]+" | sort | uniq -c
  ```

]

- `latest-tag` finds `redis` (no tag means `latest`)

- `team-owner-label` finds the 5 Deployments with no `owner` label

- In a repository, name the file `.kube-linter.yaml`: kube-linter reads it automatically

---

## Kyverno basics

- [Kyverno](https://kyverno.io/) is a policy engine for Kubernetes (CNCF graduated, 2026)

- A policy is a Kubernetes resource, written in YAML

  (no new programming language: rules use CEL, like ValidatingAdmissionPolicy)

- Policy types: `ValidatingPolicy` (accept or reject), `MutatingPolicy` (change),
  <br/>`GeneratingPolicy` (create), `ImageValidatingPolicy` (check image signatures)

- Kyverno runs in two places:

  - **in the cluster:** an admission webhook; it checks each API request

    (`Deny` rejects the request; `Audit` only writes a report)

  - **in CI:** the `kyverno` CLI checks YAML files, with no cluster

- In this lab, we use only the CLI (we do not need Kyverno in the cluster)

---

## Lab: our own policy, before the cluster

- @@LINK[k8s/kyverno-trusted-registry.yaml] is a Kyverno `ValidatingPolicy`:

  Deployments use images from `ghcr.io/bretfisher/` only

- The Kyverno CLI applies it to files, with no cluster

.lab[

- Test our manifest against the policy:
  ```bash
  kyverno apply kyverno-trusted-registry.yaml --resource dockercoins.yaml
  ```

<!-- ```expect-fail``` -->

]

- The `redis` Deployment fails: its image comes from Docker Hub

- Run the same policy in CI (`kyverno apply`) and in the cluster (admission)

  (we write the rule one time, and we use it in two places)

---

## Lab: Trivy on manifests

.lab[

- Scan the manifest for misconfigurations:
  ```bash
  trivy config dockercoins.yaml
  ```

]

- Each finding has an ID (like `KSV-0001`), a severity, and the YAML lines

- Use `--severity HIGH,CRITICAL` to see only the important findings

- Use `--exit-code 1` to fail a CI job when Trivy finds a problem

---

## Lab: scanning a live namespace

- `trivy k8s` reads resources from the cluster, then looks for misconfigurations,
  <br/>secrets, CVEs in the images, and RBAC problems

.lab[

- Deploy DockerCoins in a new namespace:
  ```bash
  kubectl create namespace scanme
  kubectl apply -n scanme -f dockercoins.yaml
  ```

<!-- ```hide kubectl wait -n scanme deploy --all --for condition=available --timeout=120s``` -->

- Scan the namespace (this takes less than a minute):
  ```bash
  trivy k8s --include-namespaces scanme --disable-node-collector --report summary
  ```

]

---

## Reading the results

- Columns: vulnerabilities, misconfigurations, secrets

  (C = critical, H = high, M = medium, L = low, U = unknown)

- Each image has CVEs: in the OS packages (`redis` has more than 100)

  and in the app packages (Ruby, Python, and Node.js in our own images)

- To see the details of one workload:
  ```bash
  trivy k8s --include-namespaces scanme --include-kinds Deployment --report all
  ```

- Without `--include-namespaces`, Trivy scans the whole cluster (a long report!)

- `--disable-node-collector`: do not start a Job on each node to read node files

---

## Lab: a compliance report

- Trivy has compliance reports: `k8s-pss-baseline-0.1`, `k8s-pss-restricted-0.1`,
  <br/>`k8s-nsa-1.0`, `k8s-cis-1.23`, `eks-cis-1.4`

.lab[

- Check our namespace against the Pod Security Standards (baseline):
  ```bash
    trivy k8s --include-namespaces scanme --disable-node-collector \
      --compliance k8s-pss-baseline-0.1 --report summary
  ```

]

- One line for each control, with PASS or FAIL

- Seccomp fails: our pods do not set a seccomp profile (there is no default)

- Try `k8s-pss-restricted-0.1`: DockerCoins fails more controls

---

## Scanning all the time

- A CLI scan shows the state at one time; clusters change all the time

- Operators scan in the cluster, and store the results as Kubernetes resources:

  - Trivy Operator: `VulnerabilityReport`, `ConfigAuditReport`, `RbacAssessmentReport`

  - Kubescape operator: posture, image CVEs, and runtime threat detection

- Send the results to a dashboard or to alerts

  (an unread report does not make us more secure!)

- Kubescape CLI: `kubescape scan framework nsa` (also `mitre`, `cis-v1.12.0`)

---

## Scanners are software, too

- March 2026: an attacker took control of release credentials of Trivy

  ([GHSA-69fq-xp46-6x23](https://github.com/aquasecurity/trivy/security/advisories/GHSA-69fq-xp46-6x23))

  - Trivy v0.69.4 had malware for about 3 hours

  - 76 of 77 tags of the `trivy-action` GitHub Action were changed to malware

  - the malware sent CI secrets (cloud, Kubernetes, SSH) to the attacker

- Security tools run with a lot of access: they are a good target

- Pin versions by digest or commit SHA, not by tag

  (`uses: aquasecurity/trivy-action@<full SHA>`, `image: trivy@sha256:...`)

- Verify signatures: Trivy releases have Sigstore bundles (`cosign verify-blob`)

---

## Lab: cleaning up

.lab[

- Delete the namespace:
  ```bash
  kubectl delete namespace scanme
  cd
  ```

]

???

:EN:- Linting and scanning manifests, charts, and clusters
:FR:- Analyse des manifests, des charts et des clusters
