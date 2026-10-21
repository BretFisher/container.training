# Kubernetes What’s New: security and API evidence

Checked: 2026-10-05. Scope: v1.35, v1.36, v1.37. These are documentation and source checks, not live lab tests. No executable lab material is supplied here.

## Evidence method

The local `k8s-catch-up` skill supplied candidates. Official task pages supplied behavior. Tagged Kubernetes source resolved release and default conflicts. An announcement confirms release intent; a release-tagged gate declaration confirms the shipped default. The general feature-gate page has stale rows for some features.

## 1. Explicit supplemental groups

- Stable in v1.35. `SupplementalGroupsPolicy` is enabled and locked to its default.
- Field: `spec.securityContext.supplementalGroupsPolicy: Strict`. Only groups from `runAsGroup`, `supplementalGroups`, and `fsGroup` apply. Default `Merge` still includes group memberships from the image.
- This controls unexpected file access through image-defined groups. It does not remove privileges to change process identity.
- A runtime must support the policy. The kubelet rejects a Strict Pod on an unsupported node. `status.containerStatuses[].user.linux` reports the first process identity, not every later identity change.
- The task page and general gate page still label this beta. The release-tagged source and SIG Node announcement confirm stable.

Sources: [task documentation](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/#supplementalgroupspolicy), [GA announcement, 2025-12-23](https://kubernetes.io/blog/2025/12/23/kubernetes-v1-35-fine-grained-supplementalgroups-control-ga/), [v1.35 gate source, lines 1650–1653](https://github.com/kubernetes/kubernetes/blob/v1.35.0/pkg/features/kube_features.go#L1650-L1653).

## 2. Cached private image credentials

- Beta in v1.35; `KubeletEnsureSecretPulledImages` defaults on.
- Configure `KubeletConfiguration.imagePullCredentialsVerificationPolicy`. Default `NeverVerifyPreloadedImages` exempts images pulled outside kubelet. `AlwaysVerify` removes that exemption.
- Reused successful credentials can verify locally. Different credentials require a registry pull. This improves isolation when tenants share a node cache.
- At first enablement, existing cached images count as preloaded because no pull records exist. Review those images before the upgrade. Registry availability still affects new credentials.
- **Skill correction:** deleting the pull-record directory restores the preloaded classification; it is not a hardening step.
- **Docs correction:** the Images page spells `NeverVerifyAllowListedImages` with a capital L. The release-tagged configuration enum is `NeverVerifyAllowlistedImages`.

Sources: [Images documentation](https://kubernetes.io/docs/concepts/containers/images/#ensure-image-pull-credential-verification), [v1.37 configuration enum, lines 79–95](https://github.com/kubernetes/kubernetes/blob/v1.37.0/staging/src/k8s.io/kubelet/config/v1beta1/types.go#L79-L95), [feature gates](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/).

## 3. Pod user namespaces

- Stable in v1.36; `UserNamespacesSupport` defaults on and is locked.
- A Pod must opt in with `spec.hostUsers: false`; upgrading does not isolate every existing Pod automatically.
- Container IDs map to separate host IDs. Container root has no root privilege outside the user namespace. This reduces exposure from some container escapes; it is not complete isolation.
- Linux and every volume filesystem need idmap mounts. The docs specify Linux 6.3+, containerd 2.0+ or CRI-O 1.25+, and runc 1.2+ or crun 1.9+ (crun 1.13+ recommended).
- The Pod UID/GID fields retain their meaning inside the container. Validate the actual runtime and mounted filesystems before adopting it.

Sources: [user namespace documentation](https://kubernetes.io/docs/concepts/workloads/pods/user-namespaces/), [v1.37 source, lines 2013–2017](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/features/kube_features.go#L2013-L2017).

## 4. CEL mutation inside the API server

- `MutatingAdmissionPolicy` is stable in v1.36, default on; API `admissionregistration.k8s.io/v1`.
- The policy declares matching and mutation. A `MutatingAdmissionPolicyBinding` selects the policy and optional parameters.
- This can replace simple mutation webhooks and remove their network dependency. CEL is bounded; external lookups still need another design.
- **Skill correction:** use `spec.mutations[].applyConfiguration.expression` with `patchType: ApplyConfiguration`, or `spec.mutations[].jsonPatch.expression` with `patchType: JSONPatch`. A direct `mutations[].expression` field is wrong.
- Apply configuration cannot modify atomic arrays, maps, or structs. Design mutations to tolerate reinvocation and avoid unwanted field changes.

Sources: [policy documentation and correct examples](https://kubernetes.io/docs/reference/access-authn-authz/mutating-admission-policy/), [v1.37 API-server gate source, lines 379–382](https://github.com/kubernetes/kubernetes/blob/v1.37.0/staging/src/k8s.io/apiserver/pkg/features/kube_features.go#L379-L382).

## 5. Pod certificates and trust bundles

- Stable in v1.37. `PodCertificateRequest`, `ClusterTrustBundle`, and `ClusterTrustBundleProjection` default on. Their beta gates were off through v1.36.
- `projected.sources[].podCertificate` requests a key and certificate chain through a signer; `clusterTrustBundle` projects trust anchors selected by name or signer.
- Kubelet refreshes certificate files. Applications must reload changed files. Separate key and chain paths require care to avoid reading files from different rotations; a credential bundle simplifies this.
- Deploy a compatible signer controller and its policy. These APIs do not supply a complete workload identity system or automatically replace cert-manager or SPIRE.
- Missing required trust bundles prevent Pod startup. `optional: true` permits an empty trust file instead.

Sources: [projected volumes](https://kubernetes.io/docs/concepts/storage/projected-volumes/), [v1.37 release announcement](https://kubernetes.io/blog/2026/08/26/kubernetes-v1-37-release/#stable-pod-certificates-and-cluster-trust-bundles), [feature gates](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/).

## 6. Constrained impersonation

- Beta in v1.36; `ConstrainedImpersonation` defaults on.
- Require an identity grant such as `impersonate:user-info` on `authentication.k8s.io` users, plus action grants such as `impersonate-on:user-info:list` on the target resource in its own group and namespace.
- This permits a controller to act as a user for selected operations. The impersonated identity must also have permission for the operation.
- `associated-node` restricts a bound ServiceAccount to its associated node. Do not describe this as arbitrary node impersonation.
- Existing broad `impersonate` grants remain effective. Audit and remove those grants when changing a controller to constrained permissions; adding narrow grants alone does not remove old access.
- The docs contain a broad sentence saying all grants use `authentication.k8s.io`; their action examples correctly use the resource’s API group. Use those examples.

Source: [official impersonation documentation](https://kubernetes.io/docs/reference/access-authn-authz/user-impersonation/#constrained-impersonation).

## 7. Storage version migration

- Beta in v1.35, default off. Stable in v1.37, default on. Confirmed in release-tagged `StorageVersionMigrator` declarations.
- API: `storagemigration.k8s.io/v1`, kind `StorageVersionMigration`; select `spec.resource.group` and `spec.resource.resource`.
- The controller rewrites stored objects using the current storage schema and encryption settings. This helps with Secret key rotation and CRD storage version changes.
- Migration is requested explicitly. A cluster upgrade or encryption configuration update does not automatically rewrite all objects.
- Wait for completion and verify storage before removing old keys or stored CRD versions. Keep old keys available until the encrypted data migration completes.
- The current task and general gate pages still say beta/off. The v1.37 release source and dedicated GA announcement resolve that conflict.

Sources: [v1.37 gate source, lines 1965–1968](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/features/kube_features.go#L1965-L1968), [GA announcement, 2026-08-31](https://kubernetes.io/blog/2026/08/31/kubernetes-v1-37-storage-version-migration-ga/), [migration task](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/storage-version-migration/).

## 8. Narrow kubelet reader permissions

- Stable in v1.36; `KubeletFineGrainedAuthz` defaults on.
- With Webhook authorization, `/pods` and `/runningPods` use `nodes/pods`; `/healthz` uses `nodes/healthz`; `/configz` uses `nodes/configz`.
- The kubelet checks the narrow subresource before falling back to `nodes/proxy`.
- Replace broad reader grants with needed subresources. Existing `nodes/proxy` access remains broad; an upgrade does not remove it.
- Ensure API-server kubelet client credentials retain the required access. Existing stats, metrics, and log subresources remain separate.

Source: [kubelet authentication and authorization](https://kubernetes.io/docs/reference/access-authn-authz/kubelet-authn-authz/#fine-grained-authorization).

## 9. External ServiceAccount token signer

- Stable in v1.36; `ExternalServiceAccountTokenSigner` defaults on.
- API-server flag: `--service-account-signing-endpoint`, pointing to a Unix socket that implements `v1.ExternalJWTSigner`.
- This interface permits integration with external key custody, including a signer backed by an HSM or cloud KMS. It does not supply that external service.
- It is mutually exclusive with `--service-account-key-file` and `--service-account-signing-key-file`.
- The signer must be ready before API-server startup. This creates a control-plane dependency that needs an availability and key-rotation plan.

Sources: [ServiceAccount administration](https://kubernetes.io/docs/reference/access-authn-authz/service-accounts-admin/#external-serviceaccount-token-signing-and-key-management), [feature gates](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/).

## 10. Admission policy from local manifests

- Beta in v1.37; exact gate `ManifestBasedAdmissionControlConfig`, default on.
- Configure each admission plugin’s `staticManifestsDir` in `AdmissionConfiguration`, passed with `--admission-control-config-file`.
- Static policies operate at startup and can protect admission resources managed through the API. Local files need host-level protection and consistent distribution to all API servers.
- Names end in `.static.k8s.io`; API creation of those names is blocked when enabled. Only supported `admissionregistration.k8s.io/v1` kinds load.
- Webhooks use URLs, not Service references. Static policies cannot use `paramKind`; bindings cannot use `paramRef`.
- **Skill correction:** invalid files at startup fail startup; invalid runtime reloads retain the previous valid configuration and record the error. They do not stop the running API server.
- Remove this configuration before a downgrade to a version that does not support it.

Source: [manifest admission documentation](https://kubernetes.io/docs/reference/access-authn-authz/manifest-admission-control/).

## 11. Webhooks exclude virtual authentication resources

- Beta in v1.37; `ExcludeAdmissionWebhookVirtualResources` defaults on.
- Webhooks skip TokenReview, SelfSubjectReview, SubjectAccessReview, LocalSubjectAccessReview, SelfSubjectAccessReview, and SelfSubjectRulesReview.
- This prevents a failed webhook from blocking the cluster’s authentication or authorization checks.
- Explicit matching rules receive a warning. Wildcard-only matching avoids the warning, but does not bypass exclusion.
- **Skill clarification:** “a wildcard rule is exempt” applies to warning generation, not webhook dispatch.
- Audit and remove reliance on these calls. Disabling the gate is a temporary compatibility option; interception is deprecated in v1.37.

Source: [excluded virtual resources](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/#excluded-virtual-resources).

## Selection recommendation

Prioritize explicit supplemental groups, cached image credentials, user namespaces, CEL mutation, certificate delivery, storage migration, and narrower kubelet permissions. These connect directly to the workshop’s Pod hardening, admission, identity, RBAC, and encryption topics. Mention constrained impersonation and static admission as selective platform changes. External signing is useful as an architecture note, but full signer operation is outside a two-day course.

## Remaining limits

No live cluster or signer was used. Managed Kubernetes availability must be checked for the provider and version; a Kubernetes maturity label does not confirm provider support. The stale documentation rows and configuration spelling issue are recorded above, and resolved where release-tagged source exists. No skill files were changed.
