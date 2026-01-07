# 🏗️ System Architecture: Agentic Analytics Platform

> **Status**: Production Ready
> **Version**: 1.0.0
> **Last Updated**: January 2026

## 1. High-Level Overview

The Agentic Analytics Platform is a **Retrieval-Augmented Generation (RAG)** system designed to execute analytical tasks autonomously. Unlike passive chatbots, it implements a **ReAct (Reasoning + Acting) Loop** that allows it to plan, retrieve context, generate SQL, execute it, and check the results before responding.

### Core Philosophy
*   **Safety First**: No action is taken without passing through the **Control Plane**.
*   **Semantic Precision**: The agent never guesses schema; it retrieves strict definitions from the **Semantic Layer**.
*   **Deep Observability**: Every "thought" and "action" is traced and visible to the user.

---

## 2. Component Architecture

```mermaid
graph TD
    User[User / Interview Panel] --> UI[Streamlit UI]
    UI --> Auth[Auth Gate]
    Auth --> Runtime[Agent Runtime]
    
    subgraph "The Brain (Agent Core)"
        Runtime --> Control[Control Plane / Governance]
        Runtime --> Planner[ReAct Planner]
        Runtime --> Context[Context Manager]
    end
    
    subgraph "The Knowledge (Semantic Layer)"
        Runtime --> RAG[Vector Store (FAISS)]
        RAG --> Embed[Embedding Model (MiniLM)]
        RAG --> Meta[Metadata Store (JSON)]
    end
    
    subgraph "The Engine (Execution)"
        Runtime --> LLM[LLM Client (Groq/Llama-3)]
        Runtime --> SQL[SQL Executor]
        SQL --> Data[Fact & Dim Tables]
    end
    
    Control -.->|Blocks| Runtime
    SQL -.->|Results| Runtime
```

### 2.1. Frontend Layer (`src/ui`)
*   **Technology**: Streamlit.
*   **Responsibility**: Chat interface, Visualization rendering (Altair), Auth handling, and Observability Panel.
*   **Key Feature**: "Thought Trace" Expander (`st.expander`) that visualizes the ReAct tokens.

### 2.2. Agent Runtime Layer (`src/agent`)
*   **Technology**: Python 3.10+, AsyncIO.
*   **Responsibility**: Orchestrates the Step-by-Step execution.
*   **State Management**: Holds `ConversationMemory` and injects `DataSignature` (schema of previous results) into the context window.

### 2.3. Control Plane (`src/agent/control_plane.py`)
*   **Responsibility**: The "Joystick" of the system.
*   **Functions**:
    *   **Budget Check**: Enforces $10/day limit.
    *   **Kill Switch**: Emergency stop mechanism.
    *   **Policy Check**: Regex & Vector-based guardrails.

### 2.4. Semantic Retrieval Layer (`src/retrieval`)
*   **Technology**: FAISS (Vector DB), Sentence-Transformers.
*   **Responsibility**: Maps "Business Terms" (e.g., "Earnings") to "Technical Columns" (e.g., `revenue`).
*   **Innovation**: Uses **Structure-Aware Chunking** to preserve table/column relationships.

---

## 3. Data Flow (The "Thinking" Process)

1.  **Ingest**: User asks "Show revenue by region".
2.  **Guard**: Logic checks for Kill Switch or Blocked Topics (e.g., "Politics").
3.  **Retrieve**: Vector Engine matches "revenue" -> `fact_sales.revenue`, "region" -> `dim_store.region`.
4.  **Plan**: LLM generates SQL: `SELECT region, SUM(revenue)...`.
5.  **Execute**: System runs SQL on the dataframe/database.
6.  **Verify**: System checks if SQL returned rows. If 0 rows or error, it self-corrects.
7.  **Respond**: System formats the answer and renders the chart in UI.

---

## 4. Security & Governance

### 4.1. Authentication
*   **Mechanism**: Role-Based Access Control (RBAC) via `st.session_state`.
*   **Credentials**: Securely managed via `.env` (Local) or `st.secrets` (Cloud).

### 4.2. Guardrails ("Defense in Depth")
| Layer | Type | Mechanism | Feature |
| :--- | :--- | :--- | :--- |
| **L1** | Operational | **Kill Switch** | Blocks all execution instantly. |
| **L2** | Content | **Vector Shield** | Blocks semantic violations (e.g. "Hate Speech" without keywords). |
| **L3** | Functional | **Read-Only SQL** | Regex blocks `DROP`, `DELETE`, `INSERT`. |

---

## 5. Technology Stack

*   **Language**: Python 3.10
*   **Frontend**: Streamlit
*   **LLM Provider**: Groq (Llama-3.1-8b-Instant)
*   **Embeddings**: HuggingFace (`all-MiniLM-L6-v2`)
*   **Vector Store**: FAISS (Local Persistence)
*   **Data Processing**: Pandas / DuckDB
*   **Diagramming**: Mermaid.js, Altair
