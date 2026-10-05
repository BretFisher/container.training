<!-- verified: 2026-10-05 -->
# Helm chart format

- What exactly is a chart?

- What's in it?

- What would be involved in creating a chart?

  (we will create a small chart in the next lab)

---

## What is a chart

- A chart is a set of files

- Some of these files are mandatory for the chart to be viable

  (more on that later)

- These files are typically packed in a tarball

- Archives can be published in HTTP chart repositories or OCI registries

- We can install from a repo, from a local tarball, or an unpacked tarball

  (the latter option is preferred when developing a chart)

---

## What's in a chart

- `Chart.yaml` is required; it contains chart metadata

- Application charts usually also have:

  - `templates/`: Kubernetes manifests and helper templates

  - `values.yaml`: default settings

- A chart can contain dependencies without its own resource templates

- Let's look at a simple chart for a basic demo app

---

## Downloading a chart

- OCI charts do not need `helm repo add`

.lab[

- Download and unpack the pinned chart:
  ```bash
  helm pull oci://ghcr.io/securecodebox/helm/juice-shop \
    --version 5.9.0 --untar
  ```

]

The unpacked chart is in `juice-shop/`. Without `--untar`, Helm saves a `.tgz`.

---

## Four different versions

| Field | Meaning | Example |
|---|---|---|
| Helm version | Version of the CLI | `4.3.0` |
| `apiVersion` | Chart metadata format | `v2` |
| `version` | Chart package version | `5.9.0` |
| `appVersion` | Application version metadata | `v20.2.0` |

- `appVersion` does not set an image tag unless a template uses it

- Use stable `v2` charts for this workshop

---

## Looking at the chart's content

- Let's look at the files and directories in the `juice-shop` chart

.lab[

- Display the tree structure of the chart we just downloaded:
  ```bash
  find juice-shop -type f
  ```

]

We see the components mentioned above: `Chart.yaml`, `templates/`, `values.yaml`.

---

## Templates

- The `templates/` directory contains YAML manifests for Kubernetes resources

  (Deployments, Services, etc.)

- These manifests can contain template tags

  (using the standard Go template library)

.lab[

- Look at the template file for the Service resource:
  ```bash
  cat juice-shop/templates/service.yaml
  ```

]

---

## Analyzing the template file

- Tags are identified by `{{ ... }}`

- `{{ include "x.y" . }}` expands a [named template](https://helm.sh/docs/chart_template_guide/named_templates/#declaring-and-using-templates-with-define-and-template)

  (previously defined with `{{ define "x.y" }}...stuff...{{ end }}`; Helm prefers `include` over `template`)

- The `.` in `{{ include "x.y" . }}` is the *context* for that named template

  (so that the named template block can access variables from the local context)

- `{{ .Release.xyz }}` refers to [built-in variables](https://helm.sh/docs/chart_template_guide/builtin_objects/) initialized by Helm

  (release name, namespace, revision, and install or upgrade operation)

- `{{ .Chart.Version }}` reads chart metadata

- `{{ .Values.xyz }}` refers to tunable/settable [values](https://helm.sh/docs/chart_template_guide/values_files/)

  (more on that in a minute)

---

## Values

- A chart can provide a
  [values file](https://helm.sh/docs/chart_template_guide/values_files/)

- It's a YAML file containing a set of default parameters for the chart

- The values can be accessed in templates with e.g. `{{ .Values.x.y }}`

  (corresponding to field `y` in map `x` in the values file)

- The values can be set or overridden when installing or upgrading a chart:

  - with `--set x.y=z` (can be used multiple times to set multiple values)

  - with `--values some-yaml-file.yaml` (set a bunch of values from a file)

- Charts following best practices will have values following specific patterns

  (e.g. having a `service` map allowing to set `service.type` etc.)

---

## Other useful tags

- `{{ if x }} y {{ end }}` allows to include `y` if `x` evaluates to `true`

  (can be used for e.g. healthchecks, annotations, or even an entire resource)

- `{{ range x }} y {{ end }}` iterates over `x`, evaluating `y` each time

  (the elements of `x` are assigned to `.` in the range scope)

- `{{- x }}`/`{{ x -}}` will remove whitespace on the left/right

- Most [Sprig](https://masterminds.github.io/sprig/) functions, with Helm additions:

  `lower` `upper` `quote` `trim` `default` `b64enc` `b64dec` `sha256sum` `indent` `toYaml` ...

---

## Pipelines

- `{{ quote blah }}` can also be expressed as `{{ blah | quote }}`

- With multiple arguments, `{{ x y z }}` can be expressed as `{{ z | x y }}`)

- Example: `{{ .Values.annotations | toYaml | indent 4 }}`

  - transforms the map under `annotations` into a YAML string

  - indents it with 4 spaces (to match the surrounding context)

- Pipelines are not specific to Helm, but a feature of Go templates

  (check the [Go text/template documentation](https://pkg.go.dev/text/template) for more details and examples)

---

## README and NOTES.txt

- At the top-level of the chart, it's a good idea to have a README

- It will be viewable with e.g. `helm show readme oci://...`

- In the `templates/` directory, we can also have a `NOTES.txt` file

- When the template is installed (or upgraded), `NOTES.txt` is processed too

  (i.e. its `{{ ... }}` tags are evaluated)

- It gets displayed after the install or upgrade

- It's a great place to generate messages to tell the user:

  - how to connect to the release they just deployed

  - which resources and endpoints the release creates

- Keep passwords out of notes and shared terminal output

---

## Additional files

- We can place arbitrary files in the chart (outside of the `templates/` directory)

- They can be accessed in templates with `.Files`

- They can be transformed into ConfigMaps or Secrets with `AsConfig` and `AsSecrets`

  (see [this example](https://helm.sh/docs/chart_template_guide/accessing_files/#configmap-and-secrets-utility-functions) in the Helm docs)

---

## Hooks and tests

- We can define *hooks* in our templates

- Hooks are resources annotated with `"helm.sh/hook": NAME-OF-HOOK`

- Hook names include `pre-install`, `post-install`, `test`, [and much more](https://helm.sh/docs/topics/charts_hooks/#the-available-hooks)

- The resources defined in hooks are loaded at a specific time

- Hook execution is *synchronous*

  (for a hook Job or Pod, Helm waits for successful completion)

- This can be used for database migrations, backups, notifications, smoke tests ...

- Hooks named `test` are executed only when running `helm test RELEASE-NAME`

???

:EN:- Helm charts format
:FR:- Le format des *Helm charts*
