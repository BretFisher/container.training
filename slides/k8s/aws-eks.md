# Amazon EKS

- EKS is Amazon's managed Kubernetes service

- AWS runs the Kubernetes control plane

- Our student clusters use kubeadm on standard EC2 (so no EKS demos today 😭)

---

## Who manages what?

- AWS operates, patches, and scales the EKS control plane

- We cannot log in to its control planehosts or access etcd directly

- We configure API endpoint access, IAM access, and Kubernetes RBAC

  - EKS exposes a Kubernetes API endpoint. We control it's network policy

- Customers always manage applications, data, permissions, and policies

- **Node and infrastructure responsibilities depend on the compute choice**

---

class: pic

![EKS compute comparison: node ownership, scaling, workload fit, and constraints for self-managed nodes, managed node groups, Auto Mode, and Fargate, with Karpenter roles](images/aws-eks-compute-2026.svg)

---

## Provisioning clusers: kubeadm vs EKS

.column-half[
### kubeadm+kubectl (vanilla K8s)

- Provision machines and install the runtime

- Run `kubeadm init` and `kubeadm join`

- Install CNI and storage integrations (`kubectl apply` or `helm`)

- Operate and upgrade the control plane and nodes
]

.column-half[
### EKS

- Create the managed control plane: AWS console, AWS CLI, IaC, or `eksctl`

- Standard: configure compute and selected add-ons

- Auto Mode: AWS provisions nodes and manages infrastructure integrations

- Fargate: AWS provisions compute per Pod using configured profiles
]

---

## Human auth/access: kubeadm vs EKS

Create Alice user and give read/write in existing namespace `demo`

.small[
.column-half[
### kubeadm+kubectl (vanilla K8s)

```bash
  # Generate Alice's key, certificate, and kubeconfig
sudo kubeadm kubeconfig user \
  --config cluster.yaml \
  --client-name alice \
  --validity-period 24h > alice.conf

  # Bind the existing edit role in demo namespace
kubectl create rolebinding alice-edit \
  --namespace demo --clusterrole edit \
  --user alice
```
]

.column-half[
### EKS (via K8s [webhook token auth][webhook-token-auth])

```bash
  # Create Alice's IAM identity (no credentials yet)
ARN=$(aws iam create-user \
  --user-name alice \
  --query User.Arn --output text)

  # Link Alice identity to the EKS cluster
aws eks create-access-entry \
  --cluster-name "$CLUSTER" \
  --principal-arn "$ARN"

  # Grant Alice read/write in demo namespace
aws eks associate-access-policy \
  --cluster-name "$CLUSTER" \
  --principal-arn "$ARN" \
  --policy-arn "$EDIT_POLICY_ARN" \
  --access-scope \
  type=namespace,namespaces=demo
```
]
]

[webhook-token-auth]: https://kubernetes.io/docs/reference/access-authn-authz/authentication/#webhook-token-authentication

---

## Pod auth: Accesssing cluster resources vs AWS resources

.column-half[
### Accessing in-cluster resources

- `kubectl create serviceaccount`: create a workload identity

- `kubectl create rolebinding`: grant Kubernetes API permissions

- Auth to other pods (DBs): Store in AWS Secrets Manager, access via [ASCP][ascp-irsa]

- Use K8s NetworkPolicy to access other Pod Services

]

.column-half[
### Accessing AWS resources

- EKS Pod Identity or IRSA provision AWS credentials for pods

- Pod workloads use AWS SDKs or ASCP to get those creds

]

[ascp-irsa]: https://docs.aws.amazon.com/secretsmanager/latest/userguide/ascp-pod-identity-integration.html

---

## Pod access to AWS: Pod Identity vs IRSA

Both provide AWS IAM role credentials to Kubernetes Pods via the [AWS SDK][irsa-sdks] and [ASCP][ascp-irsa]


.column-half[
### [EKS Pod Identity][eks-pod-identity] launched 2023

- Simpler than IRSA, Requires EKS, but no Fargate support

- Associate cluster, namespace, and ServiceAccount with a role that trusts EKS

]

.column-half[
### [IRSA][irsa-overview] launched 2019

- Older solution: IAM Roles for Service Accounts

- [Configure OIDC and IAM role trust][irsa-setup] for the intended ServiceAccount

- Use with Fargate and self-managed Kubernetes
]

[eks-pod-identity]: https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html
[pod-id-sdks]: https://docs.aws.amazon.com/eks/latest/userguide/pod-id-minimum-sdk.html
[irsa-overview]: https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html
[irsa-setup]: https://docs.aws.amazon.com/eks/latest/userguide/associate-service-account-role.html

[ascp-pod-id]: https://docs.aws.amazon.com/secretsmanager/latest/userguide/ascp-pod-identity-integration.html
[ascp-irsa]: https://docs.aws.amazon.com/secretsmanager/latest/userguide/ascp-irsa-integration.html

[irsa-sdks]: https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts-minimum-sdk.html

---

## Secrets for legacy apps: ASCP

- [AWS Secrets and Configuration Provider (ASCP)][ascp-setup] connects Secrets Manager
  and Parameter Store to EKS Pods

- Pod Identity authorizes retrieval; the Secrets Store CSI Driver mounts values as files

- The app reads the mounted credentials; no AWS SDK is needed in the app

- Create the database account and store its password separately; ASCP delivers it

