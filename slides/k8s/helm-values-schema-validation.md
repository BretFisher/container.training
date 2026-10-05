<!-- verified: 2026-10-05 -->
# Helm values schema validation

- A typo such as `imagetag` can be ignored if templates do not use it

- A wrong type such as `image=redis` can cause a template error

- `values.schema.json` checks the merged values before templates render

- Helm uses the schema with `lint`, `template`, `install`, and `upgrade`

- The schema is optional; put it beside `Chart.yaml` and `values.yaml`

---

## Start with a small chart

- This lab works without either optional chart-authoring chapter

.lab[

- Copy the example, inspect its defaults, and validate them:
  ```bash
  cp -R ~/container.training/k8s/helm-labs/schema-check .
  cat schema-check/values.yaml
  cat schema-check/values.schema.json
  helm lint ./schema-check
  helm template valid ./schema-check > schema-rendered.yaml
  ```

]

Check that defaults pass before you test invalid overrides.

---

## Schema rules

- The example uses JSON Schema draft 7

- `type` checks objects, strings, and integers

- `required` lists required keys; `minimum` limits replica count

- `enum` limits `image.pullPolicy` to the three Kubernetes choices

- `additionalProperties: false` rejects unknown keys at **each** object level

- The root lists all keys in this chart's defaults

[JSON Schema in charts](https://helm.sh/docs/topics/charts/#schema-files)

---

## Reject invalid values

- These client dry runs validate values without creating a release

.lab[

- Try an invalid pull policy:
  ```bash
  helm install broken ./schema-check --dry-run=client \
    --set image.pullPolicy=ShallNotPass
  ```
<!-- ```expect-fail``` -->

- Try a string where the chart requires an object:
  ```bash
  helm install wrong-type ./schema-check --dry-run=client \
    --set image=redis
  ```
<!-- ```expect-fail``` -->

]

Both commands fail schema validation.

---

## Reject unknown keys

.lab[

- Test an unknown key at the root:
  ```bash
  helm install typo ./schema-check --dry-run=client \
    --set imagetag=v1.0
  ```
<!-- ```expect-fail``` -->

- Test an unknown nested key:
  ```bash
  helm install nested-typo ./schema-check --dry-run=client \
    --set image.hello=world
  ```
<!-- ```expect-fail``` -->

]

Both fail because the schema rejects extra keys at both levels.

---

## Three separate validation layers

- **Values schema:** does the input match the chart's declared settings?

- **Kubernetes validation:** are the rendered resources valid API objects?

- **Cluster policy:** are these resources allowed in this cluster?

- This example's repository pattern checks a name format only

- It does not prove that an image is trusted or secure

- Do not use `--skip-schema-validation` as the normal fix for invalid values

???


:EN:- Helm schema validation
:FR:- Validation de schema Helm
