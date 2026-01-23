# 🎮 Design Pattern: The Control Plane ("The Joystick")

> **Use Case**: Governance, Safety, and Observability for Autonomous Agents.
> **Metaphor**: A "Joystick" that allows a human pilot to intervene, monitor, and control an autonomous drone.

---

## 1. The Problem
Autonomous agents are powerful but risky. Without a governance layer, they suffer from:
1.  **Runaway Costs**: Infinite loops burning token budgets.
2.  **Unsafe Actions**: Executing destructive SQL (`DROP TABLE`) or API calls.
3.  **Lack of Accountability**: "Why did it do that?" becomes a mystery.
4.  **No Emergency Stop**: Once started, you can't stop a bad chain of thought.

## 2. The Solution: The Control Plane Pattern
The **Control Plane** is a centralized governance module that sits between the **User** and the **Agent Runtime**. It is not part of the LLM; it is deterministic code that acts as a gatekeeper.

### Architecture

```mermaid
graph TD
    User([User]) --> UI[Frontend / API]
    UI --> CP[🎮 Control Plane]
    
    subgraph Governance Layer
        CP --> Policy[📜 Policy Config]
        CP --> Switch[🛑 Kill Switch]
        CP --> Budget[💸 Cost Monitor]
        CP --> Guard[🛡️ Vector Guardrail]
    end
    
    CP -- Allowed? --> Agent[🤖 Agent Runtime]
    CP -- Blocked! --> Error[⛔ Access Denied]
    
    Agent --> Tools[🛠️ Tools (SQL, API)]
    Tools -.-> CP
```

---

## 3. Core Components

### 3.1. The Kill Switch (Emergency Brake)
*   **Concept**: A thread-safe boolean flag that instantly halts all agent operations.
*   **Triggers**:
    *   **Manual**: Operator presses "STOP" in UI.
    *   **Automatic**: Budget limit exceeded ($10/day).
    *   **System**: Detects recursive error loop.
*   **Implementation**: A Singleton or Context Manager that is checked before *every* LLM call or Tool execution.

### 3.2. Faceted Policy Engine
Instead of one "Safety" check, use multiple specific gates:
*   **Budget Gate**: `if daily_spend > limit: block()`
*   **Tool Gate**: `if tool_name in blocked_list: block()`
*   **Content Gate**: `if cosine_similarity(query, blocked_topics) > 0.35: block()`
*   **Syntax Gate**: `if "DROP" in sql.upper(): block()`

### 3.3. The Model Registry
*   **Concept**: Don't hardcode `gpt-4`. Use a registry that maps `version_id` -> `model_name`.
*   **Benefit**: Allows instant **Rollback** if a new model version degrades performance.

---

## 4. Implementation Guide (Python)

Below is the skeletal structure for a robust Control Plane.

```python
@dataclass
class PolicyConfig:
    max_cost_per_day: float = 10.0
    blocked_patterns: List[str] = field(default_factory=lambda: ["DROP", "DELETE"])
    blocked_topics: List[str] = field(default_factory=lambda: ["politics", "violence"])

class ControlPlane:
    def __init__(self, policy: PolicyConfig):
        self.policy = policy
        self.kill_switch = False
        self.daily_spend = 0.0
        
    def check_can_proceed(self, query: str) -> bool:
        # 1. Check Kill Switch
        if self.kill_switch:
            raise SecurityException("Kill Switch is ACTIVE.")
            
        # 2. Check Budget
        if self.daily_spend > self.policy.max_cost_per_day:
            self.trigger_kill_switch("Budget Exceeded")
            return False
            
        # 3. Check Permissions (Regex)
        if any(p in query.upper() for p in self.policy.blocked_patterns):
            return False
            
        # 4. Check Vector Guardrails (Semantic)
        if self.check_semantic_violation(query):
            return False
            
        return True
```

---

## 5. 🤖 The Prompt Pack
Use these prompts to have an AI build this architecture for you in any new project.

### Phase 1: The Blueprint
> **System Prompt**: You are a Senior Security Architect for AI Systems.
>
> **Task**: Design a "Control Plane" class for a Python Agent.
> **Requirements**:
> 1.  Create a `PolicyConfig` dataclass that loads from `policy.json`. It must define `max_budget`, `blocked_tools`, and `blocked_topics`.
> 2.  Create a `KillSwitch` class. It must be thread-safe (use `threading.Lock`) and have `enable()`, `disable()`, and `is_active()` methods.
> 3.  The Control Plane must initialize these components and provide a master function `validate_request(query, user_id)` that returns `(bool, reason)`.

### Phase 2: The Guardrails
> **Task**: Implement Semantic Guardrails for the Control Plane.
> **Requirements**:
> 1.  Use `sentence-transformers` to load `all-MiniLM-L6-v2`.
> 2.  In `ControlPlane.__init__`, pre-calculate embeddings for the `blocked_topics` list (e.g., "politics", "hate speech").
> 3.  Implement `validate_content(text)`:
>     - Embed the input text.
>     - Calculate Cosine Similarity against blocked topics.
>     - If similarity > 0.35, block the request.
> 4.  Add a "Fail Open" mechanism: If the embedding model crashes, log an error but ALLOW the request (availability > strict filtering).

### Phase 3: The Joystick (Integration)
> **Task**: wire the Control Plane into the Agent Runtime.
> **Requirements**:
> 1.  Inject the `ControlPlane` instance into the `Agent` class.
> 2.  Before the Agent calls the LLM, call `control_plane.check_can_proceed()`.
> 3.  Before the Agent executes a Tool (like SQL), call `control_plane.validate_tool(tool_name, args)`.
> 4.  If the Control Plane returns `False`, the Agent must immediately stop and return the error message to the user. Do not ask the LLM for permission to stop.

### Phase 4: Observability
> **Task**: detailed Audit Logging.
> **Requirements**:
> 1.  Every time `validate_request` is called, log a structured event (JSON).
> 2.  Fields: `timestamp`, `trace_id`, `check_type` (e.g., "budget", "vector"), `result` (ALLOWED/BLOCKED), and `score` (if applicable).
> 3.  If the Kill Switch is triggered, send a high-priority alert (mock this with a print statement for now).

---

## 6. Summary checklist for Success
- [ ] **Fail Safe**: Does the Kill Switch work even if the LLM is hallucinating?
- [ ] **Latency**: Is the Vector Guardrail < 50ms? (Use small models like MiniLM).
- [ ] **Transparency**: Can an Admin see *why* a request was blocked? (Audit Logs).
- [ ] **Configurability**: Can I change the policy without restarting the server? (Load from JSON).
