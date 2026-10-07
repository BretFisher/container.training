<!-- verified: 2026-10-07 -->
# Sandboxed containers

- All containers on a node share one thing: the **Linux kernel of the node**

- A kernel bug can let a container escape to the node

  (examples: Dirty Pipe, CVE-2022-0847; Dirty COW, CVE-2016-5195)

- Most of the time, we trust the code that runs in our containers

- Sometimes we do not:

  - CI jobs, plugins, and code from customers

  - code that an AI agent writes and runs

- A *sandbox runtime* puts a second boundary between the container and the kernel

---

## Layers of protection

From "shares the most with the node" to "shares the least":

1. **securityContext + Pod Security Admission**: no privileged pods, no hostPath

2. **seccomp and AppArmor**: block the system calls and files that the app does not need

3. **User namespaces** (`hostUsers: false`, stable since Kubernetes 1.36):

   root in the container is not root on the node

4. **Sandbox runtime**: the app does not talk to the kernel of the node

- Layers 1 to 3 still share the kernel of the node

- Layer 4 replaces it with a user-space kernel or a virtual machine

---

## Three projects

- **gVisor** (Google): a kernel written in Go that runs in user space

  - the app sends its system calls to gVisor, not to the kernel of the node

- **Kata Containers** (OpenInfra Foundation): one lightweight VM for each pod

  - the pod gets its own Linux kernel; a hypervisor isolates it

- **Firecracker** (AWS): a small virtual machine monitor (VMM) for microVMs

  - runs AWS Lambda and Fargate

  - it is *not* a container runtime; Kubernetes uses it through Kata

---

## gVisor

- The **Sentry** catches each system call of the app and runs it

- The Sentry uses only a small, filtered set of host system calls (seccomp)

- The **Gofer** gives file access; gVisor also has its own network stack

- The "systrap" platform needs no hardware virtualization

  (it runs on any VM, including our `t3` lab nodes)

- Fast start (less than 1 second), low memory overhead

- Limits: not every system call or `/proc` file exists; more cost per system call

  (I/O-heavy apps are slower; most apps do not see a difference)

---

## Kata Containers and Firecracker

- Kata starts a small VM for each pod, with a real Linux kernel inside

  - full Linux compatibility, including privileged containers in the VM

  - hypervisors: QEMU, Cloud Hypervisor, Dragonball, or Firecracker (`kata-fc`)

- Kata and Firecracker need `/dev/kvm`:

  - bare metal instances, or

  - *nested virtualization* (on AWS since February 2026: C8i, M8i, R8i, ...)

- Our `t3` nodes do not have `/dev/kvm`, so our lab uses gVisor

- Firecracker snapshots (save and restore a running VM) are not available through Kata

  (platforms that need snapshots run Firecracker directly, outside Kubernetes)

---

## Comparison

.small[
| | gVisor | Kata Containers | Firecracker |
|-|-|-|-|
| Boundary | User-space kernel | VM per pod | microVM (it is the VMM) |
| Needs `/dev/kvm` | No | Yes | Yes |
| Start time | < 1 s | 1 to 5 s | < 1 s for the VM only |
| Compatibility | Most apps | Full Linux | Full Linux |
| Overhead | Per system call | Fixed memory per pod | Fixed memory per VM |
| In Kubernetes | RuntimeClass `runsc` | RuntimeClass `kata-*` | Through Kata (`kata-fc`) |
| Managed | GKE Sandbox | GKE (microVM), AKS | AWS Lambda, Fargate |
]

- Start times come from GKE and AWS documents; your numbers will be different

- EKS has no managed gVisor or Kata: you install them on your nodes

---

## RuntimeClass

- The node runs containerd; containerd can have more than one *runtime handler*

- A RuntimeClass gives a Kubernetes name to a handler

- A pod selects it with `runtimeClassName`

```yaml
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: gvisor
handler: runsc            # handler name in the containerd config
scheduling:
  nodeSelector:           # send these pods only to nodes with gVisor
    sandbox/gvisor: "true"
```

- `overhead.podFixed` adds CPU and memory for the sandbox to the pod

  (Kata uses it; the VM needs memory)

---

## Lab: installing gVisor on node2

.lab[

<!-- ```hide ssh-keyscan -t ed25519 node2 >> ~/.ssh/known_hosts 2>/dev/null``` -->

- Connect to node2 (if `ssh` asks about the host key, type `yes`):
  ```bash
  ssh node2
  ```

- Install the `runsc` package from the gVisor repository:
  ```bash
    curl -fsSL https://gvisor.dev/archive.key |
      sudo gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] \
      https://storage.googleapis.com/gvisor/releases release main" |
      sudo tee /etc/apt/sources.list.d/gvisor.list
    sudo apt-get update -q && sudo apt-get install -qy runsc
    runsc --version
  ```

]

- We install gVisor on node2 only

---

## Lab: adding the runsc handler to containerd

.lab[

- Add the handler to the containerd configuration, then restart containerd:
  ```bash
    sudo tee -a /etc/containerd/config.toml <<EOF
    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runsc]
    runtime_type = "io.containerd.runsc.v1"
    EOF
    sudo systemctl restart containerd
  ```

- Go back to node1:
  ```bash
  exit
  ```

- Add a label to node2, so that the scheduler knows where gVisor is:
  ```bash
  kubectl label node node2 sandbox/gvisor=true
  ```

]

---

## Lab: two pods, two runtimes

- @@LINK[k8s/gvisor-demo.yaml] has:

  - the `gvisor` RuntimeClass

  - a pod `normal` (runc, the default) on node2

  - a pod `sandboxed` (`runtimeClassName: gvisor`) on node2

