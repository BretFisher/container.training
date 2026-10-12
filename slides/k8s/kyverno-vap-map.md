<!-- verified: 2026-10-09 -->
# Kyverno + VAP + MAP

- Kyverno and the built-in admission policies are not competitors

- They use the same language: CEL

- Kyverno can work *with* VAP and MAP in 4 ways:

  - its policy types are *supersets* of VAP and MAP

  - it can *generate* native VAP and MAP objects from its policies

  - it can *report* on native VAPs (for objects that already exist)

  - its CLI can *test* native VAP and MAP files without a cluster

- Goal: enforce in the API server when we can, use Kyverno when we must

---

## Same language, more features

- A Kyverno ValidatingPolicy is a superset of a ValidatingAdmissionPolicy

- A Kyverno MutatingPolicy is a superset of a MutatingAdmissionPolicy

- Same fields: `matchConstraints`, `matchConditions`, `variables`, CEL expressions

- Kyverno adds:

  - more CEL libraries (e.g. `resource.Get()`, `http.Get()`)

  - background scans and PolicyReports

  - automatic bindings and PolicyExceptions

  - rules for Pods that also apply to Deployments, Jobs...

---

## Generating native policies

- Add this to a Kyverno ValidatingPolicy:
  ```yaml
  spec:
    autogen:
      validatingAdmissionPolicy:
        enabled: true
  ```

  (or `mutatingAdmissionPolicy` in a MutatingPolicy)

- Kyverno creates a native policy and its binding

  (named `vpol-<name>` or `mpol-<name>`)

- The API server runs the native policy *in-process*

- Kyverno does not get a webhook call for that policy

---

## When Kyverno cannot generate a native policy

- Native policies only have the basic CEL libraries

- If our policy uses a Kyverno-only feature, Kyverno keeps it in its webhook

  (e.g. `resource.Get()`, `http.Get()`, image verification)

- Other limits:

  - not with `spec.autogen.podControllers`

  - for MAP: no `variables` in `matchConditions`

- Check `status.generated` in the Kyverno policy:

  `true` = a native policy exists; `false` = Kyverno's webhook runs it

---

## Reports and tests for native policies

- Native VAPs don't check objects that already exist

- Kyverno's reports controller can scan them and write PolicyReports

  (flag `--validatingAdmissionPolicyReports`; it is off by default)

- The `kyverno` CLI can test native VAP and MAP files offline:
  ```bash
  kyverno apply my-vap.yaml --resource my-service.yaml
  ```

- We can test policies in CI before they reach a cluster

---

## Advantages and disadvantages

| | Generate native VAP/MAP | Kyverno webhook only |
| --- | --- | --- |
| Speed | No network call | Network call per request |
| Kyverno down | Policy still runs | Requests blocked or skipped |
| CEL libraries | Basic only | Extended |
| Existing objects | Only with report flag | Background scans |
| Debugging | 2 objects to check | 1 object |

- Generated policies are best for simple, critical rules

- Keep lookups, image checks, and generation in Kyverno

---

## Lab: a ValidatingPolicy that becomes a VAP

- We will block Services of type NodePort

- We write a Kyverno ValidatingPolicy with `autogen` enabled

.small[
```yaml
@@INCLUDE[k8s/kyverno-vap-nodeport.yaml]
```
]

---

## Load the policy

.lab[

- Load the policy:
  ```bash
  kubectl apply -f ~/container.training/k8s/kyverno-vap-nodeport.yaml
  ```

<!-- ```hide kubectl wait --for=create validatingadmissionpolicybinding/vpol-disallow-nodeport-binding --timeout=60s``` -->

- Check that Kyverno generated a native policy and binding:
  ```bash
  kubectl get validatingadmissionpolicies,validatingadmissionpolicybindings
  ```

- Check the status of the Kyverno policy:
  ```bash
  kubectl get validatingpolicy disallow-nodeport -o jsonpath={.status.generated}
  ```

]

The status should be `true`.

---

## Test the policy

.lab[

- Try to create a NodePort Service:
  ```bash
  kubectl create service nodeport test-nodeport --tcp=80
  ```

<!-- ```expect-fail``` -->

]

