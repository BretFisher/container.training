<!-- verified: 2026-10-07 -->
# Runtime detection with Falco

- Observe activity inside running containers

- Detect commands, file access, and network activity with rules

- Send alerts to logs or other systems

- Use Falco Talon to respond to selected alerts

---

## Detection, prevention, and response

- Falco's node agents observe Linux system calls and attach container metadata

- Rules select the activity that produces alerts

- Kyverno can reject a workload configuration at admission

- Talon responds to runtime alerts through the Kubernetes API

- The command can finish before Talon deletes the pod

---

## From command execution to pod deletion

1. A process executes a command in a container

2. Falco matches a detection rule and produces a JSON alert

3. Falco sends the alert directly to Talon over HTTP

4. Talon matches the rule name and namespace

5. Talon calls the Kubernetes API to delete the pod

- Talon needs Kubernetes permissions for its selected actions

---

## One detection rule for several commands

- Match successful execution of `sudo`, `apt`, `apt-get`, or `curl`

- Limit detection to the `falco-demo` namespace

- Include the process, command line, pod, and namespace in the alert

- These commands are forbidden by our demo policy

- Command execution alone does not prove an attack or privilege escalation

---

name: falco-response-rule

## One response rule

.small[
```yaml
- rule: Workshop command response
  match:
    rules:
      - Workshop forbidden command
    output_fields:
      - k8s.ns.name=falco-demo
  dry_run: "true"
  actions:
    - action: Delete the demo pod
      actionner: kubernetes:terminate
      parameters:
        grace_period_seconds: 0
        ignore_daemonsets: true
        ignore_statefulsets: true
        ignore_standalone_pods: false
```
]

- Match the exact Falco rule and namespace

- Start with dry-run enabled; later change only that setting

---

## Our lab sequence

1. Prepare three standalone pods with the command packages

2. Install Talon with a namespace-scoped response role

3. Install Falco and send its alerts directly to Talon

4. Check an allowed command, then detect commands in dry-run mode

5. Enable deletion and repeat one command in each pod

6. Inspect the evidence and remove the lab

---

## Prepare the working directory

- Use the student kubeadm cluster on Ubuntu 26.04 with kernel 7.0

- Use the normal container runtime, not the earlier gVisor RuntimeClass

- This exercise uses Helm and kubectl from the existing lab setup

.lab[

- Enter the repository and copy the response rule for this exercise:
  ```bash
  cd ~/container.training
  cp k8s/falco-demo/talon-rules.yaml /tmp/falco-talon-rules.yaml
  ```

- Select the chart releases used by this exercise:
  ```bash
  export FALCO_CHART_VERSION=9.2.0
  export TALON_CHART_VERSION=0.5.0
  ```

]

---

## Create the lab namespaces

- `falco` holds the detection and response services

- `falco-demo` holds the pods that Talon may delete

.lab[

- Create two new namespaces:
  ```bash
  kubectl create namespace falco
  kubectl create namespace falco-demo
  ```

]

- Use empty namespaces for this exercise

- Keep Falco's node privileges separate from Talon's response permissions

---

## Prepare the demo pods

- Each pod installs sudo and curl before detection starts

- Apt and apt-get are already in the Ubuntu image

- The image is pinned by digest in the manifest

- Readiness requires package setup to finish

.lab[

- Create the three standalone pods and wait for readiness:
  ```bash
  kubectl apply -f k8s/falco-demo/pods.yaml
  kubectl wait -n falco-demo --for=condition=Ready \
    pod/demo-sudo pod/demo-apt pod/demo-curl --timeout=300s
  ```
<!-- ```timeout 360``` -->

]

---

## Check the command packages

- Every pod must have the commands before the detection rule is loaded

.lab[

- Check the packages in each pod:
  ```bash
  for tool in sudo apt curl; do
    kubectl exec -n falco-demo "demo-$tool" -- sh -ec \
      'command -v sudo; command -v apt; command -v apt-get; command -v curl'
  done
  ```

- Check their nodes:
  ```bash
  kubectl get pods -n falco-demo -o wide
  ```

]

