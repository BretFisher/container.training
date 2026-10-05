# Exercise — Helm charts

Create a Helm chart for DockerCoins.

Level 1: package the existing DockerCoins manifests and render them.

Level 2: make the worker replica count configurable through values.

Level 3: add a values schema that rejects invalid replica counts.

Install in a separate namespace, inspect the worker, then clean up.

---

## Hints

--

Use `helm create`, then replace the sample templates with the DockerCoins manifests.

--

Use `{{ .Values.worker.replicas }}` for the worker Deployment replica count.

--

Provide a default in `values.yaml`; declare an integer with `minimum: 1` in the schema.

--

Run `helm lint` and `helm template` before `helm install`.

--

Use an explicit namespace and `--wait=watcher --timeout 3m` for the install.
