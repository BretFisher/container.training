<!-- verified: 2026-10-05 -->
# Namespaces

- Resources like Pods, Deployments, Services... exist in *Namespaces*

- So far, we (probably) have been using the `default` Namespace

- We can create other Namespaces to organize our resources

---

## Use-cases

- Example: a "dev" cluster where each developer has their own Namespace

  (and they only have access to their own Namespace, not to other folks' Namespaces)

- Example: a cluster with one `production` and one `staging` Namespace

  (with similar applications running in each of them, but with different sizes)

- Example: a "production" cluster with one Namespace per application

  (or one Namespace per component of a bigger application)

- Example: a "production" cluster with many instances of the same application

  (e.g. SAAS application with one instance per customer)

---

## Pre-existing Namespaces

- On a freshly deployed cluster, we typically have the following four Namespaces:

  - `default` (initial Namespace for our applications; also holds the `kubernetes` Service)

  - `kube-system` (for the control plane)

  - `kube-public` (readable by everyone; kubeadm stores the `cluster-info` ConfigMap there)

  - `kube-node-lease` (contains one Lease object per Node, for node heartbeats)

- Over time, we will almost certainly create more Namespaces!

---

## Creating a Namespace

- Let's see two ways to create a Namespace!

.lab[

- First, with `kubectl create namespace`:
  ```bash
  kubectl create namespace blue
  ```

- Then, with a YAML snippet:
  ```bash
    kubectl apply -f- <<EOF
    apiVersion: v1
    kind: Namespace
    metadata:
      name: green
    EOF
  ```

]

---

## Using namespaces

- We can pass a `-n` or `--namespace` flag to most `kubectl` commands

.lab[

- Create a Deployment in the `blue` Namespace:
  ```bash
  kubectl create deployment purple --image jpetazzo/color --namespace blue
  ```

- Check the Pods that were just created:
  ```bash
  kubectl get pods --all-namespaces
  kubectl get pods --all-namespaces --selector app=purple
  ```

]

---

name: visual-namespace-resource-scope-review
class: pic

<!-- Diagram #12 approved; keep the text slide and diagram slide. -->
![The same Service and Deployment names in separate namespaces, with cluster-scoped resources outside.](images/k8s-namespace-resource-scope-2026.svg)

---

## Switching the active Namespace

- We can change the "active" Namespace

- This is useful if we're going to work in a given Namespace for a while

  - it is easier than passing `--namespace ...` all the time

  - it helps to avoid mistakes
    <br/>
    (e.g.: `kubectl delete -f foo.yaml` whoops wrong Namespace!)

- We're going to see ~~one~~ ~~two~~ three different methods to switch namespaces!

---

## Method 1 (kubens/kns)

- To switch to the `blue` Namespace, run:
  ```bash
  kubens blue
  ```

- `kubens` is sometimes renamed or aliased to `kns`

  (even less keystrokes!)

- `kubens -` switches back to the previous Namespace

- Pros: probably the easiest method out there

- Cons: `kubens` is an extra tool that you need to install

---

## Method 2 (edit kubeconfig)

- Edit `~/.kube/config`

- There should be a `namespace:` field somewhere

  - except if we haven't changed Namespace yet!

  - in that case, change Namespace at least once using another method

- We can just edit that file, and `kubectl` will use the new Namespace from now on

- Pros: kind of easy; doesn't require extra tools

- Cons: there can be multiple `namespace:` fields in that file; difficult to automate

---

## Method 3 (kubectl config)

- To switch to the `blue` Namespace, run:
  ```bash
  kubectl config set-context --current --namespace blue
  ```

- This automatically edits the kubeconfig file

- This is exactly what `kubens` does behind the scenes!

- Pros: always works (as long as we have `kubectl`)

- Cons: long and complicated to type

  (but it's a good exercise for our fingers, maybe?)

---

class: extra-details

## What are contexts?

- Context = cluster + user + namespace

- Useful to quickly switch between multiple clusters

  (e.g. dev, prod, or different applications, different customers...)

- Also useful to quickly switch between identities

  (e.g. developer with "regular" access vs. cluster-admin)

- Switch context with `kubectl config use-context` or `kubectx` / `kctx`

- It is also possible to switch the kubeconfig file altogether

  (by specifying `--kubeconfig` or setting the `KUBECONFIG` environment variable)

---

class: extra-details

## What's in a context

- NAME is an arbitrary string to identify the context

- CLUSTER is a reference to a cluster

  (i.e. API endpoint URL, and optional certificate)

- AUTHINFO is a reference to the authentication information to use

  (i.e. a TLS client certificate, token, or otherwise)

- NAMESPACE is the namespace

  (empty string = `default`)

---

name: visual-context-access-review
class: pic

<!-- Diagram #13 approved; keep the text slide and diagram slide. -->
![A kubeconfig context selects cluster, authentication settings, and default namespace.](images/k8s-context-access-2026.svg)

---

## Namespaces, Services, and DNS

- When a Service is created, a record is added to the Kubernetes DNS

- For instance, for service `auth` in domain `staging`, this is typically:

  `auth.staging.svc.cluster.local`

- By default, Pods are configured to resolve names in their Namespace's domain

- For instance, a Pod in Namespace `staging` will have the following "search list":

  `search staging.svc.cluster.local svc.cluster.local cluster.local`

---

## Pods connecting to Services

- Let's assume that we are in Namespace `staging`

- ... and there is a Service named `auth`

- ... and we have code running in a Pod in that same Namespace

- Our code can:

  - connect to Service `auth` in the same Namespace with `http://auth/`

  - connect to Service `auth` in another Namespace (e.g. `prod`) with `http://auth.prod`

  - ... or `http://auth.prod.svc` or `http://auth.prod.svc.cluster.local`

---

## Deploying multiple instances of a stack

If all the containers in a given stack use DNS for service discovery,
that stack can be deployed identically in multiple Namespaces.

Each copy of the stack will communicate with the services belonging
to the stack's Namespace.

Example: we can deploy multiple copies of DockerCoins, one per
Namespace, without changing a single line of code in DockerCoins,
and even without changing a single line of code in our YAML manifests!

This is similar to what can be achieved e.g. with Docker Compose
(but with Docker Compose, each stack is deployed in a Docker "network"
instead of a Kubernetes Namespace).

---

## Namespaces and isolation

- Namespaces *do not* provide isolation

- By default, Pods in e.g. `prod` and `staging` Namespaces can communicate

- Actual isolation is implemented with *network policies*

- Network policies are resources (like deployments, services, namespaces...)

- Network policies specify which flows are allowed:

  - between pods

  - from pods to the outside world

  - and vice-versa

---

##  `kubens` and `kubectx`

- These tools are available from https://github.com/ahmetb/kubectx

- On our clusters, they are installed as `kubectx` and `kubens`, and also as `kctx` and `kns`

  (shorter names, and Tab completion doesn't clash with `kubectl`)

---

## `kube-ps1`

- It's easy to lose track of our current cluster / context / namespace

- `kube-ps1` makes it easy to track these, by showing them in our shell prompt

- It is installed on our training clusters, and when using [shpod](https://github.com/jpetazzo/shpod)

- It gives us a prompt looking like this one:
  ```
  [123.45.67.89] `(kubernetes-admin@kubernetes:default)` k8s@node1 ~
  ```
  (The highlighted part is `context:namespace`, managed by `kube-ps1`)

- Highly recommended if you work across multiple contexts or namespaces!

- Even better, use Starship 🚀 [starship.rs](https://starship.rs/)

---

class: extra-details

## Installing `kube-ps1`

- It's a simple shell script available from https://github.com/jonmosco/kube-ps1

- It needs to be [installed in our profile/rc files](https://github.com/jonmosco/kube-ps1#installing)

  (instructions differ depending on platform, shell, etc.)

- Once installed, it defines aliases called `kube_ps1`, `kubeon`, `kubeoff`

  (to selectively enable/disable it when needed)

- Pro-tip: install it on your machine during the next break!

???

:EN:- Organizing resources with Namespaces
:FR:- Organiser les ressources avec des *namespaces*
