<!-- verified: 2026-10-05 -->
# Setting up Kubernetes

- Kubernetes is made of many components that require careful configuration

- Secure operation typically requires TLS certificates and a local CA

  (certificate authority)

- Setting up everything manually is possible, but rarely done

  (except for learning purposes)

- Let's do a quick overview of available options!

---

## Local development

- Are you writing code that will eventually run on Kubernetes?

- Then it's a good idea to have a development cluster!

- Instead of shipping container images, we can test them on Kubernetes

- Extremely useful when authoring or testing Kubernetes-specific objects

  (ConfigMaps, Secrets, StatefulSets, Jobs, RBAC, etc.)

- Extremely convenient to quickly test/check what a particular thing looks like

  (e.g. what are the fields of a Deployment spec?)

---

## One-node clusters

- It's perfectly fine to work with a cluster that has only one node

- It simplifies a lot of things:

  - pod networking doesn't even need CNI plugins, overlay networks, etc.

  - these clusters can be fully contained (no pun intended) in an easy-to-ship VM or container image

  - some of the security aspects may be simplified (different threat model)

  - images can be built directly on the node (we don't need to ship them with a registry)

- Examples: Docker Desktop, k3d, KinD, MicroK8s, Minikube

  (some of these also support clusters with multiple nodes)

---

## Managed clusters ("Turnkey Solutions")

- Many cloud providers and hosting providers offer "managed Kubernetes"

- The deployment and maintenance of the *control plane* is entirely managed by the provider

  (ideally, clusters can be spun up automatically through an API, CLI, or web interface)

- Given the complexity of Kubernetes, this approach is *strongly recommended*

  (at least for your first production clusters)

- After working for a while with Kubernetes, you will be better equipped to decide:

  - whether to operate it yourself or use a managed offering

  - which offering or which distribution works best for you and your needs

---

## Managed ≠ managed

- Managed Kubernetes ≠ managed hosting

- Managed hosting typically means that the hosting provider takes care of:

  - installation, upgrades, time-sensitive security patches, backups

  - logging and metrics collection

  - setting up supervision, alerts, and on-call rotation

- Managed Kubernetes typically means that the hosting provider takes care of:

  - installation

  - maybe upgrades (kind of; you typically need to initiate/coordinate them)

  - and that's it!

---

## "Managed" Kubernetes

- "Managed Kubernetes" gives us the equivalent of a raw VM

- We still need to add a lot of things to make it production-ready

  (upgrades, logging, supervision...)

- We also need some almost-essential components that don't always come out of the box

  - ingress controller

  - network policy controller

  - storage class...

📽️[How to make Kubernetes rhyme with production readiness](https://www.youtube.com/watch?v=6G4v-ZE6OHI)

---

## Observability

- Logging, metrics, traces...

- Pick a solution (self-hosted, as-a-service?)

- Configure control plane, nodes, various components

- Set up dashboards, track important metrics

  (e.g. on AWS, track inter-AZ and external traffic per app to avoid $$$ surprises)

- Set up supervision, on-call notifications, on-call rotation

---

## Backups

- Full machine backups of the nodes?

  (not very effective)

- Backup of control plane data?

  (important; it's not always possible to obtain etcd backups)

- Backup of persistent volumes?

  (good idea; but not always effective)

- App-level backups, e.g. database dumps, log-shipping?

  (more effective and reliable; more work depending on the app and database)

---

## Upgrades

- Control plane

  *typically automated by the provider; but might cause breakage*

- Nodes

  *best case scenario: can be done in-place; otherwise: requires provisioning new nodes*

- Additional components (ingress controller, operators, etc.)

  *depends wildly on the components!*

---

name: kubernetes-operations-lifecycle
class: pic

![Kubernetes operations: Day 0 plans ownership, topology, capacity, security, recovery, and delivery; Day 1 deploys the cluster, add-ons, policies, observability, backups, and workloads; Day 2 monitors, restores, upgrades, reviews access, rotates credentials, and responds to incidents.](images/k8s-operations-lifecycle-2026.svg)

???

Day 0, Day 1, and Day 2 are operations lifecycle phases. They are not the
workshop's teaching days and do not describe elapsed calendar days.

Plan for operations before deployment. Set up observability and backups during
deployment. During operation, act on alerts, verify backups with restore tests,
and use findings to update the plan. Security controls need design, initial
enforcement, and continued review across all three phases.

These activity groups are a teaching summary, not a Kubernetes specification.
Managed services change who performs an activity; they do not remove the need
to define ownership and verify the result.

Sources:

- [Red Hat: operations lifecycle definitions](https://www.redhat.com/en/blog/how-does-red-hat-support-day-2-operations)
- [Kubernetes: production environment](https://kubernetes.io/docs/setup/production-environment/)
- [Kubernetes: security checklist](https://kubernetes.io/docs/concepts/security/security-checklist/)
- [Kubernetes: operating etcd, backups, and restores](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/)
- [Kubernetes: certificate management](https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-certs/)
- [Amazon EKS: Day 2 best practices](https://docs.aws.amazon.com/eks/latest/best-practices/)
- [Amazon EKS: security responsibilities](https://docs.aws.amazon.com/eks/latest/userguide/security.html)

Related workshop content: `gitworkflows.md` (planning and ownership),
`yamldeploy.md` ("Day 2" YAML), `rollout.md` (release recovery),
`authn-authz.md` (access checks), and `helm-secrets.md` (release data protection).

Tool references:

| Activity | Tools |
| --- | --- |
| Define ownership | [Backstage](https://backstage.io/docs/features/software-catalog/) · [CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners) |
| Design topology | [Terraform](https://developer.hashicorp.com/terraform/intro) · [Cluster API](https://cluster-api.sigs.k8s.io/) |
| Plan capacity | [Karpenter](https://karpenter.sh/docs/) · [Cluster Autoscaler](https://kubernetes.io/docs/concepts/cluster-administration/node-autoscaling/) |
| Define security baseline | [Kyverno](https://kyverno.io/docs/introduction/) · [Trivy](https://trivy.dev/docs/latest/guide/) |
| Plan recovery | [Velero](https://velero.io/docs/) · [etcdutl](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/) |
| Design delivery workflow | [Flux](https://fluxcd.io/flux/) · [Argo CD](https://argo-cd.readthedocs.io/en/stable/) |
| Cluster setup | [kubeadm](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/create-cluster-kubeadm/) · [eksctl](https://docs.aws.amazon.com/eks/latest/eksctl/what-is-eksctl.html) |
| Add-on setup | [Helm](https://helm.sh/docs/intro/using_helm/) · [EKS add-ons](https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html) |
| Access & policy setup | [kubectl](https://kubernetes.io/docs/reference/access-authn-authz/rbac/) · [Kyverno](https://kyverno.io/docs/introduction/) |
| Observability setup | [Prometheus](https://prometheus.io/docs/introduction/overview/) · [OpenTelemetry](https://opentelemetry.io/docs/platforms/kubernetes/helm/collector/) |
| Backup setup | [Velero](https://velero.io/docs/) · [etcdctl](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/) |
| Deploy workloads | [Helm](https://helm.sh/docs/intro/using_helm/) · [Kustomize](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/) |
| Health monitoring | [Grafana](https://grafana.com/docs/grafana/latest/introduction/) · [Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/) |
| Backup & restore tests | [Velero](https://velero.io/docs/) · [etcdutl](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/) |
| Upgrade & patch | [kubeadm](https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/) · [EKS](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html) |
| Access review | [kubectl auth](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_auth/kubectl_auth_can-i/) · [rbac-lookup](https://rbac-lookup.docs.fairwinds.com/) |
| Credential rotation | [cert-manager](https://cert-manager.io/docs/usage/certificate/) · [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html) |
| Incident response | [Falco](https://falco.org/docs/) · [Tetragon](https://tetragon.io/docs/overview/) |

---

## It's dangerous to go alone!

Don't hesitate to hire help before going to production with your first K8S app!

---

## Node management

- Most "Turnkey Solutions" offer fully managed control planes

  (including control plane upgrades, sometimes done automatically)

- However, with most providers, we still need to take care of *nodes*

  (provisioning, upgrading, scaling the nodes)

- Example with Amazon EKS ["managed node groups"](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html):

  *...when bugs or issues are reported [...] you're responsible for deploying these patched AMI versions to your managed node groups.*

---

## Managed clusters differences

- Most providers let you pick which Kubernetes version you want

  - some providers offer up-to-date versions

  - others lag significantly (sometimes by 2 or 3 minor versions)

- Some providers offer multiple networking or storage options

- Others will only support one, tied to their infrastructure

  (changing that is in theory possible, but might be complex or unsupported)

- Some providers let you configure or customize the control plane

  (generally through Kubernetes "feature gates")

---

## Choosing a provider

- Pricing models differ from one provider to another

  - nodes are generally charged at their usual price

  - control plane may be free or incur a small nominal fee

- Beyond pricing, there are *huge* differences in features between providers

- The "major" providers are not always the best ones!

- See [this page](https://kubernetes.io/docs/setup/production-environment/turnkey-solutions/) for a list of available providers

---

## Kubernetes distributions and installers

- If you want to run Kubernetes yourselves, there are many options

  (free, commercial, proprietary, open source ...)

- Some of them are installers, while some are complete platforms

- Some of them leverage other well-known deployment tools

  (like Puppet, Terraform ...)

- There are too many options to list them all

  (check [this page](https://kubernetes.io/partners/#iframe-landscape-conformance) for an overview!)

---

## kubeadm

- kubeadm is a tool part of Kubernetes to facilitate cluster setup

- Many other installers and distributions use it (but not all of them)

- It can also be used by itself

- Excellent starting point to install Kubernetes on your own machines

  (virtual, physical, it doesn't matter)

- It even supports highly available control planes (multiple control plane nodes)

  (this is more complex, though, because it introduces the need for an API load balancer)

---

## Manual setup

- The resources below are mainly for educational purposes!

- [Kubernetes The Hard Way](https://github.com/kelseyhightower/kubernetes-the-hard-way) by Kelsey Hightower

  *step by step guide to install Kubernetes on 4 machines (any cloud or local VMs), with certificates*

- [Deep Dive into Kubernetes Internals for Builders and Operators](https://www.youtube.com/watch?v=3KtEAa7_duA)

  *conference talk setting up a simplified Kubernetes cluster - no security or HA*

- 🇫🇷[Démystifions les composants internes de Kubernetes](https://www.youtube.com/watch?v=OCMNA0dSAzc)

  *improved version of the previous one, with certs and recent k8s versions*

---

## About our training clusters

- How did we set up these Kubernetes clusters that we're using?

--

- We used `kubeadm` on freshly installed VM instances running Ubuntu LTS

    1. Install containerd

    2. Install Kubernetes packages

    3. Run `kubeadm init` on the first node (it deploys the control plane on that node)

    4. Set up Cilium (the CNI plugin) with a single `helm install` command

    5. Run `kubeadm join` on the other nodes (with the token produced by `kubeadm init`)

    6. Copy the configuration file generated by `kubeadm init`

- Check the [prepare labs README](https://@@GITREPO@@/blob/@@GITBRANCH@@/prepare-labs/README.md) for more details

---

## `kubeadm` "drawbacks"

- Doesn't set up Docker or any other container engine

  (this is by design, to give us choice)

- Doesn't set up the overlay network

  (this is also by design, for the same reasons)

- HA control plane requires [some extra steps](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/high-availability/)

- Note that HA control plane also requires setting up a specific API load balancer

  (which is beyond the scope of kubeadm)

???

:EN:- Various ways to install Kubernetes
:FR:- Survol des techniques d'installation de Kubernetes
