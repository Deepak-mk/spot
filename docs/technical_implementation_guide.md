# 🚀 Agentic Analytics Platform: A Technical Deep Dive
> **Author**: System Architect (Antigravity)
> **Date**: December 2025
> **Format**: Technical Presentation / Whitepaper

---

## 📑 Agenda
1.  **The Challenge**: Bridging NL to SQL accurately.
2.  **The Brain (Ingestion)**: Tokenization, Structural Chunking & Semantic Layer.
3.  **The Engine (RAG)**: Vector Math & Indexing Strategy.
4.  **The Mind (Runtime)**: ReAct Loop, Memory & Feedback Loop.
5.  **The Joystick (Governance)**: Control Plane & Boundaries.
6.  **Defense in Depth (Guardrails)**: Operational vs Content Safety.
7.  **War Stories**: Failures, Hallucinations, & Fixes.
8.  **The Interface**: Visualization Principles & Observability.

---

## 1. The Challenge
We set out to build an agent that doesn't just "talk" but **acts** on data.
*   **Constraint 1**: Privacy (No sending raw data to LLM).
*   **Constraint 2**: Accuracy (Hallucination 0% tolerance for numbers).
*   **Constraint 3**: Context (Understanding "Compare Q1 to Q2").

---

## 2. The Brain: Ingestion & Embedding

### 2.1. The Tokenization Decision
We utilize **`sentence-transformers/all-MiniLM-L6-v2`**.
*   **Architecture**: BERT-based (Transformer).
*   **Tokenization Method**: **WordPiece** (Subword Tokenization).
    *   *Why WordPiece?* Unlike BPE (Byte Pair Encoding) which is common in GPT models, WordPiece is optimized for BERT's bidirectional understanding. It splits complex column names like `gross_margin_pct` into semantically meaningful subwords `['gross', '_', 'margin', '_', 'pc', '##t']`, preserving business context better than simple character splitting.
*   **Context Window**: 256 Tokens (Truncation Strategy).

### 2.2. The "Structural Chunking" Innovation
**Trade-off**: Naive Chunking vs Semantic Chunking.
*   *Naive Approach*: `RecursiveCharacterTextSplitter(chunk_size=500)`.
    *   **Failure**: Used initially. It split table definitions in half, leaving `Primary Key` in one chunk and `Columns` in another. Retrieval failed to link them.
*   *Decision*: **Structure-Aware Chunking** (`MetadataChunker`).
    *   **Logic**: We treat the `metadata.json` not as text, but as an **Object Graph**.
    *   **Atomic Units**: A "Chunk" is strictly one Table, one Metric, or one Relationship.
    *   **Result**: 100% Schema Retrieval accuracy.

### 2.3. The Semantic Layer (New)
**File**: `src/agent/semantic_layer.py`

We abstracted access to the schema behind a formal **Semantic Layer Interface**. 
*   **Goal**: Decouple the Agent logic from the Metadata implementation. 
*   **Future-Proofing**: This interface allows us to swap the backend for **Cube.js** or **dbt Semantic Layer** transparently. The Agent invokes `get_metric("revenue")` and remains agnostic to whether that metric comes from a JSON file or an enterprise API.

---

## 3. The Engine: Retrieval Augmented Generation (RAG)

### 3.1. Vector Store Architecture
**Backbone**: **FAISS** (Facebook AI Similarity Search).
*   **Index Type**: `IndexFlatIP` (Exact Search).
*   **Math**: Inner Product.
    *   Since we **L2-Normalize** all vectors ($||v|| = 1$) before indexing, the Inner Product $v \cdot q$ is mathematically identical to **Cosine Similarity**:
        $$ \text{Cosine}(A, B) = \frac{A \cdot B}{||A|| ||B||} = A \cdot B \quad (\text{if norm is 1}) $$
*   **Decision**: Why not HNSW (Approximate Nearest Neighbor)?
    *   *Scale*: Our schema metadata is < 10,000 chunks. HNSW introduces recall error (missing a key table) for speed gains we don't need at this scale. Exact Search is < 20ms and strictly better.

---

## 4. The Mind: Runtime & Learning

### 4.1. Conversational Data Inheritance
**The Problem**: "Context Blindness".
*   *User*: "Show Revenue." -> *System*: Shows Chart.
*   *User*: "What is the trend?" -> *System*: "I don't see any data."
*   *Root Cause*: LLM memory only stored the *text* answer ("Here is the revenue"), not the *data payload*.

**The Implementation**:
We implemented **Data Context Injection** in `runtime.py`.
*   Post-execution, we calculate a "Data Signature" (Row count, Columns, Sample Rows).
*   We inject this signature into the **Assistant's Memory Block** (Hidden from UI, visible to LLM).
*   *Result*: The Agent "remembers" it just saw $1.5M revenue and can perform comparative analysis in the next turn.

### 4.2. The Feedback Loop (RLHF-Lite) (New)
**File**: `src/agent/feedback.py`

We implemented a **Reinforcement Learning from Human Feedback** mechanism.
*   **Signal**: User clicks Thumbs Up (👍) or Down (👎) on an analysis.
*   **Storage**: Ratings/Corrections are persisted to `data/feedback.jsonl`.
*   **Closing the Loop**: The `PromptBuilder` now fetches highly-rated examples and injects them as **Few-Shot Prompts**.
    *   *Effect*: If the agent gets a query wrong, and you correct it (or rate a correct fallback), it "learns" that pattern permanently.

---

## 5. The Control Plane: The Joystick (Governance)

**Metaphor**: Think of the Control Plane (`src/agent/control_plane.py`) as a **Joystick** that operates the whole agent. It ensures the pilot has full control and the agent never flies beyond its designated boundaries.

