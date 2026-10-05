<!-- verified: 2026-10-05 -->
# Managing applications with Helm

## Helm today

- Helm is a package manager for Kubernetes and a CNCF graduated project

- A *chart* packages templates and default values

- A *release* is an installation of a chart in a namespace

- Helm calls the Kubernetes API with your current kubeconfig credentials

- This workshop uses Helm **4.3.0** and stable `apiVersion: v2` charts

---

## What Helm 4 adds

- Server-side apply by default for new releases

- Better readiness monitoring with the `watcher` wait strategy

- A redesigned plugin system, with an optional WebAssembly runtime

- Content-based chart caching and reproducible chart archives

- The core workflow stays: install, inspect, upgrade, history, rollback

[Helm 4 overview](https://helm.sh/docs/overview/)

???

Helm 4.0 shipped November 12, 2025. Verified with Helm 4.3.0.
Upgrades preserve the previous release's apply method. Existing Helm 3
releases keep client-side apply unless explicitly changed and tested.
OCI digest installs already existed before Helm 4; do not present them as new.

---

## Check the tools and credentials

.lab[

- Create a working directory, then check the tools and context:
  ```bash
  mkdir -p ~/helm-workshop
  cd ~/helm-workshop
  helm version --short
  kubectl config current-context
  kubectl auth can-i create deployments
  ```

]

- Use Helm 4.3.0 for these labs

- If it is missing, ask the instructor to prepare the lab

- For other machines, use the [official installation instructions](https://helm.sh/docs/intro/install/)

---

## Charts, registries, and releases

- HTTP chart repositories contain an `index.yaml` and chart archives

- OCI registries store charts at paths such as `oci://ghcr.io/...`

- [Artifact Hub](https://artifacthub.io/) indexes charts from many publishers

- Check the publisher, chart version, images, and required permissions

- One chart can create many releases with different names and values

---

## Install a chart

- We use the OWASP Juice Shop demo chart from secureCodeBox

- Keep this intentionally vulnerable app inside the lab cluster

.lab[

- Install the pinned chart in a separate namespace:
  ```bash
  helm install my-juice-shop \
    oci://ghcr.io/securecodebox/helm/juice-shop --version 5.9.0 \
    --namespace helm-intro --create-namespace \
    --wait=watcher --timeout 3m
  ```
<!-- ```timeout 240``` -->

]

[Publisher instructions](https://www.securecodebox.io/docs/getting-started/installation/)

---

## Inspect the release

.lab[

- List releases and inspect this release:
  ```bash
  helm list --namespace helm-intro
  helm status my-juice-shop --namespace helm-intro
  helm get values my-juice-shop --namespace helm-intro
  ```

- Find the resources by the chart's instance label:
  ```bash
  kubectl get all --namespace helm-intro \
    --selector app.kubernetes.io/instance=my-juice-shop
  ```

]

The chart sets this label. Helm does not add it to every chart automatically.

---

## Inspect the chart's values

- Values are the settings that a chart exposes

- Defaults come from its `values.yaml`; templates decide how to use them

.lab[

- Read the defaults for the pinned chart:
  ```bash
  helm show values oci://ghcr.io/securecodebox/helm/juice-shop \
    --version 5.9.0
  ```

]

Use `--values file.yaml` for a set of settings; use `--set` for small changes.

---

## Upgrade the release

- The chart has `replicaCount: 1` by default

.lab[

- Change the number of replicas:
  ```bash
  helm upgrade my-juice-shop \
    oci://ghcr.io/securecodebox/helm/juice-shop --version 5.9.0 \
    --namespace helm-intro --set replicaCount=2 \
    --wait=watcher --timeout 3m
  ```
<!-- ```timeout 240``` -->

- Inspect the values and history:
  ```bash
  helm get values my-juice-shop --namespace helm-intro
  helm history my-juice-shop --namespace helm-intro
  ```

]

The command needs both RELEASE and CHART, even for a values change.

---

## Wait and recover on failure

- Without `--wait`, Helm waits for hooks, not all application resources

- `--wait=watcher --timeout 3m` waits for Kubernetes readiness

- `--rollback-on-failure` rolls a failed upgrade back to a successful revision

- Readiness needs useful probes; it does not prove business operations work

- Rollback does not reverse database migrations or external side effects

[Upgrade flags](https://helm.sh/docs/helm/helm_upgrade/)

---

## Test an upgrade failure

- Use a deliberately missing image tag and a short timeout

.lab[

- Run the failed upgrade and automatic rollback:
  ```bash
  helm upgrade my-juice-shop \
    oci://ghcr.io/securecodebox/helm/juice-shop --version 5.9.0 \
    --namespace helm-intro --set image.tag=does-not-exist-helm-lab \
    --wait=watcher --timeout 30s --rollback-on-failure
  ```
<!-- ```expect-fail``` -->
<!-- ```timeout 180``` -->

- Confirm that the release returned to its previous settings:
  ```bash
  helm history my-juice-shop --namespace helm-intro
  helm get values my-juice-shop --namespace helm-intro
  ```

]

---

## Roll back and clean up

.lab[

- Restore revision 1, then inspect the new history entry:
  ```bash
  helm rollback my-juice-shop 1 --namespace helm-intro \
    --wait=watcher --timeout 3m
  helm history my-juice-shop --namespace helm-intro
  ```
<!-- ```timeout 240``` -->

- Remove the release and its lab namespace:
  ```bash
  helm uninstall my-juice-shop --namespace helm-intro
  kubectl delete namespace helm-intro
  ```

]

Rollback creates a new revision. It does not erase the old history.

???

:EN:- Helm concepts
:EN:- Installing software with Helm
:EN:- Finding charts on the Artifact Hub

:FR:- Fonctionnement général de Helm
:FR:- Installer des composants via Helm
:FR:- Trouver des *charts* sur *Artifact Hub*

:T: Getting started with Helm and its concepts

:Q: What is a Helm release?
:A: A Helm binary version
:A: ✔️An installation of a chart in a namespace
:A: An image tag
:A: An OCI registry

:Q: Where can you distribute a chart?
:A: Only on Artifact Hub
:A: Only on Docker Hub
:A: ✔️An HTTP chart repository or an OCI registry
:A: Only in a Kubernetes Secret
