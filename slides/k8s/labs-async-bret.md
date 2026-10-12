name: labs-async-bret
toc: Running the labs on your own

## Running the labs on your own

- In class, each student gets a 3-node Kubernetes cluster in the cloud

- After class, you need your own cluster. Pick one of these 3 options:

  1. **Killercoda**: a free cluster in your browser (nothing to install)

  2. **Docker Desktop**: a local cluster, enabled with one click

  3. **kind** or **k3d**: a local cluster that you create from the command line

- For all of them, you also need `kubectl`

  (Docker Desktop installs it for you)

- The Kubernetes docs list more learning options:
  <br/>https://kubernetes.io/docs/setup/learning-environment/

---

## Option 1: Killercoda (in your browser)

- Free Kubernetes playground: https://killercoda.com/playgrounds/scenario/kubernetes

- You get a **two-node** kubeadm cluster with a terminal in your browser

- Steps:

  1. Open the link above and sign in

  2. Start the **Kubernetes** playground (two nodes)

  3. Type `kubectl get nodes` in the terminal

- Limits of the free plan:

  - each session stops after **1 hour**, then the cluster is deleted

  - you must clone this repository again in each new session

- Good for short practice sessions and for labs that run commands on a node

---

## Option 2: Docker Desktop

- Docker Desktop for macOS, Windows, and Linux can run Kubernetes for you

- Free for personal use, education, and small businesses
  <br/>(see https://www.docker.com/pricing/)

- It has two ways to create the cluster:

  - **kubeadm**: one node; Docker Desktop selects the Kubernetes version

  - **kind**: one or more nodes; you select the Kubernetes version
    <br/>(faster to start; use this one)

- It installs `kubectl` and adds the context `docker-desktop`

- Good if you already use Docker Desktop and do not want more tools

---

## Docker Desktop: setup

1. Install Docker Desktop: https://docs.docker.com/desktop/

2. Open the Docker Desktop Dashboard, then select **Kubernetes**

3. Select **Create cluster**

4. Select **kind**, then set the number of nodes to **3**

5. Select **Create**, then wait until the status is "running"

6. In a terminal:
   ```bash
   kubectl config use-context docker-desktop
   kubectl get nodes
   ```

- To start again from a clean cluster: **Reset cluster**

---

## Option 3: kind or k3d

- Both tools run each Kubernetes node as a container

- **They need a container engine:**

  - kind: Docker, Podman, or nerdctl

  - k3d: Docker

  - on macOS and Windows, Docker Desktop is the easy way to get Docker

- **kind** runs upstream Kubernetes (kubeadm), like our class cluster

- **k3d** runs k3s, a smaller distribution with extra parts built in
  <br/>(Traefik, a `LoadBalancer` implementation, metrics-server)

- Both can create clusters with many nodes, and many clusters side by side

- If you are not sure, use **kind**

---

## Install `kubectl` (for kind and k3d)

- macOS:
  ```bash
  brew install kubectl
  ```

- Windows (PowerShell):
  ```bash
  winget install Kubernetes.kubectl
  ```

- Linux: follow https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/

- Check it:
  ```bash
  kubectl version --client
  ```

---

## kind: install

- macOS:
  ```bash
  brew install kind
  ```

- Windows (PowerShell):
  ```bash
  winget install Kubernetes.kind
  ```

- Linux (x86_64; for ARM64, change `amd64` to `arm64`):
  ```bash
  curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.33.0/kind-linux-amd64
  chmod +x ./kind && sudo mv ./kind /usr/local/bin/kind
  ```

- Docs: https://kind.sigs.k8s.io/docs/user/quick-start/

---

## kind: create a 3-node cluster

- Save this as `kind-3nodes.yaml`:
  ```yaml
  kind: Cluster
  apiVersion: kind.x-k8s.io/v1alpha4
  nodes:
  - role: control-plane
  - role: worker
  - role: worker
  ```

- Create the cluster, then check it:
  ```bash
  kind create cluster --config kind-3nodes.yaml
  kubectl get nodes
  ```

- Nodes: `kind-control-plane`, `kind-worker`, `kind-worker2`

- Delete it: `kind delete cluster`

---

## k3d: install

- macOS:
  ```bash
  brew install k3d
  ```

- Windows (PowerShell):
  ```bash
  choco install k3d
  ```

- Linux:
  ```bash
  curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash
  ```

- Docs: https://k3d.io/

---

## k3d: create a 3-node cluster

- Create one server and two agents, with the same Kubernetes version as class:
  ```bash
  k3d cluster create labs --agents 2 --image rancher/k3s:v1.37.1-k3s1
  kubectl get nodes
  ```

- Nodes: `k3d-labs-server-0`, `k3d-labs-agent-0`, `k3d-labs-agent-1`

- k3d already installs metrics-server
  <br/>(skip the metrics-server install in the slides)

- Delete it: `k3d cluster delete labs`

---

## Differences from the class cluster

- There is no `node1` to SSH into: run the lab commands in your own terminal

- Get the lab files on your computer:
  ```bash
  git clone -b @@GITBRANCH@@ https://@@GITREPO@@
  ```

- To run a command on a node of a local cluster, use `docker exec`:
  ```bash
  docker exec -it kind-worker bash
  ```

- `NodePort` Services are not reachable from your computer:
  <br/>use `kubectl port-forward` instead

- The AWS EKS chapter needs an AWS account: watch it, or skip it
