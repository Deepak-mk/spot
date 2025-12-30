---
marp: true
theme: default
paginate: true
backgroundColor: #ffffff
---

# From 0 to 1: The Trustworthy AI Analyst
## Unlocking Enterprise GenAI with Semantic Governance

**Candidate**: [Your Name]
**Role**: Director of Engineering (Spotter)

---

# The Problem: Why GenAI Fails in Enterprise

1.  **Hallucination**: CFOs don't trust "probabilistic" numbers.
2.  **Context Amnesia**: Analysts need multi-turn drill-downs, not one-off answers.
3.  **Safety**: There is no "Off Switch" for most LLM apps.

> **Thesis**: You don't need a better Prompt. You need a better **Architecture**.

---

# The Solution: "Spot" (Agentic Analyst)

I built a **ReAct Agent** (Reason + Action) that separates *Thinking* from *Retrieving*.

### The 3 Pillars of Trust
1.  **The Brain (Semantic Layer)**: 
    *   Decoupled Metadata. 
    *   LLM calls `get_revenue()`, not raw SQL.
2.  **The Joystick (Control Plane)**: 
    *   Hard Kill Switch. 
    *   Budget Limits ($10/day).
3.  **The Loop (Feedback)**: 
    *   RLHF (Thumbs Up) -> Few-Shot Injection.

---

# Architecture: The "Safe" Stack

```mermaid
graph LR
    User[User] -->|Query| UI[Streamlit UI]
    UI -->|Text| CP[Control Plane (Joystick)]
    CP -->|Safe?| Runtime[Agent Runtime]
    Runtime -->|Decision| Tools
    Tools -->|Context| Semantic[Semantic Layer]
    Tools -->|SQL| DB[(Database)]
```

*   **Design Choice**: Stateless Runtime + Stateful Memory.
*   **Scale**: Abstracted Vector Store (FAISS -> Pinecone).

---

# The Differentiator: Enterprise Governance

We don't just "chat". We **Observe**.

*   **Observability**: Real-time Cost & Latency tracking.
*   **Guardrails**: Regex-fenced SQL execution.
*   **Audibility**: Every token is traced.

---

# Live Demo

### Scenario: The Monday Morning Review
1.  **Revenue vs Forecast** (Complex SQL Gen)
2.  **Drill Down East** (Context Retention)
3.  **Governance Check** (The Kill Switch)

> *Let's go to the code.*
