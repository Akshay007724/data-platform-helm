# CI/CD & Deployment Guide

This document explains the full pipeline — from a developer pushing code to the change running in Kubernetes — and how to bootstrap it from scratch.

---

## Overview

```
Developer
  └─► git push to master
          │
          ▼
  GitHub Actions CI
    ├─ lint + test
    ├─ docker build + push → GHCR
    └─ commit image tag back to values-images.yaml
          │
          ▼
  ArgoCD detects values-images.yaml changed
    └─ helm upgrade data-platform . \
         --values values.yaml \
         --values values-images.yaml
          │
          ▼
  Kubernetes rolling update
    └─ new pods pull image from GHCR → old pods terminated
```

Two concerns are kept completely separate:
- **CI** (GitHub Actions) — builds and tests code, publishes images to GHCR
- **CD** (ArgoCD) — watches the git repo, applies the Helm chart when anything changes

The bridge between them is `values-images.yaml`, a file in the repo that CI writes image tags into and ArgoCD reads from.

---

## Repository structure for CI/CD

```
data-platform/
├── .github/workflows/
│   ├── document-processor.yml   ← CI + image push for the doc processor app
│   ├── platform-services.yml    ← CI + image push for data-ingestion / data-processor
│   └── helm-lint.yml            ← Helm lint on every PR touching the chart
├── argocd/
│   ├── project.yaml             ← ArgoCD AppProject (RBAC scope)
│   ├── application.yaml         ← ArgoCD Application (what to deploy, where, how)
│   └── ghcr-pull-secret.yaml    ← Instructions for the GHCR image pull secret
├── values.yaml                  ← Base Helm values — edited by humans
├── values-images.yaml           ← Image tags — written by CI automatically
└── apps/
    └── document-processor/
        └── docker-compose.prod.yml  ← Auto-updated with pinned GHCR image tag
```

---

## GitHub Actions workflows

### 1. `document-processor.yml`

**Triggers:** push or PR on `master` touching `apps/document-processor/**`

**Jobs:**

| Job | When | What it does |
|---|---|---|
| `ci` | always | `ruff check`, `ruff format --check`, `pytest` |
| `build-push` | push only | Builds Docker image, pushes to GHCR with `sha-<short>` and `latest` tags |
| `update-image-tag` | push to master only | Writes pinned image tag into `apps/document-processor/docker-compose.prod.yml` and commits it back |

**Image name:** `ghcr.io/<org>/data-platform/document-processor`

**Tags produced:**
- `sha-abc1234` — every push (immutable, used for rollback)
- `latest` — master branch only
- `v1.2.3` / `v1.2` — when a semver tag is pushed

---

### 2. `platform-services.yml`

**Triggers:** push or PR on `master` touching `services/data-ingestion/**` or `services/data-processor/**`. Also supports `workflow_dispatch` to manually rebuild.

**Jobs:**

| Job | Runs when |
|---|---|
| `changes` | always — detects which service dirs changed |
| `build-data-ingestion` | data-ingestion files changed |
| `build-data-processor` | data-processor files changed |
| `update-image-tags` | after either build succeeds on master |

The `update-image-tags` job uses `yq` to patch `values-images.yaml` in-place and commits the result. ArgoCD detects this commit and triggers a Helm upgrade.

**Images produced:**
- `ghcr.io/<org>/data-platform/data-ingestion:sha-<short>`
- `ghcr.io/<org>/data-platform/data-processor:sha-<short>`

---

### 3. `helm-lint.yml`

**Triggers:** PRs and pushes to `master` touching the Helm chart files.

Runs three checks:
1. `helm lint . --strict` — catches bad YAML, missing required values, deprecated APIs
2. `helm lint . --values values.yaml --values values-images.yaml --strict` — validates with both value files
3. `helm template | kubeval` — validates the rendered manifests against the Kubernetes API schema

PRs cannot be merged if lint fails.

---

## ArgoCD

### Prerequisites

- A running Kubernetes cluster (any provider — EKS, GKE, AKS, k3s, kind)
- `kubectl` configured to reach it
- Helm 3 installed locally

### 1. Install ArgoCD into the cluster

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for all pods to be ready
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=120s
```

### 2. Access the ArgoCD UI

```bash
# Port-forward the UI (or expose via LoadBalancer / Ingress for persistent access)
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Get the initial admin password
kubectl get secret argocd-initial-admin-secret -n argocd \
  -o jsonpath="{.data.password}" | base64 -d && echo

# Log in: https://localhost:8080  username: admin
```

### 3. Connect your GitHub repo

If the repo is private, add a deploy key or PAT:

```bash
# Via the ArgoCD CLI (install from https://argo-cd.readthedocs.io/en/stable/cli_installation/)
argocd login localhost:8080 --username admin --insecure

