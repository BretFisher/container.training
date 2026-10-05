# Kubernetes: What’s New

- Selected changes in Kubernetes **v1.35, v1.36, and v1.37**

- Focus: workload security, resource use, and cluster operations

- CNCF project promotions in 2025 and 2026 through October 5

---

## Three releases to assess

| Release | Release date | Selected themes |
| --- | --- | --- |
| v1.35 | December 17, 2025 | Resize, file permissions, traffic locality |
| v1.36 | April 22, 2026 | User namespaces, admission policies, CSI |
| v1.37 | August 26, 2026 | Pod identity, DRA, autoscaling, migration |

- Stable features can still need runtime support or configuration

- Beta does not mean enabled; check the gate and each required component

.footnote[Sources: [v1.35](https://kubernetes.io/blog/2025/12/17/kubernetes-v1-35-release/), [v1.36](https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/), [v1.37](https://kubernetes.io/blog/2026/08/26/kubernetes-v1-37-release/)]

---

## Control the groups that can access files

**Supplemental groups policy: stable in v1.35**

- Set Pod `spec.securityContext.supplementalGroupsPolicy` to `Strict`

- `Strict` excludes extra group memberships from the image's `/etc/group`

- Use `runAsGroup`, `fsGroup`, and `supplementalGroups` for required access

- This makes shared-volume permissions explicit in the Pod specification

- The field defaults to `Merge`; check node support before enforcing `Strict`

.footnote[Sources: [security context](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/#supplementalgroupspolicy), [v1.35 gate source](https://github.com/kubernetes/kubernetes/blob/v1.35.0/pkg/features/kube_features.go)]

---

## A cached private image still needs authorization

**Credential verification: beta in v1.35; gate on by default**

- Gate: `KubeletEnsureSecretPulledImages`

- The kubelet checks credentials before it reuses a private image

- This restricts one tenant's access to another tenant's cached image

- Default policy `NeverVerifyPreloadedImages` exempts preloaded images

- Assess `imagePullCredentialsVerificationPolicy: AlwaysVerify` on shared nodes

- Plan registry access and credentials before changing the policy

.footnote[Source: [image pull credential verification](https://kubernetes.io/docs/concepts/containers/images/#ensure-image-pull-credential-verification)]

---

## Separate container users from host users

**Pod user namespaces: stable in v1.36**

- Pod `spec.hostUsers: false` maps container users into separate host IDs

- Root inside the container has an unprivileged ID on the host

- This adds isolation when a container process escapes its container

- Check Linux, container runtime, and filesystem support for ID-mapped mounts

- The field still defaults to `true`; an upgrade does not enable this per Pod

- Continue to restrict privileges, capabilities, and host access

.footnote[Source: [Pod user namespaces](https://kubernetes.io/docs/concepts/workloads/pods/user-namespaces/)]

---

## Run simple mutations inside the API server

**MutatingAdmissionPolicy: stable in v1.36**

- Use `admissionregistration.k8s.io/v1` and a policy binding

- CEL expressions produce `ApplyConfiguration` or `JSONPatch` mutations

- Example use: add a required label when a matching Pod is created

- An in-process policy avoids a separate webhook service for that mutation

- Keep external controllers for policies that need external data or workflows

- Test matching, reinvocation, and failure behavior before enforcement

.footnote[Source: [mutating admission policies](https://kubernetes.io/docs/reference/access-authn-authz/mutating-admission-policy/)]

---

## Reduce control-plane key exposure

**External ServiceAccount token signing: stable in v1.36**

- API server `--service-account-signing-endpoint` selects an external signer

- The signer can keep private keys outside the API server process

- This supports separate key custody and key rotation

- The endpoint uses the Kubernetes signing protocol over a Unix socket

- Deploy and monitor a compatible signer; a KMS service alone is insufficient

- Do not combine this endpoint with the local signing-key flags

.footnote[Source: [external signing and key management](https://kubernetes.io/docs/reference/access-authn-authz/service-accounts-admin/#external-serviceaccount-token-signing-and-key-management)]

---

## Give node readers less access

**Fine-grained kubelet authorization: stable in v1.36**

- With webhook authorization, use `nodes/pods`, `nodes/healthz`, or `nodes/configz`

- These permissions can replace broad `nodes/proxy` access for specific readers

- `nodes/proxy` still works and permits much more than status inspection

- Review monitoring-agent roles and the API server's kubelet client identity

- Check the endpoints each reader needs before reducing permissions

.footnote[Source: [kubelet authorization](https://kubernetes.io/docs/reference/access-authn-authz/kubelet-authn-authz/#fine-grained-authorization)]

---

## Constrain what an impersonator can do

**Constrained impersonation: beta in v1.36; gate on by default**

- Gate: `ConstrainedImpersonation`

- Grant permission for an identity and for the actions performed as that identity

- Example: a support controller can list Pods as a user without gaining all their rights

- RBAC uses `impersonate:<mode>` and `impersonate-on:<mode>:<verb>`

- Existing broad `impersonate` grants still apply as a fallback

- Review and remove broad grants when adopting constrained rules

.footnote[Source: [constrained impersonation](https://kubernetes.io/docs/reference/access-authn-authz/user-impersonation/#constrained-impersonation)]

---

## Kubernetes can manage Pod certificate files

**Pod certificates and ClusterTrustBundles: stable in v1.37**

- A projected `podCertificate` source gives a Pod a private key and certificate

- The kubelet creates requests and rotates the files

- A projected `clusterTrustBundle` source supplies trusted CA certificates

- A separate signer must approve and issue certificates under its policy

- Applications must reload rotated files and use them for TLS or mTLS

- Certificate issuance does not configure application TLS automatically

.footnote[Source: [Pod certificates and trust bundles](https://kubernetes.io/blog/2026/08/28/kubernetes-v1-37-pod-certificates-and-cluster-trust-bundles/)]

---

## Rewrite stored objects after a change

**Storage version migration: stable in v1.37; enabled by default**

- Use `storagemigration.k8s.io/v1` `StorageVersionMigration`

- The controller rewrites one resource type under the current storage settings

- Uses include Secret encryption-key rotation and CRD storage-version changes

- A new encryption key does not re-encrypt existing Secrets by itself

- Monitor migration completion before removing old keys or stored-version support

- Back up etcd and assess the write load before a large migration

.footnote[Sources: [migration graduation](https://kubernetes.io/blog/2026/08/31/kubernetes-v1-37-storage-version-migration-ga/), [v1.37 gate source](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/features/kube_features.go)]

---

## Resize containers without recreating the Pod

**Container resize and Pod generation tracking: stable in v1.35**

- Change container CPU and memory through the `pods/resize` subresource

- `resizePolicy` determines whether the container must restart

- The Pod can keep its identity, but a resize can wait for node capacity

- Inspect applied resources and `PodResizePending` / `PodResizeInProgress`

- `observedGeneration` shows which specification revision the kubelet has seen

- Update the workload's desired configuration as well as the running Pod

.footnote[Source: [container resize and generation tracking](https://kubernetes.io/docs/tasks/configure-pod-container/resize-container-resources/)]

---

## Retry a container and track rollout resource use

**Both changes: beta in v1.35; gates on by default**

- `ContainerRestartRules`: a container can have its own restart policy

- `restartPolicyRules` can retry specified exit codes

- Use this when one container needs different recovery behavior

- `DeploymentReplicaSetTerminatingReplicas` adds `status.terminatingReplicas`

- Terminating Pods can still consume resources during a rollout

- Include them in capacity analysis when Pod counts exceed the rollout budget

.footnote[Sources: [container restart rules](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#individual-container-restart-policy-and-rules), [terminating replicas](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#terminating-pods)]

---

## Tune HPA response and allow idle workloads to stop

- **Per-HPA tolerance: stable in v1.37**

- Set `spec.behavior.scaleUp.tolerance` and `scaleDown.tolerance` separately

- Example: a 5% scale-up tolerance responds to smaller changes than 10%

- **Scale to zero: beta in v1.37; `HPAScaleToZero` on by default**

- `spec.minReplicas: 0` requires an Object or External metric

- CPU and memory usage cannot restart a workload that has no running Pods

- Provide a working metrics adapter and allow for startup delay

.footnote[Source: [HPA tolerance and scale to zero](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/)]

---

## Memory QoS requires an explicit node policy

**MemoryQoS: beta in v1.37; gate on by default**

- Uses Linux cgroup v2 to apply memory protection and throttling

- `memoryReservationPolicy: TieredReservation` protects memory requests

- `memoryThrottlingFactor` enables throttling before a memory limit is reached

- Defaults are `None` and unset: gate activation alone adds neither behavior

- Assess latency and OOM behavior with representative workloads

- Review existing explicit settings when upgrading from the alpha feature

.footnote[Source: [Memory QoS beta behavior and defaults](https://kubernetes.io/blog/2026/09/14/kubernetes-v1-37-memory-qos-graduates-to-beta/)]

---

## Deliver immutable files through an OCI registry

**Image volumes: stable in v1.36**

- Pod `spec.volumes[].image` mounts an OCI image or artifact as files

- The volume is read-only; applications consume it through a volume mount

- Uses include model files, policy data, and other immutable content

- Separate these files from the application's executable image

- Check runtime support and registry credentials on every target node

- Pin content by digest when a deployment needs reproducible files

.footnote[Source: [image volumes](https://kubernetes.io/docs/tasks/configure-pod-container/image-volumes/)]

---

## CSI drivers can improve scheduling and protect tokens

**Both changes: stable in v1.36**

- Mutable attach limits refresh `CSINode` capacity as node conditions change

- Driver field: `spec.nodeAllocatableUpdatePeriodSeconds`

- This reduces placement on nodes whose available attach slots have changed

- `spec.serviceAccountTokenInSecrets: true` moves CSI tokens to the secrets map

- That map avoids the plain-text logging exposure of `volume_context`

- Both need driver support; the token field also requires `tokenRequests`

.footnote[Sources: [mutable attach limits](https://kubernetes.io/docs/concepts/storage/storage-limits/#mutable-csi-node-allocatable-count), [CSI driver fields](https://kubernetes.io/docs/reference/kubernetes-api/storage/csi-driver-v1/)]

---

## Find PVCs that workloads no longer reference

**Unused PVC tracking: beta in v1.37; gate on by default**

- Gate: `PersistentVolumeClaimUnusedSinceTime`

- PVC condition `Unused: True` means no non-terminal Pod references the claim

- `lastTransitionTime` records when the controller observed that state

- A Pending Pod still counts as a user of the claim

- Use this signal to review storage costs and abandoned workloads

- Confirm retention and recovery requirements before deleting data

.footnote[Source: [unused PVC tracking](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#unused-pvc-tracking)]

---

## Prefer nearby endpoints; validate network inputs

- **Traffic distribution: stable in v1.35**

- Service `spec.trafficDistribution` supports `PreferSameZone` / `PreferSameNode`

- These preferences can reduce latency and cross-zone traffic; fallback remains

- **Strict IP/CIDR validation: beta in v1.36; gate on by default**

- Gate: `StrictIPCIDRValidation`; affects built-in API fields

- Remove leading-zero IPv4 octets and use network CIDRs where subnets are required

- Validate rendered templates before rollout; unchanged stored values are tolerated

.footnote[Sources: [traffic distribution](https://kubernetes.io/docs/concepts/services-networking/service/#traffic-distribution-control), [validation KEP](https://github.com/kubernetes/enhancements/tree/master/keps/sig-network/4858-ip-cidr-validation)]

---

## DRA can serve existing extended-resource requests

**DRA extended resources: stable in v1.37**

- A `DeviceClass` can set `spec.extendedResourceName`

- Existing Pod resource requests can then use a DRA driver

- The scheduler creates the required claim; workload authors need not create one

- This reduces the changes needed to migrate device allocation

- Install a compatible DRA driver and verify its device classes

- Driver deployment and hardware support remain operator responsibilities

.footnote[Source: [DRA extended-resource allocation](https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/dra-api/#extended-resource-allocation-by-dra)]

---

## Restrict allocation or evict users of one device

**DRA device taints and tolerations: stable in v1.37**

- Drivers publish taints in `ResourceSlice`; operators can use `DeviceTaintRule`

- `NoSchedule` prevents new allocations without a matching toleration

- `NoExecute` also evicts Pods that use the device without tolerating the taint

- This permits device maintenance without taking every device on a node offline

- Define recovery behavior and test tolerations before device maintenance

.footnote[Source: [DRA device taints and tolerations](https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/device-taints/)]

---

## Schedule a required group of Pods together

**Gang scheduling and PodGroup API: beta in v1.37; disabled by default**

- Gate: `GenericWorkload`; API: `scheduling.k8s.io/v1beta1`

- A `PodGroup` defines a required minimum count for scheduling

- Pods join with `spec.schedulingGroup.podGroupName`

- Placement waits until enough members can be scheduled together

- This reduces partial placement of coupled training or batch jobs

- Enable the gate, API, and scheduler support before adopting the feature

.footnote[Source: [gang scheduling](https://kubernetes.io/docs/concepts/scheduling-eviction/gang-scheduling/)]

---

## Check shared-volume SELinux labels before v1.37

**Volume mount labeling: stable across v1.36 and v1.37**

- v1.36: `SELinuxChangePolicy` and the `ReadWriteOncePod` optimization are stable

- v1.37: `SELinuxMount` extends the default to all eligible volumes

- A supported mount applies one SELinux context instead of relabeling each file

- Pods with different labels that share a volume on one node can conflict

- Check driver support and the SELinux warning controller before upgrading

- `spec.securityContext.seLinuxChangePolicy: Recursive` permits an explicit opt-out

.footnote[Source: [SELinux volume labels and upgrade checks](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/#efficient-selinux-volume-relabeling)]

---

## Upgrade nodes and replace deprecated network settings

| Change | Required action |
| --- | --- |
| cgroup v1 rejected by default, v1.35 | Move nodes to cgroup v2 before upgrade |
| kube-proxy IPVS deprecated, v1.35 | Assess and test a supported proxy mode, preferably nftables on Linux |
| Service `externalIPs` deprecated, v1.36 | Use a load balancer controller, NodePort, or Gateway API implementation |
| kube-dns deprecated, v1.37 | Migrate to CoreDNS |

- The temporary `failCgroupV1: false` override remains in v1.37

- IPVS and `externalIPs` still work; their later removal dates are plans

.footnote[Sources: [cgroups](https://kubernetes.io/docs/concepts/architecture/cgroups/#deprecation-of-cgroup-v1), [IPVS](https://kubernetes.io/docs/reference/networking/virtual-ips/#proxy-mode-ipvs), [external IPs](https://kubernetes.io/docs/concepts/services-networking/service/#external-ips), [kube-dns](https://kubernetes.io/blog/2026/08/26/kubernetes-v1-37-release/#deprecation-of-kube-dns)]

---

## Replace unsupported volume and static-Pod patterns

- **v1.36: `gitRepo` volume plugin is permanently disabled**

- Clone into `emptyDir` with an init container, or use a maintained sync tool

- The API can still accept the old field; acceptance does not mean it will run

- **v1.37: static Pods cannot reference Secrets or ConfigMaps**

- Supply protected files on the node, or use an API-managed workload

- Audit kubeadm control-plane manifests and other static Pods before upgrade

.footnote[Sources: [gitRepo removal](https://kubernetes.io/docs/concepts/storage/volumes/#gitrepo), [static Pod enforcement](https://kubernetes.io/blog/2026/08/26/kubernetes-v1-37-release/#kubelet-static-pods-can-no-longer-reference-secrets-or-configmaps)]

---

## Finish two other migrations

- **Community change highlighted in the v1.35 release**

- Ingress NGINX retired in March 2026; use a maintained controller

- For Gateway API, translate routes and test TLS, rewrites, and controller behavior

- **v1.37: `kubectl run --filename` / `-f` is deprecated**

- For a manifest, use the apply or create operation

- Reserve the run operation for a Pod described through its arguments

.footnote[Sources: [Ingress NGINX retirement](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/), [migration behavior](https://kubernetes.io/blog/2026/02/27/ingress-nginx-before-you-migrate/), [kubectl flag deprecation](https://kubernetes.io/blog/2026/08/26/kubernetes-v1-37-release/)]

---

## CNCF: Sandbox to Incubating in 2025

| Project | Promotion date |
| --- | --- |
| [OpenYurt](https://www.cncf.io/projects/openyurt/) | January 10, 2025 |
| [Kubescape](https://www.cncf.io/projects/kubescape/) | January 13, 2025 |
| [Metal3.io](https://www.cncf.io/projects/metal3-io/) | August 14, 2025 |
| [Lima](https://www.cncf.io/projects/lima/) | October 14, 2025 |
| [OpenFGA](https://www.cncf.io/projects/openfga/) | October 28, 2025 |

- Dates are the maturity-change dates in CNCF project records

- New admission directly at Incubating is excluded

.footnote[Sources: linked CNCF project records; announcement evidence is in the research notes.]

---

## CNCF: Incubating to Graduated in 2025

| Project | Promotion date |
| --- | --- |
| [in-toto](https://www.cncf.io/projects/in-toto/) | February 10, 2025 |
| [Knative](https://www.cncf.io/projects/knative/) | September 11, 2025 |
| [Crossplane](https://www.cncf.io/projects/crossplane/) | October 28, 2025 |
| [Dragonfly](https://www.cncf.io/projects/dragonfly/) | October 28, 2025 |

- Dragonfly's public announcement came in January 2026

- CubeFS is excluded: it graduated in December 2024

.footnote[Sources: linked CNCF project records; announcement and TOC evidence is in the research notes.]

---

## CNCF: Sandbox to Incubating in 2026

**Through October 5, 2026**

| Project | Promotion date |
| --- | --- |
| [Fluid](https://www.cncf.io/projects/fluid/) | January 8, 2026 |
| [Microcks](https://www.cncf.io/projects/microcks/) | May 3, 2026 |
| [HAMi](https://www.cncf.io/projects/hami/) | July 2, 2026 |
| [Confidential Containers](https://www.cncf.io/projects/confidential-containers/) | July 8, 2026 |
| [k8gb](https://www.cncf.io/projects/k8gb/) | July 18, 2026 |
| [Meshery](https://www.cncf.io/projects/meshery/) | September 14, 2026 |

.footnote[Sources: linked CNCF project records; supporting evidence is in the research notes.]

---

## CNCF: Incubating to Graduated in 2026

**Through October 5, 2026**

| Project | Promotion date |
| --- | --- |
| [Kyverno](https://www.cncf.io/projects/kyverno/) | March 16, 2026 |
| [OpenTelemetry](https://www.cncf.io/projects/opentelemetry/) | May 11, 2026 |
| [Cloud Native Buildpacks](https://www.cncf.io/projects/buildpacks/) | July 17, 2026 |
| [Kubeflow](https://www.cncf.io/projects/kubeflow/) | July 24, 2026 |
| [Karmada](https://www.cncf.io/projects/karmada/) | September 3, 2026 |

- CNCF maturity evaluates the project; check each component's support and stability

.footnote[Sources: linked CNCF project records; announcement evidence is in the research notes.]