### 5.1. The Joystick Mechanism
This is not a passive logging system; it is an active, real-time feedback loop. Every action the agent attempts is routed through the Control Plane, which validates it against safety protocols before execution.

*   **Joystick Inputs**: The system constantly monitors key pressure points:
    *   **Budget Pressure**: Are we burning tokens too fast?
    *   **Safety Pressure**: Is the manual "Stop" button pressed?
    *   **Policy Pressure**: Is the agent trying to run a forbidden command?

### 5.2. Defining the Boundaries
We set hard boundaries to ensure the agent operates strictly within safe limits:

1.  **The Emergency Brake (Kill Switch)**
    *   *Function*: Instantly halts all agent operations.
    *   *Trigger*: Can be **Manual** (via the UI Joystick button) or **Automatic** (when cost limits are hit).
    *   *Result*: The "Joystick" locks the controls immediately.

2.  **The Fuel Limit (Cost Budget)**
    *   *Boundary*: **$10.00 / day** (Configurable).
    *   *Mechanism*: Real-time token counting -> Cost Calculation.
    *   *Action*: If `daily_cost > limit`, the joystick automatically pulls back and enables the Kill Switch.

3.  **The Fight Zone (Permission Policy)**
    *   *Boundary*: **Read-Only Access**.
    *   *Mechanism*: A Regex-based "Geofence" that blocks `DROP`, `DELETE`, `INSERT`, or `UPDATE` commands. The agent is physically incapable of modifying the database.

---

## 6. Defense in Depth: Guardrails

We implement a multi-layered security strategy to ensure the agent is safe for enterprise use.

### 6.1. Layer 1: Operational Guardrails (The "Brakes")
*   **Kill Switch**: Physical thread lock that halts execution immediately.
*   **Budget Circuit Breaker**: Auto-kill if daily cost > $10.00.
*   **Rate Limiting**: Max 60 requests/minute to prevent DoS.

### 6.2. Layer 2: Content Guardrails (The "Filter")
*   **Topic Blocking**: `PolicyConfig.blocked_topics` enforces a deny-list (e.g., "politics", "religion") using efficient regex matching.
*   **Input Validation**: `PermissionChecker` scans for malicious SQL patterns (`DROP`, `DELETE`) before execution.
*   **Output Validation**: *Future*: Integrate NVIDIA NeMo Guardrails for semantic output checking.

### 6.3. Layer 3: Semantic Guardrails (The "Truth")
*   **Schema Abstraction**: The LLM never sees the raw schema, only the `SemanticLayer` definitions, preventing "Hallucinated Joins".

---

## 7. ⚔️ War Stories: Failures & Fixes (Post-Mortem)

This is the most critical section. Building agents is 10% coding and 90% debugging edge cases.

### Failure #1: The "12-Month" Hallucination
*   **Scenario**: User asked "Forecast for **next 3 months**".
*   **Behavior**: System displayed a chart with **12 months** (Jan-Dec).
*   **Root Cause**:
    *   The LLM's generated SQL failed (syntax error).
    *   The System triggered `_get_fallback_sql`.
    *   The Fallback Logic had a generic check: `if "month" in query: return 12_month_sql`.
    *   Since "3 months" contains the word "month", it triggered the generic 12-month report.
*   **The Fix**: **Priority Reordering**.
    *   We moved the specific `if "3 months"` check to the **top** of the logic stack, ensuring it intercepts the intent before the generic handler.

### Failure #2: The "Double SQL" Confusion
*   **Scenario**: System used a Fallback query, but the Chat UI showed *two* SQL queries: the failed one (in text) and the working one (in expander).
*   **Root Cause**: The LLM's text response (containing the failed code) was displayed "as is", while the backend silently swapped the execution SQL.
*   **The Fix**: **Regex Content Cleaning**.
    *   We implemented a regex stripper in `runtime.py` that, upon triggering fallback, actively removes SQL code blocks from the *text response*, ensuring the user sees a clean "Used optimized query" message.

### Failure #3: Visualization Principles Violation
*   **Scenario**: "Show Forecast **vs** Actual".
*   **Behavior**: Chart showed only one bar (Actuals). Forecast was missing.
*   **Root Cause**: The generic `render_chart` function blindly picked `df.columns[1]` as the Y-axis and ignored other columns.
*   **The Fix**: **Multi-Series Polymorphism**.
    *   Updated `streamlit_app.py` to check `len(numeric_cols)`.
    *   If > 1, we perform a **Pandas Melt** (`pd.melt`) to transform the data from Wide to Long format.
    *   We then switch chart renderers to **Grouped Bar** or **Multi-Line** using Altair's `color` encoding.

---

## 8. The Interface: Observability & UX

### 7.1. Deep Observability
We moved beyond "logs" to "Telemetry".
*   **Structured Data**: Logs are stored as Dicts, not Strings.
*   **UI Implementation**: We render a Pandas DataFrame `st.dataframe` to allow:
    *   **Filtering**: Show only ERRORs or WARNINGs.
    *   **Sorting**: Find the latest trace.
*   **Metrification**: Real-time Cost Estimation ($0.50 per 1M tokens) helps stakeholders understand API burn rate.

### 7.2. Dynamic Visualization
*   **Constraint**: User wants to toggle between Bar/Line/Pie.
*   **Solution**: We built a **Chart Selector Component** that acts as a middleware.
    *   It validates data suitability (e.g., "Cannot render Scatter scatter plot with only 1 numeric column").
    *   It updates the view state without re-running the SQL query.

---

## 9. Future Roadmap
*   **LLM Agnosticism**: Abstract `GroqClient` to specific interfaces (OpenAI, Anthropic).
*   **Enterprise Semantic Layer**: Native integration with dbt Semantic Layer.
*   **Active Learning**: Automated regression testing on feedback examples.

---
> *Code is easy. Context is hard.*
