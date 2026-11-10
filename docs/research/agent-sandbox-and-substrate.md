# Scope: Agent Sandbox and Agent Substrate chapters

Research date: 2026-11-10.
Deck: `slides/kube-sec-twodays.yml`, group "Kubernetes Security in the age of AI".
Status: scope only. No slides written. No command here has run on a lab yet.

## Where the new chapters go

Put two new chapters right after `k8s/sandbox.md`:

```yaml
    - k8s/sandbox.md          # gVisor, Kata, Firecracker, RuntimeClass (existing)
    - k8s/agent-sandbox.md    # NEW: Sandbox CRDs, warm pools, claims (lab)
    - k8s/agent-substrate.md  # NEW: actors, workers, suspend/resume (concepts; lab TBD)
```

The order goes from one level to the next:

1. `sandbox.md`: isolate **one pod** (a runtime: gVisor or Kata).
2. `agent-sandbox.md`: manage **one sandbox for each agent session** (Kubernetes objects).
3. `agent-substrate.md`: run **thousands of sessions on a few pods** (suspend and resume).

Each chapter uses the one before it: Agent Sandbox uses the `gvisor`
RuntimeClass from `sandbox.md`, and Substrate uses gVisor checkpoint/restore.

## The two projects

| | Agent Sandbox | Agent Substrate |
|-|-|-|
| Home | `kubernetes-sigs/agent-sandbox`, a SIG Apps subproject (part of Kubernetes) | `agent-substrate/substrate`, CNCF Sandbox (donated by Google Cloud, KubeCon NA, Nov 2026) |
| Version on 2026-11-10 | v1.0.10 (2026-11-06) | "1.0" (README and Google blog); no release on the GitHub page |
| Unit | 1 Sandbox = 1 pod, stable name, its own storage | 1 Actor = 1 session; many actors share a few Worker pods |
| Idle sessions | Pod keeps running, or is paused or deleted (TTL) | Actor is snapshotted to object storage; its Worker slot is freed |
| Wake up | WarmPool + Claim: a pod is already running | Restore from a snapshot on a warm Worker, < 500 ms (project number) |
| Isolation | Delegated to a RuntimeClass (runc, gVisor, Kata) | Required: gVisor or Cloud Hypervisor microVM; plain containers are not supported |
| Network and identity | Normal Kubernetes: NetworkPolicy, RBAC, ServiceAccount | Default-deny; inbound only through `atenet-router`; SPIFFE certificates; egress gateway injects credentials |
| API | CRDs: `Sandbox` (`agents.x-k8s.io/v1beta1`), `SandboxTemplate`, `SandboxClaim`, `SandboxWarmPool` (`extensions.agents.x-k8s.io`) | CRDs `WorkerPool`, `SandboxConfig`, `CSIDriverConfig` (`ate.dev/v1`); actors through a gRPC API and `kubectl ate` |
| Install | `kubectl apply -f .../releases/download/v1.0.10/sandbox-with-extensions.yaml` | `go run ./cmd/ate-setup deploy ate-system ...` from a clone (kind, GKE) |
| Needs | Kubernetes 1.29+ recommended | Kubernetes 1.37+, PostgreSQL, object storage (GCS, or `rustfs` in kind) |
| Clients | Python SDK `k8s-agent-sandbox`, Go SDK, optional `sandbox-router` | `kubectl ate`; kagent (CNCF Sandbox) uses Substrate as its default backend |

Version gap to check on a lab: the README shows `agents.x-k8s.io/v1beta1` for
`Sandbox`, but the repo `AGENTS.md` still lists the extensions as `v1alpha1`.
Read the CRDs after the install and use what the cluster serves.

## Lab fit (our lab: kubeadm 1.37.1 on EC2 `t3`, no `/dev/kvm`, gVisor on node2)

- **Agent Sandbox: good fit.** One `kubectl apply`, plain CRDs, and it uses
  our `gvisor` RuntimeClass. Nothing new on the nodes.
- **Agent Substrate: unknown fit.** The `gvisor` sandbox class does not need
  KVM, and our Kubernetes version is new enough. But:
  - the documented installs are kind and GKE only; kubeadm and EKS are not documented;
  - the install runs from source: Go and Docker on node1, plus PostgreSQL and
    S3-compatible storage in the cluster;
  - we do not know if `ateworker-gvisor` needs privileged worker pods, or its
    own `runsc` on the node (it runs gVisor checkpoint/restore inside the pod).

  Recommendation: slides-only first. Spike a lab on one test cluster; add a
  lab only if the spike passes `labtest`.

## Chapter 1: `k8s/agent-sandbox.md` (about 10 slides, 5 labs)

Slides:

1. Why agents need a different pod: long-running, stateful, one per session,
   runs code that we do not trust. A Deployment or a StatefulSet does not fit.
2. The four CRDs and who uses each one (platform team: Template, WarmPool;
   agent or app: Claim). One diagram (see Diagrams).
