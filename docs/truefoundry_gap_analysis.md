# Gap Analysis: Spot vs. TrueFoundry

This document compares **Spot (Agentic Analytics Platform)** against the **TrueFoundry AI Gateway & Platform** specifications.

| Feature Area | TrueFoundry Capability | Spot Current State | Status |
| :--- | :--- | :--- | :--- |
| **1. Application Analytics** | | | |
| **Basic Metrics** | Request Count, Latency, Error Rate, Cost | ✅ **Full Coverage**. (Queries, Avg Latency, Daily Cost, Error Logs). | 🟢 MATCH |
| **Streaming Metrics** | TTFS (Time to First Token), ITL (Inter-Token Latency) | ⚠️ **Planned**. Currently tracking E2E Latency. TTFS requires streaming response refactor. | � LOW PRIORITY |
| **Granularity** | Per-Model, Per-User, Per-Team breakdown | ⚠️ **Partial**. We log Username/Model. Full drill-down charts are a future enhancement. | 🟡 PARTIAL |
| **2. Governance & Security** | | | |
| **Guardrails** | Input/Output validation, PII redaction | ✅ **High Coverage**. Semantic "Shield", Blocked Topics, SQL Injection checks. | 🟢 MATCH |
| **Guardrail Analytics** | "How often are content policies enforced?" | ✅ **RESOLVED**. Implemented "Guardrail Health" Donut Chart (Green/Red) in Dashboard. | � MATCH |
| **Rate Limiting** | Throttling requests by user/key | ✅ **Implemented**. `PolicyConfig` has `requests_per_minute` limits. | 🟢 MATCH |
| **3. AI Gateway Features** | | | |
| **Model Registry** | Versioning and routing to multiple models | ✅ **Implemented**. `ControlPlane` has a `ModelRegistry` class. | 🟢 MATCH |
| **Caching** | Semantic Caching to save costs | ✅ **RESOLVED**. Implemented `SemanticCache` with "⚡ Cached" indicator. | � MATCH |
| **Prompt Mgmt** | Versioned prompts, A/B testing | ✅ **RESOLVED**. Implemented "Prompt Editor" tab in Admin UI. | � MATCH |

## Recommendation
To match the "TrueFoundry Control Plane" experience more closely, we should implement **Guardrail Analytics**.

**Proposed Action:**
Add a **"Guardrail Health"** chart to the `Governance & Health` panel that shows:
-   **Green**: Safe Queries
-   **Red**: Blocked by Shield

This is the most visible "Control Plane" feature missing from the UI.
