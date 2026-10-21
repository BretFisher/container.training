# Sandbox runtimes: gVisor, Kata Containers, and Firecracker

Research date: 2026-10-07. Target: the workshop's kubeadm clusters.
Status: documented facts checked against primary sources; all lab commands and the lab design are untested.

## 1. Summary

**gVisor.** gVisor is an application kernel. It runs in user space and implements a Linux-like interface. Its Sentry component intercepts the system calls of the application and acts as the guest kernel. The Sentry does not pass application system calls through to the host kernel. A separate Gofer process mediates file system access. [gVisor docs](https://gvisor.dev/docs/). The isolation boundary is a user-space kernel, not a virtual machine.
When to use: untrusted code on nodes without hardware virtualization, or where you need fast start and low fixed overhead.

**Kata Containers.** Kata runs each pod in a lightweight virtual machine with its own guest kernel. It plugs into containerd as a shim and uses a hypervisor. [Kata hypervisors](https://github.com/kata-containers/kata-containers/blob/main/docs/hypervisors.md). The isolation boundary is hardware virtualization.
When to use: untrusted code that needs full Linux kernel compatibility, privileged containers inside a sandbox, or confidential computing (QEMU with TDX/SEV-SNP).

**Firecracker.** Firecracker is a virtual machine monitor (VMM). It uses KVM to create and run microVMs, and it has a minimal device model. [Firecracker README](https://github.com/firecracker-microvm/firecracker/blob/main/README.md). It is not a Kubernetes runtime by itself. Kubernetes reaches it through Kata Containers.
When to use: you build a multi-tenant platform (functions, sandboxes) and you control bare metal or KVM-capable hosts.

## 2. Comparison table

| Topic | gVisor | Kata Containers | Firecracker |
|-|-|-|-|
| Isolation boundary | User-space application kernel (Sentry) [docs](https://gvisor.dev/docs/) | VM per pod, own guest kernel [AKS](https://learn.microsoft.com/en-us/azure/aks/use-pod-sandboxing) | microVM; it is the VMM only [README](https://github.com/firecracker-microvm/firecracker/blob/main/README.md) |
| Host kernel exposure | Sentry runs in a restricted seccomp sandbox and makes its own limited host calls [docs](https://gvisor.dev/docs/) | KVM interface plus the VMM process on the host | KVM interface plus a VMM with thread-specific seccomp filters; production use goes through the `jailer` [README](https://github.com/firecracker-microvm/firecracker/blob/main/README.md) |
| containerd shim | `containerd-shim-runsc-v1`, `runtime_type = "io.containerd.runsc.v1"` [containerd quick start](https://gvisor.dev/docs/user_guide/containerd/quick_start/) | `containerd-shim-kata-v2` (Untested/inferred: name from Kata packaging, not re-checked on a lab) | No CRI shim of its own. Used through Kata (`fc` shim) or `firecracker-containerd` |
| RuntimeClass handler | `runsc` (handler you configure in containerd) | `kata-<shim>`, for example `kata-qemu-runtime-rs` [kata-deploy template](https://github.com/kata-containers/kata-containers/blob/main/tools/packaging/kata-deploy/helm-chart/kata-deploy/templates/runtimeclasses.yaml) | `kata-fc` via kata-deploy (Untested/inferred from the shim name `fc`) |
| Hardware needs | systrap platform: no KVM. KVM platform: optional [platforms](https://gvisor.dev/docs/architecture_guide/platforms/) | Bare metal or nested virtualization [Kata install](https://github.com/kata-containers/kata-containers/blob/main/docs/install/README.md) | Read/write access to `/dev/kvm` [getting started](https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md) |
| Start and overhead | GKE: start < 200 ms, dynamic overhead with low base memory [GKE Sandbox](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/sandbox-pods) | GKE microVM (Kata + Cloud Hypervisor): about 1-2 s start, fixed 250 mCPU / 130 MiB per pod [GKE Sandbox](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/sandbox-pods). kata-deploy default overhead: QEMU 320Mi, CLH/FC/Dragonball 130Mi, 250m CPU [template](https://github.com/kata-containers/kata-containers/blob/main/tools/packaging/kata-deploy/helm-chart/kata-deploy/templates/runtimeclasses.yaml) | VMM memory overhead <= 5 MiB and <= 125 ms to guest `/sbin/init`, measured on `.metal` with a minimal kernel and rootfs [SPECIFICATION](https://github.com/firecracker-microvm/firecracker/blob/main/SPECIFICATION.md) |
| Syscall / app compatibility | Not every syscall, `/proc` or `/sys` file is implemented; higher per-syscall overhead [docs](https://gvisor.dev/docs/) | Full Linux guest kernel [GKE Sandbox](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/sandbox-pods) | Full Linux guest kernel (Firecracker-tuned) |
| Networking | Own user-space stack (netstack); `--network=host` is faster but decreases isolation [networking](https://gvisor.dev/docs/user_guide/networking/) | Host network is not supported [Limitations](https://github.com/kata-containers/kata-containers/blob/main/docs/Limitations.md) | virtio-net backed by host TAP devices [design](https://github.com/firecracker-microvm/firecracker/blob/main/docs/design.md) |
| Storage | Gofer mediates file access [docs](https://gvisor.dev/docs/); GKE: no hostPath, no raw block [GKE Sandbox](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/sandbox-pods) | hostPath, subPath and procfs/sysfs mounts have documented limits [Limitations](https://github.com/kata-containers/kata-containers/blob/main/docs/Limitations.md) | File-backed virtio-block only [README](https://github.com/firecracker-microvm/firecracker/blob/main/README.md); Kata `fc` shim needs the devmapper snapshotter [values.yaml](https://github.com/kata-containers/kata-containers/blob/main/tools/packaging/kata-deploy/helm-chart/kata-deploy/values.yaml) |
| GPU | NVIDIA via `nvproxy` (T4, A100/A10G, L4, H100 listed) [GPU](https://gvisor.dev/docs/user_guide/gpu/) | QEMU only in the Kata table [hypervisors](https://github.com/kata-containers/kata-containers/blob/main/docs/hypervisors.md) | No (Kata hypervisor table shows no GPU) [hypervisors](https://github.com/kata-containers/kata-containers/blob/main/docs/hypervisors.md) |
| Governance | Google open source, Apache-2.0 ([repo](https://github.com/google/gvisor)) | Open Infrastructure Foundation [katacontainers.io](https://katacontainers.io/) | AWS open source, Apache-2.0 [README](https://github.com/firecracker-microvm/firecracker/blob/main/README.md) |
| Latest release | `release-20260928.0`, 2026-09-30 [releases](https://github.com/google/gvisor/releases) | 4.2.0, 2026-09-15 [releases](https://github.com/kata-containers/kata-containers/releases) | v1.17.0, 2026-09-10 [releases](https://github.com/firecracker-microvm/firecracker/releases) |

### Current vs deprecated

- **gVisor platforms.** systrap replaced ptrace as the default platform in mid-2023. ptrace is no longer supported and will eventually be removed. KVM gives the best performance on bare metal. Inside a VM, systrap often performs better than KVM because of nested virtualization overhead. [Platforms](https://gvisor.dev/docs/architecture_guide/platforms/)
- **Kata 4.x.** Kata 4.0.0 (2026-07-20) made the Rust runtime (`runtime-rs`) the default. The Go runtime is deprecated: no new features, only critical bug and CVE fixes. [4.0.0 release notes](https://github.com/kata-containers/kata-containers/releases/tag/4.0.0). kata-deploy sets `defaultShim` to `qemu-runtime-rs` on every architecture. [values.yaml](https://github.com/kata-containers/kata-containers/blob/main/tools/packaging/kata-deploy/helm-chart/kata-deploy/values.yaml)
- **Kata hypervisors.** The 4.0.0 notes list QEMU, Cloud Hypervisor, and Dragonball for runtime-rs. Dragonball is a built-in VMM that runs in the same process as the Rust shim. [4.0.0 notes](https://github.com/kata-containers/kata-containers/releases/tag/4.0.0), [hypervisors](https://github.com/kata-containers/kata-containers/blob/main/docs/hypervisors.md). The Kata hypervisor table also lists Firecracker and StratoVirt.
- **Firecracker in Kata.** kata-deploy has an `fc` shim (amd64 only, devmapper snapshotter) and no `fc-runtime-rs` shim. [values.yaml](https://github.com/kata-containers/kata-containers/blob/main/tools/packaging/kata-deploy/helm-chart/kata-deploy/values.yaml). Untested/inferred: Firecracker under Kata therefore uses the deprecated Go runtime today. Do not teach Kata+Firecracker as the main Kata path.

## 3. Firecracker clarification

- Firecracker is a VMM that uses KVM. It exposes an API to configure vCPUs, memory, network interfaces, and block devices, then boots a guest kernel. [README](https://github.com/firecracker-microvm/firecracker/blob/main/README.md)
- It does not pull OCI images, does not implement CRI, and has no Kubernetes integration by itself.
- **Through Kata.** Kata configures Firecracker as one of its hypervisors. [Kata with Firecracker](https://github.com/kata-containers/kata-containers/blob/main/docs/how-to/how-to-use-kata-containers-with-firecracker.md)
- **firecracker-containerd.** It lets containerd manage containers as Firecracker microVMs. It needs a specialized containerd binary. Its roadmap still lists "exploring CRI conformance and compatibility with Kubernetes". It has no GitHub releases; the last commit is from 2026-07-16. [README](https://github.com/firecracker-microvm/firecracker-containerd/blob/main/README.md). Treat it as not ready for Kubernetes.
- **AWS Lambda and Fargate.** An AWS whitepaper states that Lambda and Fargate use Firecracker on bare metal instances, and that Lambda runs functions in microVMs. [AWS logical separation whitepaper](https://docs.aws.amazon.com/whitepapers/latest/logical-separation/serverless-and-containers.html). The 2018 AWS Open Source blog states that Fargate tasks run on Firecracker microVMs. [AWS blog](https://aws.amazon.com/blogs/opensource/firecracker-open-source-secure-fast-microvm-serverless/). The EKS Fargate user guide says only that each pod has its own compute boundary and does not share the kernel with another pod; it does not name Firecracker. [EKS Fargate](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)

## 4. Kubernetes integration

RuntimeClass (`node.k8s.io/v1`) maps a name to a CRI handler. The handler must match a runtime that is configured in containerd. `overhead.podFixed` adds resources to scheduling and quota (stable since v1.24). `scheduling.nodeSelector` and `tolerations` send pods only to nodes that have the runtime. [RuntimeClass](https://kubernetes.io/docs/concepts/containers/runtime-class/)

containerd 2.x (config version 3) uses `plugins."io.containerd.cri.v1.runtime".containerd.runtimes.<handler>`. [containerd CRI config](https://github.com/containerd/containerd/blob/main/docs/cri/config.md). Config version 2 uses `plugins."io.containerd.grpc.v1.cri".containerd.runtimes.<handler>`. [gVisor containerd](https://gvisor.dev/docs/user_guide/containerd/quick_start/)

Example (UNTESTED; the overhead values are illustrative, not measured):

```yaml
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: gvisor
handler: runsc
overhead:
  podFixed:
    cpu: 100m
    memory: 64Mi
scheduling:
  nodeSelector:
    sandbox.example/gvisor: "true"
---
apiVersion: v1
kind: Pod
metadata:
  name: sandboxed
spec:
  runtimeClassName: gvisor
  containers:
  - name: shell
    image: busybox
    command: ["sleep", "infinity"]
```

For Kata, `runtimeClassName` is the name that kata-deploy creates, for example `kata-qemu-runtime-rs`. kata-deploy fills in the overhead for each shim. [template](https://github.com/kata-containers/kata-containers/blob/main/tools/packaging/kata-deploy/helm-chart/kata-deploy/templates/runtimeclasses.yaml)

**Pod Security Standards.** PSS has no standard that marks a pod as sandboxed. The PSS page states that sandboxed workloads may need fewer restrictions on privileges because they are isolated from the host kernel. [PSS FAQ](https://kubernetes.io/docs/concepts/security/pod-security-standards/). Pod Security Admission does not check `runtimeClassName`. Use an admission policy (for example Kyverno) to require a RuntimeClass in a namespace.

**User namespaces as a lighter step.** `hostUsers: false` is stable since Kubernetes v1.36. Root in the container maps to an unprivileged host UID. It needs Linux 6.3+, containerd 2.0+, and runc 1.2+. [User namespaces](https://kubernetes.io/docs/concepts/workloads/pods/user-namespaces/). It still shares the host kernel. A kernel bug is still reachable. Teach it as the step before a sandbox runtime, not as a replacement.

## 5. Managed Kubernetes

- **GKE Sandbox.** Offers two types: `gvisor` and `microvm`. microVM uses Kata Containers with Cloud Hypervisor and needs nested virtualization. gVisor is on by default in Autopilot and needs Container-Optimized OS. In Standard clusters, you cannot enable GKE Sandbox on the default node pool. gVisor does not support privileged containers or hostPath; microVM supports privileged containers but not GPUs or `hostNetwork`. [GKE Sandbox](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/sandbox-pods)
- **AKS Pod Sandboxing.** Uses Kata Containers, the Microsoft Hyper-V hypervisor, and the Cloud Hypervisor VMM. RuntimeClass is `kata-vm-isolation`. It needs Azure Linux and a Generation 2 VM size with nested virtualization (example `Standard_D4s_v3`). No host network, no Arm64, no FIPS or Trusted Launch on that node pool. [AKS Pod Sandboxing](https://learn.microsoft.com/en-us/azure/aks/use-pod-sandboxing)
- **EKS.** Fargate gives each pod its own compute boundary with no shared kernel; it does not allow privileged pods, DaemonSets, or `hostNetwork`. [EKS Fargate](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html). The AWS guide for moving from Fargate to EKS Auto Mode gets "Fargate-like isolation" with one pod per node (topology spread or anti-affinity), not with a sandbox runtime. [Auto Mode migration](https://docs.aws.amazon.com/eks/latest/userguide/auto-migrate-fargate.html). EKS best practices lists Firecracker for sandboxed execution but links only to an external thread. [Tenant isolation](https://docs.aws.amazon.com/eks/latest/best-practices/tenant-isolation.html). Untested/inferred: I found no AWS doc that offers gVisor or Kata as a managed EKS feature. On managed or self-managed nodes, you install them yourself.
- **EC2 nested virtualization.** AWS now supports nested virtualization (KVM and Hyper-V as L1) on non-metal instances: M7i, M7i-flex, M8i, M8id, M8i-flex, C7i, C7i-flex, C8i, C8id, C8i-flex, R7i, R7iz, R8i, R8id, R8i-flex, X8i, I7i, I7ie. You enable it with `--cpu-options NestedVirtualization=enabled`. AWS recommends bare metal for performance-sensitive workloads. [EC2 nested virtualization](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/amazon-ec2-nested-virtualization.html). T3 is not on the list. Note: the Firecracker getting-started guide still says EC2 supports KVM only on `.metal`; this text is older than the EC2 page. [getting started](https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md)

## 6. Lab feasibility for this workshop

Lab: kubeadm on EC2 `t3.small`/`t3.medium`/`t3.large` ([variables.tf](../../prepare-labs/terraform/providers/aws/variables.tf)), Ubuntu 26.04 amd64, containerd with a version-2 config file ([containerd-config.toml](../../prepare-labs/lib/containerd-config.toml)), Cilium 1.20.

Verified:
- gVisor systrap uses seccomp `SECCOMP_RET_TRAP` and is the platform for VMs without virtualization support. [Platforms](https://gvisor.dev/docs/architecture_guide/platforms/). gVisor needs Linux 5.6+ on x86_64 or ARM64. [Install](https://gvisor.dev/docs/user_guide/install/)
- T3 is not in the EC2 nested virtualization list, so a T3 instance has no `/dev/kvm`. [EC2 nested virtualization](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/amazon-ec2-nested-virtualization.html)
- Kata needs bare metal or nested virtualization. [Kata install](https://github.com/kata-containers/kata-containers/blob/main/docs/install/README.md). Firecracker needs `/dev/kvm`. [getting started](https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md)

Conclusion: gVisor can run on the student labs. Kata and Firecracker cannot run on T3. For an instructor demo, use one node from the list above (for example `m8i.large` or `c8i.large`) with nested virtualization enabled, or a `.metal` instance. Untested/inferred: the smallest size of each family supports the feature; check with `aws ec2 describe-instance-types` before you choose.

Recommended student hands-on (ALL UNTESTED; run on one worker node, as root):

```bash
# 1. Install runsc and the shim from the gVisor apt repository (see the Install page).
# 2. Add the handler to /etc/containerd/config.toml (version 2 file, matches the lab):
#    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runsc]
#      runtime_type = "io.containerd.runsc.v1"
systemctl restart containerd
kubectl label node <worker> sandbox.example/gvisor=true
```

Then apply the RuntimeClass and pod from section 4 and compare:

```bash
kubectl exec sandboxed -- dmesg        # expect "Starting gVisor..." lines
kubectl exec sandboxed -- uname -r     # compare with a normal pod and the node
kubectl run normal --image=busybox -- sleep infinity
kubectl exec normal -- uname -r        # same as the node kernel
```

gVisor documents the `dmesg` output and warns that an attacker can fake it, so do not use it as a security check. [Docker quick start](https://gvisor.dev/docs/user_guide/quick_start/docker/). Untested: the exact `uname -r` string that gVisor reports, and whether `dmesg` works in busybox without extra capabilities.

Risks to test before the workshop (all untested):
- Cilium 1.20 networking for a runsc pod (veth into netstack), NetworkPolicy, and `kubectl exec/logs/port-forward`. GKE lists port forwarding as unsupported for gVisor; check whether that is a GKE limit or a gVisor limit.
- containerd version on Ubuntu 26.04 and whether the version-2 config file keeps working; the gVisor page suggests `version = 3` for containerd 2.x. [gVisor containerd](https://gvisor.dev/docs/user_guide/containerd/quick_start/)
- Memory on `t3.small` with the extra Sentry and Gofer processes.
- Add `prepare-labs` steps only after a manual test passes; record the install in a setting, not by hand.

Instructor-only demo: Kata with kata-deploy (default `qemu-runtime-rs`) on a nested-virtualization node. Show `uname -r` in a Kata pod vs the node, like the AKS verification step. [AKS](https://learn.microsoft.com/en-us/azure/aks/use-pod-sandboxing). Show the RuntimeClass `overhead` that kata-deploy creates.

## 7. How to teach it

Core mental model (one ladder, each step adds a boundary):

1. Shared kernel: namespaces and cgroups. All containers call the host kernel directly.
2. Syscall filtering: seccomp `RuntimeDefault`, capabilities, LSMs, user namespaces. Same kernel, smaller surface.
3. User-space kernel: gVisor. The app calls the Sentry; the Sentry calls a small set of host syscalls.
4. VM per pod: Kata (with QEMU, Cloud Hypervisor, Dragonball, or Firecracker). The app calls its own guest kernel; the host sees a VMM process and KVM.

Slide outline (4-6 slides):
- Why: a kernel bug is a node escape for every pod on that node.
- The ladder above, as one diagram.
- gVisor vs Kata table: boundary, start time, overhead, compatibility, hardware need (use the GKE numbers, and say they are GKE numbers).
- Firecracker is a VMM: where it is used (Lambda, Fargate, Kata).
- RuntimeClass: handler, `overhead`, `scheduling`; one YAML.
- Lab: gVisor pod vs normal pod (`dmesg`, `uname -r`); demo: Kata pod.

Common student questions:
- "Is gVisor a VM?" No. It is a user-space kernel. The KVM platform uses virtualization extensions, but the sandbox keeps a process model. [Platforms](https://gvisor.dev/docs/architecture_guide/platforms/)
- "Why not run every pod sandboxed?" Each runtime adds overhead and compatibility limits. GKE recommends sandboxes for untrusted or third-party code, with little benefit for trusted first-party code. [GKE Sandbox](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/sandbox-pods)
- "Can I run Kata on my cloud VMs?" Only on bare metal or on instance types with nested virtualization (EC2 list above; AKS needs Gen2 with nested virtualization; GKE needs nested virtualization).
- "Does Pod Security Admission enforce a sandbox?" No. Use a policy engine to require `runtimeClassName`.
- "Do DaemonSets and node agents work?" Agents that need the host (hostPath, hostNetwork, privileged) conflict with the sandbox; GKE and AKS document these limits. Run node agents with the default runtime.

Common misconceptions:
- "Containers are VMs." A normal container shares the host kernel. Only Kata gives a guest kernel.
- "gVisor is a VM." It is an application kernel in user space.
- "Firecracker is a container runtime." It is a VMM; Kata or firecracker-containerd adds the container layer.
- "User namespaces are a sandbox." They reduce privilege on the host but keep the shared kernel.
- "`dmesg` proves isolation." gVisor says an attacker can fake it.

## 8. Sources

- https://gvisor.dev/docs/
- https://gvisor.dev/docs/architecture_guide/platforms/
- https://gvisor.dev/docs/user_guide/install/
- https://gvisor.dev/docs/user_guide/containerd/quick_start/
- https://gvisor.dev/docs/user_guide/quick_start/docker/
- https://gvisor.dev/docs/user_guide/networking/
- https://gvisor.dev/docs/user_guide/gpu/
- https://github.com/google/gvisor/releases
- https://katacontainers.io/
- https://github.com/kata-containers/kata-containers/releases (4.0.0, 4.1.0, 4.2.0)
- https://github.com/kata-containers/kata-containers/releases/tag/4.0.0
- https://github.com/kata-containers/kata-containers/blob/main/docs/hypervisors.md
- https://github.com/kata-containers/kata-containers/blob/main/docs/install/README.md
- https://github.com/kata-containers/kata-containers/blob/main/docs/Limitations.md
- https://github.com/kata-containers/kata-containers/blob/main/docs/how-to/how-to-use-kata-containers-with-firecracker.md
- https://github.com/kata-containers/kata-containers/blob/main/tools/packaging/kata-deploy/helm-chart/kata-deploy/values.yaml
- https://github.com/kata-containers/kata-containers/blob/main/tools/packaging/kata-deploy/helm-chart/kata-deploy/templates/runtimeclasses.yaml
- https://github.com/firecracker-microvm/firecracker/blob/main/README.md
- https://github.com/firecracker-microvm/firecracker/blob/main/SPECIFICATION.md
- https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md
- https://github.com/firecracker-microvm/firecracker/blob/main/docs/design.md
- https://github.com/firecracker-microvm/firecracker/releases
- https://github.com/firecracker-microvm/firecracker-containerd/blob/main/README.md
- https://kubernetes.io/docs/concepts/containers/runtime-class/
- https://kubernetes.io/docs/concepts/workloads/pods/user-namespaces/
- https://kubernetes.io/docs/concepts/security/pod-security-standards/
- https://github.com/containerd/containerd/blob/main/docs/cri/config.md
- https://docs.cloud.google.com/kubernetes-engine/docs/concepts/sandbox-pods
- https://learn.microsoft.com/en-us/azure/aks/use-pod-sandboxing
- https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/amazon-ec2-nested-virtualization.html
- https://docs.aws.amazon.com/eks/latest/userguide/fargate.html
- https://docs.aws.amazon.com/eks/latest/userguide/auto-migrate-fargate.html
- https://docs.aws.amazon.com/eks/latest/best-practices/tenant-isolation.html
- https://docs.aws.amazon.com/whitepapers/latest/logical-separation/serverless-and-containers.html
- https://aws.amazon.com/blogs/opensource/firecracker-open-source-secure-fast-microvm-serverless/ (first-party AWS blog; used only for the Fargate statement)

No software was installed, no cloud or cluster resources were created, and no other files were changed during this research.
