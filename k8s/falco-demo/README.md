# Falco and Talon workshop fixtures

The complete student walkthrough is in [`slides/k8s/falco.md`](../../slides/k8s/falco.md).
It includes every setup, install, trigger, inspection, response, and cleanup
command in teaching order. Students apply the existing files; they do not
write policies or install native Falco or Talon binaries.

The workshop chapter remains commented out. No live lab test has run.

## Files and architecture

- `pods.yaml`: three standalone Ubuntu pods, pinned by image digest. Startup
  installs sudo and curl; readiness waits for package setup. Prepare them
  before loading the detection rule so bootstrap apt commands do not trigger it.
- `falco-values.yaml`: modern eBPF driver, container metadata, all-rule matching,
  one sudo/apt/apt-get/curl rule scoped to `falco-demo`, JSON and direct HTTP output.
- `talon-values.yaml`: one replica, no default resource grants or notifiers,
  disabled leader election, and logging for inspection.
- `talon-rules.yaml`: exact rule-name and namespace match, dry-run initially,
  then pod termination. The slides change a copy in `/tmp`; this file stays safe
  for the next exercise.
- `talon-rbac.yaml`: pod get/list/delete and ReplicaSet get in `falco-demo` only.

Falco observes runtime activity. Talon deletes a pod after an alert arrives.
The program can finish before deletion; this does not prevent its execution.
Standalone pods make deletion visible without a controller replacing them.

## Static rendering

Existing Helm is required. Run from the repository root:

```sh
make -C k8s/falco-demo render
```

This downloads and renders the pinned charts into `/tmp/falco-demo-render/`.
It does not install a release or access the cluster. Override `RENDER_DIR`,
`FALCO_CHART_VERSION`, or `TALON_CHART_VERSION` with Make variables when needed.

Checked on 2026-10-07 with official release packages: Falco chart 9.2.0
(engine 0.45.0) and Talon chart 0.5.0 (app 0.3.0). Rendering confirmed that
Talon's ClusterRole has no grants, only our response rule matches events,
and its generated configuration disables leader election. Its chart uses
`default true` for that boolean, so our values use the string `"false"` to
render a real YAML false. The rule checksum changes the Deployment template
when the response file changes, so Helm upgrade triggers a rollout.

The Ubuntu 24.04 multi-architecture image digest was read from the official
Docker Hub tag API. Its package setup and actual compatibility remain untested.

## Node preparation

`prepare-labs/settings/kubernetes-cloudinit.env` runs `kubepkgs` and `kubetools`,
which install Helm. The Falco DaemonSet carries the engine and embedded modern
eBPF probe; no Falco host binary or manual driver compilation is needed for
this path. Bret confirmed Ubuntu 26.04 with kernel 7.0 for the student VMs. Nodes still
need BTF and BPF ring buffer support plus the agent's
required privileges and runtime socket access. No provisioning changes were made.

## Pending lab validation

- [ ] Verify driver startup and ready Falco coverage on the student nodes.
- [ ] Verify fixture package setup and readiness.
- [ ] Verify actual namespace permissions and pod metadata.
- [ ] Verify allowed command, dry-run matching, and sudo/apt/curl deletion.
- [ ] Verify the response-rule upgrade rolls out and loads the changed rule.
- [ ] Verify unrelated pods are unaffected and cleanup allows a fresh rerun.
- [ ] Review `labtest` directives against observed exits and timing.
- [ ] Enable the chapter only after lab validation.

[Source research](../../docs/research/falco-talon-lab.md) records documentation
and static evidence. A successful render is not a tested lab.