argocd repo add https://github.com/akshay007724/data-platform-helm.git \
  --username your-github-username \
  --password <github-pat-with-repo-read-scope>
```

Public repos need no credentials.

### 4. Create the GHCR image pull secret

Required only if GHCR images are private (default for private repos):

```bash
# Create the namespace first
kubectl create namespace data-platform

# Create the pull secret (needs a PAT with read:packages scope)
kubectl create secret docker-registry ghcr-pull-secret \
  --namespace data-platform \
  --docker-server=ghcr.io \
  --docker-username=<github-username-or-org> \
  --docker-password=<github-pat-read-packages>
```

For public GHCR images, skip this step and remove the `global.imagePullSecrets` parameter from `argocd/application.yaml`.

### 5. Apply the ArgoCD manifests

```bash
# Replace your-org with your actual GitHub org/username
sed -i 's/your-org/<your-github-org>/g' argocd/application.yaml argocd/project.yaml

kubectl apply -f argocd/project.yaml
kubectl apply -f argocd/application.yaml
```

ArgoCD will immediately detect the Helm chart in the repo and perform the first sync (install).

### 6. Verify the deployment

```bash
# Watch the sync in the CLI
argocd app get data-platform
argocd app sync data-platform   # force an immediate sync if needed

# Or check pods in the cluster
kubectl get pods -n data-platform
kubectl get svc  -n data-platform
```

---

## End-to-end flow: pushing a code change

```
1. Developer edits services/data-ingestion/src/main.py
2. git commit && git push origin master
3. GitHub Actions: platform-services.yml triggers
   ├─ build-data-ingestion: docker build + push
   │     → ghcr.io/<org>/data-platform/data-ingestion:sha-abc1234
   └─ update-image-tags:
         values-images.yaml updated:
           dataIngestion.image.tag: "sha-abc1234"
         → git commit: "ci(platform): update service image tags [sha: abc1234]"
         → git push
4. ArgoCD polls the repo (every 3 min) or receives a webhook
5. ArgoCD detects values-images.yaml changed → out of sync
6. ArgoCD runs: helm upgrade data-platform . \
     --values values.yaml --values values-images.yaml
7. Kubernetes performs a rolling update:
   - New pods scheduled with sha-abc1234 image
   - Old pods terminated after new pods pass readiness checks
8. ArgoCD reports: Synced / Healthy
```

---

## Rollback

Because every image is tagged with its commit SHA and `values-images.yaml` is a git file, rollback is a git revert:

```bash
# Find the last good commit to values-images.yaml
git log --oneline values-images.yaml

# Revert to it
git revert <bad-commit-sha> --no-edit
git push origin master
# ArgoCD detects the change and downgrades automatically
```

Or force an immediate ArgoCD sync to a specific git revision:

```bash
argocd app rollback data-platform <argocd-history-id>
# List history IDs with: argocd app history data-platform
```

---

## Required GitHub repository secrets

No additional secrets are needed — workflows use the built-in `GITHUB_TOKEN` which automatically has `write:packages` permission for GHCR in the same org/user. If you need to push to a different org's GHCR, set a `GHCR_TOKEN` secret and replace `secrets.GITHUB_TOKEN` in the login steps.

---

## Enabling ArgoCD webhook (optional, faster syncs)

By default ArgoCD polls every 3 minutes. For instant syncs on push:

1. In your GitHub repo: **Settings → Webhooks → Add webhook**
   - Payload URL: `https://<argocd-server>/api/webhook`
   - Content type: `application/json`
   - Events: `push`

2. In ArgoCD, set the webhook secret:
   ```bash
   kubectl patch secret argocd-secret -n argocd \
     --type merge \
     -p '{"stringData":{"webhook.github.secret":"<your-webhook-secret>"}}'
   ```

After this, ArgoCD syncs within seconds of every push.

---

## Helm-only deployment (without ArgoCD)

If you prefer to skip ArgoCD and run Helm directly:

```bash
# First install — fetch dependencies, then install
helm dependency update .
helm install data-platform . \
  --namespace data-platform \
  --create-namespace \
  --values values.yaml \
  --values values-images.yaml

# Upgrade after a new image is pushed
helm upgrade data-platform . \
  --namespace data-platform \
  --values values.yaml \
  --values values-images.yaml \
  --set dataIngestion.image.tag=sha-abc1234

# Check status
helm status data-platform -n data-platform
kubectl get pods -n data-platform

# Rollback one revision
helm rollback data-platform -n data-platform

# Rollback to a specific revision
helm history data-platform -n data-platform
helm rollback data-platform <revision-number> -n data-platform
```
