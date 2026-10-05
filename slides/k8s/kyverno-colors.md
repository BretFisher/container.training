<!-- verified: 2026-10-05 -->
## Painting pods

- As an example, we'll implement a policy regarding "Pod color"

- The color of a Pod is the value of the label `color`

- Example: `kubectl label pod hello color=yellow` to paint a Pod in yellow

- We want to implement the following policies:

  - color is optional (i.e. the label is not required)

  - if color is set, it *must* be `red`, `green`, or `blue`

  - once the color has been set, it cannot be changed

  - once the color has been set, it cannot be removed

---

## Immutable primary colors, take 1

- First, we will add a policy to block forbidden colors

  (i.e. only allow `red`, `green`, or `blue`)

- One possible approach:

  - *match* all pods

  - *validate* with a CEL expression: if the `color` label exists,
    <br/>it must be `red`, `green`, or `blue`

- We could also use an *object selector* to *match* only the pods
  <br/>with a `color` label that is not `red`, `green`, or `blue`

---

.small[
```yaml
@@INCLUDE[k8s/kyverno-pod-color-1.yaml]
```
]

---

## Testing without the policy

- First, let's create a pod with an "invalid" label

  (while we still can!)

- We will use this later

.lab[

- Create a pod:
  ```bash
  kubectl run test-color-0 --image=nginx
  ```

- Apply a color label:
  ```bash
  kubectl label pod test-color-0 color=purple
  ```

]

---

## Load and try the policy

.lab[

- Load the policy:
  ```bash
  kubectl apply -f ~/container.training/k8s/kyverno-pod-color-1.yaml
  ```

- Create a pod:
  ```bash
  kubectl run test-color-1 --image=nginx
  ```

- Try to apply a few color labels:
  ```bash
  kubectl label pod test-color-1 color=purple
  kubectl label pod test-color-1 color=red
  kubectl label pod test-color-1 color-
  ```

<!-- ```expect-fail``` -->

]

---

## Immutable primary colors, take 2

- Next rule: once a `color` label has been added, it cannot be changed

  (i.e. if `color=red`, we can't change it to `color=blue`)

- Our approach:

  - *match* all pod updates

  - add *matchConditions* selecting pods that have a `color` label
    <br/>
    (both in their "before" and "after" states)

  - *deny* these pods if their `color` label has changed

- Again, other approaches are possible!

---

.small[
```yaml
@@INCLUDE[k8s/kyverno-pod-color-2.yaml]
```
]

---

## Comparing "old" and "new"

- CEL expressions have access to the object before and after the request

- For UPDATE requests, we can access:

  `oldObject` → the object as it is right now (before the request)

  `object` → the object with the changes made by the request

---

## Missing labels

- We can access the `color` label through `object.metadata.labels.color`

- If we reference a label (or any field) that doesn't exist, the expression fails

  (with an error similar to `no such key: color`)

- By default (`failurePolicy: Fail`), an error rejects the request!

- To work around that, check that the key exists first, with [optional fields][cel-optional]:

  `'color' in object.metadata.?labels.orValue({})`

[cel-optional]: https://kubernetes.io/docs/reference/using-api/cel/

---

## Load and try the policy

.lab[

- Load the policy:
  ```bash
  kubectl apply -f ~/container.training/k8s/kyverno-pod-color-2.yaml
  ```

- Create a pod:
  ```bash
  kubectl run test-color-2 --image=nginx
  ```

- Try to apply a few color labels:
  ```bash
  kubectl label pod test-color-2 color=purple
  kubectl label pod test-color-2 color=red
  kubectl label pod test-color-2 color=blue --overwrite
  ```

<!-- ```expect-fail``` -->

]

---

## Immutable primary colors, take 3

- Last rule: once a `color` label has been added, it cannot be removed

- Our approach is to match all pod updates that:

  - *had* a `color` label (in `oldObject`)

- And *deny* them if they *don't have* a `color` label anymore (in `object`)

- Again, other approaches are possible!

---

.small[
```yaml
@@INCLUDE[k8s/kyverno-pod-color-3.yaml]
```
]

---

## Load and try the policy

.lab[

- Load the policy:
  ```bash
  kubectl apply -f ~/container.training/k8s/kyverno-pod-color-3.yaml
  ```

- Create a pod:
  ```bash
  kubectl run test-color-3 --image=nginx
  ```

- Try to apply a few color labels:
  ```bash
  kubectl label pod test-color-3 color=purple
  kubectl label pod test-color-3 color=red
  kubectl label pod test-color-3 color-
  ```

<!-- ```expect-fail``` -->

]

---

## Background checks

- What about the `test-color-0` pod that we created initially?

  (remember: we did set `color=purple`)

- We can see the infringing Pod in a PolicyReport

.lab[

- Check that the pod still an "invalid" color:
  ```bash
  kubectl get pods -L color
  ```

- List PolicyReports:
  ```bash
  kubectl get policyreports
  kubectl get polr
  ```

]

(Sometimes it takes a little while for the infringement to show up, though.)
