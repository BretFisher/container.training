<!-- verified: 2026-10-05 -->
# The Gateway API

- The Gateway API is how Kubernetes exposes HTTP (and other) services

- It is the successor of the `Ingress` resource:

  - `Ingress` still works, but it is frozen (no new features)

  - the most used Ingress controller, ingress-nginx, reached end of life in March 2026

- Gateway API handles what Ingress could only do with vendor extensions:

  (header-based routing, traffic splitting, request rewrites...)

---

## Gateway API in a nutshell

- Handle HTTP, GRPC, TCP, TLS, UDP routes (HTTP and GRPC are the most supported)

- Finer-grained permission model

  (e.g. define which namespaces can use a specific "gateway"; more on that later)

- Standardize more "core" features than Ingress

  (header-based routing, traffic weighing, rewrite requests and responses...)

- Pave the way for further extension thanks to different feature sets

  (`Core` vs `Extended` vs `Implementation-specific`)

- Can also be used for service meshes

---

## Gateway API personas

- Gateway API [formally defines three personas][gateway-personas]:

  - infrastructure provider
    <br/>
    (~network admin; potentially works within managed providers)

  - cluster operator
    <br/>
    (~Kubernetes admin; potentially manages multiple clusters)

  - application developer

- Each persona owns different resources (next slides)

[gateway-personas]: https://gateway-api.sigs.k8s.io/docs/concepts/roles-and-personas/

---

class: pic

## Gateway API resources

