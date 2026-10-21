# Kubernetes: What’s New — operations evidence

Checked: October 5, 2026. Core scope: Kubernetes v1.35, v1.36, and v1.37 only. These are documentation and release-source checks. They are not live cluster tests.

## Scope and selection

Official announcements confirm the release dates: [v1.35, December 17, 2025](https://kubernetes.io/blog/2025/12/17/kubernetes-v1-35-release/), [v1.36, April 22, 2026](https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/), and [v1.37, August 26, 2026](https://kubernetes.io/blog/2026/08/26/kubernetes-v1-37-release/).

The chapter selects changes that affect workload security, resource use, or routine cluster operations. Related changes share a slide. Alpha features, narrow implementation changes, and features that require a separate course chapter are omitted. The [inventory](kubernetes-whats-new-inventory.md) records all 96 skill reference files, including 35 selections and 61 omissions. It does not claim to enumerate every release enhancement. Omitted skill claims are not independently release-verified.

Security, admission, identity, migration-controller, and SELinux checks are in [security evidence](kubernetes-whats-new-security-evidence.md). The separate [CNCF evidence](cncf-promotions-2025-2026.md) uses actual promotion dates and distinguishes direct admission from promotion. Ingress NGINX retirement is an adjacent community migration issue highlighted by the v1.35 announcement; it is not a core Kubernetes feature graduation.

## Workload lifecycle and autoscaling

| Selection | Verified milestone and behavior | Operator limit |
| --- | --- | --- |
| In-place container resize | Stable in v1.35. CPU and memory changes use `pods/resize`; `resizePolicy` controls container restart. Pending and in-progress conditions report progress. | A request can wait for node capacity. A running-Pod resize does not update the workload template. |
| Pod generation tracking | Stable in v1.35. `observedGeneration` reports the specification revision processed by the kubelet; resize conditions also carry generation information. | Compare desired and observed state before assuming a requested resize is applied. |
| Container restart rules | Beta in v1.35; `ContainerRestartRules` defaults on. Container restart policy and exit-code rules can differ from the Pod policy. | The selected change is individual-container recovery, not the later whole-Pod restart action. |
| Terminating replica count | Beta in v1.35; `DeploymentReplicaSetTerminatingReplicas` defaults on. `.status.terminatingReplicas` reports terminating Deployment/ReplicaSet Pods. | These Pods can retain resources during termination. Count them when assessing rollout capacity. |
| HPA tolerance | Stable in v1.37. Separate `scaleUp.tolerance` and `scaleDown.tolerance` override the global tolerance for one HPA. | v1.35 beta was disabled by default in tagged source, despite release prose suggesting otherwise. Do not teach a beta default from that prose. |
| HPA scale to zero | Beta in v1.37; `HPAScaleToZero` defaults on. `minReplicas: 0` requires at least one Object or External metric. | A working adapter and a metric available without running Pods are needed to scale from zero. CPU or memory usage alone cannot do this. |
| Memory QoS | Beta in v1.37; `MemoryQoS` defaults on. `TieredReservation` sets memory protection; `memoryThrottlingFactor` enables throttling. | Linux cgroup v2 is required. Defaults are reservation policy `None` and an unset throttling factor. Enabling the gate alone activates neither behavior. |

Sources: [resize and generation](https://kubernetes.io/docs/tasks/configure-pod-container/resize-container-resources/), [container restart rules](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#individual-container-restart-policy-and-rules), [terminating replicas](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#terminating-pods), [HPA](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/), [Memory QoS beta announcement](https://kubernetes.io/blog/2026/09/14/kubernetes-v1-37-memory-qos-graduates-to-beta/), [v1.35 feature declarations](https://github.com/kubernetes/kubernetes/blob/v1.35.0/pkg/features/kube_features.go), [v1.37 feature declarations](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/features/kube_features.go).

**Memory QoS correction:** the v1.36 announcement described beta promotion, but the v1.36 tagged gate source still declares alpha. The v1.37 announcement, feature history, and detailed beta article agree on v1.37. Existing explicit alpha configuration needs review; an unchanged default configuration does not acquire protection or throttling automatically.

## Storage

| Selection | Verified milestone and behavior | Operator limit |
| --- | --- | --- |
| Image volumes | Stable in v1.36. `spec.volumes[].image` mounts OCI image/artifact contents as a read-only volume. | The runtime must support image volumes. Registry authentication and image availability remain node requirements. Pin a digest for reproducibility. |
| Mutable CSI attach limits | Stable in v1.36. `CSIDriver.spec.nodeAllocatableUpdatePeriodSeconds` permits periodic refresh of the driver's allocatable count. A `ResourceExhausted` attachment error can trigger a refresh and fail the affected Pod so its controller can replace it. | Driver support is required. The configured periodic interval has a minimum of 10 seconds. |
| CSI tokens in secrets | Stable in v1.36. `CSIDriver.spec.serviceAccountTokenInSecrets: true` passes requested ServiceAccount tokens in the CSI request secrets map instead of `volume_context`. | Default is false. Configure `tokenRequests` and update the driver to read the secrets map. This avoids ordinary context logging, but does not remove the driver's responsibility to protect secrets. |
| Unused PVC tracking | Beta in v1.37; `PersistentVolumeClaimUnusedSinceTime` defaults on. `Unused: True` means no non-terminal Pod references the PVC; `lastTransitionTime` reports when that condition was observed. | Pending Pods count as references. This is a review signal, not automatic deletion, a backup guarantee, or proof that data can be removed. |

Sources: [image volumes](https://kubernetes.io/docs/tasks/configure-pod-container/image-volumes/), [CSI storage limits](https://kubernetes.io/docs/concepts/storage/storage-limits/#mutable-csi-node-allocatable-count), [CSI driver API](https://kubernetes.io/docs/reference/kubernetes-api/storage/csi-driver-v1/), [unused PVC tracking](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#unused-pvc-tracking), [v1.36 announcement](https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/), [feature-gate history](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/).

## Networking, devices, and scheduling

| Selection | Verified milestone and behavior | Operator limit |
| --- | --- | --- |
| Traffic distribution | Stable in v1.35. `PreferSameZone` and `PreferSameNode` express endpoint locality preferences. | Fallback remains. These preferences are not the strict endpoint restriction of a `Local` traffic policy. |
| Strict IP/CIDR validation | Beta in v1.36; `StrictIPCIDRValidation` defaults on. Built-in fields reject ambiguous IP forms and malformed subnet CIDRs. | Validation ratcheting permits unchanged stored values. Validate generated templates before rollout; do not assume every custom-resource field uses these validators. |
| DRA extended resources | Stable in v1.37. `DeviceClass.spec.extendedResourceName` links existing extended-resource requests to DRA allocation. The scheduler creates the required claim. | Operators still need a compatible DRA driver and device class. This does not install a driver or supply hardware. |
| DRA device taints | Stable in v1.37. Driver `ResourceSlice` taints and operator `DeviceTaintRule` objects can restrict or revoke allocations. `NoSchedule` prevents new allocations; `NoExecute` also evicts users that lack toleration. | Test device recovery and tolerations before maintenance. The general gate table has overlapping historical beta/stable rows; the feature documentation and release-tagged source confirm stable. |
| Gang scheduling | Beta in v1.37; `GenericWorkload` defaults off. `PodGroup` uses `scheduling.k8s.io/v1beta1`; member Pods use `spec.schedulingGroup.podGroupName`. A minimum count governs admission to scheduling. | Enable the gate, the API with runtime configuration, and scheduler support. Later failures or evictions can reduce the running group below its minimum; this is not a continuous quorum guarantee. |

Sources: [Service traffic distribution](https://kubernetes.io/docs/concepts/services-networking/service/#traffic-distribution-control), [strict validation KEP 4858](https://github.com/kubernetes/enhancements/tree/master/keps/sig-network/4858-ip-cidr-validation), [feature-gate history](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/), [DRA extended resources](https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/dra-api/#extended-resource-allocation-by-dra), [DRA device taints](https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/device-taints/), [gang scheduling](https://kubernetes.io/docs/concepts/scheduling-eviction/gang-scheduling/), [v1.37 feature declarations](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/features/kube_features.go).

## Migration findings

| Change | Confirmed state in the selected releases | Teaching decision |
| --- | --- | --- |
| cgroup v1 | From v1.35, kubelet defaults to `failCgroupV1: true`. The temporary false override remains in v1.37. | Teach migration to cgroup v2. Do not call default refusal complete code removal. |
| kube-proxy IPVS | Deprecated in v1.35; still available in v1.37. Later disabling/removal dates are plans. | Assess a supported proxy mode, preferably nftables on Linux, with node and network-plugin compatibility checks. |
| Service external IPs | Deprecated in v1.36; still usable when the gate permits them. Later disabling/removal dates are plans. | Select a load-balancing or routing replacement for the workload. Gateway API needs an implementation; installing its API alone does not provide a data plane. |
| kube-dns | Deprecated in v1.37. | Use CoreDNS. Do not describe deprecation as immediate removal. |
| gitRepo volumes | Permanently disabled in v1.36. The API field remains accepted. | Use an init container with `emptyDir` or a maintained sync tool. API acceptance does not prove kubelet support. |
| Static Pod API references | v1.37 enforces the restriction on Secret/ConfigMap references, with no opt-out. | Audit static manifests before upgrade. Use protected node files or an API-managed workload. |
| kubectl run filename flag | `--filename` / `-f` deprecated in v1.37. | Use apply/create for manifests and run for an argument-defined Pod. |
| Ingress NGINX | Community retirement in March 2026, highlighted in the v1.35 release. | Move to a maintained controller. Test route translation, TLS, rewrites, and controller-specific behavior. |

Sources: [cgroup v1 deprecation](https://kubernetes.io/docs/concepts/architecture/cgroups/#deprecation-of-cgroup-v1), [IPVS](https://kubernetes.io/docs/reference/networking/virtual-ips/#proxy-mode-ipvs), [Service external IPs](https://kubernetes.io/docs/concepts/services-networking/service/#external-ips), [gitRepo](https://kubernetes.io/docs/concepts/storage/volumes/#gitrepo), [v1.37 deprecations and static Pod enforcement](https://kubernetes.io/blog/2026/08/26/kubernetes-v1-37-release/), [Ingress NGINX retirement notice](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/), [Ingress migration guidance](https://kubernetes.io/blog/2026/02/27/ingress-nginx-before-you-migrate/).

## Validation and limits

- The chapter contains 30 authored slides, with no speaker notes or executable lab commands.
- It compiled with the repository's existing MarkMaker dependencies in the running slide container. A temporary, single-chapter manifest was used; no workshop manifest was edited for this chapter.
- The resulting Remark deck contains 32 slides because the compiler adds two closing slides. The 30 authored slides were checked for overflow. The migration table and the largest CNCF table were also inspected visually. No clipped text or content/source overlap was found.
- Existing repository style and the standard HTML template were used. No new rendering system, tool installation, or common script was added.
- No current lab exercise was executed. Field names, defaults, and milestones are documentation/source-checked; runtime behavior and driver compatibility are not lab-validated.
- Future removal schedules and 2026 promotions are bounded by the October 5, 2026 research date. Recheck them before a later workshop.
