<!-- verified: 2026-10-05 -->
# Kubernetes concepts

- Kubernetes is a container management system

- It runs and manages containerized applications on a cluster

--

- What does that really mean?

---

## What can we do with Kubernetes?

- Let's imagine that we have a 3-tier e-commerce app:

  - web frontend

  - API backend

  - database

- We have built images for our frontend and backend components

  (e.g. with Dockerfiles and `docker build`)

- We are running them successfully with a local environment

  (e.g. with Docker Compose)

- Let's see how we would deploy our app on Kubernetes!

---


## Kubernetes, level 1

--

- Leave our database outside of Kubernetes (because database be scary🥺)

--

- Deploy a managed Kubernetes cluster (experts managing the cluster for you)

--

- Start 5 containers using image `yourorg/api:v1.3`

--

- Place an internal load balancer in front of these containers

--

- Start 10 containers using image `yourorg/webfront:v1.3`

--

- Place a public load balancer in front of these containers

--

- It's Black Friday (or Christmas), traffic spikes, grow our cluster and add containers

--

- New release! Replace my containers with the new image `yourorg/webfront:v1.4`

--

- Keep processing requests during the upgrade; update my containers one at a time

---

## Kubernetes, level 2

- Deploy a pre-production environment

  (still using our external database, for now)

- Resource management and scheduling

  (reserve CPU/RAM for containers; placement constraints; priorities)

- Autoscaling

  (straightforward on CPU; more complex on other metrics)

- Advanced rollout patterns

  (blue/green deployment, canary deployment)

---

## Kubernetes, level 3

- Run staging databases on the cluster

  (no replication, no backups, no scaling)

- Automatic or semi-automatic deployment of feature branches

  (each with its own database)

- Fine-grained access control

  (defining *what* can be done by *whom* on *which* resources)

- Batch jobs

  (one-off; parallel; also cron-style periodic execution)

- Package applications with e.g. Helm charts

---

## Kubernetes, level 4

- Stateful services with persistence, replication, backups

  (databases, message queues, etc.)

- Automate complex tasks with *operators*

  (e.g. database replication, failover, etc.)

- Combine the two previous points with database operators like [CloudNativePG][cnpg]

  (learn more about database operators: [FR][pirates-video-fr], [EN][pirates-video-en])

- Leverage advanced storage with e.g. local ZFS volumes

  (learn more about ZFS and databases on k8s: [FR][zfs-video-fr], [EN][zfs-video-en])

- Deploy and manage clusters in-house

[cnpg]: https://cloudnative-pg.io/
[pirates-video-fr]: https://www.youtube.com/watch?v=d_ka7PlWo1I
[pirates-video-en]: https://www.youtube.com/watch?v=ojUdBjbiKWk&t=5s
[zfs-video-fr]: https://www.youtube.com/watch?v=XN9YL93f8tI
[zfs-video-en]: https://www.youtube.com/watch?v=3sJIYiDnod4

---

## Kubernetes, level 5

- Deploying and managing clusters at scale

  (hundreds of clusters, thousands of nodes...)

- Writing custom operators

- Hybrid deployments

---

## Disclaimer

The levels mentioned in the previous slides are not necessarily linear.

They aren't exhaustive either (we didn't mention e.g. observability and alerting).

---

## Kubernetes architecture

---

class: pic

![haha only kidding](images/k8s-arch1.png)

---

## Kubernetes architecture

- Ha ha ha ha

- OK, I was trying to scare you, it's much simpler than that ❤️

---

class: pic

![Kubernetes control plane and worker nodes connected by a physical network](images/k8s-arch2-2026.svg)

---

class: bret-skip

## Credits

