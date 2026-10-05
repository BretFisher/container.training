<!-- verified: 2026-10-05 -->
# Creating a basic chart

- Package the five DockerCoins components in one release

- Start with the existing manifests; add templates when settings must vary

.lab[

- Create a chart and remove the sample NGINX templates:
  ```bash
  helm create dockercoins
  sed -i '/^appVersion:/d' dockercoins/Chart.yaml
  rm -r dockercoins/templates
  mkdir dockercoins/templates
  cp ~/container.training/k8s/dockercoins.yaml dockercoins/templates/
  sed -i 's/image: redis$/image: redis:8.2.2/' \
    dockercoins/templates/dockercoins.yaml
  ```

]

These commands use the Linux student VM.

---

## Render before you deploy

.lab[

- Check the chart and inspect its rendered manifests:
  ```bash
  helm lint ./dockercoins
  helm template helmcoins ./dockercoins --namespace helmcoins \
    > helmcoins-rendered.yaml
  cat helmcoins-rendered.yaml
  ```

]

- Rendering checks templates and values; it does not contact Kubernetes

- It does not prove that images can run or cluster policy will allow them

---

## Namespace and resource ownership

- An earlier exercise can already have DockerCoins in the default namespace

- These manifests use fixed names such as `hasher` and `redis`

- Install in a separate namespace to avoid resource conflicts

- Helm checks ownership metadata before adopting existing resources

- A second release with these fixed names in the same namespace will conflict

- Design names and selectors for multiple releases; do not bypass ownership checks

---

## Install and inspect

.lab[

- Create the namespace and install the release:
  ```bash
  helm install helmcoins ./dockercoins --namespace helmcoins \
    --create-namespace --wait=watcher --timeout 3m
  ```
<!-- ```timeout 240``` -->

- Inspect the release and the worker:
  ```bash
  helm list --namespace helmcoins
  kubectl get deployments,services --namespace helmcoins
  kubectl logs deploy/worker --tail=10 --namespace helmcoins
  ```

]

Always specify the release namespace in Helm commands.

---

## What this chart provides

- Helm records the chart, values, and rendered manifests in release history

- We can upgrade, roll back, and uninstall this group of resources

- This chart has no tunable settings yet

- Next steps: template replicas, resource names, images, and security settings

- Add recommended labels to identify the application and release

[Chart labels](https://helm.sh/docs/chart_best_practices/labels/)

---

## Clean up

.lab[

- Remove the release and the empty lab namespace:
  ```bash
  helm uninstall helmcoins --namespace helmcoins
  kubectl delete namespace helmcoins
  ```

]

The chart directory stays on disk for further work.

???


:EN:- Writing a basic Helm chart for the whole app
:FR:- Écriture d'un *chart* Helm simplifié
