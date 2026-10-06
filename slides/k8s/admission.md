<!-- verified: 2026-10-05 -->
# Dynamic Admission Control

- This is one of the many ways to extend the Kubernetes API

- High level summary: dynamic admission control relies on webhooks that are ...

  - dynamic (can be added/removed on the fly)

  - running inside or outside the cluster

  - *validating* (yay/nay) or *mutating* (can change objects that are created/updated)

  - selective (can be configured to apply only to some kinds, some selectors...)

  - mandatory or optional (should it block operations when webhook is down?)

- Used for themselves (e.g. policy enforcement) or as part of operators

---

## Use cases

- Defaulting

  *injecting image pull secrets, sidecars, environment variables...*

- Policy enforcement and best practices

  *prevent: `latest` images, deprecated APIs...*

  *require: PDBs, resource requests/limits, labels/annotations, local registry...*

- Problem mitigation

  *block nodes with vulnerable kernels, inject log4j mitigations, rewrite images...*

- Extended validation for operators

---

## You said *dynamic?*

- Some admission controllers are built in the API server

- They are enabled/disabled through Kubernetes API server configuration

  (e.g. `--enable-admission-plugins`/`--disable-admission-plugins` flags)

- Here, we're talking about *dynamic* admission controllers

- They can be added/remove while the API server is running

  (without touching the configuration files or even having access to them)

- This is done through two kinds of cluster-scope resources:

  ValidatingWebhookConfiguration and MutatingWebhookConfiguration

---

## You said *webhooks?*

- A ValidatingWebhookConfiguration or MutatingWebhookConfiguration contains:

  - a resource filter
    <br/>
    (e.g. "all pods", "deployments in namespace xyz", "everything"...)

  - an operations filter
    <br/>
    (e.g. CREATE, UPDATE, DELETE)

  - the address of the webhook server

- Each time an operation matches the filters, it is sent to the webhook server

---

## What gets sent exactly?

- The API server will `POST` a JSON object to the webhook

- That object will be a Kubernetes API message with `kind` `AdmissionReview`

- It will contain a `request` field, with, notably:

  - `request.uid` (to be used when replying)

  - `request.object` (the object created/deleted/changed)

  - `request.oldObject` (when an object is modified)

  - `request.userInfo` (who was making the request to the API in the first place)