- The first schema is a Kubernetes cluster with storage backed by multi-path iSCSI

  (Courtesy of [Yongbok Kim](https://www.yongbok.net/blog/))


---

## Kubernetes architecture: the nodes

- The nodes executing our containers run a collection of services:

  - a container runtime (typically `containerd`, same thing Docker runs underneath)

  - `kubelet` (the "node agent")

  - `kube-proxy` (a necessary but not sufficient network component)

---

## Kubernetes architecture: the control plane

- The Kubernetes logic (its "brains") is a collection of services:

  - the `kube-apiserver` (our point of entry to everything!)

  - core services like the `kube-scheduler` and `kube-controller-manager`

  - `etcd` (a highly available key/value store; the "database" of Kubernetes)

- Together, these services form the control plane of our cluster

---

class: pic

![Kubernetes architecture with control-plane components, worker nodes, and interfaces](images/k8s-arch4-2026.svg)

---

class: extra-details

## Running the control plane on special nodes

- It is common to reserve a dedicated node(s) for the control plane

  (Except for single-node development clusters, like when using minikube or k3s)

- This node is then called a control plane node

- Normal applications are restricted from running on this node

  (By using a mechanism called ["taints"](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/))

- When high availability is required, each service of the control plane must be resilient

- The control plane is then replicated on multiple nodes

---

class: extra-details

## Running the control plane outside containers

- The services of the control plane can run in or out of containers

- For instance: since `etcd` is a critical service, some people
  deploy it directly on a dedicated cluster (without containers)

  (This is illustrated on the first "super complicated" schema)

- In some hosted Kubernetes offerings (e.g. AKS, GKE, EKS), the control plane is invisible

  (We only "see" a Kubernetes API endpoint)

---

class: pic
![](images/control-planes/single-node-dev.svg)

---

class: pic
![](images/control-planes/managed-kubernetes.svg)

---

class: pic
![](images/control-planes/single-control-and-workers.svg)

---

class: pic
![](images/control-planes/stacked-control-plane.svg)

---

class: pic
![](images/control-planes/non-dedicated-stacked-nodes.svg)

---

class: pic
![](images/control-planes/advanced-control-plane.svg)

---

class: pic
![](images/control-planes/advanced-control-plane-split-events.svg)

---

class: extra-details

## How many nodes should a cluster have?

- There is no particular constraint

  (no need to have an odd number of nodes for quorum)

- A cluster can have zero node

  (but then it won't be able to start any pods)

- For testing and development, having a single node is fine

- For production, make sure that you have extra capacity

  (so that your workload still fits if you lose a node or a group of nodes)

- Kubernetes is tested with [up to 5000 nodes](https://kubernetes.io/docs/setup/best-practices/cluster-large/)

  (however, running a cluster of that size requires a lot of tuning)

---

class: extra-details

## Do we need to run Docker at all?

No!

--

- The Docker Engine used to be the default option to run containers with Kubernetes

- Then the CRI standard (Container Runtime Interface) was introduced

- Built-in support for Docker (`dockershim`) was removed in 2022 with K8s 1.24

  - But it lives on as a supported CRI via `cri-dockerd`

  - "Kubernetes dropped Docker support" was a common misconception

- We can leverage other pluggable runtimes through the *Container Runtime Interface*

---

class: extra-details

## Some runtimes available through CRI

- [containerd](https://github.com/containerd/containerd/blob/main/README.md)

  - CNCF graduated project, maintained by many vendors and community
  - used by Docker Engine, microk8s, k3s, EKS, AKS, GKE; also standalone
  - comes with its own CLI, `ctr`

- [CRI-O](https://github.com/cri-o/cri-o/blob/main/README.md):

  - CNCF graduated project, maintained by Red Hat, SUSE, and community
  - used by OpenShift and Oracle Cloud Native Environment
  - designed specifically as a minimal runtime for Kubernetes

- [And more](https://kubernetes.io/docs/setup/production-environment/container-runtimes/)

---

class: extra-details

## Do we need to run Docker at all?

Yes!

--

- Kubernetes, by default, can't build or push images

- We will need to build images and ship them around

- We can do these things without Docker
  <br/>
  (but with some languages/frameworks, it might be much harder)

- Docker is still the most popular local and single-node container engine

---

class: extra-details

## Do we need to run Docker at all?

- On our Kubernetes clusters:

  *Not anymore*

- On our development environments, CI pipelines ... :

  *Yes, almost certainly*

---

## Interacting with Kubernetes

- We will interact with our Kubernetes cluster through the Kubernetes API

- The Kubernetes API is (mostly) RESTful

- It allows us to create, read, update, delete *resources*

- A few common resource types are:

  - node (a machine — physical or virtual — in our cluster)

  - pod (group of containers running together on a node)

  - service (stable network endpoint to connect to one or multiple containers)

---

class: pic

![Two containers in a Pod with shared resources](images/k8s-arch3-2026.svg)

---

## Scaling

- How would we scale the pod shown on the previous slide?

- **Do** create additional pods

  - each pod can be on a different node

  - each pod will have its own IP address

- **Do not** add more NGINX containers in the pod

  - all the NGINX containers would be on the same node

  - they would all have the same IP address
    <br/>(resulting in `Address already in use` errors)

---

## Together or separate

- Should we put e.g. a web application server and a cache together?
  <br/>
  ("cache" being something like e.g. Memcached or Redis)

- Putting them **in the same pod** means:

  - they have to be scaled together

  - they can communicate very efficiently over `localhost`

- Putting them **in different pods** means:

  - they can be scaled separately

  - they must communicate over remote IP addresses
    <br/>(incurring more latency, lower performance)

- Both scenarios can make sense, depending on our goals
