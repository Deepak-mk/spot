# 👔 Mock Interview Q&A: Director of Engineering (ThoughtSpot)

**Usage**: Use these as "Flashcards". Cover the answer, try to speak it out loud, then compare.

---

## 🟢 Round 1: The "Hook" & Introduction

**Q: Tell me about yourself?**
*   **Bad Answer**: "I managed teams at X and Y..." (Too generic).
*   **Director Answer**: "I am a builder-leader. For the last 15 years, I've focused on Data Platforms. Most recently at ExamRoom.AI, I scaled a team to 40+ engineers. But what drives me is **Agentic AI**. I actually spent this weekend building a prototype 'Agentic Analyst' called **Spot** to really understand the architectural challenges you face with Spotter. I implemented a Control Plane, Semantic Layer, and RLHF loop because I believe 'Trust' is the product, not just AI."

**Q: Why ThoughtSpot?**
*   **Answer**: "Because you solved the hardest part: **TML (The Semantic Layer)**. Everyone else is trying to throw raw SQL at LLMs and failing. ThoughtSpot has the 'Ground Truth' via TML. My prototype proved to me that without a Semantic Layer, hallucinations are inevitable. I want to build on that foundation."

---

## 🟡 Round 2: Backend Engineering & System Design (Priority #1)

**Q: "Design the backend for a high-concurrency Analytics API."**
*   **Key Concepts**: AsyncIO (FastAPI), Caching (Redis), Queueing (Celery/Kafka).
*   **Your "Spot" Answer**: "In 'Spot', I kept the runtime stateless so it can scale horizontally.
    *   *API Layer*: I'd use **FastAPI** with `async/await` to handle thousands of concurrent SSE (Server-Sent Events) streams for chat.
    *   *State*: I'd offload conversation history to **Redis** (Semantic Cache) to reduce DB hits.
    *   *Worker*: Heavy SQL generation happens on background workers (Celery) to keep the API non-blocking."

**Q: "How does Python's GIL affect your Agent architecture?"**
*   **Answer**: "The Global Interpreter Lock prevents true parallelism in threads.
    *   *Impact*: Since LLM calls are I/O bound (network latency), standard `threading` is fine.
    *   *Bottleneck*: If we do heavy dataframe processing (CPU bound) in the main thread, the API will choke.
    *   *Solution*: I run Dataframe operations (Pandas/Polars) in a separate **ProcessPool** or microservice to bypass the GIL."

**Q: "Database Isolation Levels: Why do they matter for an Analyst Agent?"**
*   **Answer**: "If an Agent runs a long analytical query (`READ COMMITTED`) while a transaction updates records, we might get inconsistent aggregates (Phantom Reads).
    *   *Spot Implementation*: For the Agent, I enforce `READ UNCOMMITTED` (Snapshot) where possible for speed, or `REPEATABLE READ` if accuracy is paramount, ensuring the 'Answer' matches the 'Data' seen at start of query."

---

## 🟠 Round 3: People Management & Organization (Priority #2)

**Q: "Your roadmap shows hiring 5 engineers. Who do you hire first?"**
*   **Answer**: "I hire a **Senior Backend/Platform Engineer** first, not an AI Researcher. Why? Because the model (Llama/GPT) is a commodity. The competitive moat is the **Infrastructure** (The Control Plane, The Context Engine, The Guardrails). I need strong engineers to build the 'Joystick' reliability features I prototyped in `control_plane.py`."

**Q: "How do you manage Technical Debt?"**
*   **Answer**: "I follow the **20% Tax** rule. Every sprint creates debt. In my roadmap, I allocated Q2 specifically for 'Observability & Refactoring'. For example, my prototype uses `pandas` for everything. Tech debt repayment means migrating that to `Polars` or `DuckDB` for performance before we hit scale limits."

---

## 🟣 Round 4: Agentic AI Strategy (The Differentiator)

**Q: "Hallucinations are the biggest risk. How do you stop them?"**
*   **Your "Spot" Evidence**:
    1.  **Restriction**: "I don't let the LLM guess schema. I force it to use a `SemanticLayer` (TML equivalent). It can't invent a metric that isn't defined."
    2.  **Verification**: "I use a **ReAct Loop**. The agent must *execute* the SQL and see the result *before* answering. If the SQL fails, it triggers a self-correction loop."
    3.  **Governance**: "I built a `ContentGuardrail` that regex-blocks requests about 'politics' or 'competitors' before they even reach the model."