.lab[

- Create a namespace, then apply the file:
  ```bash
  kubectl create namespace sandbox
  kns sandbox
  kubectl apply -f ~/container.training/k8s/gvisor-demo.yaml
  ```

<!-- ```hide kubectl wait pod normal sandboxed --for=condition=Ready --timeout=120s``` -->

- Check that the two pods run on node2:
  ```bash
  kubectl get pods -o wide
  ```

]

---

## Lab: which kernel?

.lab[

- Show the kernel version in each pod:
  ```bash
  kubectl exec normal -- uname -r
  kubectl exec sandboxed -- uname -r
  ```

- Read the kernel log in the normal pod:
  ```bash
  kubectl exec normal -- dmesg
  ```

<!-- ```expect-fail``` -->

- Read the kernel log in the sandboxed pod:
  ```bash
  kubectl exec sandboxed -- dmesg
  ```

]

- `normal` shows the kernel of node2, and it cannot read the kernel log

- `sandboxed` shows the kernel version of gVisor, and the boot log of gVisor

---

## Lab: what does the node see?

- A container with runc is a normal process on the node

- A container with gVisor runs inside the gVisor processes

.lab[

- Look for the `sleep` processes of our pods on node2:
  ```bash
  ssh node2 pgrep -a sleep
  ```

- Look for the gVisor kernel (the Sentry) on node2:
  ```bash
  ssh node2 pgrep -af runsc-sandbox | cut -c1-60
  ```

]

- We see only one `sleep infinity`: it is the process of `normal`

- The `sleep` of `sandboxed` runs inside `runsc-sandbox`, not on node2

---

## Lab: an attack with a privileged pod

- An attacker can create a privileged pod (a policy failed, or a role is too large)

- @@LINK[k8s/gvisor-escape.yaml] has two privileged pods on node2:

  `escape-runc` and `escape-gvisor`

.lab[

- Create the pods:
  ```bash
  kubectl apply -f ~/container.training/k8s/gvisor-escape.yaml
  ```

<!-- ```hide kubectl wait pod escape-runc escape-gvisor --for=condition=Ready --timeout=120s``` -->

- Look for the disk of node2 in each pod:
  ```bash
  kubectl exec escape-runc -- ls -l /dev/nvme0n1p1
  kubectl exec escape-gvisor -- ls -l /dev/nvme0n1p1
  ```

]

- `kubectl apply` shows a PodSecurity warning, but it does not block the pods

---

## Lab: taking over the node (or not)

.lab[

- In the runc pod, mount the disk of node2, then read its kubelet credentials:
  ```bash
  kubectl exec escape-runc -- mount /dev/nvme0n1p1 /mnt
  kubectl exec escape-runc -- ls /mnt/var/lib/kubelet/pki
  ```

- Try the same thing in the gVisor pod:
  ```bash
  kubectl exec escape-gvisor -- mount /dev/nvme0n1p1 /mnt
  ```

<!-- ```expect-fail``` -->

]

- With runc, "privileged" gives the pod the devices of the node: we own node2

- With gVisor, the pod is "privileged" only inside the sandbox

  (the gVisor kernel shows the device file, but it cannot read the disk)

---

## What gVisor does not protect

- gVisor protects the kernel of the node; it does not fix a bad pod spec

- A `hostPath` volume still gives files of the node to the pod

  (gVisor would not stop the `hacktheplanet` DaemonSet!)

- The ServiceAccount token in the pod still works with the API server

- The pod still has network access, unless a NetworkPolicy blocks it

- So we still need:

  - Pod Security Admission or Kyverno (for example, no `hostPath`)

  - RBAC with least privilege

  - NetworkPolicies

---

## Requiring a sandbox

- Pod Security Admission does not check `runtimeClassName`

- To require gVisor in a namespace, use a policy engine:

  - a Kyverno rule that adds or requires `runtimeClassName: gvisor`

  - or a ValidatingAdmissionPolicy

- Use the RuntimeClass `nodeSelector` and node taints

  to keep sandbox pods and normal pods on different nodes

---

## Agent Sandbox

- [Agent Sandbox](https://github.com/kubernetes-sigs/agent-sandbox): a Kubernetes SIG Apps project (v1.0 in 2026)

- It is made for AI agents: one long-running, stateful sandbox for each session

- Custom resources:

  - `Sandbox`: one isolated pod with a stable name and storage

  - `SandboxTemplate`: the pod spec that we use again

  - `SandboxWarmPool`: sandboxes that are started before we need them

  - `SandboxClaim`: takes a sandbox from the pool (start in less than 1 second)

- It does not isolate by itself: it uses a RuntimeClass (gVisor or Kata)

---

## Choosing a sandbox

- Code that you wrote and trust: runc + Pod Security + user namespaces

- Untrusted code, any node type: **gVisor**

- Untrusted code that needs full Linux (or privileged inside the sandbox): **Kata**

  (needs bare metal or nested virtualization)

- Your own platform for functions or agents, with snapshots: **Firecracker** directly

- Many AI agent sessions on Kubernetes: **Agent Sandbox** + gVisor or Kata

- Test your app in the sandbox first: some system calls and `/proc` files are missing

---

## Lab: cleaning up

.lab[

- Delete the namespace and the RuntimeClass:
  ```bash
  kns default
  kubectl delete namespace sandbox
  kubectl delete runtimeclass gvisor
  ```

]

- gVisor stays installed on node2

  (without the RuntimeClass, Kubernetes does not use it)

???

:EN:- Sandboxed containers: gVisor, Kata Containers, Firecracker
:FR:- Conteneurs isolés : gVisor, Kata Containers, Firecracker
