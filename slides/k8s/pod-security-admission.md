<!-- verified: 2026-10-09 -->
# Pod Security Admission

- Built-in admission controller that applies the Pod Security Standards

- It replaces Pod Security Policies (PSP), which were removed in Kubernetes 1.25

- Easier to use

  (doesn't require complex interaction between policies and RBAC)

---

## PSA in theory

- Leans on PSS (Pod Security Standards)

- Defines three policies:

  - `privileged` (can do everything; for system components)

  - `restricted` (no root user; almost no capabilities)

  - `baseline` (in-between with reasonable defaults)

- Label namespaces to indicate which policies are allowed there

- Also supports setting global defaults

- Supports `enforce`, `audit`, and `warn` modes

---

## Pod Security Standards

- `privileged`

  - can do everything

- `baseline`

  - no privileged pods, hostNetwork, hostPID, hostIPC, hostPorts, hostPath volumes
  - limits capabilities, SELinux, AppArmor, seccomp (not `Unconfined`), sysctls
  - containers can still run as root and use the default capabilities

- `restricted` (= everything in `baseline`, plus:)

  - limits volumes to configMap, emptyDir, ephemeral, secret, PVC, ...
  - `runAsNonRoot: true`, `allowPrivilegeEscalation: false`
  - seccomp profile `RuntimeDefault` (or `Localhost`) is mandatory
  - drop `ALL` capabilities (only `NET_BIND_SERVICE` can be added back)

---

class: extra-details

## Why `baseline` ≠ `restricted` ?

- `baseline` = should work for that vast majority of images

- `restricted` = better, but might break / require adaptation

- Many images run as root by default

- Some images use CAP_CHOWN (to `chown` files)

- Some programs use CAP_NET_RAW (e.g. `ping`)

---

## Namespace labels

- Three optional labels can be added to namespaces:

  `pod-security.kubernetes.io/enforce`

  `pod-security.kubernetes.io/audit`

  `pod-security.kubernetes.io/warn`

- The values can be: `baseline`, `restricted`, `privileged`

  (setting it to `privileged` doesn't really do anything)

- Optional `...-version` labels pin the rules of a Kubernetes version

  (example: `pod-security.kubernetes.io/enforce-version=v1.37`; default: `latest`)

---

## `enforce`, `audit`, `warn`

- `enforce` = prevents creation of pods

- `warn` = allow creation but include a warning in the API response

  (will be visible e.g. in `kubectl` output)

- `audit` = allow creation but generate an API audit event

  (will be visible if API auditing has been enabled and configured)

---

## Blocking privileged pods

- Let's block `privileged` pods everywhere

- And issue warnings and audit for anything above the `restricted` level

.lab[

- Set up the default policy for all namespaces:
  ```bash
  kubectl label namespaces \
      pod-security.kubernetes.io/enforce=baseline \
      pod-security.kubernetes.io/audit=restricted \
      pod-security.kubernetes.io/warn=restricted \
      --all
  ```

]

- Running pods that break the new policy get a warning, but they keep running

- Look at the warning about `kube-system` in the output!

---

class: extra-details

## Check before you apply

- When adding an `enforce` policy, we see warnings

  (for the pods that would infringe that policy)

- It's possible to do a `--dry-run=server` to see these warnings

  (without applying the label)

- It will only show warnings for `enforce` policies

  (not `warn` or `audit`)

---

## What about `kube-system`?

- We have many system components in `kube-system` (Cilium, kube-proxy...)

- Many of them need `privileged` (host network, host paths, capabilities)

- If `baseline` applied there, their new pods could not start after an update!

- But our output says:

  `namespace "kube-system" is exempt from Pod Security, and the policy ... will be ignored`

- The API server of our cluster has an *exemption* for `kube-system`

  (in its *admission configuration*: we will look at it soon)

- Without that exemption: label `kube-system` with `enforce=privileged`

---

## What about new namespaces?

- If new namespaces are created, they will get default permissions

- What can we do about this?

  - make sure that whoever/whatever creates namespaces sets labels correctly?

  - use mutating policies to automatically add labels when namespaces are created?

  - change default permissions with an *admission configuration* file?

  - something else?

- Question: is one of these options better/safer?

---

## Access control

- Kubernetes RBAC has a separate `create` permission

- It is possible to let someone create a Namespace, but not change its labels

  (the latter would require `patch` or `update` permissions)

- However, if someone can create a Namespace, they can set any labels at creation time

- We can't control specific labels with RBAC, but we can do it with admission control

  (CEL policies, Kyverno...)

- Conclusion: it's possible to let users create namespaces, but it requires tight controls

---

## Alternative solution

- Don't let users create namespaces directly

- Delegate that to our CI/CD, gitops, ... and make sure *that* sets labels correctly

- Or use a controller to create namespaces on our behalf

  (Example: https://github.com/jpetazzo/nsplease)

---

## Admission configuration

- The API server can read an *admission configuration file*

  (flag: `--admission-control-config-file`)

- For Pod Security, this file sets:

  - the defaults for namespaces with no labels

  - exemptions (namespaces, users, RuntimeClasses) that Pod Security ignores

- Our clusters already have one!

  (some hardened distributions, like Talos, have one too)

---

## Looking at our admission configuration

.lab[

- Check the flag in the static pod manifest of the API server:
  ```bash
  sudo grep admission /etc/kubernetes/manifests/kube-apiserver.yaml
  ```

- Look at the file:
  ```bash
  sudo cat /etc/kubernetes/AdmissionConfiguration.yaml
  ```

]

- `defaults`: `enforce: privileged`, `audit: baseline`, `warn: baseline`

- `exemptions`: the `kube-system` namespace

---

## How did it get there?

- We created our clusters with `kubeadm`

- The kubeadm `ClusterConfiguration` adds the flag and mounts the file:

```yaml
apiServer:
  extraArgs:
  - name: admission-control-config-file
    value: /etc/kubernetes/AdmissionConfiguration.yaml
  extraVolumes:
  - name: admission-control-config-file
    hostPath: /etc/kubernetes/AdmissionConfiguration.yaml
    mountPath: /etc/kubernetes/AdmissionConfiguration.yaml
    readOnly: true
```

- On managed clusters (EKS, AKS, GKE), we cannot change the API server flags

  (we use namespace labels, or a policy engine like Kyverno)

---

## The admission configuration, line by line (1/3)

```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: AdmissionConfiguration
plugins:
- name: PodSecurity
  configuration:
    apiVersion: pod-security.admission.config.k8s.io/v1
    kind: PodSecurityConfiguration
    defaults:
      enforce: "privileged"
      enforce-version: "latest"
      audit: "baseline"
      audit-version: "latest"
      warn: "baseline"
      warn-version: "latest"
    exemptions:
      usernames: []
      runtimeClasses: []
      namespaces: [ kube-system ]
```

---

## The admission configuration, line by line (2/3)

```yaml
    defaults:
      enforce: "privileged"
      enforce-version: "latest"
      audit: "baseline"
      audit-version: "latest"
      warn: "baseline"
      warn-version: "latest"
```

- `defaults`: for each mode, used when the namespace has no label for that mode

- `enforce: privileged`: reject no pods

- `audit: baseline`: add an annotation to the audit event of a pod that breaks `baseline`

- `warn: baseline`: send a warning to the client (e.g. `kubectl`)

- `*-version: latest`: use the rules of the API server version (or pin one, e.g. `v1.37`)

---

## The admission configuration, line by line (3/3)

```yaml
    exemptions:
      usernames: []
      runtimeClasses: []
      namespaces: [ kube-system ]
```

- `exemptions`: Pod Security skips all checks (`enforce`, `audit`, `warn`) for these

- `usernames`: requests from these authenticated users

  (controllers create the pods of a Deployment, so this exempts only direct pod creation)

- `runtimeClasses`: pods with a `runtimeClassName` in this list

  (e.g. a sandboxed runtime like gVisor or Kata Containers)

- `namespaces`: all pods in these namespaces; their labels are ignored

- Each exemption is a gap in our policy: keep the lists short!

---

## PSA rule changes since GA (1.25)

.small[
| Version | Level | Change |
|-|-|-|
| 1.25 | restricted | Windows pods skip privilege escalation, seccomp, capabilities |
| 1.27 | baseline | allow sysctl `net.ipv4.ip_local_reserved_ports` |
| 1.29 | baseline | allow sysctls `net.ipv4.tcp_keepalive_*`, `tcp_fin_timeout` |
| 1.31 | baseline | allow SELinux type `container_engine_t` |
| 1.32 | baseline | allow sysctls `net.ipv4.tcp_rmem`, `tcp_wmem` |
| **1.34** | **baseline** | **block `host` in probes and lifecycle hooks** |
| 1.35 | both | `hostUsers: false` pods: allow root user (and any `procMount` in baseline) |
| 1.37 | baseline | allow sysctls `tcp_slow_start_after_idle`, `tcp_notsent_lowat` |
]

- With `latest`, an API server upgrade changes the rules, with no edit to our config

- Most changes allow more, but 1.34 blocks more: pods that passed on 1.33 can fail

- Pin a version (e.g. `enforce-version: v1.33`) to upgrade the rules on our own schedule

---

## How to read `enforce: privileged`

- Each setting is `<mode>: <level>`

- The *level* is a set of rules (from no rules to the most rules):

  `privileged` (no rules) → `baseline` → `restricted`

- The *mode* is the action when a pod breaks the rules of that level:

  `enforce` = reject the pod; `warn` = show a warning; `audit` = write it in the audit log

- `enforce: privileged` = "reject pods that break no rules" = reject no pods

- `warn: baseline` = "show a warning for pods that break the `baseline` rules"

- Each mode has its own level: PSA checks each pod 3 times, maybe with 3 levels

---

## What PSA does for each new pod

1. Is the namespace, the user, or the RuntimeClass exempt?

   Yes: allow the pod, with no checks. Stop.

2. For each mode (`enforce`, `warn`, `audit`), find the level:

   the namespace label `pod-security.kubernetes.io/<mode>`, or (if no label) the `defaults`

3. Check the pod against the rules of that level

4. If the pod breaks the rules: do the action of that mode

5. If `enforce` did not reject it, the pod is created (with or without warnings)

- Each mode is separate: a namespace with only an `enforce` label

  still uses the `defaults` for `warn` and `audit`

---

## Walkthrough: a namespace with no labels

- We create `hacktheplanet` (a DaemonSet with a `hostPath` volume) in `nolabels`

| Mode | Label? | Level | Breaks the rules? | Result |
|-|-|-|-|-|
| `enforce` | no: default | `privileged` | no (no rules) | allowed |
| `warn` | no: default | `baseline` | yes (`hostPath`) | warning in `kubectl` |
| `audit` | no: default | `baseline` | yes (`hostPath`) | entry in the audit log |

- Result: the pods run, and we see a warning

- We will test this in the next lab

---

## Walkthrough: a namespace with labels

- We create `hacktheplanet` in `default`

  (our earlier lab added labels: `enforce=baseline`, `warn=restricted`, `audit=restricted`)

| Mode | Label? | Level | Breaks the rules? | Result |
|-|-|-|-|-|
| `enforce` | yes | `baseline` | yes (`hostPath`) | **pod rejected** |
| `warn` | yes | `restricted` | yes (root user, ...) | warning in `kubectl` |
| `audit` | yes | `restricted` | yes (root user, ...) | entry in the audit log |

- Result: `kubectl apply` shows a warning, and succeeds!

- But no pods run... why?

---

## Pods vs. workload resources

- `hacktheplanet` is a DaemonSet, not a Pod

- `warn` and `audit` also check the pod template of workload resources

  (DaemonSet, Deployment, Job...: we see the warning at `kubectl apply`)

- `enforce` checks only Pods: PSA does not reject the DaemonSet

- Then the DaemonSet controller creates the pods, and `enforce` rejects each one

- The error is not in our terminal: it is in the events of the controller

  (`kubectl describe daemonset hacktheplanet`; for a Deployment, its ReplicaSet)

---

## Testing the default policy

.lab[

- Create a namespace with no Pod Security labels, then deploy `hacktheplanet` in it:
  ```bash
  kubectl create namespace nolabels
  kubectl apply -n nolabels -f ~/container.training/k8s/hacktheplanet.yaml
  ```

<!-- ```hide kubectl rollout status -n nolabels daemonset hacktheplanet --timeout=120s``` -->

- Check the pods:
  ```bash
  kubectl get pods -n nolabels
  ```

]

- We get a `baseline` warning (`hostPath volumes`), but the pods run

  (the default is `enforce: privileged`; earlier labs need privileged pods)

---

## Changing the default policy

- To block these pods, change the defaults to `enforce: baseline`

  (in the admission configuration file, on each control plane node)

- The API server reads the file only when it starts

  (kubeadm: move its manifest out of `/etc/kubernetes/manifests`, then back)

- Then, exceptions get a label: `pod-security.kubernetes.io/enforce=privileged`

.lab[

- Delete our test namespace:
  ```bash
  kubectl delete namespace nolabels
  ```

]

---

## So, which solution is the best?

- It depends!

- If namespaces are exclusively created by admins and deployment pipelines:

  *make sure the pipelines set the labels properly*

- If users need to be able to create arbitrary namespaces:

  *enable admission configuration and a validation rule to block security labels*

- If you can't enable admission configuration (e.g. some managed clusters):

  *you can work around it with more complex mutation/validation rules*

???

:EN:- Preventing privilege escalation with Pod Security Admission
:FR:- Limiter les droits des conteneurs avec *Pod Security Admission*