---

## Inspect our detection and response files

- One Falco rule matches sudo, apt, apt-get, and curl in `falco-demo`

- JSON alerts carry the command, pod, and namespace to Talon

- Talon's response matches the rule name and starts in dry-run mode

.lab[

- Read the detection configuration and our copied response rule:
  ```bash
  cat k8s/falco-demo/falco-values.yaml
  cat /tmp/falco-talon-rules.yaml
  ```

]

- The chart values remove global grants; our separate Role permits demo deletion

---

## Install Talon

- Talon receives alerts and applies our response rule

.lab[

- Grant the demo namespace permissions before Talon starts:
  ```bash
  kubectl apply -f k8s/falco-demo/talon-rbac.yaml
  ```

- Install the response service with the copied rule:
  ```bash
  helm install falco-talon falco-talon \
    --repo https://falcosecurity.github.io/charts \
    --version "$TALON_CHART_VERSION" -n falco \
    -f k8s/falco-demo/talon-values.yaml \
    --set-file config.rulesOverride=/tmp/falco-talon-rules.yaml \
    --wait --timeout 5m
  ```
<!-- ```timeout 360``` -->

]

---

## Verify response permissions

.lab[

- Check pod deletion in the demo namespace; the answer must be `yes`:
  ```bash
  kubectl auth can-i delete pods -n falco-demo \
    --as=system:serviceaccount:falco:falco-talon
  ```

- Check pod deletion in `default`; the answer must be `no`:
  ```bash
  kubectl auth can-i delete pods -n default \
    --as=system:serviceaccount:falco:falco-talon
  ```
<!-- ```expect-fail``` -->

]

- Stop if Talon can delete pods outside the demo namespace

---

## Install Falco

- Falco runs as a DaemonSet on the monitored nodes

- The values load the command rule and send JSON alerts to Talon

.lab[

- Install the node agents:
  ```bash
  helm install falco falco \
    --repo https://falcosecurity.github.io/charts \
    --version "$FALCO_CHART_VERSION" -n falco \
    -f k8s/falco-demo/falco-values.yaml --wait --timeout 5m
  ```
<!-- ```timeout 360``` -->

]

---

## Check agent coverage and startup

.lab[

- Check readiness and node placement:
  ```bash
  kubectl rollout status -n falco daemonset/falco --timeout=120s
  kubectl get pods -n falco -o wide
  kubectl get service -n falco falco-talon
  ```
<!-- ```timeout 150``` -->

- Read startup logs from Falco and Talon:
  ```bash
  kubectl logs -n falco -l app.kubernetes.io/name=falco \
    -c falco --prefix --tail=80
  kubectl logs -n falco deployment/falco-talon --tail=80
  ```

]

- Each node hosting a demo pod must have a ready Falco agent

---

## Run an allowed command

- Our rule does not match `id`

.lab[

- Run the command and confirm the pod is still present:
  ```bash
  kubectl exec -n falco-demo demo-curl -- id
  kubectl get pod -n falco-demo demo-curl
  ```

]

- Our demo pods start as root so package setup can run

- This exercise detects program execution, not a change of user identity

---

## Detect three commands in dry-run mode

- Version commands execute each program without package changes or requests

.lab[

- Trigger the same Falco rule with three different commands:
  ```bash
  kubectl exec -n falco-demo demo-sudo -- sudo --version
  kubectl exec -n falco-demo demo-apt -- apt --version
  kubectl exec -n falco-demo demo-curl -- curl --version
  ```

]

- Dry-run should match the response rule without deleting pods

---

## Inspect the alerts and dry-run result

.lab[

- Read Falco's command alerts:
  ```bash
  kubectl logs -n falco -l app.kubernetes.io/name=falco \
    -c falco --prefix --since=5m --tail=200
  ```

- Read Talon's response and confirm all pods remain:
  ```bash
  kubectl logs -n falco deployment/falco-talon --since=5m --tail=200
  kubectl get pods -n falco-demo
  ```

]

- Find `Workshop forbidden command` for each program

