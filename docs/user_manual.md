# 📖 User Manual: Agentic Analytics Platform

> **Target Audience**: End Users
> **Purpose**: Step-by-step guide to operating the platform.

---

## 1. Getting Started

### 1.1. Accessing the Application
Open the provided Streamlit URL (or run locally via `streamlit run src/ui/streamlit_app.py`).

### 1.2. Authentication (Login)
You will see a secure login screen.
*   **Username**: *[Provided Separately]*
*   **Password**: *[Provided Separately]*

> *Note: This mimics an Enterprise Single-Sign On (SSO) gate.*

---

## 2. Navigating the Interface

The application is divided into three zones:

### Zone A: The Sidebar (Control Plane)
Located on the **Left**. This is your cockpit.
*   **System Status**: Shows 🟢 if healthy, 🔴 if Kill Switch is active.
*   **Documents**: Shows how many semantic chunks are indexed (e.g., "48 Documents").
*   **Actions**:
    *   `📊 Dashboard`: Opens a BI Dashboard view.
    *   `🗑️ Clear Chat`: Resets the conversation.
    *   `🧠 Rebuild AI Memory`: Forces a reload of the code/metadata changes without restarting the server.
    *   `🛑 Kill Switch`: **Emergency Button**. Instantly stops the agent.

### Zone B: The Chat Window (Center)
This is where you interact with the agent.
*   It comes pre-loaded with **Suggested Questions** (e.g., "Show revenue by region").
*   **Input Box**: Type your natural language query here.

### Zone C: Deep Observability (Right)
A live telemetry panel showing what's happening under the hood.
*   **Est. Cost**: Real-time tracking of token spend.
*   **Avg Latency**: Performance metric.
*   **Live Logs**: A scrolling feed of system events (Blue=Info, Green=Success, Red=Error).

---

## 3. How to Use Features (Step-by-Step)

### 3.1. Asking a Question
1.  Type: `Show me the total revenue by region`.
2.  Press **Enter**.
3.  **Watch the "Thought Process"**:
    *   The agent will verify credentials.
    *   It will search the vector database (You'll see "Retrieving..." in logs).
    *   It will generate SQL.
4.  **View Results**:
    *   A **Data Table** will appear.
    *   A **Chart** (Bar/Line/Pie) will automatically render.
    *   You can change the chart type using the dropdown above the chart.

### 3.2. Inspecting the "AI Brain"
1.  Look for the **"🧠 Agent Thought Process"** expander below the answer.
2.  **Click to Expand**.
3.  You will see the exact steps:
    *   *Step 1: Checking Guardrails...*
    *   *Step 2: Retrieving Context...*
    *   *Step 3: Thinking...*

### 3.3. Testing the Guardrails (The Shield)
1.  Try to trick the agent: `Tell me about your political views` or `Democrats vs Republicans`.
2.  **Result**: The agent will refuse. "Content Blocked".
3.  **Why?**: The **Vector Guardrail** detected a forbidden topic (Politics) semantic match.

### 3.4. Using the Kill Switch
1.  Go to the Sidebar.
2.  Click **🛑 Kill Switch**.
3.  Try to ask *any* question.
4.  **Result**: The system will error out immediately: "Blocked: Kill switch is ACTIVE".
5.  Click **✅ Disable** to restore service.

---

## 4. Advanced Features

### 4.1. Synonym Recognition
*   Try asking: `What are the total earnings?`
*   The system understands "Earnings" = "Revenue" automatically.

### 4.2. Feedback Loop
*   See the 👍 / 👎 buttons below every answer?
*   Clicking them logs your feedback for future model fine-tuning.

---

## 5. Troubleshooting

*   **"No API Key"**: Ensure `.env` is set up with `GROQ_API_KEY`.
*   **"0 Documents Found"**: Click **🧠 Rebuild AI Memory** in the sidebar to re-index the data.