- Look at the error message:

  `ValidatingAdmissionPolicy 'vpol-disallow-nodeport' ... denied request`

- The API server rejected the request, not Kyverno

---

## Lab: a MutatingPolicy that becomes a MAP

- We will add the label `team=platform` to each new ConfigMap

.small[
```yaml
@@INCLUDE[k8s/kyverno-map-team-label.yaml]
```
]

---

## Load and test the policy

.lab[

- Load the policy:
  ```bash
  kubectl apply -f ~/container.training/k8s/kyverno-map-team-label.yaml
  ```

<!-- ```hide kubectl wait --for=create mutatingadmissionpolicybinding/mpol-add-team-label-binding --timeout=60s``` -->

- Check that Kyverno generated a native policy and binding:
  ```bash
  kubectl get mutatingadmissionpolicies,mutatingadmissionpolicybindings
  ```

- Create a ConfigMap and look at its labels:
  ```bash
  kubectl create configmap test-team-label --from-literal=color=blue
  kubectl get configmap test-team-label --show-labels
  ```

]

The ConfigMap has the label `team=platform`.

---

## Stop Kyverno

- The API server runs the native policies

- So they should still work when Kyverno's admission controller is down

.lab[

- Stop the Kyverno admission controller:
  ```bash
  kubectl scale deployment -n kyverno kyverno-admission-controller --replicas=0
  kubectl wait --for=delete pod -n kyverno \
          -l app.kubernetes.io/component=admission-controller
  ```

- Try to create a NodePort Service again:
  ```bash
  kubectl create service nodeport test-nodeport --tcp=80
  ```

<!-- ```expect-fail``` -->

]

---

## Restart Kyverno

.lab[

- Create another ConfigMap and look at its labels:
  ```bash
  kubectl create configmap test-team-label-2 --from-literal=color=red
  kubectl get configmap test-team-label-2 --show-labels
  ```

]

- Both policies work without Kyverno, because the API server runs them

.lab[

- Start the Kyverno admission controller again:
  ```bash
  kubectl scale deployment -n kyverno kyverno-admission-controller --replicas=1
  kubectl rollout status deployment -n kyverno kyverno-admission-controller
  ```

]

---

## Test a native policy with the CLI

.lab[

- Export the generated VAP:
  ```bash
  kubectl get validatingadmissionpolicy vpol-disallow-nodeport -o yaml > vap.yaml
  ```

- Create a test Service manifest (without sending it to the cluster):
  ```bash
  kubectl create service nodeport web --tcp=80 --dry-run=client -o yaml > svc.yaml
  ```

- Test the native VAP offline:
  ```bash
  kyverno apply vap.yaml --resource svc.yaml
  ```

<!-- ```expect-fail``` -->

]

The result is `fail: 1`: the policy would reject this Service.

---

## Clean up

.lab[

- Delete the Kyverno policies:
  ```bash
  kubectl delete validatingpolicy disallow-nodeport
  kubectl delete mutatingpolicy add-team-label
  ```

<!-- ```hide
kubectl wait --for=delete validatingadmissionpolicy/vpol-disallow-nodeport --timeout=60s
kubectl wait --for=delete mutatingadmissionpolicy/mpol-add-team-label --timeout=60s
``` -->

- Check that Kyverno also deleted the native policies:
  ```bash
  kubectl get validatingadmissionpolicies,mutatingadmissionpolicies
  ```

- Delete the test objects and files:
  ```bash
  kubectl delete configmap test-team-label test-team-label-2
  rm vap.yaml svc.yaml
  ```

]

---

## Summary

- Write policies once, in Kyverno's format

- Let Kyverno generate native VAP and MAP for simple rules

  (fast, and they work when Kyverno is down)

- Keep advanced rules in Kyverno's webhook

  (lookups, image verification, generation, cleanup)

- Use Kyverno for reports and CI tests of all policies

???

:EN:- Kyverno with ValidatingAdmissionPolicy and MutatingAdmissionPolicy
:FR:- Kyverno avec ValidatingAdmissionPolicy et MutatingAdmissionPolicy