- Check the process name, pod name, and `falco-demo` namespace

- Do not enable deletion if the metadata or dry-run match is missing

---

## Enable pod deletion with one change

- Keep the Falco command list unchanged

- Change only the copied Talon rule's dry-run setting

.lab[

- Switch the response rule to active mode and inspect it:
  ```bash
  sed -i 's/dry_run: "true"/dry_run: "false"/' /tmp/falco-talon-rules.yaml
  cat /tmp/falco-talon-rules.yaml
  ```

]

- The repository's original rule stays in dry-run mode for the next exercise

---

## Load the changed response rule

.lab[

- Upgrade Talon with the updated file:
  ```bash
  helm upgrade falco-talon falco-talon \
    --repo https://falcosecurity.github.io/charts \
    --version "$TALON_CHART_VERSION" -n falco \
    -f k8s/falco-demo/talon-values.yaml \
    --set-file config.rulesOverride=/tmp/falco-talon-rules.yaml \
    --wait --timeout 5m
  ```
<!-- ```timeout 360``` -->

- Wait for the rollout that the rule checksum triggers:
  ```bash
  kubectl rollout status -n falco deployment/falco-talon --timeout=120s
  ```
<!-- ```timeout 150``` -->

]

---

## Detect sudo and delete its pod

- The exec connection can close when Talon deletes the pod

- The deletion check establishes the result

.lab[

- Execute sudo, then wait for the pod to disappear:
  ```bash
  kubectl exec -n falco-demo demo-sudo -- sudo --version || true
  kubectl wait -n falco-demo --for=delete pod/demo-sudo --timeout=60s
  ```
<!-- ```timeout 90``` -->

]

- A successful deletion does not show that sudo gained privileges

---

## Repeat with apt and curl

.lab[

- Trigger apt and check its pod deletion:
  ```bash
  kubectl exec -n falco-demo demo-apt -- apt --version || true
  kubectl wait -n falco-demo --for=delete pod/demo-apt --timeout=60s
  ```
<!-- ```timeout 90``` -->

- Trigger curl and check its pod deletion:
  ```bash
  kubectl exec -n falco-demo demo-curl -- curl --version || true
  kubectl wait -n falco-demo --for=delete pod/demo-curl --timeout=60s
  ```
<!-- ```timeout 90``` -->

]

- One detection rule and one response rule cover all three cases

---

## Check the response evidence

.lab[

- Read the alerts and response actions:
  ```bash
  kubectl logs -n falco -l app.kubernetes.io/name=falco \
    -c falco --prefix --since=5m --tail=200
  kubectl logs -n falco deployment/falco-talon --since=5m --tail=200
  kubectl get pods -n falco-demo
  ```

- Confirm existing application pods are still present:
  ```bash
  kubectl get pods -n default
  ```

]

- Correlate each command alert with a successful Talon deletion

- Standalone pods stay deleted; a Deployment would create replacements

---

## Limits of this policy

- A process-name list covers only the named programs

- Other programs can perform the same activity

- Renamed binaries can bypass a process-name rule

- Detection depends on node coverage, event collection, and rule matching

- A Deployment normally creates a replacement for a deleted pod

- Pod deletion cannot undo earlier file changes or network requests

---

## Remove the response and detection services

.lab[

- Remove Talon first, then Falco:
  ```bash
  helm uninstall falco-talon -n falco
  helm uninstall falco -n falco
  ```

- Remove the two namespaces created for this exercise:
  ```bash
  kubectl delete namespace falco-demo falco --wait=true --timeout=120s
  ```
<!-- ```timeout 150``` -->

]

---

## Documentation

- [Falco kernel events](https://falco.org/docs/concepts/event-sources/kernel/)

- [Falco installation with Helm](https://falco.org/docs/getting-started/deployment/)

- [Falco Talon architecture](https://github.com/falcosecurity/falco-talon)

- [Talon response rules](https://falco-talon.github.io/docs/rules/)

- [Talon Kubernetes actions](https://falco-talon.github.io/docs/actionners/list/)