**Q: "How would you scale this to 10,000 concurrent users?"**
*   **Your "Spot" Evidence**:
    1.  **Statelessness**: "My `AgentRuntime` is stateless; memory is passed per-request. This means we can scale horizontally on K8s."
    2.  **Vector Store**: "I used FAISS for the prototype, but for 10k users, I'd migrate to **Milvus** or **Weaviate** for distributed indexing."
    3.  **Caching**: "I would implement semantic caching (Redis) for common queries like 'Show Revenue', so we don't hit the LLM for repeated questions."

**Q: "We need to support multiple tenants. How does your architecture handle data isolation?"**
*   **Your "Spot" Evidence**:
    *   "Currently, my `ControlPlane` is global. To handle multi-tenancy, I would inject a `tenant_id` into every `MetadataChunk` and `VectorSearch` filter. The `PermissionChecker` would then enforce `WHERE tenant_id = X` on every SQL query generated, essentially Row-Level Security (RLS) at the prompt level."

**Q: "A Product Manager wants to ship a 'Beta' that hallucinates 20% of the time. What do you do?"**
*   **Answer**: "I block it. As Director, I own **Trust**. If we ship 80% accuracy, we lose the user forever.
    *   *Action*: I would implement the **Evaluation Harness** (like the `tests/run_suite.py` I built) and set a hard gate: 'We do not ship until Functional Accuracy > 95% on the Golden Test Suite'. I would offer to scope-cut features to hit that quality bar, but I won't compromise on Trust."

*   **Answer**: "I follow the **20% Tax** rule. Every sprint creates debt. In my roadmap, I allocated Q2 specifically for 'Observability & Refactoring'. For example, my prototype uses `pandas` for everything. Tech debt repayment means migrating that to `Polars` or `DuckDB` for performance before we hit scale limits."

---

## 🟣 Round 4: Behavioral (The "Culture Fit")

**Q: "Tell me about a time you failed."**
*   **Your "Spot" Story**: "In my prototype, I initially tried to verify SQL by just asking the LLM 'Is this correct?'. It just hallucinated 'Yes'. I failed to realize LLMs can't grade themselves.
    *   *Correction*: I pivoted to **Deterministic Verification**. I wrote code (`Binder Error` checks in Python) to catch errors.
    *   *Lesson*: Trust Code, not Models."

**Q: "How do you handle conflict with other leaders?"**
*   **Answer**: "I focus on **Data, not Opinion**. If a PM argues for a feature, I ask for the metric. In my prototype, I built a `FeedbackManager` to collect user 'Thumbs Up/Down'. I would use that data to settle arguments. 'Users are downvoting this feature 60% of the time; let's fix it'."

---

## 🔵 Round 5: The "Bar Raiser" (Advanced Strategy)

**Q: "How do you structure an AI Engineering organization?"**
*   **Answer**: "I prefer the **'Embedded Squad'** model over a centralized 'AI Lab'.
    *   *Why*: Centralized labs build cool demos that never ship.
    *   *My Approach*: I embed AI Engineers directly into product squads (e.g., the 'Search Squad', the 'Dashboard Squad').
    *   *Platform Team*: I keep a small central 'AI Platform' team (like the one that would build the `ControlPlane` and `AgentRuntime` I prototyped) to build shared tooling/infrastructure for the squads."

**Q: "Build vs Buy: Should we train our own LLM?"**
*   **Answer**: "No. Not for general reasoning.
    *   *Strategy*: We 'Buy' intelligence (Llama 3, GPT-4) via API for reasoning.
    *   *We Build*: The Context Engine (Semantic Layer) and the Guardrails.
    *   *Exception*: We only fine-tune small models (7B) for specific tasks like 'Text-to-TML' conversion if latency/cost becomes a blocker, but we don't train from scratch."

**Q: "Why will Spotter win against Microsoft Copilot?"**
*   **Answer**: "**Ground Truth**.
    *   Microsoft Copilot is trained on the open internet (Excel files, loose text). It guesses.
    *   Spotter is built on TML (The Semantic Layer). We don't guess; we *retrieve*. My prototype proved that binding LLMs to a strict Semantic Layer is the only way to get 100% SQL accuracy. Enterprises buy Trust, not just Chat."

---

## ⚡ Bonus: Questions YOU Ask Them

1.  "I implemented a `ControlPlane` to handle Budget and Kill Switches. Does Spotter have a similar centralized governance layer, or is it distributed across services?"
2.  "My prototype achieved 100% SQL safety. How does ThoughtSpot handle 'Prompt Injection' attacks where users try to trick the TML layer?"
3.  "I see TML as the biggest moat. Are there plans to open-source parts of the Semantic Layer to encourage community agents?"