3. Lifecycle: create, pause and resume, scheduled deletion (TTL).
   Confirm the field names on the lab before writing the slide.
4. Security: Agent Sandbox does not isolate. The isolation comes from the
   RuntimeClass, and NetworkPolicy, RBAC, and quotas still apply.
5. Router, `sandboxd`, and the SDKs: one slide, concepts only.

Labs (namespace `agents`, on node2 with gVisor):

1. Install the controller at a fixed version (v1.0.10). Check the CRDs and their versions.
2. Create a `Sandbox` with `runtimeClassName: gvisor`; `uname -r` shows gVisor
   (same check as in `sandbox.md`).
3. Create a `SandboxTemplate` and a `SandboxWarmPool` with 2 replicas; watch the pods start.
4. Create a `SandboxClaim`; it takes a warm pod. Compare its time with a new
   `Sandbox`. Show that the pool makes a new pod to replace it.
5. Add a default-deny egress NetworkPolicy to the template's pods (reuse
   `netpol.md`); show that the sandbox cannot reach the API server or the internet.

New files: `k8s/agent-sandbox/*.yaml` (template, pool, claim, policy).

## Chapter 2: `k8s/agent-substrate.md` (about 8 slides, lab TBD)

Slides:

1. The problem: agents wait 90 to 95% of the time (inference, APIs, people).
   One running pod per session costs too much at 10,000 users.
2. Actors and Workers: an actor is a session (files, memory, env, network
   rules); a worker is a warm pod in a WorkerPool. Diagram.
3. Suspend and resume: snapshot to object storage at the end of a turn;
   `atenet-router` holds the next request, then restores the actor on a free worker.
4. Why gVisor makes this possible: it owns its memory and process tables,
   so it can save them and restore them on another node.
5. Zero trust by default: no tokens in the actor, egress gateway injects
   credentials, SPIFFE identity, inbound traffic only through the router,
   no actor-to-actor traffic.
6. Agent Sandbox or Agent Substrate? (table above, shorter). They solve
   different problems: one sandbox per session versus many sessions per pod.
7. Project status: CNCF Sandbox since Nov 2026; new project, many open issues.
   Test it before production.

Lab (only if the spike passes): install with the gVisor class only, create the
counter actor, call it, `kubectl ate suspend`, call it again, show that the count is still there.

## Changes to `sandbox.md` that come with this work

- gVisor is now in the CNCF (Sandbox, Nov 2026): update "gVisor (Google)".
- Move the "Agent Sandbox" slide into the new chapter; leave one line that
  points to it.
- "Choosing a sandbox": add one line for Substrate.
- The cleanup lab deletes the `gvisor` RuntimeClass and the `sandbox` namespace.
  Keep the RuntimeClass until the end of `agent-sandbox.md`, then move that cleanup there.
- One slide or one line on the word "sandbox": a CNCF maturity level, a
  sandbox runtime (gVisor), and the Agent Sandbox CRD are three different things.

## Diagrams (Excalidraw, 16:9, style of `k8s-arch3-2026.excalidraw`)

- `agent-sandbox-crds`: Template → WarmPool (warm pods) → Claim → Sandbox pod on gVisor.
- `agent-substrate-actors`: router → control plane → Workers in a WorkerPool,
  with snapshots going to and from object storage.

## Open questions

1. Time: the AI group already has podspec, user namespaces, catch-up skill,
   sandbox (20 slides), linting, and Falco. Do both chapters fit in day 2,
   or does Substrate become an "(Optional)" or extra-details part?
2. Substrate lab: is it worth a spike on a test lab (cloud cost; needs approval)?
   Or slides only, with a short recorded demo?
3. Python SDK lab: install `k8s-agent-sandbox` on node1 and run code in a
   sandbox from Python, or keep labs to `kubectl` only?
4. kagent: one line in the Substrate chapter, or leave it out?

## Sources

- [kubernetes-sigs/agent-sandbox](https://github.com/kubernetes-sigs/agent-sandbox) and [releases](https://github.com/kubernetes-sigs/agent-sandbox/releases) (v1.0.5 to v1.0.10)
- [Agent Sandbox docs](https://agent-sandbox.sigs.k8s.io/docs/)
- [agent-substrate/substrate](https://github.com/agent-substrate/substrate)
- [ate.dev quickstart](https://ate.dev/docs/get-started/quickstart/), [operator install](https://ate.dev/docs/guides/operator-install/), [sandbox classes](https://ate.dev/docs/reference/sandbox-classes/)
- [Google Open Source blog, 2026-11-05: Agent Substrate and gVisor donated to the CNCF](https://opensource.googleblog.com/2026/11/sandboxing-untrusted-ai-agents-at-scale.html)
- [CNCF Sandbox application, issue #523](https://github.com/cncf/sandbox/issues/523)
- [CNCF announcement, 2026-11-10](https://www.cncf.io/announcements/2026/11/10/cncf-hits-major-milestones-with-global-community-growth-record-industry-investment-and-a-new-generation-of-projects-to-build-ai-systems-in-production/)
