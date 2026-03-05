# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A production-ready **Helm chart** for a data engineering platform that deploys Kafka (streaming), Apache Flink (stream processing), Apache Airflow (orchestration), and two custom microservices (data-ingestion and data-processor) onto Kubernetes.

## Common Commands

```bash
# Fetch/update chart dependencies (Kafka, Airflow, Flink Operator)
helm dependency update .

# Validate templates and lint
helm lint .
helm template my-release . --values values.yaml

# Install or upgrade
helm install my-release . -n data-platform --create-namespace
helm upgrade my-release . --reuse-values --set pipelineConfig.LOG_LEVEL=DEBUG

# Package the chart
helm package .

# Verify a deployed release
kubectl get pods -n data-platform -l app.kubernetes.io/instance=my-release
kubectl get svc  -n data-platform -l app.kubernetes.io/instance=my-release
```

## Architecture

All Kubernetes resources live under `templates/`. The chart conditionally renders each component via `.Values.<component>.enabled` flags (all `true` by default).

**Dependency charts** (in `charts/` as `.tgz`):
- `kafka` (Bitnami 32.4.3) — 3-broker cluster, 10Gi storage, PLAINTEXT
- `airflow` (Apache 1.19.0) — KubernetesExecutor, PostgreSQL backend
- `flink-kubernetes-operator` (Apache 1.9.0) — manages Flink session clusters

**Custom templates** (`templates/`):
- `data-ingestion/` — Deployment + Service + HPA (port 8080, scales 2→10)
- `data-processor/` — Deployment + Service + HPA (port 8081, scales 2→20)
- `flink-jobs/flink-session-cluster.yaml` — FlinkDeployment CRD (2 TaskManagers)
- `configmaps/` — Three ConfigMaps: pipeline env vars, Kafka `.properties`, Flink job config
- `serviceaccount.yaml`, `rbac.yaml` — service account + Role/RoleBinding (includes Flink CRD permissions)
- `_helpers.tpl` — shared template helpers: naming, labels, Kafka bootstrap server string

## Key Patterns

- **ConfigMap checksum annotations** on Deployments: pods automatically restart when ConfigMaps change.
- **Kafka bootstrap server** is computed by `_helpers.tpl` (`data-platform.kafkaBootstrapServers`) — do not hardcode it in templates.
- **Flink state backend** is RocksDB with S3 checkpointing (paths configured via `flinkJobConfig` in `values.yaml`).
- Custom microservice images are placeholders (`data-platform/data-ingestion:latest`) — real images must be supplied at install time via `--set`.

## values.yaml Structure

Top-level keys map directly to components:
```
global, serviceAccount, rbac,
kafka, airflow, flinkOperator, flinkJobs,
dataIngestion, dataProcessor,
pipelineConfig, kafkaClientConfig, flinkJobConfig
```

`pipelineConfig` values are injected as environment variables into both microservice Deployments. `kafkaClientConfig` is mounted as a `.properties` file. `flinkJobConfig` populates the Flink session cluster ConfigMap.
