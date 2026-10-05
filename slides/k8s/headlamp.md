<!-- verified: 2026-10-05 -->
# Headlamp, a web UI for Kubernetes

- Kubernetes resources can also be viewed (and changed) with a web UI

- [Headlamp] is a Kubernetes SIG UI project

  (the Kubernetes Dashboard is archived; Headlamp replaces it)

- Headlamp users need to authenticate

  (with a token, or with OIDC)

- Headlamp should be exposed over HTTPS

  (to prevent interception of the aforementioned token)

- Ideally, this requires obtaining a proper TLS certificate

  (for instance, with Let's Encrypt)

[Headlamp]: https://headlamp.dev/

---

## Two ways to run Headlamp

- As a desktop app (Linux, macOS, Windows)

  - it uses our kubeconfig file, like `kubectl`

  - nothing to install on the cluster

- In the cluster, with a Helm chart

  - everyone with a browser (and a token) can use it

  - this is what we will do now

---

## What's in the Helm chart?

- The Headlamp server itself (a Deployment and a Service)

- A ServiceAccount with `cluster-admin` privileges

  (bound with a ClusterRoleBinding; this is the default!)

- Headlamp has no anonymous mode: we always need a token to log in

- But anyone with the token of that ServiceAccount is `cluster-admin`!

---

## Installing Headlamp

- We will expose Headlamp with a `NodePort`, to connect to it easily

.lab[

- Install Headlamp:
  ```bash
    helm upgrade --install --repo https://kubernetes-sigs.github.io/headlamp/ \
      --namespace headlamp --create-namespace headlamp headlamp \
      --set service.type=NodePort
  ```

<!-- ```hide kubectl rollout status deployment headlamp --namespace headlamp``` -->

]

---

## Connecting to Headlamp

.lab[

- Check which port Headlamp is on:
  ```bash
  kubectl get svc --namespace=headlamp
  ```

]

You'll want the `3xxxx` port.

.lab[

- Connect to http://oneofournodes:3xxxx/

<!-- ```hide curl -fsS http://node1:$(kubectl get svc headlamp --namespace headlamp -o jsonpath={.spec.ports[0].nodePort})/ -o /dev/null``` -->

]

Headlamp will then ask us for a token.

---

## Obtaining an admin token

- The Helm chart created a ServiceAccount named `headlamp`

- We can ask the API server for a short-lived token for that ServiceAccount

.lab[

- Create a token:
  ```bash
  kubectl create token headlamp --namespace=headlamp
  ```

]

The token should start with `eyJ...` (it's a JSON Web Token).

It expires after one hour (use `--duration` to change that).

---

## Headlamp authentication

- Copy paste the token (starting with `eyJ...`) obtained earlier

- We're logged in!

- We can see (and change) everything in the cluster

--

.warning[Remember, this token gives full control of our cluster to anyone who has it!]

---

## A read-only token

- We can give a token with fewer permissions instead

- The `view` ClusterRole gives read-only access to most resources

  (but not to Secrets)

.lab[

- Create a ServiceAccount bound to the `view` ClusterRole:
  ```bash
  kubectl create serviceaccount viewer --namespace=headlamp
  kubectl create clusterrolebinding headlamp-viewer \
          --clusterrole=view --serviceaccount=headlamp:viewer
  ```

- Create a token for that ServiceAccount:
  ```bash
  kubectl create token viewer --namespace=headlamp
  ```

]

---

## Logging in with the read-only token

- Log out of Headlamp, and log in again with the new token

- We can see most resources, but we can't change them

- Headlamp hides the actions that our token can't do

.lab[

- Check what that token can do:
  ```bash
  kubectl auth can-i list pods --as=system:serviceaccount:headlamp:viewer
  kubectl auth can-i list secrets --as=system:serviceaccount:headlamp:viewer
  ```

<!-- ```expect-fail``` -->

]

---

## The risks

- The steps that we just showed you are *for educational purposes only!*

- We exposed Headlamp over plain HTTP, on every node of the cluster

- We left a ServiceAccount with `cluster-admin` privileges

- If you do that on your production cluster, people [can and will abuse it](https://www.wired.com/story/cryptojacking-tesla-amazon-cloud/)

  (Tesla's Kubernetes console was used to mine cryptocurrency in 2018)

---

## Better ways to deploy Headlamp

- Keep the Service internal (`ClusterIP`, the default)

- Connect with `kubectl port-forward`:

  `kubectl port-forward --namespace=headlamp service/headlamp 8080:80`

  (then connect to http://localhost:8080/)

- Or use an Ingress or a Gateway with a proper TLS certificate

- Set `clusterRoleBinding.create=false` in the Helm chart

- Use [OIDC] for authentication, and RBAC for permissions

[OIDC]: https://headlamp.dev/docs/latest/installation/in-cluster/oidc/

---

## Removing the admin access

- Seriously, don't leave that `cluster-admin` binding in place!

- We keep Headlamp (and the read-only `viewer` token) for later

.lab[

- Upgrade the release, without the ClusterRoleBinding:
  ```bash
    helm upgrade headlamp --repo https://kubernetes-sigs.github.io/headlamp/ \
      --namespace headlamp headlamp --reuse-values \
      --set clusterRoleBinding.create=false
  ```

- Check that the admin token doesn't work anymore:
  ```bash
  kubectl auth can-i list secrets --as=system:serviceaccount:headlamp:headlamp
  ```

<!-- ```expect-fail``` -->

]

The token is still valid, but RBAC checks permissions on each request.

---

## Other UIs

- [k9s](https://k9scli.io/) is a terminal UI

  (it runs in our shell, with our kubeconfig, like `kubectl`)

- The [Headlamp desktop app](https://headlamp.dev/docs/latest/installation/desktop/)

  (no installation on the cluster; it can switch between multiple clusters)

- Headlamp also has [plugins](https://headlamp.dev/docs/latest/development/plugins/)

  (to add views for other tools, e.g. Flux, cert-manager, Prometheus...)

---

# Security implications of `kubectl apply`

- When we do `kubectl apply -f <URL>`, we create arbitrary resources

- Resources can be evil; imagine a `deployment` that ...

--
  - starts bitcoin miners on the whole cluster

--
  - hides in a non-default namespace

--
  - bind-mounts our nodes' filesystem

--
  - inserts SSH keys in the root account (on the node)

--
  - encrypts our data and ransoms it

--
  - ☠️☠️☠️

---

## `kubectl apply` is the new `curl | sh`

- `curl | sh` is convenient

- It's safe if you use HTTPS URLs from trusted sources

--

- `kubectl apply -f` is convenient

- It's safe if you use HTTPS URLs from trusted sources

- Example: the official setup instructions for most pod networks

--

- The same is true for `helm install` with a chart from a remote repository

  (e.g. the Headlamp chart that we just installed: it created a `cluster-admin` binding!)

--

- It introduces new failure modes

  (for instance, if you try to apply YAML from a link that's no longer valid)

???

:EN:- The Headlamp web UI
:FR:- L'interface web Headlamp
