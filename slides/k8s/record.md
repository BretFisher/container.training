# Recording deployment actions

- Each rollout of a Deployment creates a new ReplicaSet (a *revision*)

- `kubectl rollout history` lists these revisions

- Its `CHANGE-CAUSE` column comes from the annotation `kubernetes.io/change-cause`

  (we set it on the Deployment; Kubernetes copies it to the current ReplicaSet)

- Kubernetes doesn't set it for us: we (or our tooling) set it at each change

- Note: `kubectl --record` used to set it automatically; that flag is deprecated

---

## Recording a change

.lab[

- Roll back `worker` to image version 0.1, and record why:
  ```bash
  kubectl set image deployment worker worker=dockercoins/worker:v0.1
  kubectl annotate deployment worker --overwrite \
          kubernetes.io/change-cause="Roll back to v0.1"
  ```

- Promote it to version 0.2 again:
  ```bash
  kubectl set image deployment worker worker=dockercoins/worker:v0.2
  kubectl annotate deployment worker --overwrite \
          kubernetes.io/change-cause="Promote to v0.2"
  ```

- View the change history:
  ```bash
  kubectl rollout history deployment worker
  ```

]

---

## One change cause for each change

- Set the annotation *after* the change that creates the new revision

  (an annotation alone doesn't create a revision; it updates the current one)

- If we forget it, the new revision gets the *previous* change cause

  (the history then shows a wrong reason for that revision)

- Changes that don't create a revision (e.g. `kubectl scale`) aren't in the history

- In practice, set it in our tooling, in the same change as the update:

  - `metadata.annotations` in the YAML that our CI or GitOps tool applies

  - for example, with the commit message or the pull request title
