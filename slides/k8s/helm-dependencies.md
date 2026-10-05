# Charts using other charts

- A parent chart can depend on other charts

- A dependency contributes its resources to the same Helm release

- This optional lab uses DockerCoins and a small local Redis chart

- The example uses the official Redis image, with a fixed tag

- The Redis chart is for an ephemeral lab: no persistence, TLS, or authentication

---

## Declare a dependency

- Dependencies belong in the parent's `Chart.yaml`

```yaml
apiVersion: v2
name: dockercoins-deps
version: 0.1.0
dependencies:
  - name: redis
    version: 0.1.0
    repository: file://../redis
    condition: redis.enabled
```

- `file://` packages a local chart; HTTP and OCI repositories are also supported

- Use the singular key `condition`

- `redis.enabled=false` disables this dependency; DockerCoins then needs another Redis

---

## Inspect the local examples

.lab[

- Copy the parent and its Redis dependency:
  ```bash
  mkdir -p ~/helm-dependency-workshop
  cd ~/helm-dependency-workshop
  cp -R ~/container.training/k8s/helm-labs/dockercoins-deps .
  cp -R ~/container.training/k8s/helm-labs/redis .
  cat dockercoins-deps/Chart.yaml
  cat dockercoins-deps/values.yaml
  cat redis/values.yaml
  ```

]

The parent owns four app components. The dependency owns the Redis Deployment and Service.

---

## Update and lock

.lab[

- Resolve and package the dependency, then inspect the lock:
  ```bash
  helm dependency update ./dockercoins-deps
  cat dockercoins-deps/Chart.lock
  ls dockercoins-deps/charts/
  ```

]

- `Chart.lock` records the resolved chart versions and dependency digest

- Commit it with `Chart.yaml`; review and test updates

- Fixed versions and a lock help repeatability; retain trusted chart archives too

---

## Build versus update

- `helm dependency update` resolves `Chart.yaml` and writes `Chart.lock`

- `helm dependency build` rebuilds `charts/` from the existing lock

- Without a lock, `build` behaves like `update`

.lab[

- Rebuild from the lock and render the full application:
  ```bash
  helm dependency build ./dockercoins-deps
  helm lint ./dockercoins-deps
  helm template coins ./dockercoins-deps --namespace helm-dependencies \
    > dependencies-rendered.yaml
  ```

]

---

## Configure the dependency

- Parent values under `redis:` become the child chart's values

```yaml
redis:
  enabled: true
  fullnameOverride: redis
```

- This chart exposes `fullnameOverride` as a supported setting

- The rendered Service is named `redis`, as the DockerCoins clients expect

- Inspect a vendor chart's values and rendered output before you choose it

- Use supported configuration; do not edit packaged vendor templates

---

## Deploy and inspect

.lab[

- Install the whole application as one release:
  ```bash
  helm install coins ./dockercoins-deps --namespace helm-dependencies \
    --create-namespace --wait=watcher --timeout 3m
  ```
<!--
```timeout 240```
-->

- Check the Service and worker:
  ```bash
  kubectl get service redis --namespace helm-dependencies
  kubectl logs deploy/worker --namespace helm-dependencies --tail=10
  helm list --namespace helm-dependencies
  ```

]

The dependency has no separate Helm release or separate revision history.

---

## Multiple copies and cleanup

- `alias` can include the same chart more than once

- Each alias needs distinct resource names and its own values

- Our fixed DockerCoins Service names permit one copy per namespace

.lab[

- Remove the parent release and its dependency resources:
  ```bash
  helm uninstall coins --namespace helm-dependencies
  kubectl delete namespace helm-dependencies
  ```

]

???


:EN:- Depending on other charts
:EN:- Charts within charts

:FR:- Dépendances entre charts
:FR:- Un chart peut en cacher un autre
