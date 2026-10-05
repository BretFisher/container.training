<!-- verified: 2026-10-05 -->
# Policy Management with Kyverno

- Kyverno is a policy engine for Kubernetes

- It has many use cases, including:

  - enforcing or giving warnings about best practices or misconfigurations
    <br/>(e.g. `:latest` images, healthchecks, requests and limits...)

  - tightening security
    <br/>(possibly for multitenant clusters)

  - preventing some modifications
    <br/>(e.g. restricting modifications to some fields, labels...)

  - modifying, generating, cleaning up resources automatically

---

## Examples (validation)

- [Disallow `:latest` tag](https://github.com/kyverno/policies/tree/main/best-practices-vpol/disallow-latest-tag)

- [Disallow secrets in environment variables](https://github.com/kyverno/policies/tree/main/other-vpol/disallow-secrets-from-env-vars)

- [Require that containers drop all capabilities](https://github.com/kyverno/policies/tree/main/best-practices-vpol/require-drop-all)

- [Prevent creation of Deployment, ReplicaSet, etc. without an HPA](https://github.com/kyverno/policies/tree/main/other-vpol/check-hpa-exists)

- [Forbid CPU limits](https://github.com/kyverno/policies/tree/main/other-vpol/forbid-cpu-limits)

- [Check that memory requests are equal to limits](https://github.com/kyverno/policies/tree/main/other-vpol/memory-requests-equal-limits)

- [Require containers to have healthchecks](https://github.com/kyverno/policies/tree/main/best-practices-vpol/require-probes)

---

## Examples (mutation)

- [Automatically add environment variables from a ConfigMap](https://github.com/kyverno/policies/tree/main/other-mpol/add-env-vars-from-cm)

- [Add image as an environment variable](https://github.com/kyverno/policies/tree/main/other-mpol/add-image-as-env-var)

---

## Examples (generation)

- [Automatically create a PDB when a Deployment is created](https://github.com/kyverno/policies/tree/main/other-gpol/create-default-pdb)

- [Automatically create a NetworkPolicy when a Namespace is created](https://github.com/kyverno/policies/tree/main/best-practices-gpol/add-network-policy)

- [Automatically create a ResourceQuota and a LimitRange when a Namespace is created](https://github.com/kyverno/policies/tree/main/best-practices-gpol/add-ns-quota)

---

## Examples (advanced validation)

- [Prevent Ingresses with the same host and path](https://github.com/kyverno/policies/tree/main/other-vpol/unique-ingress-paths)

- [Only allow images with a verified build provenance (SLSA attestation)](https://github.com/kyverno/policies/tree/main/other-ivpol/verify-image-slsa)

---

## More about Kyverno

- Open source (https://github.com/kyverno/kyverno/)

- Compatible with all clusters

  (doesn't require to reconfigure the control plane, enable feature gates...)

- We don't endorse / support it in a particular way, but we think it's cool

- It's not the only solution!

  (see e.g. [OPA Gatekeeper](https://open-policy-agent.github.io/gatekeeper/website/docs/) or [Validating Admission Policies](https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/))

---

## How does it work?

- Kyverno is implemented as a *controller* or *operator*

- It typically runs as a few Deployments on our cluster

- Policies are defined as *custom resources*

- They are implemented with a set of *dynamic admission control webhooks*

- Policy rules are written in [CEL] (Common Expression Language)

  (the same language as Kubernetes `ValidatingAdmissionPolicy`)

[CEL]: https://kubernetes.io/docs/reference/using-api/cel/

---

## Custom resource definitions

- When we install Kyverno, it will register new resource types, including:

  - ValidatingPolicy, MutatingPolicy, GeneratingPolicy, DeletingPolicy
    <br/>(cluster-scope; each one also has a `Namespaced...` version)

  - PolicyReport and ClusterPolicyReport (used in audit mode)

  - UpdateRequest (used internally when generating resources asynchronously)

- ClusterPolicy and Policy (the older, JMESPath-based types) are deprecated since 1.19

- We will be able to do e.g. `kubectl get policyreports --all-namespaces`

  (to see policy violations across all namespaces)

- Policies will be defined in YAML and registered/updated with e.g. `kubectl apply`

---

## Installing Kyverno

The recommended [installation method][install-kyverno] is to use Helm charts.

(It's also possible to install with a single YAML manifest.)

.lab[

- Install Kyverno:
  ```bash
    helm upgrade --install --repo https://kyverno.github.io/kyverno/ \
      --namespace kyverno --create-namespace kyverno kyverno --wait
  ```

]

(`--wait` waits until Kyverno is ready to check our policies.)

[install-kyverno]: https://kyverno.io/docs/installation/installation/

---

## Kyverno policies in a nutshell

- Which resources does it *select?*

  - `matchConstraints`: by API group, version, resource, and operation
    <br/>(and optionally *namespace selector*, *object selector*)

  - `matchConditions`: extra CEL conditions (e.g. "the object has a label")

- Which operation should be done?

  - validate, mutate, or generate (one policy kind for each)

- For validation, whether it should *deny*, *audit*, or *warn* about failures

- Operation details (what exactly to validate, mutate, or generate)

---

## Validating objects

Example: [require resource requests and limits][kyverno-requests-limits].

```yaml
validations:
- expression: >-
    object.spec.containers.all(c,
      c.?resources.?requests.?memory.hasValue() &&
      c.?resources.?requests.?cpu.hasValue() &&
      c.?resources.?limits.?memory.hasValue())
  message: "CPU and memory resource requests and memory limits are required."
```

(`?` makes each field optional: a missing field is a policy failure, not an error.)

(The full policy also checks `initContainers` and `ephemeralContainers`.)

[kyverno-requests-limits]: https://github.com/kyverno/policies/tree/main/best-practices-vpol/require-pod-requests-limits

---

## Optional fields

Example: [disallow `NodePort` Services][kyverno-disallow-nodeports].

```yaml
validations:
- expression: object.spec.?type.orValue('') != 'NodePort'
  message: "Services of type NodePort are not allowed."
```

`?type` means that the field is optional.

`.orValue('')` gives the value to use when the field doesn't exist.

`object.spec.type` alone would cause an error if the field doesn't exist.

[kyverno-disallow-nodeports]: https://github.com/kyverno/policies/tree/main/best-practices-vpol/restrict-node-port

---

## `spec.validationActions`

- `Deny` = reject the request

- `Audit` = don't reject the request, but report the violation in a PolicyReport

  (more on that later)

- `Warn` = don't reject the request, but return a warning in the API response

  (`kubectl` shows it as a `Warning:` line)

- We can combine `Audit` and `Warn`

- To enforce a policy, we need `Deny`

---

## `spec.evaluation`

- Policies have two flags to control when they run

- `evaluation.admission.enabled` = run that policy at admission

  (when an object gets created/updated and validation controllers get invoked)

- `evaluation.background.enabled` = run that policy in the background

  (periodically check if existing objects fit the policy)

- Both are `true` by default

---

## Background checks

- Admission controllers are only invoked when we change an object

- Existing objects are not affected

  (e.g. if we create "invalid" objects *before* installing the policy)

- Kyverno can also run checks in the background, and report violations

  (we'll see later how they are reported)

- `evaluation.background.enabled: true/false` controls that

---

## Loops

Example: [require image tags][kyverno-disallow-latest].

This uses `object`, the object that we're validating.

CEL *macros* like `all()`, `exists()`, `filter()`, `map()` loop over lists.

```yaml
validations:
- expression: "object.spec.containers.all(c, c.image.contains(':'))"
  message: "An image tag is required."
```

Note: again, there should also be a check for `initContainers` and `ephemeralContainers`.

[kyverno-disallow-latest]: https://github.com/kyverno/policies/tree/main/best-practices-vpol/disallow-latest-tag

---

class: extra-details

## Variables

Requiring image tags in all containers can also be done with a *variable*:

```yaml
variables:
- name: allContainers
  expression: >-
    object.spec.containers +
    object.spec.?initContainers.orValue([]) +
    object.spec.?ephemeralContainers.orValue([])
validations:
- expression: "variables.allContainers.all(c, c.image.contains(':'))"
  message: "An image tag is required."
```

---

## `request` and other variables

- CEL expressions have access to a few variables, including:

  `object`: the object being created or modified

  `oldObject`: the object being modified (only for UPDATE)

  `request.operation`: CREATE, UPDATE, DELETE, or CONNECT

  `request.userInfo`: information about the user making the API request

- `object` and `oldObject` are very convenient to block specific *modifications*

  (e.g. making some labels or annotations immutable)

(See [here][kyverno-cel] for details.)

[kyverno-cel]: https://kyverno.io/docs/policy-types/validating-policy/

---

## Generating objects

- Let's review a fairly common use-case...

- When we create a Namespace, we also want to automatically create:

  - a LimitRange (to set default CPU and RAM requests and limits)

  - a ResourceQuota (to limit the resources used by the namespace)

  - a NetworkPolicy (to isolate the namespace)

- We can do that with a Kyverno GeneratingPolicy

---

## Overview

- A GeneratingPolicy has a `generate` section with a CEL expression

- That expression calls `generator.Apply(namespace, [objects])`, with:

  - the Namespace in which to create the objects

  - a list of objects to create

- Each object can be:

  - *either* written in the policy (with `apiVersion`, `kind`, `metadata`, `spec`)

  - *or* a copy of an existing resource (obtained with `resource.Get(...)`)

---

## In practice

- We will use the policy @@LINK[k8s/kyverno-namespace-setup.yaml]

- We need to generate 3 resources, so we define 3 variables in the policy

- Excerpt:
  ```yaml
    generate:
    - expression: >-
        generator.Apply(object.metadata.name,
          [ variables.limitrange, variables.resourcequota, variables.networkpolicy ])
  ```

- Note that we have to specify the Namespace

  (and we get it from the name of the resource being created, i.e. the Namespace)

---

## CEL expressions

- All the fields of the objects are available in CEL expressions

  (when generating, mutating, or validating resources; in `matchConditions`...)

- We can use `object` and `request`, as well as [a few other variables][kyverno-cel]

- We can filter and transform lists, for instance:

  `object.spec.containers.filter(c, c.name == 'worker').map(c, c.image)`

  `(object.spec.containers + object.spec.?initContainers.orValue([])).map(c, c.image)`

- To test policies without a cluster, [install the kyverno CLI][kyverno-cli]

  (then use `kyverno apply policy.yaml --resource object.yaml`)

[kyverno-cli]: https://kyverno.io/docs/kyverno-cli/

---

## Data sources

- It's also possible to access data in Kubernetes ConfigMaps:
  ```yaml
    variables:
    - name: ingressconfig
      expression: >-
        resource.Get("v1", "configmaps", object.metadata.namespace, "ingressconfig")
  ```

- And then use it e.g. in a policy generating or modifying Ingress resources:
  ```yaml
  ...
  host: object.metadata.name + "." + variables.ingressconfig.data.domainsuffix
  ...
  ```

---

## Kubernetes API calls

- It's also possible to access arbitrary Kubernetes resources with `resource.Get`:
  ```yaml
    variables:
    - name: dns
      expression: >-
        resource.Get("v1", "services", "kube-system", "kube-dns").spec.clusterIP
  ```

- And then use that e.g. in a MutatingPolicy:
  ```yaml
    mutations:
    - patchType: ApplyConfiguration
      applyConfiguration:
        expression: >-
          Object{ spec: Object.spec{
            containers: object.spec.containers.map(c, Object.spec.containers{
              name: c.name,
              env: [ Object.spec.containers.env{ name: "DNS", value: variables.dns } ]
            })
          }}
  ```

---

## Lifecycle

- After generated objects have been created, we can change them

  (Kyverno won't automatically revert them)

- Except if we set `evaluation.synchronize.enabled: true`

  (in that case, Kyverno reverts changes, and updates the generated objects
  <br/>when the policy or the copied resource changes)

- This is convenient for e.g. ConfigMaps shared between Namespaces

---

class: extra-details

## Deleting the policy or the trigger

- By default, the generated object and triggering object have independent lifecycles

  (deleting the triggering object doesn't affect the generated object)

- With `evaluation.synchronize.enabled: true`, deleting the triggering object
  <br/>also deletes the generated objects

- With `evaluation.orphanDownstreamOnPolicyDelete.enabled: true`, the generated
  <br/>objects stay when we delete the policy

- See the [GeneratingPolicy documentation][kyverno-gpol] for details

[kyverno-gpol]: https://kyverno.io/docs/policy-types/generating-policy/

---

class: extra-details

## Asynchronous creation

- Kyverno creates resources asynchronously

  (by creating an UpdateRequest resource first)

- This is useful when the resource cannot be created

  (because of permissions or dependency issues)

- Kyverno will periodically loop through the pending UpdateRequests

- Once the resource is created, the UpdateRequest is marked as Completed

  (and then deleted)

---

class: extra-details

## Autogen rules for Pod validating policies

- In Kubernetes, we rarely create Pods directly

  (instead, we create controllers like Deployments, DaemonSets, Jobs, etc)

- As a result, Pod validating policies can be tricky to debug

  (the policy blocks invalid Pods, but doesn't block their controller)

- Kyverno helps us with "autogen rules"

  (when we create a Pod policy, it will automatically create policies on Pod controllers)

- This can be customized with `spec.autogen.podControllers` if needed

  ([see documentation for details][kyverno-autogen])

[kyverno-autogen]: https://kyverno.io/docs/policy-types/validating-policy/

---

## Footprint

- 22 CRDs

- About a dozen webhooks

  (Kyverno adds webhooks when we add policies)

- 6 services, 4 Deployments, 2 ConfigMaps

- Internal resources (UpdateRequest) "parked" in a Namespace

---

## Strengths

- Kyverno is very easy to install

- The setup of the webhooks is fully automated

  (including certificate generation)

- It offers both namespaced and cluster-scope policies

- The policy language is CEL, which is also used by Kubernetes itself

  (e.g. in ValidatingAdmissionPolicy and in CRD validation rules)

- It has pretty good documentation, including many examples

- There is also a CLI tool to test policies without a cluster

- It continues to evolve and gain new features

???

:EN:- Policy Management with Kyverno
:FR:- Gestion de *policies* avec Kyverno
