# Falco and Kyverno demo research

Research date: 2026-10-05. Target: the workshop's kubeadm clusters.
Status: documented components; proposed integration and lab are untested.

## Recommended workshop scope

Use two short demonstrations with independent configuration. Kyverno rejects an unsafe pod specification. Falco then detects an unexpected command in an allowed pod. An interactive shell is a simpler trigger than sudo because it needs no sudo-enabled image or elevation setup. An optional sudo attempt can follow, but label it as an attempt unless UID evidence proves elevation. Falco can load its own rules; Kyverno generation is not required. This reduces setup while keeping the distinction between admission control and runtime detection clear. The combined generation design below is optional.

## Verified documentation

- Kyverno checks Kubernetes API requests and can reject resource definitions. Its generation policies create and synchronize Kubernetes resources. Current `GeneratingPolicy` examples use `policies.kyverno.io/v1`; existing `ClusterPolicy` generate documentation also remains available. Neither feature executes Falco detection logic. [Architecture](https://kyverno.io/docs/introduction/how-kyverno-works/), [GeneratingPolicy](https://kyverno.io/docs/policy-types/generating-policy/), [ClusterPolicy generate](https://kyverno.io/docs/policy-types/cluster-policy/generate/).
- Falco evaluates runtime event conditions and produces alerts. Its default `Non sudo setuid` rule excludes sudo and su. `Sudo Potential Privilege Escalation` targets a specific CVE-2021-3156 command pattern; it is not a general sudo detector. Use a custom rule for this demo. [Rules](https://falco.org/docs/concepts/rules/), [Default rules](https://falco.org/docs/reference/rules/default-rules/).
- Falco now recommends its Kubernetes operator; the existing Helm chart remains supported. The documented operator prerequisites include Kubernetes 1.29+ and administrative installation access. A container metadata plugin is required for container fields in rules. [Operator deployment](https://falco.org/docs/setup/operator/).
- `Rulesfile` uses `artifact.falcosecurity.dev/v1alpha1`. It supports structured `spec.inlineRules` or `spec.configMapRef.name`; a referenced ConfigMap must contain `data.rules.yaml`. Its selector targets nodes, not application namespaces. Scope application events in the Falco rule condition. [Rulesfile reference](https://github.com/falcosecurity/falco-operator/blob/main/docs/crds/rulesfile.md).
- The artifact controller delivers rules into shared volumes. Falco normally watches its rule files and reloads changes. Confirm the installed versions' status and logs before each trigger; resource creation alone does not prove that every node loaded the rule. [Operator architecture](https://github.com/falcosecurity/falco-operator/blob/main/docs/architecture.md), [Hot reload](https://falco.org/docs/installation/).
- `allowPrivilegeEscalation: false` sets the process `no_new_privs` control. This prevents privilege gains through mechanisms such as setuid execution. It does not mean that the sudo binary cannot start or that a runtime alert cannot occur. [Kubernetes security context](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/).

## Proposed integration

Use Kyverno to generate a Falco `Rulesfile` in the Falco namespace when an administrator labels the demo namespace. Give the generation controller the required Rulesfile RBAC. Put the custom rule inline, so one generated resource is sufficient. Synchronize it through Kyverno. Falco's operator then loads the detection rule; Falco observes the processes.

This is a composition of documented resource generation and rule loading, not a verified native Kyverno–Falco integration. Test the exact policy API and versions first. A ConfigMap plus a Rulesfile reference is another option, but adds a resource. A generated ConfigMap alone is insufficient: Falco must reference or mount it. The traditional Helm route uses `customRules` and configured rule paths. Avoid two controllers managing the same ConfigMap. [Falco custom rules](https://falco.org/docs/concepts/rules/default-custom/).

## Proposed demonstration

1. Show Kyverno rejecting a pod that allows privilege escalation.
2. Use a narrow demo-only policy exception for an intentionally permissive pod. Start as a nonroot user in a pinned image containing sudo and a narrowly configured sudo command. This is a controlled configuration demonstration; no vulnerable sudo release is needed.
3. Have Kyverno generate the custom rule. Verify generation, rule loading, and node coverage before executing the command.
4. Run a harmless `sudo -n id`. Alert on execution of sudo or su inside the demo container. Display process, parent, command, user UID, and container identity. Label this evidence as execution of a privilege-changing tool.
5. For a confirmed transition, compare the original `id` result with `sudo -n id` returning UID 0, and correlate a second alert for the root child process. Binary name alone cannot prove elevation. Starting a container as root also does not prove a transition or host compromise.
6. Deploy the hardened variant with `allowPrivilegeEscalation: false`; repeat the command and show elevation failing. The attempt alert may still occur. Then remove the demo exception and prove Kyverno rejects the permissive variant again.

## Checks before slides

- Pin and verify Falco engine, operator, rules, plugins, Kyverno, and demo image on the student node kernel and runtime.
- Test sudo behavior, effective UID fields, child process correlation, custom rule scope, and repeatable alert output. Default first-match rule evaluation can hide a later matching demo rule; test ordering or an appropriate matching mode. [Chart configuration](https://github.com/falcosecurity/charts/blob/master/charts/falco/README.md).
- Confirm both successful and blocked cases, namespace scoping, policy exception removal, and cleanup. Separate an attempt alert from evidence of a successful UID change.
- Keep Falco installation and node permissions separate from restrictions on student workloads. Use logs for the initial demo; a UI and alert routing add dependencies.

No software was installed, no cluster resources were created, and no slide sources were changed during this research.