(See [the documentation](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/#request) for a detailed example showing more fields.)

.footnote[Review #104: the next diagram may replace this text after review.]

---

name: visual-admissionreview-exchange-review
class: pic

<!-- Diagram proposal #104; adjacent text retained for review. -->
![AdmissionReview exchange](images/k8s-admissionreview-exchange-2026.svg)

---

## How should the webhook respond?

- By replying with another `AdmissionReview` in JSON

- It should have a `response` field, with, notably:

  - `response.uid` (matching the `request.uid`)

  - `response.allowed` (`true`/`false`)

  - `response.status.message` (optional string; useful when denying requests)

  - `response.patchType` (when a mutating webhook changes the object: `JSONPatch`)

  - `response.patch` (the patch, encoded in base64)

---

## What if the webhook *does not* respond?

- If "something bad" happens, the API server follows the `failurePolicy` option

  - this is a per-webhook option (specified in the webhook configuration)

  - it can be `Fail` (the default) or `Ignore` ("allow all, unmodified")

- What's "something bad"?

  - webhook responds with something invalid

  - webhook takes more than 10 seconds to respond
    <br/>
    (this can be changed with `timeoutSeconds` field in the webhook config)

  - webhook is down or has invalid certificates
    <br/>
    (TLS! It's not just a good idea; for admission control, it's the law!)

---

## What did you say about TLS?

- The webhook configuration can indicate:

  - either `url` of the webhook server (has to begin with `https://`)

  - or `service.name` and `service.namespace` of a Service on the cluster

- In the latter case, the Service has to accept TLS connections on port 443

  (that's the default; it can be changed with `service.port`)

- It has to use a certificate with a `subjectAltName` extension with `DNS:<name>.<namespace>.svc`

  (the CN alone is not enough: the API server ignores it)

- The certificate needs to be valid (signed by a CA trusted by the API server)

  ... alternatively, we can pass a `caBundle` in the webhook configuration

---

## Webhook server inside or outside

- "Outside" webhook server is defined with `url` option

  - convenient for external webhooks (e.g. tamper-resistant audit trail)

  - also great for initial development (with a tunnel to a local machine)

  - requires outbound connectivity (duh) and can become a SPOF

- "Inside" webhook server is defined with `service` option

  - convenient when the webhook needs to be deployed and managed on the cluster

  - also great for air gapped clusters

  - development can be harder (but tools like [Tilt](https://tilt.dev) can help)

---

## Developing a simple admission webhook

- We're going to register a custom webhook!

- It implements a strict policy on a specific label

  (using a little Flask app)

  - if a pod sets a label `color`, it must be `blue`, `green`, `red`

  - once that `color` label is set, it cannot be removed or changed

- It also logs each `AdmissionReview` that it receives

  (so we can see what the API server sends)

- We will run it on our cluster 🔥

---

## Deploying the webhook on the cluster

- Let's see what's needed to host the webhook server on the cluster!

- The webhook needs to be reachable through a Service on our cluster

- The Service needs to accept TLS connections on port 443

- We need a proper TLS certificate:

  - with the right `CN` and `subjectAltName` (`<servicename>.<namespace>.svc`)

  - signed by a trusted CA

- We can either use a "real" CA, or use the `caBundle` option to specify the CA cert

  (the latter makes it easy to use self-signed certs)

---

## In practice

- We're going to generate a key pair and a self-signed certificate

- We will store them in a Secret

- We will run the webhook in a Deployment, exposed with a Service

- We will update the webhook configuration to use that Service

- The Service will be named `admission`, in Namespace `webhooks`

  (keep in mind that the ValidatingWebhookConfiguration itself is at cluster scope)

---

## Let's get to work!

.lab[

- Make sure we're in the right directory:
  ```bash
  cd ~/container.training/webhooks/admission
  ```

- Create the namespace:
  ```bash
  kubectl create namespace webhooks
  ```

- Switch to the namespace:
  ```bash
  kubectl config set-context --current --namespace=webhooks
  ```

]

---

## Deploying the webhook

- *Normally,* we would author an image for this

- Since our webhook is just *one* Python source file ...

  ... we'll store it in a ConfigMap, and install dependencies on the fly

.lab[

- Load the webhook source in a ConfigMap:
  ```bash
  kubectl create configmap admission --from-file=flask/webhook.py
  ```

- Create the Deployment and Service:
  ```bash
  kubectl apply -f k8s/webhook-server.yaml
  ```

]

---

## Generating the key pair and certificate

- Let's call OpenSSL to the rescue!

  (of course, there are plenty others options; e.g. `cfssl`)

.lab[

- Generate a self-signed certificate:
  ```bash
    NAMESPACE=webhooks
    SERVICE=admission
    CN=$SERVICE.$NAMESPACE.svc
    openssl req -x509 -newkey rsa:4096 -nodes -keyout key.pem -out cert.pem \
        -days 30 -subj /CN=$CN -addext subjectAltName=DNS:$CN
  ```

- Load up the key and cert in a Secret:
  ```bash
  kubectl create secret tls admission --cert=cert.pem --key=key.pem
  ```

]

---

## Register the webhook configuration

- Our webhook configuration is in `k8s/webhook-configuration.yaml`

- It sends CREATE and UPDATE on Pods (in all Namespaces) to our Service

- Just after we register the webhook, it will be called for each matching request

- The `failurePolicy` is `Ignore`

  (so if the webhook server is down, we can still create pods)

.lab[

- Register the webhook:
  ```bash
  kubectl apply -f k8s/webhook-configuration.yaml
  ```

]

---

## Add our self-signed cert to the `caBundle`

- The API server won't accept our self-signed certificate

- We need to add it to the `caBundle` field in the webhook configuration

- The `caBundle` will be our `cert.pem` file, encoded in base64

---

Shell to the rescue!

.lab[

- Load up our cert and encode it in base64:
  ```bash
  CA=$(base64 -w0 < cert.pem)
  ```

- Define a patch operation to update the `caBundle`:
  ```bash
    PATCH='[{
        "op": "replace",
        "path": "/webhooks/0/clientConfig/caBundle",
        "value":"'$CA'"
    }]'
  ```

- Patch the webhook configuration:
  ```bash
    kubectl patch validatingwebhookconfiguration \
                  admission.webhook.container.training \
                  --type='json' -p="$PATCH"
  ```

]

---

## Try it out!

.lab[

- Wait until the webhook server is ready (it installs Flask when it starts):
  ```bash
  kubectl rollout status deployment admission
  ```

<!-- ```timeout 300``` -->

- Create a pod named `chroma`:
  ```bash
  kubectl run --restart=Never chroma --image=nginx
  ```

- Try to add a label `color` set to `pink`:
  ```bash
  kubectl label pod chroma color=pink
  ```

<!-- ```expect-fail``` -->

- Add a label `color` set to `red`:
  ```bash
  kubectl label pod chroma color=red
  ```

- Try to change it to `blue`:
  ```bash
  kubectl label pod chroma color=blue --overwrite
  ```

<!-- ```expect-fail``` -->

]

---

## What did the webhook receive?

- The webhook logs each `AdmissionReview` (in YAML)

- Each one is long (a few hundred lines), so let's look at its structure first

.lab[

- Show the top-level fields of the last `AdmissionReview`:
  ```bash
  kubectl logs deployment/admission | grep -E '^[a-zA-Z]|^  [a-zA-Z]' | tail -20
  ```

]

- Find `operation: UPDATE`, `object:` and `oldObject:` in the request

  (the webhook compares the labels of `oldObject` and `object`)

- Use `kubectl logs deployment/admission | less` to see everything

---

## Cleaning up

- Our webhook checks every Pod in every Namespace

- Let's remove it, so that it doesn't affect the next labs

.lab[

- Remove the webhook configuration:
  ```bash
  kubectl delete validatingwebhookconfiguration admission.webhook.container.training
  ```

- Switch back to the `default` Namespace:
  ```bash
  kubectl config set-context --current --namespace=default
  ```

]

---

## Real world examples

- [kube-image-keeper][kuik] rewrites image references to use mirrored images

  (e.g. when the source registry is unavailable)

- [Kyverno] implements very extensive policies

  (validation, generation... it deserves a whole chapter on its own!)

[kuik]: https://github.com/enix/kube-image-keeper
[kyverno]: https://kyverno.io/

---

## Alternatives

- Kubernetes Validating Admission Policies

- Relatively recent (alpha: 1.26, beta: 1.28, GA: 1.30)

- Declare validation rules with Common Expression Language ([CEL][cel-spec])

- Validation is done entirely within the API server

  (no external webhook = no latency, no deployment complexity...)

- Mutating Admission Policies do the same for mutations (GA: 1.36)

- Not as powerful as full-fledged webhook engines like Kyverno

  (see e.g. [this page of the Kyverno doc][kyverno-vap] for a comparison)

[kyverno-vap]: https://kyverno.io/docs/policy-types/validating-policy/
[cel-spec]: https://github.com/cel-expr/cel-spec

???

:EN:- Dynamic admission control with webhooks
:FR:- Contrôle d'admission dynamique (webhooks)
