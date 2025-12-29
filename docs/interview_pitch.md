# 🎯 Pitch Deck: Director of Engineering (ThoughtSpot Spotter)
**Candidate**: [Your Name]
**Theme**: "From 0-to-1: Building a Trustworthy AI Analyst"

---

## 1. The Narrative (The "Why")
**Context**: You are looking for a leader who can drive **"Spotter"** (GenAI Analytics) from 0 to 1.
**My Pitch**: "Lead from the front."
To prove I understand the architectural challenges of *Spotter*, I didn't just read about it. **I built a functional prototype of an Agentic Analyst** over the weekend.

---

## 2. Architecture Deep Dive ("I Speak Your Language")

### A. Spotter = My `runtime.py` (The Brain)
**The Challenge**: Chatbots guess. Analysts calculate.
**My Solution**: I implemented a **ReAct Agent Loop** (Reasoning + Acting) identical to how Spotter operates under the hood.
*   **How it works**:
    1.  **Thought**: The LLM parses the user query ("Show revenue for East region").
    2.  **Plan**: It decides it needs to query the database. It DOES NOT generate the answer yet.
    3.  **Action**: It calls the `sql_executor` tool with a specific SQL query.
    4.  **Observation**: The system returns the *actual data* (rows, columns).
    5.  **Synthesize**: Only then does the LLM generate the final response.
*   **Director Insight**: "I understand that for Enterprise Analytics, the LLM is not a database; it's a reasoning engine that orchestrates tools."

### B. TML (ThoughtSpot Modeling Language) = My `semantic_layer.py`
**The Challenge**: LLMs fail when they don't understand the business logic (e.g., "What is Churn?").
**My Solution**: I built a **Semantic Abstraction Layer**.
*   **Abstraction**: Just like TML, I don't let the LLM guess column names. I provide strict `Metric` and `Dimension` definitions.
*   **Accuracy**: When a user asks for "Revenue", the agent calls `get_metric("revenue")` from the semantic layer. It returns the *approved* definition (`SUM(fact_sales.amt)`), ensuring 100% consistency.
*   **Director Insight**: "You can't scale GenAI without a Semantic Layer. TML is the competitive advantage because it grounds the AI in truth."

### C. Enterprise Governance = My `Control Plane` (The Differentiator)
**The Challenge**: CSOs won't buy AI that they can't control. "What if it spends $10k overnight?"
**My Solution**: I built a dedicated **Control Plane** (The "Joystick").
*   **Kill Switch**: A physical (thread-safe) lock that admins can trigger to instantly halt all agent threads.
*   **Budget Monitor**: Real-time token tracking that auto-triggers the Kill Switch if daily costs exceed $10.00.
*   **Policy Guardrails**: Regex-fenced `PermissionChecker` that strictly prohibits `DROP`, `DELETE`, or `INSERT` commands.
*   **Director Insight**: "Safety isn't a feature; it's the product. Building this Governance Layer is how we move Spotter from 'Demo' to 'Enterprise Production'."

---

## 3. "War Stories" (The Technical Deep Dive)
*Use these to answer "Tell me about a technical challenge."*

### Challenge A: The "12-Month Hallucination"
*   **Problem**: User asked for "3 months", LLM wrote bad SQL, fallback showed "12 months".
*   **The Fix**: I didn't blame the prompt. I rewrote the **Fallback Logic** (Python) to prioritize granular constraints.
*   **Lesson**: "Prompt Engineering is brittle. **Code Logic** is robust. We need hybrid architectures."

### Challenge B: "Context Blindness"
*   **Problem**: User: "Show Revenue". Agent: (Shows 10M). User: "Is that good?" Agent: "I don't know."
*   **The Fix**: **Data Context Injection**. I forced the runtime to inject a *Data Signature* (Row counts, summary stats) into the LLM's short-term memory.
*   **Lesson**: "State Management is the hardest part of GenAI chat. The LLM needs to 'see' the data it just queried."

---

## 4. Leadership Philosophy (Matches JD)
*   **"0 to 1 Hands-on"**:
    *   "I defined the architecture, wrote the Python core, and set up the CI/CD pipeline myself. I know the pain of `pip install` and the complexity of Vector Stores."
*   **"Customer Centricity"**:
    *   "I prioritized the **Control Plane** (Budget/Safety) because I know Enterprise CSOs won't buy Black Boxes. Safety is a feature, not an afterthought."
*   **"Scalability"**:
    *   "I abstracted the `VectorStore`. Today it's FAISS (local); tomorrow it's Pinecone/Milvus. I designed for modularity."

---
*Ready to build the next generation of Spotter.*
