# 🎮 Design Pattern: The Enterprise Control Plane

> **Use Case**: Complete Governance, Management, and Observability for AI Agents.
> **Scope**: Backend Logic + Frontend Management + Dynamic Configuration.

---

## 1. The Architecture
An Enterprise Control Plane is not just a "checker" code block; it is a full-stack system consisting of three layers:

1.  **The Gatekeeper (Backend)**: Intercepts every request. (Kill Switch, Policy Engine).
2.  **The Manager (Frontend)**: Admin UI to update rules at runtime.
3.  **The Observer (Analytics)**: Dashboard to monitor blocks, costs, and traces.

```mermaid
graph TD
    Admin[👮‍♂️ Admin] --> ManagerUI[🖥️ Guardrails Manager]
    ManagerUI -- Updates JSON --> Config[📂 Policy & Prompts Config]
    
    User([User]) --> AgentUI[💬 Chat Interface]
    AgentUI --> Gatekeeper[🛡️ Gatekeeper (Backend)]
    
    Config -. Loads .-> Gatekeeper
    
    Gatekeeper -- Approved --> Agent[🤖 Agent Runtime]
    Gatekeeper -- Blocked --> Log[📝 Audit Log]
    
    Agent --> Tools[🛠️ Tools]
```

---

## 2. Component 1: The Gatekeeper (Backend)
*See previous section for `KillSwitch` and `PolicyConfig` implementation.*

**Key Addition**: The Gatekeeper must be **Hot-Reloadable**. It should re-read the configuration whenever the Manager updates it, without restarting the server.

---

## 3. Component 2: The Manager (Dynamic UI)
You need a "Control Panel" so non-technical admins can govern the AI.

### Pattern: The Dynamic List Editor (Streamlit/React)
Allow admins to add "Blocked Topics" or specific "Forbidden Words" instantly.

**Python Implementation (Streamlit)**:
```python
def render_guardrails_manager(control_plane):
    st.header("🛡️ Governance Manager")
    
    # 1. Load current policy
    policy = control_plane.policy
    
    # 2. Dynamic Topic Editor
    st.subheader("🚫 Blocked Topics")
    
    # Add New
    new_topic = st.text_input("New Topic to Block")
    if st.button("Add Topic"):
        policy.blocked_topics.append(new_topic)
        control_plane.update_policy(policy)  # Save to JSON & Reload
        st.success(f"Blocked: {new_topic}")
        st.rerun()
        
    # List Existing
    for i, topic in enumerate(policy.blocked_topics):
        c1, c2 = st.columns([4, 1])
        c1.write(f"• {topic}")
        if c2.button("Remove", key=f"del_{i}"):
            policy.blocked_topics.pop(i)
            control_plane.update_policy(policy)
            st.rerun()
```

---

## 4. Component 3: Prompt Engineering System
Hardcoding prompts in `myprompt.py` is an anti-pattern. Use a **Prompt Manager**.

### Pattern: The "Brain Surgeon"
Decouple the "System Prompt" from the code. Store it in `prompts.yaml` and allow edits via UI.

**Implementation**:
1.  **Config**: `config/prompts.yaml`
    ```yaml
    system_prompt: "You are a helpful assistant..."
    ```
2.  **Manager Class**:
    ```python
    class PromptManager:
        def get_system_prompt(self):
            return load_yaml("prompts.yaml")["system_prompt"]
            
        def update_prompt(self, new_text):
            save_yaml("prompts.yaml", {"system_prompt": new_text})
    ```
3.  **UI Editor**:
    ```python
    current_prompt = prompt_manager.get_system_prompt()
    new_prompt = st.text_area("System Instructions", value=current_prompt)
    if st.button("Save Instructions"):
        prompt_manager.update_prompt(new_prompt)
    ```

---

## 5. Component 4: Analytics (Observability)
You cannot govern what you cannot see.

### Pattern: The Scorecard
Track "Governance Events" specifically.
*   **Safety Score**: `(Total Requests - Blocked Requests) / Total Requests`
*   **Interventions**: How many times did the Kill Switch trigger?

**Implementation**:
The Gatekeeper should maintain a counter:
```python
self.stats = {"allowed": 0, "blocked": 0, "violations": []}
```
Expose this as a metric in the Admin Dashboard.

---

## 🤖 The "Full Stack" Prompt Pack
Use these prompts to generate the complete system.

### Prompt 1: The Data Structures (Backend)
> **Role**: System Architect.
> **Task**: Define the Configuration Schema for an AI Control Plane.
> **Requirements**:
> 1.  Create a `PolicyConfig` Pydantic model with:
>     - `blocked_topics` (List[str])
>     - `sensitivity` (float, 0.0-1.0)
> 2.  Create a `PromptConfig` model that holds `system_instructions`.
> 3.  Write functions `save_config(config)` and `load_config()` that persist these to JSON/YAML files.

### Prompt 2: The Logic (Gatekeeper)
> **Role**: AI Security Engineer.
> **Task**: Write the `ControlPlane` class.
> **Requirements**:
> 1.  Initialize with the `PolicyConfig` loaded from file.
> 2.  Implement `validate_input(text)`:
>     - Check if `text` matches any `blocked_topics` using Semantic Search (Cosine Similarity).
> 3.  Implement `update_policy(new_policy)`:
>     - Save the new policy to disk.
>     - Refresh the active configuration in memory immediately.

### Prompt 3: The Manager UI (Frontend)
> **Role**: Streamlit Developer.
> **Task**: Build a "Guardrails Manager" page.
> **Requirements**:
> 1.  Take the `ControlPlane` object as input.
> 2.  **Tab 1 - Topics**: Create a list editor where I can Add/Remove strings from `policy.blocked_topics`. When I click "Save", call `control_plane.update_policy`.
> 3.  **Tab 2 - Sensitivity**: A slider (0.0 to 1.0) to control the strictness.
> 4.  **Tab 3 - Prompts**: A large text area to edit the System Prompt. Save to `PromptConfig`.

### Prompt 4: The Integration
> **Role**: Senior Python Dev.
> **Task**: Wire it all together.
> **Requirements**:
> 1.  In `main.py`, initialize `ControlPlane`.
> 2.  In the Chat loop, before calling the LLM, run `control_plane.validate_input(user_query)`.
> 3.  If valid, retrieve the *latest* prompt using `prompt_manager.get_system_prompt()`.
> 4.  If invalid, return a canned "I cannot answer that" response.

---

## Summary Checklist
- [ ] **Hot Reload**: Can I change a rule without restarting the container?
- [ ] **Dynamic Prompts**: Can I tweak the persona without deploying code?
- [ ] **Audit Trail**: Do I know *who* changed the policy and *when*?
- [ ] **Fail Safe**: If the config file is corrupt, does it fall back to a safe default?
