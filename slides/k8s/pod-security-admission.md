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
