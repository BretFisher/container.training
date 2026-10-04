# Labels and annotations

- Most resources can have *labels* and *annotations*: key/value pairs in `metadata`

```yaml
metadata:
  name: pingpong
  labels:
    app: pingpong
  annotations:
    deployment.kubernetes.io/revision: "1"
```

- Kubernetes and tools add some of them for us

  (e.g. `kubectl create deployment pingpong` adds the label `app=pingpong`)

- We can add, change, and remove them at any time

  (`kubectl label`, `kubectl annotate`, `kubectl edit`, `kubectl apply`...)

---

## Labels vs. annotations

- **Labels** identify and group resources

  - short values (up to 63 characters)

  - Kubernetes can *select* resources by their labels

  - examples: `app=pingpong`, `env=prod`, `team=payments`

- **Annotations** hold extra information for people and tools

  - values can be long (even whole JSON documents)

  - Kubernetes cannot select resources by their annotations

  - examples: last revision of a Deployment, build commit, contact email

- Rule of thumb: if we want to *find* or *group* resources by it, it's a label

---

## Selectors

- A *selector* is an expression that matches labels

- A resource matches when it has *at least* all the labels of the selector

- `kubectl` accepts selectors with `--selector` (or `-l`):

  ```bash
  kubectl get pods -l app=pingpong            # label app has value pingpong
  kubectl get pods -l app                     # label app exists (any value)
  kubectl get pods -l app=pingpong,env!=prod  # both conditions
  kubectl get pods --show-labels              # show all labels
  ```

- Selectors work with most `kubectl` commands

  (`get`, `delete`, `logs`, `label`, ...)

---

## Selectors connect Kubernetes resources

- Kubernetes uses selectors to link resources together

- A Deployment finds its Pods with a selector:

```yaml
spec:
  selector:
    matchLabels:
      app: pingpong
```

- A Service sends traffic to the Pods that match its selector

- Many other resources work the same way

  (network policies, pod disruption budgets, affinity rules...)

- If we change the labels of a Pod, it can leave (or join) a Deployment or a Service!

???

:EN:- Labels, annotations, and selectors (short version)
:FR:- *Labels*, annotations et sélecteurs (version courte)
