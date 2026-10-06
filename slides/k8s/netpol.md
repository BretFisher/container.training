<!-- verified: 2026-10-05 -->
# Network policies

- Namespaces help us to *organize* resources

- Namespaces do not provide isolation

- By default, every pod can contact every other pod

- By default, every service accepts traffic from anyone

- If we want this to be different, we need *network policies*

---

## What's a network policy?

A network policy is defined by the following things.

- A *pod selector* indicating which pods it applies to

  e.g.: "all pods in namespace `blue` with the label `zone=internal`"

- A list of *ingress rules* indicating which inbound traffic is allowed

  e.g.: "TCP connections to ports 8000 and 8080 coming from pods with label `zone=dmz`,
  and from the external subnet 4.42.6.0/24, except 4.42.6.5"

- A list of *egress rules* indicating which outbound traffic is allowed

A network policy can provide ingress rules, egress rules, or both.

---

## How do network policies apply?

- A pod can be "selected" by any number of network policies

- If a pod isn't selected by any network policy, then its traffic is unrestricted

  (In other words: in the absence of network policies, all traffic is allowed)

- If a pod is selected by at least one network policy, then all traffic is blocked ...

  ... unless it is explicitly allowed by one of these network policies

---

class: extra-details

## Traffic filtering is flow-oriented

- Network policies deal with *connections*, not individual packets

- Example: to allow HTTP (80/tcp) connections to pod A, you only need an ingress rule

  (You do not need a matching egress rule to allow response traffic to go through)

- This also applies for UDP traffic

  (Allowing DNS traffic can be done with a single rule)

- Network policy implementations use stateful connection tracking

---

## Pod-to-pod traffic

- Connections from pod A to pod B have to be allowed by both pods:

  - pod A has to be unrestricted, or allow the connection as an *egress* rule

  - pod B has to be unrestricted, or allow the connection as an *ingress* rule

- As a consequence: if a network policy restricts traffic going from/to a pod,
  <br/>
  the restriction cannot be overridden by a network policy selecting another pod

- This prevents an entity managing network policies in namespace A
  (but without permission to do so in namespace B)
  from adding network policies giving them access to namespace B

---

## The rationale for network policies

- In network security, it is generally considered better to "deny all, then allow selectively"

  (The other approach, "allow all, then block selectively" makes it too easy to leave holes)

- As soon as one network policy selects a pod, the pod enters this "deny all" logic

- Further network policies can open additional access

- Good network policies should be scoped as precisely as possible

- In particular: make sure that the selector is not too broad

  (Otherwise, you end up affecting pods that were otherwise well secured)

---

## Our first network policy

This is our game plan:

- run a web server in a pod

- create a network policy to block all access to the web server

- create another network policy to allow access only from specific pods

---

## Running our test web server

.lab[

- Let's use the `nginx` image:
  ```bash
  kubectl create deployment testweb --image=nginx
  ```

<!--
```bash
kubectl wait deployment testweb --for condition=available
```
-->

- Find out the IP address of the pod with one of these two commands:
  ```bash
  kubectl get pods -o wide -l app=testweb
  IP=$(kubectl get pods -l app=testweb -o json | jq -r .items[0].status.podIP)
  ```

- Check that we can connect to the server:
  ```bash
  curl $IP
  ```
]

The `curl` command should show us the "Welcome to nginx!" page.

---

## Adding a very restrictive network policy

- The policy will select pods with the label `app=testweb`

- It will specify an empty list of ingress rules (matching nothing)

.lab[

- Apply the policy in this YAML file:
  ```bash
    kubectl apply -f ~/container.training/k8s/netpol-deny-all-for-testweb.yaml
  ```

- Check if we can still access the server:
  ```bash
  curl -m3 $IP
  ```

<!-- ```expect-fail``` -->

]

The `curl` command should now time out after 3 seconds.

---

## Looking at the network policy

This is the file that we applied:

```yaml
@@INCLUDE[k8s/netpol-deny-all-for-testweb.yaml]
```

---

## Allowing connections only from specific pods

- We want to allow traffic from pods with the label `run=testcurl`

- Reminder: this label is automatically applied when we do `kubectl run testcurl ...`

.lab[

- Apply another policy:
  ```bash
  kubectl apply -f ~/container.training/k8s/netpol-allow-testcurl-for-testweb.yaml
  ```

]

---

## Looking at the network policy

This is the second file that we applied:

```yaml
@@INCLUDE[k8s/netpol-allow-testcurl-for-testweb.yaml]
```

---

## Testing the network policy

- Let's create pods with, and without, the required label

