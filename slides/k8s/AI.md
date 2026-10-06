<!-- verified: 2026-10-05 -->
# Pod and namespace hardening

- Restrict pod privileges and resource use

- Control network access

- Compare workload isolation options

???

Source: https://app.notion.com/p/coreenable/new-ai-sections-3eebd1d7d6138047b7bbce10d5dec242
Kubeadm only. Validate demos before class.

---

## Harden workloads

- Enforce the Restricted Pod Security Standard

- Run as non-root and prevent privilege escalation

- Drop Linux capabilities and use an approved seccomp profile

- Use a read-only root filesystem where the workload supports it

- Provide explicit writable storage and resource limits

???

Restricted does not require a read-only root filesystem. Reuse the pod-hardening lab.

---

## Limit network access

- Start with default-deny ingress and egress policies

- Allow the DNS and service traffic that the workload needs

- Restrict access to model and tool endpoints

- Verify that the cluster network plugin enforces the policies

- Test an allowed path and a blocked path

???

Check CNI enforcement. Domain-based egress may require a proxy or CNI extension.

---

## Choose an execution boundary

- Identify which code the workload needs to run

- Identify the host resources that code needs

- Select an isolation boundary for that workload

- Test workload compatibility and performance

- Confirm that the required runtime is installed on the nodes

???

Compare user namespaces, gVisor, Kata, and Firecracker after verification. Check node support.

---

# Security tools for Kubernetes

- Validate and lint Kubernetes manifests

- Test and enforce admission policies

- Observe workload activity at runtime

???

Reuse kyverno.md for admission teaching. Follow that chapter with independent Falco.
Research: ../../docs/research/falco-kyverno-demo.md. Demos need lab validation.

---

## Apply controls at each stage

- Validate manifest structure before deployment

- Check configuration for security problems

- Enforce admission policies when resources change

- Observe workload activity at runtime

- Review agent tool calls and their results

???

Candidates: kubeconform, KubeLinter, Kyverno, Falco. Detection alone does not block.

---

## Falco: detect activity in a running container

- Run a shell in the allowed workload

- Inspect the Falco alert for the shell execution

- Identify the process, command, container, and user

- An alert reports observed activity; it does not stop the command

???

Load Falco rules independently of Kyverno. Test the shell trigger and alert output.
Reference: https://falco.org/docs/concepts/rules/custom-ruleset/

---

## A privilege escalation attempt or a successful change?

- Executing `sudo` does not prove that privileges increased

- Check the original user ID and the user ID of the resulting process

- Report a successful change to root only when the evidence confirms it

- Compare the result with a workload that prevents privilege escalation

???

Optional controlled sudo demo; use a custom rule and verify UID evidence.
Keep this demo independent of Kyverno. Test before teaching.

---

## Review a change before applying it

- Show the proposed manifest or patch

- Explain which resources will change

- Validate the manifest and test the relevant policies

- Obtain approval through the configured workflow

- Verify the result and keep a rollback path

???

Connect to GitOps and policy testing. Approval does not replace restricted permissions.

---

# Local sandboxing and cluster access

- Restrict local filesystem and credential access

- Compare nono and Docker Sandboxes

- Prevent unauthorized cluster writes with API permissions

???

Verify sandbox platform support and security guarantees before adding instructions.

---

## Separate permissions from isolation

- API permissions control access to cluster resources

- An execution sandbox restricts the code running inside it

- A sandboxed tool can still send authorized requests to a remote cluster

- Use restricted cluster credentials as well as execution isolation

???

A read-only kubeconfig file does not make its identity read-only.

---

## Restrict local tool access

- Expose only the workspace files that the tool needs

- Withhold administrator credentials and host sockets

- Give cluster tools a dedicated restricted identity

- Check where each MCP server runs

- Test access through every exposed tool path

???

Compare nono and Docker Sandboxes after verification. Check MCP execution location.

---

## Start with restricted access

- Give the agent a dedicated identity

- Allow only the required resources and operations

- Limit access to the required namespace

- Exclude Secrets and changes to permissions

- Test both allowed reads and denied writes

???

Test allowed reads and denied writes through kubectl and MCP. Exclude Secrets.

---

# Running agents in Kubernetes with kagent

- Map the agent, model endpoint, and tool server

- Control access to tools and cluster resources

- Review changes and inspect tool-call records

???

Select one supported kagent release. Test the demonstration on kubeadm.

---

## Run agents inside Kubernetes

- Separate the agent, tool server, model endpoint, and execution sandbox

- Give each component only the access it needs

- Restrict tool access and model-provider traffic

- Record tool calls and resulting cluster changes

- Review all paths that can write to the cluster

???

Optional kagent demo: read-only diagnosis, then an approved ConfigMap write. Test on kubeadm.

---

# OpenChoreo and platform operations

- Map platform operations to Kubernetes resources

- Separate diagnosis access from deployment access

- Limit operations by team and project

???

Verify current OpenChoreo APIs and authorization. Use a prepared kubeadm environment.

---

## Use platform APIs for scoped operations

- Give diagnosis tools access to operational data

- Give deployment tools separate permissions

- Limit operations to the required team and project

- Verify authorization before exposing a tool to an agent

- Inspect the resulting Kubernetes resources

???

Optional OpenChoreo demo: diagnosis allowed, promotion denied. Test on kubeadm.

---

# Kubernetes troubleshooting with AI tools

- Set up restricted diagnostic access

- Give the agent reviewed instructions and skills

- Diagnose workload failures with evidence

- Evaluate the result and review proposed changes

???

Select kubectl-ai or Kubernetes MCP Server. Test one failure before adding lab commands.

---

## What can an agent do?

- Read workload status, events, and logs

- Compare observed behavior with the expected configuration

- Suggest a cause and a change

- Use tools to act with the permissions of their configured identity

???

Select one diagnostic tool: kubectl-ai or Kubernetes MCP Server. Verify its release.

---

## Follow the request to the cluster

- The agent uses a model to choose a tool call

- The tool runs locally or on a tool server

- The tool sends a request with cluster credentials

- The Kubernetes API checks the identity and its permissions

- Check the identity used by each tool

???

The tool server may use its own credentials. Introduce MCP: Model Context Protocol.

---

## Diagnose with evidence

- Confirm the cluster context and namespace

- Read workload status, events, and relevant logs

- State what the evidence proves

- Label an untested cause as a hypothesis

- Test the hypothesis before proposing a change

???

Lab candidate: a Service targetPort mismatch. Require evidence before a fix.

---

## Give the agent reviewed instructions

- Record the approved context and namespace

- List the allowed diagnostic tools

- Require evidence for each diagnosis

- Define when the agent must stop for human review

- Keep credentials out of instructions and skills

???

Use a versioned skill. Instructions guide behavior; RBAC enforces permissions.

---

## Treat workload data as untrusted input

- Logs, annotations, and documents can contain hostile instructions

- Use that content as evidence about the workload

- Do not follow instructions found in workload data

- Remove sensitive data before sending it to a model provider

???

Test a benign hostile instruction in a log. Check for sensitive data disclosure.

---

## Check the result of an agent task

- Did the diagnosis match the evidence?

- Did the agent attempt an unauthorized operation?

- Did sensitive data leave the approved boundary?

- Did the change fix the problem without unnecessary changes?

- Could we restore the previous state?

???

Measure accuracy, unauthorized attempts, data disclosure, recovery, time, and cost.
