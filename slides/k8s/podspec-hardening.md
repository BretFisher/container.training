<!-- verified: 2026-10-09 -->
# Hardening the pod spec

- Pod Security Admission *rejects* pods that break a policy

- But it does not *write* a good pod spec for us

- Most pod security settings are off by default

- We start from a template: [github.com/BretFisher/podspec](https://github.com/BretFisher/podspec)

  (one `pod.yaml` file, with a comment on each line)

- We copy its fields into the pod template of our Deployments, DaemonSets, etc.

---

## What a pod gets by default

| Setting | Default | Risk |
|-|-|-|
| User | The `USER` of the image (often root) | Root in the container |
| `allowPrivilegeEscalation` | `true` | `sudo` and setuid binaries work |
| Capabilities | The runtime set (14, with `NET_RAW`, `CHOWN`, `SETUID`...) | More kernel access |
| Seccomp | `Unconfined` (on our cluster) | All system calls |
| Root filesystem | Writable | Attacker can change binaries |
| ServiceAccount token | Mounted in every container | An API credential to steal |
| Service env vars | One set for each Service | Information about the namespace |
| User namespace | The node's (`hostUsers: true`) | UID 0 in the pod = UID 0 on the node |

---

## Pod-level settings

```yaml
spec:
  automountServiceAccountToken: false  # mount the token only if the app calls the API
  enableServiceLinks: false            # use DNS names, not Docker-link env vars
  hostUsers: false                     # a user namespace for the pod (stable in 1.36)
  securityContext:
    seccompProfile:
      type: RuntimeDefault             # the default seccomp profile of containerd
    runAsUser: 1001                    # if the Dockerfile has no USER
    runAsGroup: 1001
    runAsNonRoot: true                 # the kubelet refuses to start root containers
```

- Pod-level `securityContext` applies to all containers of the pod

- We look at `hostUsers` in detail in the next chapter

---

## Container-level settings

```yaml
    securityContext:
      allowPrivilegeEscalation: false  # sets "no_new_privs": setuid does not work
      privileged: false
      capabilities:
        drop: ["ALL"]                  # add back only what the app needs
      readOnlyRootFilesystem: true     # mount an emptyDir where the app writes
```

- `pod.yaml` in the repo does not drop capabilities: the `restricted` policy requires it

- `readOnlyRootFilesystem` is not in `restricted`, but it stops many attacks

  (the app needs a writable volume for `/tmp`, caches, PID files...)

- AppArmor: containerd applies its default profile when the field is not set

  (set `appArmorProfile` only if *all* nodes have AppArmor)

---

## The other fields in `pod.yaml`

- They are not security settings, but they make a better pod:

  - an exact image tag (not `latest` or `stable`)

  - a readiness probe (rolling updates wait for it)

  - memory limit = memory request (the scheduler reserves what the app can use)

  - a CPU request, and no CPU limit (unless we need the `Guaranteed` QoS)

  - `terminationGracePeriodSeconds`: time to stop gracefully (default 30 seconds)

- Our lab file @@LINK[k8s/podspec-hardened.yaml] uses all of the security settings

---

## Lab: a namespace with the `restricted` policy

.lab[

- Create a namespace, and set `enforce` and `warn` to `restricted`:
  ```bash
  kubectl create namespace podspec
  kubectl label namespace podspec \
      pod-security.kubernetes.io/enforce=restricted \
      pod-security.kubernetes.io/warn=restricted
  ```

- Create a Deployment with no security settings:
  ```bash
  kubectl create deployment plain -n podspec \
      --image=ghcr.io/nginx/nginx-unprivileged:1.31.6-alpine
  ```

- Check the Deployment:
  ```bash
  kubectl get deployment plain -n podspec
  ```

]

- The warning lists the 4 problems, and the Deployment has 0 pods

---

## Lab: the hardened Deployment

.lab[

- Create the hardened Deployment:
  ```bash
  kubectl apply -n podspec -f ~/container.training/k8s/podspec-hardened.yaml
  ```

<!-- ```hide kubectl rollout status -n podspec deployment hardened --timeout=120s``` -->

- Check that its pod runs:
  ```bash
  kubectl get pods -n podspec
  ```

- Move the `plain` Deployment to the `default` namespace, to compare the two pods:
  ```bash
  kubectl delete deployment plain -n podspec
  kubectl create deployment plain -n default \
      --image=ghcr.io/nginx/nginx-unprivileged:1.31.6-alpine
  ```

<!-- ```hide kubectl rollout status -n default deployment plain --timeout=120s``` -->

]

---

## Lab: compare the two pods

.lab[

- Look at the user, capabilities, `no_new_privs`, and seccomp in each pod:
  ```bash
  kubectl exec -n default deploy/plain -- \
      grep -E "^(Uid|CapBnd|NoNewPrivs|Seccomp):" /proc/1/status
  kubectl exec -n podspec deploy/hardened -- \
      grep -E "^(Uid|CapBnd|NoNewPrivs|Seccomp):" /proc/1/status
  ```

]

- `CapBnd`: the capabilities that the process can get (`0` = none)

- `NoNewPrivs: 1`: setuid binaries do not give more privileges

- `Seccomp: 2`: a seccomp filter is active (`0` = no filter)

---

## Lab: token and root filesystem

.lab[

- Look for the ServiceAccount token in the plain pod:
  ```bash
  kubectl exec -n default deploy/plain -- ls /var/run/secrets/kubernetes.io/serviceaccount
  ```

- Look for it in the hardened pod:
  ```bash
  kubectl exec -n podspec deploy/hardened -- ls /var/run/secrets/kubernetes.io/serviceaccount
  ```

<!-- ```expect-fail``` -->

- Try to write to the root filesystem of the hardened pod:
  ```bash
  kubectl exec -n podspec deploy/hardened -- touch /etc/hacked
  ```

<!-- ```expect-fail``` -->

]

- The hardened pod has no token: a stolen pod gives no API access

- The root filesystem is read-only, even for the user of the app

---

## Lab: cleaning up

.lab[

- Delete the namespace and the `plain` Deployment:
  ```bash
  kubectl delete namespace podspec
  kubectl delete deployment plain -n default
  ```

]

- Put these settings in your Helm charts and Kustomize bases

  (and check them in CI, with the linters later in this section)

???

:EN:- Hardening the pod spec with securityContext
:FR:- Sécuriser la spécification des pods
