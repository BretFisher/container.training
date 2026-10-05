<!-- verified: 2026-10-05 -->
# Helm release Secrets

- Helm must retain chart data and values to support rollback

- By default, each revision is stored in a Kubernetes Secret

- The Secret is in the release's namespace

- Reading these Secrets can expose sensitive values and manifests

---

## Create two revisions

- Use a separate `orange` release with harmless demo values

.lab[

- Install the pinned chart, then change replica count:
  ```bash
  helm install orange oci://ghcr.io/securecodebox/helm/juice-shop \
    --version 5.9.0 --namespace helm-secrets --create-namespace \
    --wait=watcher --timeout 3m
  helm upgrade orange oci://ghcr.io/securecodebox/helm/juice-shop \
    --version 5.9.0 --namespace helm-secrets --set replicaCount=2 \
    --wait=watcher --timeout 3m
  ```
<!-- ```timeout 480``` -->

]

---

## Find the history Secrets

.lab[

- Compare release history with the stored Secrets:
  ```bash
  helm history orange --namespace helm-secrets
  kubectl get secrets --namespace helm-secrets \
    --selector owner=helm,name=orange
  ```

- Select the deployed revision by label:
  ```bash
  SECRET=$(kubectl get secrets --namespace helm-secrets \
    --selector owner=helm,name=orange,status=deployed \
    -o jsonpath='{.items[0].metadata.name}')
  kubectl describe secret "$SECRET" --namespace helm-secrets
  ```

]

The type is `helm.sh/release.v1`; the `release` field contains the payload.

---

## Decode the demo payload

- Kubernetes adds one base64 layer; Helm adds base64 and gzip around JSON

.lab[

- Decode to a local file without printing binary data:
  ```bash
  kubectl get secret "$SECRET" --namespace helm-secrets \
    -o go-template='{{ .data.release | base64decode | base64decode }}' \
    | gzip -dc > orange-release.json
  ```

- Inspect the fields and demo values:
  ```bash
  python3 -c 'import json; r=json.load(open("orange-release.json")); print(sorted(r)); print(r["config"])'
  ```

]

Only use this procedure with the lab's demo data.

---

## What the payload contains

- `chart`: chart metadata, templates, and default values

- `config`: values supplied for this release

- `manifest`: rendered Kubernetes manifests, including any Secrets

- `info`, `name`, `namespace`, `version`: release status and revision

- Earlier revisions retain earlier values, even after a value is changed

- Base64 and compression do **not** encrypt the data

???

Verified against Helm 4.3.0 storage code and the lab's release Secrets.
https://github.com/helm/helm/blob/v4.3.0/pkg/storage/driver/util.go

---

## Protect release history

- Restrict `get`, `list`, and `watch` access to Secrets with namespace RBAC

- Limit which users and automation can read release history

- Avoid sending secret values through Helm when an existing Secret can be referenced

- Treat rendered output, dry runs, and CI logs as possible secret exposures

- Encryption at rest protects storage; it does not stop an authorized API reader

- Apply the controls from the Secrets and encryption-at-rest chapters

---

## Clean up the demo

.lab[

- Delete the release, namespace, and decoded local data:
  ```bash
  helm uninstall orange --namespace helm-secrets
  kubectl delete namespace helm-secrets
  rm orange-release.json
  ```

]

Default uninstall removes this release's history. `--keep-history` retains it.

???


:EN:- Deep dive into Helm internals
:FR:- Fonctionnement interne de Helm
