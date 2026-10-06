# The Gateway API

- The Gateway API is how Kubernetes exposes HTTP (and other) services

- It is the successor of the `Ingress` resource:

  - `Ingress` still works, but it is frozen (no new features)

  - the most used Ingress controller, ingress-nginx, reached end of life in March 2026

- It standardizes what Ingress could only do with vendor annotations:

  (header-based routing, traffic splitting, redirects, request rewrites...)

- It is implemented by many controllers:

  (Envoy Gateway, NGINX Gateway Fabric, Istio, Cilium, cloud load balancer controllers...)

---

## Gateway API resources

- Each resource belongs to a different role (or "persona"):

- `GatewayClass` = a type of gateway (infrastructure provider)

  (e.g. "Envoy proxy in the cluster", or "AWS Application Load Balancer")

- `Gateway` = how traffic enters the cluster: addresses, ports, TLS (cluster operator)

  (it often creates a cloud load balancer, or a `LoadBalancer` Service)

- `HTTPRoute` = which requests go to which `Service` (application developer)

- `Service` = our good old Kubernetes Service

- Developers can change their routes without access to the `Gateway`

---

## An `HTTPRoute` example

.small[
```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: shop
spec:
  parentRefs:                    # which Gateway(s) this route attaches to
  - name: public
    namespace: gateways
  hostnames: [ "shop.example.com" ]
  rules:
  - matches:
    - path: { type: PathPrefix, value: /api }
    backendRefs:                 # 90% to v1, 10% to v2 (canary)
    - { name: api-v1, port: 80, weight: 90 }
    - { name: api-v2, port: 80, weight: 10 }
  - backendRefs:                 # everything else
    - { name: web, port: 80 }
```
]

---

## What routes can do

- Match requests on path, headers, query parameters, method

- Split traffic between Services with weights (canary, blue/green)

- Redirect requests (e.g. HTTP → HTTPS) or rewrite paths and hostnames

- Add, change, or remove request and response headers

- Mirror a copy of requests to another Service (for testing)

- Other route types: `GRPCRoute`, `TLSRoute`, `TCPRoute`, `UDPRoute`

- Features are tagged `Core` (all controllers) or `Extended` (optional)

  (check what your controller supports before you rely on a feature)

---

## Guardrails: who can use a `Gateway`?

- With `Ingress`, any `Ingress` in any Namespace can claim any hostname

  (e.g. a dev Namespace could "steal" traffic for a production hostname)

- A `Gateway` decides which Namespaces can attach routes to it:

  - `Same`: only routes in the Gateway's Namespace (the default)

  - `Selector`: only Namespaces with specific labels

  - `All`: any Namespace (like `Ingress`)

- With RBAC, platform teams own `Gateways`; app teams own their `HTTPRoutes`

???

:EN:- The Gateway API (short version)
:FR:- La Gateway API (version courte)
