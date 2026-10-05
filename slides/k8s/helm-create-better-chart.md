# A chart for each DockerCoins component

- This optional lab deploys five releases from one reusable chart

- Use the Helm 4.3.0 scaffold and explicit component values

- Each release has its own image, Service name, and port

- Use a separate namespace because DockerCoins expects fixed Service names

---

## Inspect the current scaffold

.lab[

- Generate the chart and read the relevant templates:
  ```bash
  mkdir -p ~/helm-component-workshop
  cd ~/helm-component-workshop
  helm create helmcoins
  rm -r helmcoins/templates/tests
  rm helmcoins/templates/NOTES.txt
  sed -i '/^appVersion:/d' helmcoins/Chart.yaml
  cat helmcoins/templates/deployment.yaml
  cat helmcoins/templates/service.yaml
  ```

]

- Image: `.Values.image.tag`, with `.Chart.AppVersion` as a fallback

- Port: `.Values.service.port` in both Deployment and Service

- Probes: conditional blocks that use the probe values

- Names: the `fullname` helper supports `fullnameOverride`

- Remove the sample HTTP test, notes, and NGINX version metadata

---

## Separate common and component values

.lab[

- Copy and inspect the example values:
  ```bash
  cp -R ~/container.training/k8s/helm-labs/component-values .
  cat component-values/common.yaml
  cat component-values/redis.yaml
  cat component-values/worker.yaml
  ```

]

- Common values disable the unnecessary ServiceAccount token mount

- Component files pin image tags and set `fullnameOverride`

- Redis uses port 6379; the web components use port 80

- The worker has no listening port and does not need network probes

---

## Use probe values

- The scaffold's defaults use HTTP probes for NGINX

- DockerCoins has different health requirements

- Set `httpGet: null` to remove that default before adding `tcpSocket`

- For the worker, set the whole probe value to `null`

- A TCP probe checks that a port accepts connections, not application correctness

- In a production chart, use probes that check the component's useful health state

---

## Render all five releases

.lab[

- Render and lint with the same values that you will deploy:
  ```bash
  for COMPONENT in hasher rng webui worker redis; do
    helm lint ./helmcoins -f component-values/common.yaml \
      -f component-values/$COMPONENT.yaml
    helm template "$COMPONENT" ./helmcoins \
      --namespace helm-components -f component-values/common.yaml \
      -f component-values/$COMPONENT.yaml > "$COMPONENT-rendered.yaml"
  done
  cat redis-rendered.yaml
  ```

]

Check image tags, names, ports, selectors, and probes before deployment.

---

## Deploy the components

.lab[

- Install the data store and web services before the worker:
  ```bash
  for COMPONENT in redis hasher rng webui worker; do
    helm upgrade --install "$COMPONENT" ./helmcoins \
      --namespace helm-components --create-namespace \
      -f component-values/common.yaml -f component-values/$COMPONENT.yaml \
      --wait=watcher --timeout 3m
  done
  ```
<!-- ```timeout 960``` -->

]

`upgrade --install` selects an operation. Repeating it can create revisions and run hooks.

---

## Check the result

.lab[

- List the releases, Services, and worker output:
  ```bash
  helm list --namespace helm-components
  kubectl get services --namespace helm-components
  kubectl logs deploy/worker --namespace helm-components --tail=10
  ```

]

- The `redis`, `hasher`, and `rng` names match the DockerCoins clients

- No helper template or hard-coded container port needs to be changed

- The generic scaffold also creates an unused worker Service

- A dedicated component chart could make Service creation conditional

---

## Change a component and clean up

.lab[

- Scale the worker with the same full values files:
  ```bash
  helm upgrade worker ./helmcoins --namespace helm-components \
    -f component-values/common.yaml -f component-values/worker.yaml \
    --set replicaCount=2 --wait=watcher --timeout 3m
  helm history worker --namespace helm-components
  ```
<!-- ```timeout 240``` -->

- Remove the five releases and their namespace:
  ```bash
  helm uninstall redis hasher rng webui worker --namespace helm-components
  kubectl delete namespace helm-components
  ```

]

???


:EN:- Writing better Helm charts for app components
:FR:- Écriture de *charts* composant par composant
