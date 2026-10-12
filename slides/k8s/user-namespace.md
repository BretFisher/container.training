<!-- verified: 2026-10-09 -->
# User namespaces

- By default, UID 0 (root) in a container is UID 0 on the node

- Capabilities, seccomp, and AppArmor limit what that root user can do

- But if a process escapes the container, it is root on the node

  (container escapes come from kernel and runtime bugs: there are new ones each year)

- A *user namespace* gives the pod its own range of user IDs:

  - UID 0 in the pod = a high, unprivileged UID on the node

  - each pod gets a different range (no other pod uses it)

- One field in the pod spec: `hostUsers: false` (stable since Kubernetes 1.36)

---

## How it works

- The kubelet gives each pod a range of 65536 host UIDs and GIDs

- The container runtime maps the pod's UIDs to that range:

  `0-65535` in the pod → for example `3670278144-3670343679` on the node

- Capabilities are only for the namespace of the pod

  (`CAP_SYS_ADMIN` in the pod does not give admin access to the node)

- Volumes use *idmap mounts* (a Linux kernel feature):

  UID 0 in the pod writes files that belong to UID 0 on the node

- The default is still `hostUsers: true`: we must set it in each pod

---

## Requirements and limits

- Linux 6.3 or later, containerd 2.0+ or CRI-O 1.25+, runc 1.2+ or crun 1.9+

  (our lab nodes: Ubuntu 26.04 with Linux 7.0, containerd 2.4, runc 1.5)

- Each filesystem of the volumes must support idmap mounts

  (NFS does not)

- The pod cannot also use `hostNetwork`, `hostPID`, or `hostIPC`

  (`spec.hostNetwork: Forbidden: when hostUsers is false`)

- Managed clusters: check the node OS and the runtime version first

---

## Lab: two pods, two user namespaces

- From the Kubernetes docs: @@LINK[k8s/userns-demo.yaml]

  (pod `hostusers` with the default, pod `userns` with `hostUsers: false`, both on node2)

.lab[

- Create a namespace and the two pods:
  ```bash
  kubectl create namespace userns
  kubectl apply -n userns -f ~/container.training/k8s/userns-demo.yaml
  ```

<!-- ```hide kubectl wait -n userns pod --all --for condition=Ready --timeout=120s``` -->

- Look at the user ID map of each pod:
  ```bash
  kubectl exec -n userns hostusers -- cat /proc/self/uid_map
  kubectl exec -n userns userns -- cat /proc/self/uid_map
  ```

]

---

## Reading the UID map

- Each line: `UID in the pod`, `UID on the node`, `number of UIDs`

- `hostusers`: `0 0 4294967295`

  (all UIDs, with no change: root in the pod is root on the node)

- `userns`: `0 <a large number> 65536`

  (root in the pod is that large UID on the node)

- In both pods, `id` shows `uid=0(root)`

  (the process cannot see the difference from inside!)

---

## Lab: look from the node

.lab[

<!-- ```hide ssh-keyscan -t ed25519 node2 >> ~/.ssh/known_hosts 2>/dev/null``` -->

- Show the user of the `sleep` process of each pod, on node2:
  ```bash
  ssh node2 ps -o user:12,pid,cmd -C sleep
  ```

]

- One `sleep` process runs as `root`, the other as a large UID

  (the same number as in the UID map of the `userns` pod)

- Note: `ps -o uid` shows a negative number for these UIDs: use `user:12`

---

## Lab: a simulated escape

- What if the `userns` process escapes from its container?

- It has the rights of its UID on the node: let's run a command as that UID

.lab[

- Get the host UID of root in the `userns` pod:
  ```bash
  HOSTUID=$(kubectl exec -n userns userns -- cat /proc/self/uid_map | awk '{print $2}')
  echo $HOSTUID
  ```

- On node2, read `/etc/shadow` as that UID:
  ```bash
  ssh node2 sudo setpriv --reuid=$HOSTUID --regid=$HOSTUID --clear-groups cat /etc/shadow
  ```

<!-- ```expect-fail``` -->

]

- Permission denied: no files on the node belong to that UID

- An escape from the `hostusers` pod is UID 0: it can read the file

---

## Lab: what about `hostPath`?

- @@LINK[k8s/userns-hostpath.yaml]: like `hacktheplanet`, two pods mount `/root` of node2

.lab[

- Create the two pods:
  ```bash
  kubectl apply -n userns -f ~/container.training/k8s/userns-hostpath.yaml
  ```

<!-- ```hide kubectl wait -n userns pod --all --for condition=Ready --timeout=120s``` -->

- Write a file in `/root` of the node from each pod:
  ```bash
  kubectl exec -n userns hostroot-hostusers -- touch /host-root/hostusers-was-here
  kubectl exec -n userns hostroot-userns -- touch /host-root/userns-was-here
  ```

- Look at the owners of the files on node2:
  ```bash
  ssh node2 sudo ls -ln /root
  ```

]

---

## Why did it work?

- The kubelet mounts the volumes of the `userns` pod with an idmap mount

- In that volume, UID 0 in the pod = UID 0 on the node

  (so the app can use its files, but root in the pod writes root files on the node!)

- User namespaces protect the node from a process that *escapes*

- They do not protect the node from a `hostPath` volume

- Block `hostPath` with Pod Security (`baseline`): each layer stops different attacks

---

## User namespaces and Pod Security

- Since Kubernetes 1.35, the `restricted` policy accepts root in a pod

  when the pod has `hostUsers: false`

- `runAsNonRoot` and `runAsUser` are not checked for these pods

  (root in the pod is not root on the node)

- Good for images that must run as root

- The other `restricted` checks still apply

  (drop `ALL` capabilities, `allowPrivilegeEscalation: false`, seccomp...)

---

## Lab: root in a `restricted` namespace

- @@LINK[k8s/userns-restricted.yaml]: two root pods; only one has `hostUsers: false`

.lab[

- Create a `restricted` namespace, and try to create the two pods in it:
  ```bash
  kubectl create namespace userns-restricted
  kubectl label namespace userns-restricted pod-security.kubernetes.io/enforce=restricted
  kubectl apply -n userns-restricted -f ~/container.training/k8s/userns-restricted.yaml
  ```

<!-- ```expect-fail``` -->

]

- `root-userns` is created

- `root-hostusers` is rejected: `runAsNonRoot != true`

---

## Lab: cleaning up

.lab[

- Delete the namespaces:
  ```bash
  kubectl delete namespace userns userns-restricted
  ```

<!-- ```hide ssh node2 sudo rm -f /root/hostusers-was-here /root/userns-was-here``` -->

]

- Our lab file from the previous chapter already sets `hostUsers: false`

- Add it to your pod templates, and test each app

  (some apps need changes, for example a volume on NFS)

???

:EN:- Isolating pods with user namespaces
:FR:- Isoler les pods avec les espaces de noms utilisateur
