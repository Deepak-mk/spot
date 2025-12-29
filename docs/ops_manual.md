# ⚙️ Operations & Scaling Manual (The "Day 2" Plan)

**Purpose**: This document outlines the strategy to take `Spot` from a single-node prototype to a distributed enterprise service.
**Target Audience**: DevOps, SRE, Tech Leads.

---

## 1. Infrastructure Scaling Strategy

### A. Compute (Stateless Runtime)
*   **Current**: Single Container (`docker/Dockerfile.api`).
*   **Target State**: Kubernetes (EKS/GKE).
*   **Scaling Policy**: Horizontal Pod Autoscaling (HPA) based on `external_metric: queue_depth` (not just CPU).
*   **Why**: Reasoning agents are CPU-intensive. We need to isolate tenant workloads.

### B. Memory (Vector Store)
*   **Current**: Local FAISS Index (In-Memory).
*   **Target State**: Distributed Vector DB (Milvus or Weaviate).
*   **Migration Plan**:
    1.  Deploy Managed Milvus.
    2.  Implement `VectorStoreAction` interface for Milvus.
    3.  Dual-write integration period.
    4.  Cutover.

### C. Database (Metadata Store)
*   **Current**: `metadata.json` (File-based).
*   **Target State**: Postgres (RDS) with a caching layer (Redis).
*   **Why**: To support multi-tenant schema isolation and RBAC.

---

## 2. Observability & SLAs

### Key Performance Indicators (KPIs)
| Metric | SLA Target | Alert Threshold |
| :--- | :--- | :--- |
| **Response Latency** | < 3s (P95) | > 5s |
| **Hallucination Rate** | < 0.1% | > 0.5% (triggers Incident) |
| **Availability** | 99.9% | < 99.9% |

### The "Kill Switch" Protocol
1.  **Level 1 (Automated)**: Cost > Budget -> Stop Agent. Refill req required.
2.  **Level 2 (Manual)**: "Red Button" in Admin UI. Stops all active threads immediately.
3.  **Audit**: All Kill Events are logged to S3 (Immutable Logs) for compliance.

---

## 3. Security posture
*   **Secrets**: Move from `.env` to HashiCorp Vault / AWS Secrets Manager.
*   **Egress**: Strict Network Policies (Calico) denying all outbound traffic except to LLM Provider API.
*   **RBAC**: Integrate with OIDC/Okta for SSO.

---
*Strategy Approved by: Director of Engineering*
