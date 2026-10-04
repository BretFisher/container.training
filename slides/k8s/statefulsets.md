# StatefulSets

- StatefulSets are a type of resource in the Kubernetes API

  (like pods, deployments, services...)

- They offer mechanisms to deploy scaled stateful applications

- At a first glance, they look like Deployments:

  - a StatefulSet defines a pod spec and a number of replicas *R*

  - it will make sure that *R* copies of the pod are running

  - that number can be changed while the StatefulSet is running

  - updating the pod spec will cause a rolling update to happen

- But they also have some significant differences

---

## StatefulSets unique features

- Pods in a StatefulSet are numbered (from 0 to *R-1*) and ordered

- They are started and updated in order (from 0 to *R-1*)

- A pod is started (or updated) only when the previous one is ready

- They are stopped in reverse order (from *R-1* to 0)

- Each pod knows its identity (i.e. which number it is in the set)

- Each pod can discover the IP address of the others easily

- The pods can persist data on attached volumes

🤔 Wait a minute ... Can't we already attach volumes to pods and deployments?

---

## Revisiting volumes

- [Volumes](https://kubernetes.io/docs/concepts/storage/volumes/) are used for many purposes:

  - sharing data between containers in a pod

  - exposing configuration information and secrets to containers

  - accessing storage systems

- Let's see examples of the latter usage

---

## Volumes types

- There are many [types of volumes](https://kubernetes.io/docs/concepts/storage/volumes/#types-of-volumes) available:

  - built-in types (emptyDir, hostPath, configMap, secret, nfs, iscsi...)

  - CSI drivers for everything else (cloud disks like AWS EBS; Ceph; Portworx...)

- Using a volume directly in a Pod requires:

  - creating the storage out-of-band (outside of the Kubernetes API)

  - referencing it in the pod description, with all its parameters

---

## Using an NFS volume

Here is another example using a volume on an NFS server:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-using-my-nfs-volume
spec:
  containers:
  - image: ...
    name: container-using-my-nfs-volume
    volumeMounts:
    - mountPath: /my-nfs
      name: my-nfs-volume
  volumes:
  - name: my-nfs-volume
    nfs:
      server: 192.168.0.55
      path: "/exports/assets"
```

---

## Shortcomings of volumes

- Their lifecycle (creation, deletion...) is managed outside of the Kubernetes API

  (we can't just use `kubectl apply/create/delete/...` to manage them)

- If a Deployment uses a volume, all replicas end up using the same volume

- That volume must then support concurrent access

  - some volumes do (e.g. NFS servers support multiple read/write access)

  - some volumes support concurrent reads

  - some volumes support concurrent access for colocated pods

- What we really need is a way for each replica to have its own volume

---

## Individual volumes

- The Pods of a StatefulSet can have individual volumes

  (i.e. in a StatefulSet with 3 replicas, there will be 3 volumes)

- These volumes can be either:

  - allocated from a pool of pre-existing volumes (disks, partitions ...)

  - created dynamically using a storage system

- This introduces a bunch of new Kubernetes resource types:

  Persistent Volumes, Persistent Volume Claims, Storage Classes

  (and also `volumeClaimTemplates`, that appear within StatefulSet manifests!)

---

## StatefulSet recap

- A StatefulSet manages a number of identical pods

  (like a Deployment)

- These pods are numbered, and started/upgraded/stopped in a specific order

- These pods are aware of their number

  (e.g., #0 can decide to be the primary, and #1 can be secondary)

- These pods can find the IP addresses of the other pods in the set

  (through a *headless service*)

- These pods can each have their own persistent storage

---

## When do we need a StatefulSet?

- When the pods are *not* interchangeable

- Databases (one primary, some replicas)

- Clustered apps with a quorum (etcd, Consul, ZooKeeper, Kafka...)

- Apps where each pod needs a stable network name

  (e.g. `db-0.db`, `db-1.db`, through a headless service)

- Apps where each pod needs its own disk, which stays with that pod

  (even when the pod is restarted or moved to another node)

---

## StatefulSet or Deployment?

- StatefulSet advantages:

  - stable pod names and DNS names

  - ordered start, stop, and rolling update

  - one Persistent Volume Claim per pod, kept across restarts and moves

- Deployment advantages:

  - any pod can replace any other pod

  - faster scaling and rollouts (no ordering)

- Stateless app → Deployment; stateful app → StatefulSet

- On a managed cloud, also compare with a managed database service (e.g. RDS)

---

## Obtaining per-pod storage

- StatefulSets can have *persistent volume claim templates*

  (declared in `spec.volumeClaimTemplates` in the StatefulSet manifest)

- A claim template will create one Persistent Volume Claim per pod

  (the PVC will be named `<claim-name>-<statefulset-name>-<pod-index>`)

- Persistent Volume Claims are matched 1-to-1 with Persistent Volumes

- Persistent Volume provisioning can be done:

  - automatically (by leveraging *dynamic provisioning* with a Storage Class)

  - manually (human operator creates the volumes ahead of time, or when needed)

???

:EN:- Deploying apps with StatefulSets
:EN:- Understanding Persistent Volume Claims and Storage Classes
:FR:- Déployer une application avec un *StatefulSet*
:FR:- Comprendre les *Persistent Volume Claims* et *Storage Classes*

