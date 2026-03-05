# Deploy — GHCR + Flux GitOps

End-to-end guide to push the document-processor image to GitHub Container Registry (GHCR) and run it on Kubernetes using Flux.

---

## How it works

```
git push to master
      │
      ▼
GitHub Actions CI
  lint → test → docker build → push to GHCR
  ghcr.io/akshay007724/data-platform/document-processor:sha-abc1234
      │
      ▼
Flux (running in cluster) detects new tag via ImageRepository
      │
      ▼
ImagePolicy selects newest sha-* tag
      │
      ▼
ImageUpdateAutomation writes new tag into k8s/app.yaml → commits to master
      │
      ▼
Kustomization detects git change → applies updated manifests
      │
      ▼
Kubernetes rolling update → new pod pulls image from GHCR
```

---

## Prerequisites

| Tool | Install |
|---|---|
| Docker Desktop | docker.com/products/docker-desktop |
| kubectl | included with Docker Desktop |
| Flux CLI | `brew install fluxcd/tap/flux` |
| GitHub account | github.com |

Enable Kubernetes in Docker Desktop:
**Docker Desktop → Settings → Kubernetes → Enable Kubernetes → Apply**

Wait ~2 minutes for Kubernetes to start, then verify:

```bash
kubectl get nodes
# NAME             STATUS   ROLES           AGE
# docker-desktop   Ready    control-plane   2m
```

---

## Step 1 — Create a GitHub Personal Access Token

Go to: **github.com → Settings → Developer Settings → Personal access tokens → Tokens (classic)**

Click **Generate new token (classic)** with these scopes:
- `repo` — full repository access (Flux needs to commit image tags back)
- `write:packages` — push images to GHCR
- `read:packages` — pull images from GHCR

Copy the token — you will use it in Steps 2 and 4.

---

## Step 2 — Bootstrap Flux into your cluster

Flux installs itself into the cluster and starts watching your GitHub repo.

```bash
export GITHUB_TOKEN=<your-pat-from-step-1>
export GITHUB_USER=akshay007724

flux bootstrap github \
  --owner=$GITHUB_USER \
  --repository=data-platform-helm \
  --branch=master \
  --path=flux/clusters/local \
  --personal \
  --token-auth
```

**What this does:**
- Installs Flux controllers into the `flux-system` namespace
- Creates a `flux-system` secret with your GitHub token (for reading and writing the repo)
- Commits a `flux-system/` folder into `flux/clusters/local/` in your repo
- Flux immediately starts watching that path for resources to apply

Verify Flux is running:

```bash
flux check
# ► checking prerequisites
# ✔ Kubernetes 1.31.0 >=1.28.0-0
# ► checking controllers
# ✔ helm-controller: deployment ready
# ✔ kustomize-controller: deployment ready
# ✔ notification-controller: deployment ready
# ✔ source-controller: deployment ready
# ✔ image-automation-controller: deployment ready
# ✔ image-reflector-controller: deployment ready
# ✔ all checks passed
```

---

## Step 3 — Create the GHCR pull secret for Kubernetes

The cluster needs credentials to pull the image from GHCR (required for private images).

```bash
kubectl create namespace document-processor

kubectl create secret docker-registry ghcr-pull-secret \
  --namespace document-processor \
  --docker-server=ghcr.io \
  --docker-username=akshay007724 \
  --docker-password=<your-pat-from-step-1>
```

---

## Step 4 — Create the GHCR auth secret for Flux image scanning

Flux needs separate credentials to scan GHCR for new image tags.

```bash
kubectl create secret docker-registry ghcr-flux-auth \
  --namespace flux-system \
  --docker-server=ghcr.io \
  --docker-username=akshay007724 \
  --docker-password=<your-pat-from-step-1>
```

---

## Step 5 — Apply the Flux manifests

```bash
cd /Users/akshayfiles/Desktop/claude_code

kubectl apply -f flux/clusters/local/document-processor/gitrepository.yaml
kubectl apply -f flux/clusters/local/document-processor/kustomization.yaml
kubectl apply -f flux/clusters/local/document-processor/imagerepository.yaml
kubectl apply -f flux/clusters/local/document-processor/imagepolicy.yaml
kubectl apply -f flux/clusters/local/document-processor/imageupdateauto.yaml
```

