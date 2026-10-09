# Restricting Pod Permissions

- By default, our pods and containers can do *everything*

  (including taking over the entire cluster)

- We are going to show an example of a malicious pod

  (which will give us root access to the whole cluster)

- Then we will explain how to avoid this with admission control

  (PodSecurityAdmission, ValidatingAdmissionPolicy, or an external policy engine)

---

## Setting up a namespace

- For simplicity, let's work in a separate namespace

- Let's create a new namespace called "green"

.lab[

- Create the "green" namespace:
  ```bash
  kubectl create namespace green
  ```

- Change to that namespace:
  ```bash
  kns green
  ```

]

---

## Creating a basic Deployment

- Just to check that everything works correctly, deploy NGINX

.lab[

- Create a Deployment using the official NGINX image:
  ```bash
  kubectl create deployment web --image=nginx
  ```

- Confirm that the Deployment, ReplicaSet, and Pod exist, and that the Pod is running:
  ```bash
  kubectl get all
  ```

]

---

## One example of malicious pods

- We will now show an escalation technique in action

- We will deploy a DaemonSet that adds our SSH key to the root account

  (on *each* node of the cluster)

- The Pods of the DaemonSet will do so by mounting `/root` from the host

.lab[

- Check the file `k8s/hacktheplanet.yaml` with a text editor:
  ```bash
  vim ~/container.training/k8s/hacktheplanet.yaml
  ```

<!--
```wait DaemonSet```
```keys :q!```
```key ^J```
-->

- If you would like, change the SSH key (by changing the GitHub user name)

]

---

## Deploying the malicious pods

- Let's deploy our "exploit"!

.lab[

- Create the DaemonSet:
  ```bash
  kubectl create -f ~/container.training/k8s/hacktheplanet.yaml
  ```

- Check that the pods are running:
  ```bash
  kubectl get pods
  ```

- Confirm that the SSH key was added to the node's root account:
  ```bash
  sudo cat /root/.ssh/authorized_keys
  ```

]

---

## Mitigations

- This can be avoided with *admission control*

- Admission control = filter for (write) API requests

- Admission control can use:

  - plugins (compiled in API server; enabled/disabled by reconfiguration)

  - webhooks (3rd party controllers, registered dynamically)

- Admission control has many other uses

  (enforcing quotas, adding ServiceAccounts or Pod labels automatically, etc.)

---

## Admission plugins (Built-in to API Server)

- [PodSecurityAdmission](https://kubernetes.io/docs/concepts/security/pod-security-admission/)

  - use pre-defined policies (privileged, baseline, restricted)

  - label namespaces to indicate which policies they can use

  - optionally, define default rules (in the absence of labels)

- [ValidatingAdmissionPolicy](https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/)

  - Validate resouce spec's against CEL policies before they are deployed

- [Mutating Admission Policies](https://kubernetes.io/docs/reference/access-authn-authz/mutating-admission-policy/)

  - Change resources before they hit VAP

.footnote[PodSecurityPolicy (PSP) was removed in Kubernetes 1.25; PSA replaced it.]

---

## Dynamic admission (3rd party policy engines)

- Leverage the API servers `ValidatingWebhookConfigurations`

  (to register a validating webhook)

- Examples:

  [Kubewarden](https://www.kubewarden.io/)

  [Kyverno](https://kyverno.io/policies/)

  [OPA Gatekeeper](https://github.com/open-policy-agent/gatekeeper)

- These policy engines also run a-sync controllers

  (background audit and reports for resources that already exist)

---

## Validating Admission Policies (VAP)

- Evaluated in the API server

  (don't require an external server; don't add network latency)

- Written in CEL (Common Expression Language)

- Stable in Kubernetes 1.30

- More limited than plugin validators (Kyverno, OPA Gatekeeper...)

- Can extend Pod Security Admission (you *could* use both together)

- Check [the documentation][vapdoc] for examples

[vapdoc]: https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/

---

## Mutating Admission Policies (MAP)

- Same model as VAP: CEL rules, evaluated in the API server, no webhook

- Stable since Kubernetes 1.36

- Two objects: `MutatingAdmissionPolicy` + `MutatingAdmissionPolicyBinding`

- Difference with VAP:

  - VAP *checks* an object (deny, warn, or audit)

  - MAP *changes* an object (e.g. add a label, set a default value)

  - MAP runs first; then VAP checks the changed object

- More limited than plugin mutators (Kyverno, OPA Gatekeeper...)

- Check [the documentation][mapdoc] for examples

[mapdoc]: https://kubernetes.io/docs/reference/access-authn-authz/mutating-admission-policy/

---

## Built-in vs. webhook admission

| | Built-in (PSA, VAP, MAP) | Webhooks (Kyverno...) |
| --- | --- | --- |
| Runs in | API server | Separate controller |
| Install | Nothing | Deploy and upgrade it separately |
| Latency | No network call | Network call per request |
| Failure | Fails with API server | Blocks or skips requests based on config |
| Rules | PSA levels or CEL | Any logic; external data |
| Existing in-cluster resources | Not checked | Audit controllers report |

- You can use just one, or combine them

- Example: Use PSA for basic pod protection and Kyverno for everything else

---

## What policy engines add

| Ability | PSA, VAP, MAP | Kyverno | Gatekeeper |
| --- | --- | --- | --- |
| Check or change the request | ✅ | ✅ | ✅ |
| Read other objects or APIs | Params, Namespace | ✅ | ✅ |
| Audit existing objects | ❌ | ✅ | ✅ |
| Create other resources | ❌ | ✅ | ❌ |
| Delete resources by rule | ❌ | ✅ | ❌ |
| Verify image signatures | ❌ | ✅ | With Ratify |
| Test policies with a CLI | `kyverno` | `kyverno` | `gator` |

- PSA checks only Pods, with 3 fixed levels

- VAP and MAP see the request, its Namespace, and one params object

---

## Comparing the policy engines

| | Kyverno | OPA Gatekeeper | Kubewarden |
| --- | --- | --- | --- |
| Policy language | YAML + CEL | Rego | WebAssembly (Rust, Go...), also Rego and CEL |
| Policy format | Kubernetes resource | ConstraintTemplate + Constraint | Wasm module in an OCI registry |
| CLI for tests | `kyverno` | `gator` | `kwctl` |
| CNCF maturity | Graduated (2026) | Graduated (OPA, 2021) | Sandbox (2022) |
| GitHub stars (Oct. 2026) | 8,200 | 4,300 | 240 |

- All three can change requests and audit existing objects

- Gatekeeper runs the policy add-ons of GKE (Policy Controller) and AKS (Azure Policy)

- Kubewarden: a policy is a program; build, sign, and ship it like an image

---

## Acronym salad

- PSA = Pod Security Admission

  (an admission plugin called PodSecurity, enforcing PSS)

- PSS = Pod Security Standards

  (a set of 3 policies: privileged, baseline, restricted)

- VAP = ValidatingAdmissionPolicy (CEL rules that accept or reject objects)

- MAP = MutatingAdmissionPolicy (CEL rules that change objects)

- OPA = Open Policy Agent (policy engine; Gatekeeper runs it as a webhook)

.footnote[Content that mentions PSP is out of date: Kubernetes 1.25 (August 2022) removed it.]

???

:EN:- Mechanisms to prevent pod privilege escalation
:FR:- Les mécanismes pour limiter les privilèges des pods
