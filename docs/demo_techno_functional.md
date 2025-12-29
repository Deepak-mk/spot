# 🛠️ Techno-Functional Demo Guide
**Audience**: Product Managers, Solution Architects, Analytics Leads.
**Goal**: Demonstrate *how* the architecture delivers reliable business value.

---

## 1. The Core Problem
*   **Business Pain**: "Dashboards are dead. Business users want answers, not filters."
*   **Tech Pain**: "LLMs hallucinate numbers. We can't trust them with financial data."

## 2. The Solution: "The Agentic Analyst"
We built an **Agentic SQL System**, not a Chatbot. It doesn't "guess" the answer; it "calculates" it.

### Key Differentiators (The "Secret Sauce")
1.  **Schema Accuracy (The "Brain")**:
    *   *Show*: The `metadata.json` or `Semantic Layer`.
    *   *Explain*: "We don't send raw data to the LLM. We send *schema definitions*. The LLM acts as a translator from English to SQL."
2.  **Governance (The "Joystick")**:
    *   *Show*: The Control Plane in the UI (Red/Green indicators).
    *   *Explain*: "We have a Kill Switch and Budget Limits ($10/day). It's enterprise-safe."
3.  **Self-Correction (The "Loop")**:
    *   *Show*: The "Thumbs Up" button.
    *   *Explain*: "It uses Few-Shot Learning. Every time a user rates an answer, the system gets smarter without code changes."

## 3. The Demo Flow (Script)

### Step 1: The "Simple" Ask (Context)
*   **Ask**: "Show me total revenue."
*   **Tech Highlight**: Point out the generated SQL in the expander. "See? It generated `SELECT SUM(revenue)...`. It didn't make up a number."

### Step 2: The "Complex" Ask (Reasoning)
*   **Ask**: "Compare revenue by region for the last 3 months."
*   **Tech Highlight**: Show the Multi-Step Reasoning (ReAct).
    *   Observation: "It identified 'Region' as a dimension and '3 months' as a time filter."
    *   Action: "It executed a specific SQL Group By query."

### Step 3: The "Context" Ask (Memory)
*   **Ask**: "What about just California?"
*   **Tech Highlight**: "Notice I didn't say 'revenue' again. The Agent inherited the *Data Context* from the previous turn."

## 4. Q&A Anticipation
*   **Q: Can it write to the DB?**
    *   *A*: No. The `PermissionChecker` regex-blocks any `INSERT`/`UPDATE`. Read-only.
*   **Q: What if the schema changes?**
    *   *A*: We just update the `Semantic Layer`. The Agent adapts instantly.