Verify they are ready:

```bash
flux get sources git
flux get kustomizations
flux get image repositories
flux get image policies
```

---

## Step 6 — Push code to trigger the CI pipeline

Any push to `master` touching `data-platform/apps/document-processor/**` triggers the GitHub Actions workflow, which builds the Docker image and pushes it to GHCR.

```bash
cd /Users/akshayfiles/Desktop/claude_code

# Make any change to the app to trigger CI
git add .
git commit -m "feat: initial deployment"
git pull --rebase origin master
git push origin master
```

Watch the CI pipeline:
**github.com/akshay007724/data-platform-helm/actions**

Once the image is pushed to GHCR, Flux picks up the new tag within 1 minute, updates `k8s/app.yaml` with the new SHA tag, commits it back to master, and applies the updated deployment to Kubernetes.

---

## Step 7 — Verify the deployment

```bash
# Check all pods are running
kubectl get pods -n document-processor

# Expected output:
# NAME                        READY   STATUS    RESTARTS
# chromadb-xxx                1/1     Running   0
# ollama-xxx                  1/1     Running   0
# app-xxx                     1/1     Running   0

# Check services
kubectl get svc -n document-processor

# Watch Flux reconciliation
flux get kustomizations --watch

# Check image was updated
flux get image policies
```

---

## Step 8 — Access the app

```bash
# Option A: port-forward (quickest for local)
kubectl port-forward svc/app 8000:8000 -n document-processor

# Open in browser
open http://localhost:8000
```

For a persistent external URL on Docker Desktop, the `LoadBalancer` service gets `localhost` as its external IP automatically:

```bash
kubectl get svc app -n document-processor
# NAME   TYPE           CLUSTER-IP     EXTERNAL-IP   PORT(S)
# app    LoadBalancer   10.96.x.x      localhost     8000:xxxxx/TCP
```

Open **http://localhost:8000** directly — no port-forward needed.

---

## What happens on every future code push

```
git push → GitHub Actions → GHCR image (sha-xxxxxxx)
                                    ↓
                            Flux scans GHCR (every 1m)
                                    ↓
                  ImagePolicy picks newest sha-* tag
                                    ↓
             ImageUpdateAutomation commits new tag to master
                                    ↓
                  Kustomization applies updated app.yaml
                                    ↓
                     Kubernetes rolling update (zero downtime)
```

No manual steps after the initial setup.

---

## Rollback

```bash
# Option A: revert the image tag commit in git
git log --oneline | grep "ci(flux)"
git revert <bad-commit-sha> --no-edit
git push origin master
# Flux detects the revert and redeploys the previous image

# Option B: force a specific image directly
kubectl set image deployment/app \
  app=ghcr.io/akshay007724/data-platform/document-processor:sha-<good-sha> \
  -n document-processor
```

---

## Useful commands

```bash
# Force Flux to reconcile immediately (don't wait 1–5 min)
flux reconcile kustomization document-processor
flux reconcile image repository document-processor

# Tail app logs
kubectl logs -f deployment/app -n document-processor

# Tail Flux logs
flux logs --follow

# Delete everything (full teardown)
kubectl delete namespace document-processor
flux uninstall
```

---

## File structure

```
/
├── .github/workflows/
│   └── document-processor.yml     ← CI: lint, test, build, push to GHCR
├── flux/clusters/local/
│   └── document-processor/
│       ├── gitrepository.yaml      ← Flux watches this GitHub repo
│       ├── kustomization.yaml      ← Flux applies k8s/ manifests
│       ├── imagerepository.yaml    ← Flux scans GHCR for new tags
│       ├── imagepolicy.yaml        ← selects newest sha-* tag
│       └── imageupdateauto.yaml    ← writes new tag back to git
└── data-platform/apps/document-processor/
    └── k8s/
        ├── namespace.yaml          ← document-processor namespace
        ├── chromadb.yaml           ← ChromaDB deployment + service + PVC
        ├── ollama.yaml             ← Ollama deployment + service + PVC
        └── app.yaml                ← main app deployment + service + PVCs + ConfigMap
```