![Diagram showing GatewayClass, Gateway, HTTPRoute, Service](https://gateway-api.sigs.k8s.io/images/resource-model.png)

---

## Gateway API resources

- `Service` = our good old Kubernetes service

- `HTTPRoute` = describes which requests should go to which `Service`

  (created by application developers)

- `Gateway` = how traffic enters the system

  (could correspond to e.g. a `LoadBalancer` `Service`; created by cluster operators)

- `GatewayClass` = represents different types of `Gateways`

  (many gateway controllers will offer only one)

---

## `HTTPRoute` anatomy

- `spec.parentRefs` = where requests come from

  - typically a single `Gateway`

  - could be multiple `Gateway` resources

  - can also be a `Service` (for cluster mesh uses)

- `spec.hostnames` = which hosts (HTTP `Host:` header) this applies to

- `spec.rules[].matches` = which requests this applies to (match paths, headers...)

- `spec.rules[].filters` = optional transformations (change headers, rewrite URI...)

- `spec.rules[].backendRefs` = where requests go to

---

## Our Gateway controller: Envoy Gateway

- Many controllers implement the Gateway API

  (Envoy Gateway, NGINX Gateway Fabric, Istio, cloud load balancer controllers...)

- We'll use [Envoy Gateway][envoy-gateway], part of the CNCF Envoy project

  (it runs in any cluster, and it's common on EKS too)

- It watches `Gateway` resources, and runs an Envoy proxy for each `Gateway`

- Our lab clusters don't have a cloud load balancer

- So we'll run the proxy on every node, receiving traffic on port 80 (`hostPort`)

[envoy-gateway]: https://gateway.envoyproxy.io/

---

## Installing Envoy Gateway

<!-- ##VERSION## https://github.com/envoyproxy/gateway/releases -->

.lab[

- Install Envoy Gateway with its Helm chart (it also installs the Gateway API CRDs):
  ```bash
    helm upgrade --install eg oci://docker.io/envoyproxy/gateway-helm \
         --version v1.9.2 --namespace envoy-gateway-system --create-namespace
  ```

- Wait until the controller is ready:
  ```bash
    kubectl wait --namespace envoy-gateway-system \
            deployment/envoy-gateway --for=condition=Available
  ```

]

---

## Creating our Gateway

- @@LINK[k8s/envoy-gateway.yaml] defines an `EnvoyProxy` (one proxy per node, on port 80),

  a `GatewayClass` named `eg`, and a `Gateway` named `eg` (accepting routes from all namespaces)

.lab[

- Create these resources, and wait until the `Gateway` is ready:
  ```bash
  kubectl apply -f ~/container.training/k8s/envoy-gateway.yaml
  kubectl wait --namespace envoy-gateway-system \
          gateway/eg --for=condition=Programmed
  ```

- Send a request to the proxy (we should get a 404, since there are no routes yet):
  ```bash
  curl -i localhost
  ```

]

---

## Two apps to route to

.lab[

- Create a `blue` and a `green` Deployment and Service

  (`blue` may already exist from an earlier chapter)
  ```bash
  kubectl create deployment blue --image=jpetazzo/color
  kubectl expose deployment blue --port=80
  kubectl create deployment green --image=jpetazzo/color
  kubectl expose deployment green --port=80
  ```

]

---

## A basic HTTP route

.lab[

- Send all requests to `blue`:
  ```bash
    kubectl apply -f- <<EOF
    apiVersion: gateway.networking.k8s.io/v1
    kind: HTTPRoute
    metadata:
      name: blue
    spec:
      parentRefs: [ { name: eg, namespace: envoy-gateway-system } ]
      rules: [ { backendRefs: [ { name: blue, port: 80 } ] } ]
    EOF
  ```

]

---

## Testing our route

.lab[

- Check that the route was accepted by the `Gateway`:
  ```bash
  kubectl describe httproute blue | grep -A3 Conditions
  ```

- Send a request to the proxy:
  ```bash
  curl localhost
  ```

- Send a request to any node, from our computer:

  `http://A.B.C.D/` (with the IP address of any of our nodes)

]

We should get a response from the `blue` pod.

---

## Matching paths and headers

```yaml
@@INCLUDE[k8s/gateway-route-matches.yaml]
```

---

## Matching paths and headers in action

.lab[

- Update our route:
  ```bash
  kubectl apply -f ~/container.training/k8s/gateway-route-matches.yaml
  ```

- Check which pod answers each request:
  ```bash
  curl -s localhost | grep -o "This is pod [^ ]*"
  curl -s localhost/green | grep -o "This is pod [^ ]*"
  curl -s localhost/greenhouse | grep -o "This is pod [^ ]*"
  curl -s -H "x-color: green" localhost | grep -o "This is pod [^ ]*"
  ```

]

`/greenhouse` goes to `blue`: `PathPrefix` matches whole path elements, not characters.

---

## Traffic splitting

- Let's send 90% of the requests to `blue` and 10% to `green` (e.g. for a canary)

```yaml
@@INCLUDE[k8s/gateway-route-canary.yaml]
```

---

## Traffic splitting in action

- This route only applies to requests for `canary.example.com`

- We don't need a DNS record: we can set the `Host:` header with `curl`

.lab[

- Create the route:
  ```bash
  kubectl apply -f ~/container.training/k8s/gateway-route-canary.yaml
  ```

- Send 100 requests, and count which pod answered:
  ```bash
    for i in $(seq 100); do
      curl -s -H "Host: canary.example.com" localhost | grep -o "pod [a-z]*/[a-z]*"
    done | sort | uniq -c
  ```

]

---

## On EKS

- The `GatewayClass`, `Gateway`, and `HTTPRoute` resources stay the same

- With Envoy Gateway, the only change is how traffic reaches the proxy:

  - the proxy runs with a `Deployment` (the default) behind a `LoadBalancer` `Service`

  - the AWS Load Balancer Controller provisions an NLB for that `Service`

- AWS also has its own Gateway controller: the AWS Load Balancer Controller

  - `GatewayClass` controller `gateway.k8s.aws/alb` provisions a managed ALB

  - no proxy in the cluster; TLS certificates can come from ACM

- Either way, application developers write the same `HTTPRoute` resources

---

## `Core` vs `Extended` vs `Implementation-specific`

- All Gateway controllers must support `Core` features

- Some optional features are in the `Extended` set:

  - they may or may not be supported

  - but at least, their specification is part of the API definition

- Gateway controllers can also have `Implementation-specific` features

  (=proprietary extensions)

- In the following slides, we'll tag features with `Core` or `Extended`

---

## `HTTPRoute.spec.rules[].matches`

Some fields are part of the `Core` set; some are part of the `Extended` set.

```yaml
match:
  path:                   # Core
    value: /hello
    type: PathPrefix      # default value; can also be "Exact"
  headers:                # Core
  - name: x-custom-header
    value: foo
  queryParams:            # Extended
  - type: Exact           # can also have implementation-specific values, e.g. Regex
    name: product
    value: pizza
  method: GET             # Extended
```

---

## `HTTPRoute.spec.rules[].filters.*HeaderModifier`

`RequestHeaderModifier` is `Core`

`ResponseHeaderModifier` is `Extended`

```yaml
type: RequestHeaderModifier       # or ResponseHeaderModifier
requestHeaderModifier:            # or responseHeaderModifier
  set:                            # replace an existing header
  - name: x-my-header
    value: hello
  add:                            # appends to an existing header
  - name: x-my-header             # (adding a comma if it's already set)
    value: hello
  remove:
  - x-my-header
```

---

## `HTTPRoute.spec.rules[].filters.RequestRedirect`

```yaml
type: RequestRedirect
requestRedirect:
  scheme: https                     # http or https
  hostname: newxyz.example.com
  path:
    type: ReplaceFullPath           # or ReplacePrefixMatch
    replaceFullPath: /new
  port: 8080
  statusCode: 302                   # default=302; 301 and 302 are Core; 303 307 308 are Extended
```

All fields are optional. Empty fields mean "leave as is".

Note that while `RequestRedirect` is `Core`, some options are `Extended`!

(See the [API specification for details][http-request-redirect].)

[http-request-redirect]: https://gateway-api.sigs.k8s.io/reference/api-spec/1.6/spec/#httprequestredirectfilter

---

## `HTTPRoute.spec.rules[].filters.URLRewrite`

```yaml
type: URLRewrite
urlRewrite:
  hostname: newxyz.example.com
  path:
    type: ReplacePrefixMatch        # or ReplaceFullPath
    replacePrefixMatch: /new
```

`hostname` will rewrite the HTTP `Host:` header.

This is an `Extended` feature.

It cannot be used in the same rule as `RequestRedirect`.

---

## `HTTPRoute.spec.rules[].filters.RequestMirror`

This is an `Extended` feature. It sends a copy of all (or a fraction) of requests to another backend. Responses from the mirrored backend are ignored.

```yaml
type: RequestMirror
requestMirror:
  percent: 10
  fraction:
    numerator: 1
    denominator: 10
  backendRef:
    group: "" # default
    kind: Service # default
    name: log-some-requests
    namespace: my-observability-namespace # defaults to same namespace
    port: 80
```

Specify `percent` or `fraction`, not both. If neither is specified, all requests get mirrored.

---

## Other routes

- `GRPCRoute` can use GRPC services and methods to route requests

  *this is useful if you're using GRPC; otherwise you can ignore it!*

- `TLSRoute` can use SNI header to route requests (without decrypting traffic)

  *this is useful to host multiple TLS services on a single address with end-to-end encryption*

- `TCPRoute` can route TCP connections

  *this is useful to colocate multiple protocols on the same address, e.g. HTTP+HTTPS+SSH*

- `UDPRoute` can route UDP packets

  *ditto, e.g. for DNS/UDP, DNS/TCP, DNS/HTTPS*

---

## `gateway.spec.listeners.allowedRoutes`

- With `Ingress`, any `Ingress` resource can "catch" traffic

- This could be a problem e.g. if a dev/staging environment accidentally (or maliciously) creates an `Ingress` with a production hostname

- Gateway API introduces guardrails

- A `Gateway` can indicate if it can be referred by routes:

  - from all namespaces (like with `Ingress`)

  - only from the same namespace

  - only from specific namespaces matching a selector

- That's why our `Gateway` has `allowedRoutes.namespaces.from: All` (see @@LINK[k8s/envoy-gateway.yaml])

???

:EN:- The Gateway API
:FR:- La Gateway API

