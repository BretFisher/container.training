# Falco and Talon lab research

Research date: 2026-10-07. Target: kubeadm. Status: draft; live tests remain paused.

## Verified configuration

Falco sends JSON alerts directly to Talon over HTTP. No Falcosidekick deployment is required. Use the root endpoint, for example `http://falco-talon.falco.svc.cluster.local:2803/`. Current Falco configuration uses snake_case:

```yaml
falco:
  json_output: true
  json_include_output_property: true
  json_include_output_fields_property: true
  http_output:
    enabled: true
    url: http://falco-talon.falco.svc.cluster.local:2803/
```

[Falco output channels](https://falco.org/docs/concepts/outputs/channels/) describe JSON output and HTTP. [Talon architecture](https://github.com/falcosecurity/falco-talon) accepts events from Falco directly. The [older introduction](https://falco.org/blog/falco-talon-v0-1-0/) shows the root URL but uses obsolete camelCase Falco keys; use current chart keys.

The Falco container plugin obtains basic Kubernetes namespace and pod names from runtime metadata. `collectors.containerEngine.enabled: true` is required for this approach; the runtime socket must be accessible. `collectors.kubernetes.enabled: false` still supplies pod ID, name, namespace, and labels. A separate k8s-metacollector is not required for these fields. Verify actual metadata before enabling response. [Falco 9.2.0 values](https://github.com/falcosecurity/charts/blob/falco-9.2.0/charts/falco/values.yaml).

Use a custom rule matching successful process execution, namespace `falco-demo`, and `proc.name in (sudo, apt, apt-get, curl)`. Include `%k8s.ns.name` and `%k8s.pod.name` explicitly in the output: Talon needs these JSON output fields to select the pod. Include command and UID for student inspection. Set `falco.rule_matching: all` when retaining default rules, so another matching rule cannot suppress the demo alert. This detects execution of these names, not successful privilege escalation, package installation, or data transfer. [Falco chart configuration](https://github.com/falcosecurity/charts/blob/master/charts/falco/README.md).

## Talon rule

The rule below shows the verified rules schema. It is a proposal, not a tested file. Falco's rule name must be exactly `Demo prohibited command` for this example.

```yaml
- rule: Terminate demo pod
  description: Respond to the demo command alert only.
  dry_run: "true"
  match:
    rules:
      - Demo prohibited command
    output_fields:
      - k8s.ns.name=falco-demo
  actions:
    - action: Delete the demo pod
      actionner: kubernetes:terminate
      parameters:
        ignore_daemonsets: true
        ignore_statefulsets: true
        ignore_standalone_pods: false
        grace_period_seconds: 0
```

`dry_run` belongs to the Talon rule, not the action parameters. Quoted `"true"` matches its string schema; use `"false"` only for the later response phase. Rule matching compares exact Falco rule names and checks output fields. [Talon v0.3.0 rule parser](https://github.com/falcosecurity/falco-talon/blob/v0.3.0/internal/rules/rules.go).

`kubernetes:terminate` requires `k8s.ns.name` and `k8s.pod.name`. It deletes the pod through the Kubernetes API. It defaults to ignoring standalone pods, so explicitly set `ignore_standalone_pods: false`. A controller can replace a deleted managed pod; standalone pods make the response easier to observe. Namespace-scoped pod get/list/delete permissions are the core permissions for this case. [Terminate implementation](https://github.com/falcosecurity/falco-talon/blob/main/actionners/kubernetes/terminate/terminate.go).

## Helm values and remaining checks

The separate Talon chart has these documented values:

```yaml
replicaCount: 1
rbac:
  serviceAccount:
    create: true
    name: falco-talon
config:
  defaultNotifiers: []
  watchRules: true
  printAllEvents: true
  deduplication:
    leaderElection: false
  rulesOverride: |
    # Put the complete demo rule here.
```

This is a values shape reference, not a complete install configuration. The chart has broad default RBAC verb lists. The exact method to suppress its ClusterRole and ClusterRoleBinding was not verified because their templates could not be read. Do not assume that `rbac.create: false` exists. Verify rendered resources before using the proposed namespace Role and RoleBinding. [Talon values](https://github.com/falcosecurity/charts/blob/master/charts/falco-talon/values.yaml).

`config.rulesOverride` appends content after the packaged rules; it does not replace the file. The packaged file checked here defines two action templates, without matching rules. Use a unique demo action name to avoid a template collision. WatchRules permits reload, but ConfigMap updates and loaded configuration must still be checked. [ConfigMap template](https://github.com/falcosecurity/charts/blob/master/charts/falco-talon/templates/configmap.yaml), [Packaged rules](https://github.com/falcosecurity/charts/blob/master/charts/falco-talon/rules.yaml), [Helm documentation](https://falco-talon.github.io/docs/installation_usage/helm/).

Version evidence is inconsistent across cached official pages: Falco chart metadata reports 9.2.0 with app 0.45.0; current Talon GitHub Chart.yaml reports chart 0.5.0 with app 0.3.0, while its raw cached URL reports 0.4.0. Falco's dependency constraint is 0.4.*. Use separate releases, and confirm the packaged repository index and version-specific chart values before pinning the walkthrough. The repository index could not be read through the web tool. [Falco Chart.yaml](https://github.com/falcosecurity/charts/blob/master/charts/falco/Chart.yaml), [Talon Chart.yaml](https://github.com/falcosecurity/charts/blob/master/charts/falco-talon/Chart.yaml).

## Proposed walkthrough

Prepare three standalone pods before loading the custom rule. Install the demo commands in their startup phase, then wait until all commands are available. Load Falco and Talon rules. In dry-run mode, execute harmless version queries and confirm alerts, exact rule match, namespace, and pod name. Then enable response and repeat one query per pod. Observe Falco's event, Talon's response, and pod deletion. Each deleted pod must be recreated before a repeat. The process can run before the asynchronous deletion arrives; this is response, not syscall prevention.

Pending live checks: kernel/driver support, runtime socket and metadata, installed chart pins, rendered namespace-only RBAC, dry-run behavior, rule reload, deterministic alerts, direct HTTP delivery, and pod deletion. No installation or cluster commands were run during this research.

## Static package verification after research

On 2026-10-07, the official [packaged repository index](https://falcosecurity.github.io/charts/index.yaml)
confirmed Falco 9.2.0 and Talon 0.5.0. Both released archives were downloaded
and rendered locally with the existing Helm CLI, without installing them.
Empty documented RBAC lists render Talon with a ClusterRole containing no
grants. The packaged response file has two reusable action templates and our
one matching rule. The chart uses `default true` for leader election, so a
boolean false is overwritten; string `"false"` renders the intended YAML false.
Its rules checksum changes the Deployment template on a rules update. These
checks resolve the earlier packaged-version and chart-RBAC uncertainties.
Actual startup, namespace authorization, metadata, detection, deletion, and
cleanup still require the student kubeadm lab.
