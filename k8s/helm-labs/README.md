# Helm lab examples

These examples support the Helm chapters in `slides/k8s/`. Use Helm 4.3.0
and the Linux kubeadm student VM.

- `schema-check/`: small chart with a closed values schema. Its defaults pass
  validation. The slide lab rejects wrong types, invalid pull policies,
  and unknown keys with client dry runs.
- `component-values/`: common and component settings for a chart generated
  by `helm create helmcoins`. The files pin images, configure names and ports,
  and replace the scaffold's NGINX probes with TCP probes or no probe.
- `redis/`: local, ephemeral Redis dependency with a configurable resource name.
- `dockercoins-deps/`: four DockerCoins components plus the local Redis
  dependency. `Chart.lock` pins the dependency. Keep `redis/` beside it so the
  `file://../redis` reference works. Generated `charts/` archives are ignored.

Run `cd slides && make helm-labs-check` from the repository root to build the
locked dependency and lint/render the checked-in charts. This check does
not deploy resources. The slide chapters contain the cluster exercises;
run them through the existing `make labtest` target with an approved lab tag.

The DockerCoins images use `v0.1`; Redis uses `8.2.2`. Tags improve
repeatability but can be moved by a publisher. Production deployments should
use reviewed immutable image digests and retained chart artifacts.

Redis has no persistence, authentication, or TLS in this lab. The parent
chart uses fixed DockerCoins names, so deploy one copy per namespace.
This is a dependency lesson, not a production Redis configuration.