- On password rotation, the app must reload credentials or restart

[ascp-setup]: https://docs.aws.amazon.com/secretsmanager/latest/userguide/ascp-pod-identity-integration.html

---

class: pic

![EKS workload access: Pod Identity and IRSA provide AWS credentials; ASCP uses either to deliver secrets](images/aws-eks-workload-access-2026.svg)

---

## Operations and upgrades

- EKS versions receive 14 months of standard support, then 12 months extended

- Extended support has a higher cluster charge; check the cluster upgrade policy

- Know which updates you are responsible for: 

  - Control Plane version? 
  - node OS?
  - node agents?
  - K8s add-ons? 

---

## EKS best practices

.column-half[
.small[
- **Size subnets for peak Pod count, including rolling update**

- **Give workloads limited AWS perms (Pod Identity or IRSA) and no instance metadata**

- Restrict access to the Kubernetes API endpoint (enable Private access)

- Update add-ons separately from Kubernetes

- Measure resource requests before tuning autoscaling

- Test whether applications survive node replacement

- Enable multiple instance types and AZs for nodes

- Enable control plane logs

- **Use a dedicated ServiceAccount for each application**

- **Disable automatic ServiceAccount Kubernetes API token mounts when unused**

]]
.column-half[
.small[
- Avoid unnecessary cluster-admin access

- **Enforce Pod admission controls via Pod Security Standards, Kyverno, or Gatekeeper**

- **Run containers as non-root, read-only FS, and prevent privilege escalation** (Pod Spec)

- **Enable Pod seccomp default profile cluster-wide**

- **Default-deny Pod traffic and explicitly allow required connections**

- Combine restrictive AWS Security Groups and K8s NetworkPolicies

- Keep credentials out of images, manifests, and source control

- Limit secret access (RBAC) and test application credential rotation

- Enable threat detection for audit logs and container runtimes (GuardDuty, Falco)
]]

---

## Official EKS guidance

.column-half[
.small[

- [Best practices][eks-guidance-best-practices]

- [Security guide][eks-guidance-security-guide]

- [EKS security][eks-guidance-security]

- [Auto Mode security][eks-guidance-auto-security]

- [IAM][eks-guidance-iam]

- [Cluster access][eks-guidance-access]

- [RBAC][eks-guidance-rbac]

- [Pod security][eks-guidance-pods]

- [Runtime security][eks-guidance-runtime]

- [Network security][eks-guidance-network]

- [Image security][eks-guidance-images]

]
]

.column-half[
.small[

- [Secrets and encryption][eks-guidance-secrets]

- [Node security][eks-guidance-nodes]

- [Audit logs][eks-guidance-audit]

- [Incident response][eks-guidance-response]

- [Tenant isolation][eks-guidance-tenants]

- [Multi-account strategy][eks-guidance-accounts]

- [Upgrades][eks-guidance-upgrades]

- [IP capacity][eks-guidance-ips]

- [Application reliability][eks-guidance-reliability]

- [Autoscaling][eks-guidance-scaling]

]
]

[eks-guidance-best-practices]: https://docs.aws.amazon.com/eks/latest/best-practices/
[eks-guidance-security-guide]: https://docs.aws.amazon.com/eks/latest/best-practices/security.html
[eks-guidance-security]: https://docs.aws.amazon.com/eks/latest/userguide/security.html
[eks-guidance-auto-security]: https://docs.aws.amazon.com/eks/latest/best-practices/autosecure.html
[eks-guidance-iam]: https://docs.aws.amazon.com/eks/latest/best-practices/identity-and-access-management.html
[eks-guidance-access]: https://docs.aws.amazon.com/eks/latest/best-practices/cluster-access-management.html
[eks-guidance-rbac]: https://docs.aws.amazon.com/eks/latest/userguide/rbac-hardening.html
[eks-guidance-pods]: https://docs.aws.amazon.com/eks/latest/best-practices/pod-security.html
[eks-guidance-runtime]: https://docs.aws.amazon.com/eks/latest/best-practices/runtime-security.html
[eks-guidance-network]: https://docs.aws.amazon.com/eks/latest/best-practices/network-security.html
[eks-guidance-images]: https://docs.aws.amazon.com/eks/latest/best-practices/image-security.html
[eks-guidance-secrets]: https://docs.aws.amazon.com/eks/latest/best-practices/data-encryption-and-secrets-management.html
[eks-guidance-nodes]: https://docs.aws.amazon.com/eks/latest/best-practices/protecting-the-infrastructure.html
[eks-guidance-audit]: https://docs.aws.amazon.com/eks/latest/best-practices/auditing-and-logging.html
[eks-guidance-response]: https://docs.aws.amazon.com/eks/latest/best-practices/incident-response-and-forensics.html
[eks-guidance-tenants]: https://docs.aws.amazon.com/eks/latest/best-practices/tenant-isolation.html
[eks-guidance-accounts]: https://docs.aws.amazon.com/eks/latest/best-practices/multi-account-strategy.html
[eks-guidance-upgrades]: https://docs.aws.amazon.com/eks/latest/best-practices/cluster-upgrades.html
[eks-guidance-ips]: https://docs.aws.amazon.com/eks/latest/best-practices/ip-opt.html
[eks-guidance-reliability]: https://docs.aws.amazon.com/eks/latest/best-practices/application.html
[eks-guidance-scaling]: https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-compute.html
