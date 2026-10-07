# Deploying DockerCoins with YAML

- We have deployed DockerCoins twice:

  - with Compose, on a single machine

  - with `kubectl create` and `kubectl expose`, on our cluster (9 commands!)

- Now we know that YAML is better for anything that we want to repeat

  (it's reviewed, versioned in git, and applied with a single command)

- Let's remove DockerCoins, then deploy it again from a single YAML file

---

## Removing our first deployment of DockerCoins

.lab[

- Delete the Deployments and Services that we created with `kubectl`:
  ```bash
  kubectl delete deployment hasher redis rng webui worker --cascade=foreground
  kubectl delete service hasher redis rng webui
  ```

  (`--cascade=foreground` waits until the Pods are gone, too)

- Delete the `rng` DaemonSet from the DaemonSets chapter, too:
  ```bash
  kubectl delete daemonset rng --cascade=foreground
  ```

- Check that only the `kubernetes` Service is left:
  ```bash
  kubectl get all
  ```

]

---

## Our YAML manifest

- @@LINK[k8s/dockercoins.yaml] has the same 5 Deployments and 4 Services as before

- Each resource is separated by `---`; for instance, `rng`:

.small[
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app: rng
  name: rng
spec:
  replicas: 1
  selector:
    matchLabels:
      app: rng
  template:
    metadata:
      labels:
        app: rng
    spec:
      containers:
      - image: ghcr.io/bretfisher/dockercoins/rng:v0.1
        name: rng
```
]

---

## Deploying with YAML

.lab[

- Apply the manifest:
  ```bash
  kubectl apply -f ~/container.training/k8s/dockercoins.yaml
  ```

<!-- ```hide
kubectl wait deploy --all --for condition=available --timeout=120s
``` -->

- Check what was created:
  ```bash
  kubectl get deployments,services
  ```

- Check that the `worker` is working (Ctrl-C to stop):
  ```bash
  kubectl logs deploy/worker --follow
  ```

<!--
```wait units of work done```
```key ^C```
-->

]

---

name: visual-k8s-dockercoins-manifest-map-2026-review-40
class: pic

<!-- Diagram proposal #40; adjacent text retained for review. -->
![One manifest defines the whole application](images/k8s-dockercoins-manifest-map-2026.svg)

---

## Back to the web UI

- The `webui` Service is a new `NodePort` Service

  (so it probably has a different port number than before!)

.lab[

- Check the port number of the `webui` Service:
  ```bash
  kubectl get service webui
  ```

- Open the web UI in your browser (http://node-ip-address:3xxxx/)

<!-- ```open http://node1:3xxxx/``` -->

]

- Next time, we can deploy DockerCoins with one command

  (and remove it with one command, too: `kubectl delete -f dockercoins.yaml`)

???

:EN:- Deploying DockerCoins with YAML
:FR:- Déployer DockerCoins avec du YAML