.lab[

- Try to connect to testweb from a pod with the `run=testcurl` label:
  ```bash
  kubectl run testcurl --rm -i --restart=Never --image=curlimages/curl -- curl -m3 $IP
  ```

- Try to connect to testweb with a different label:
  ```bash
  kubectl run testkurl --rm -i --restart=Never --image=curlimages/curl -- curl -m3 $IP
  ```

<!-- ```expect-fail``` -->

]

The first command will work (and show the "Welcome to nginx!" page).

The second command will fail and time out after 3 seconds.

(The timeout is obtained with the `-m3` option.)

---

## An important warning

- Network policies are enforced by the network plugin (CNI)

- Some network plugins don't enforce network policies at all

  (e.g. Flannel on its own)

- Some only enforce them when the feature is turned on

  (e.g. on AWS EKS, the VPC CNI needs `enableNetworkPolicy` set to `true`)

- Unsupported features might be silently ignored

  (Making you believe that you are secure, when you're not)

---

## Network policies, pods, and services

- Network policies apply to *pods*

- A *service* can select multiple pods

  (And load balance traffic across them)

- It is possible that we can connect to some pods, but not some others

  (Because of how network policies have been defined for these pods)

- In that case, connections to the service will randomly pass or fail

  (Depending on whether the connection was sent to a pod that we have access to or not)

---

## Network policies and namespaces

- A good strategy is to isolate a namespace, so that:

  - all the pods in the namespace can communicate together

  - other namespaces cannot access the pods

  - external access has to be enabled explicitly

- Let's see what this would look like for the DockerCoins app!

---

## Network policies for DockerCoins

- We are going to apply two policies

- The first policy will prevent traffic from other namespaces

- The second policy will allow traffic to the `webui` pods

- That's all we need for that app!

---

## Blocking traffic from other namespaces

This policy selects all pods in the current namespace.

It allows traffic only from pods in the current namespace.

(An empty `podSelector` means "all pods.")

```yaml
kind: NetworkPolicy
apiVersion: networking.k8s.io/v1
metadata:
  name: deny-from-other-namespaces
spec:
  podSelector: {}
  ingress:
  - from:
    - podSelector: {}
```

---

## Allowing traffic to `webui` pods

This policy selects all pods with label `app=webui`.

It allows traffic from any source.

(An empty `from` field means "all sources.")

```yaml
kind: NetworkPolicy
apiVersion: networking.k8s.io/v1
metadata:
  name: allow-webui
spec:
  podSelector:
    matchLabels:
      app: webui
  ingress:
  - from: []
```

---

## Applying both network policies

- Both network policies are declared in the file @@LINK[k8s/netpol-dockercoins.yaml]

.lab[

- Apply the network policies:
  ```bash
  kubectl apply -f ~/container.training/k8s/netpol-dockercoins.yaml
  ```

- Check that we can still access the web UI from outside
  <br/>
  (and that the app is still working correctly!)

- Check that we can't connect anymore to `rng` or `hasher` through their ClusterIP

]

Note: using `kubectl port-forward` allows us to connect
regardless of existing network policies. This allows us to debug and
troubleshoot easily, without having to poke holes in our firewall.

---

## Cleaning up our network policies

- The network policies that we have installed block all traffic to the default namespace

- We should remove them, otherwise further demos and exercises will fail!

.lab[

- Remove all network policies:
  ```bash
  kubectl delete networkpolicies --all
  ```

]

---

## Default deny: a better starting point

- The DockerCoins policies only filter *ingress* (inbound) traffic

- Our pods can still connect to anything: other namespaces, the internet...

  (e.g. a compromised pod can download tools, or send data out)

- A common baseline is to deny *all* traffic, in both directions, in each namespace

- Then, we add policies to allow each flow that we need

- But careful: with "deny all egress", pods can't reach CoreDNS

  (name resolution fails, and most apps break in confusing ways!)

- So, the first egress policy that we need will allow DNS

---

## A default deny policy

```yaml
@@INCLUDE[k8s/netpol-default-deny.yaml]
```

- An empty `podSelector` selects all the pods in the Namespace

- `policyTypes` is needed here, because the policy has no rules

  (without it, a policy with no `egress` rules doesn't restrict egress)

---

## Allowing DNS

.small[
```yaml
@@INCLUDE[k8s/netpol-allow-dns.yaml]
```
]

- Kubernetes adds the label `kubernetes.io/metadata.name` to every Namespace (to select it by name)

---

## Selectors: AND vs. OR

- In the previous policy, `namespaceSelector` and `podSelector` are in the *same* item:

  "pods with label `k8s-app=kube-dns` **AND** in Namespace `kube-system`"

- With a `-` before `podSelector`, they would be *two* items:

  "pods in Namespace `kube-system` **OR** pods with label `k8s-app=kube-dns` (in our Namespace)"

- One extra `-` can open much more traffic than we wanted!

- Always check the result with `kubectl describe networkpolicy`

  (it shows how Kubernetes understood the rules)

---

## Testing default deny and DNS

.lab[

- Create a Namespace and apply the default deny policy:
  ```bash
  kubectl create namespace egress-lab
  kubectl apply -n egress-lab -f ~/container.training/k8s/netpol-default-deny.yaml
  ```

- Try to resolve a name (this should fail after a few seconds):
  ```bash
  kubectl run -n egress-lab dns1 --rm -i --restart=Never --image=busybox \
          -- nslookup -type=a kubernetes.io.
  ```

<!-- ```expect-fail``` -->

]

---

## Testing the DNS policy

.lab[

- Apply the DNS policy, then try again (this should work):
  ```bash
  kubectl apply -n egress-lab -f ~/container.training/k8s/netpol-allow-dns.yaml
  kubectl run -n egress-lab dns2 --rm -i --restart=Never --image=busybox \
          -- nslookup -type=a kubernetes.io.
  ```

- Try to connect to the website (this should still fail):
  ```bash
  kubectl run -n egress-lab web1 --rm -i --restart=Never --image=busybox \
          -- wget -T3 -O- http://kubernetes.io
  ```

<!-- ```expect-fail``` -->

- Clean up:
  ```bash
  kubectl delete namespace egress-lab
  ```

]

---

## Cluster-wide policies (what's coming)

- NetworkPolicies are *namespaced*: the owner of a Namespace controls them

- Platform teams also need rules that Namespace owners can't change

- SIG Network is working on `ClusterNetworkPolicy` (`v1alpha2` in 2026)

  - a cluster-scoped resource, managed by cluster admins

  - `Admin` tier: evaluated *before* NetworkPolicies (can't be overridden)

  - `Baseline` tier: evaluated *after* NetworkPolicies (default rules)

  - actions: `Accept`, `Deny`, `Pass`

- It's alpha: check that your network plugin supports it before using it

---

class: extra-details

## `ClusterNetworkPolicy` example

Monitoring can always connect to every Namespace (even if a NetworkPolicy denies it):

.small[
```yaml
apiVersion: policy.networking.k8s.io/v1alpha2
kind: ClusterNetworkPolicy
metadata:
  name: allow-monitoring
spec:
  tier: Admin
  priority: 10
  subject:
    namespaces: {}
  ingress:
  - name: allow-from-monitoring
    action: Accept
    from:
    - namespaces:
        matchLabels:
          kubernetes.io/metadata.name: monitoring
```
]

---

## Protecting the control plane

- Should we add network policies to block unauthorized access to the control plane?

  (etcd, API server, etc.)

--

- At first, it seems like a good idea ...

--

- But it *shouldn't* be necessary:

  - not all network plugins support network policies

  - the control plane is secured by other methods (mutual TLS, mostly)

  - the code running in our pods can reasonably expect to contact the API
    <br/>
    (and it can do so safely thanks to the API permission model)

- If we block access to the control plane, we might disrupt legitimate code

- ...Without necessarily improving security

---

## Tools and resources

- [Cilium Network Policy Editor](https://editor.networkpolicy.io/)

- Two resources by [Ahmet Alp Balkan](https://ahmet.im/):

  - a [very good talk about network policies](https://www.youtube.com/watch?list=PLj6h78yzYM2P-3-xqvmWaZbbI1sW-ulZb&v=3gGpMmYeEO8) at KubeCon North America 2017

  - a repository of [ready-to-use recipes](https://github.com/ahmetb/kubernetes-network-policy-recipes) for network policies

---

## Documentation

- As always, the [Kubernetes documentation](https://kubernetes.io/docs/concepts/services-networking/network-policies/) is a good starting point

- The API documentation has a lot of detail about the format of various objects: <!-- ##VERSION## -->

  - [NetworkPolicy](https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.37/#networkpolicy-v1-networking-k8s-io)

  - [NetworkPolicySpec](https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.37/#networkpolicyspec-v1-networking-k8s-io)

  - [NetworkPolicyIngressRule](https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.37/#networkpolicyingressrule-v1-networking-k8s-io)

  - etc.

???

:EN:- Isolating workloads with Network Policies
:FR:- Isolation réseau avec les *network policies*
