# 🚀 Agentic Analytics Platform (Enterprise Edition)

> **Interview Panel Welcome**: This repository contains the complete source code, documentation, and "One-Click" setup for the Agentic SQL Platform.

---

## 📚 Documentation Package

We have prepared a complete documentation suite for your review:

| Document | Audience | Description |
| :--- | :--- | :--- |
| **[🚀 AWS Proposal](docs/proposal_aws.md)** | **Exec/Product** | Bespoke pitch for AWS: "Governed Autonomy". |
| **[🏗️ System Architecture](docs/architecture.md)** | **Architects** | Six-Layer Agentic Runtime and Control Plane design. |
| **[📄 The Whitepaper](docs/whitepaper_combined.md)** | **Technical** | Comprehensive report on Decision Systems & RAG. |
| **[⚙️ Implementation Guide](docs/technical_implementation_guide.md)** | **Engineers** | Deep dive into self-healing loops and guardrails. |
| **[📖 User Manual](docs/user_manual.md)** | **End Users** | Guide to the Decision Portal & Observability Panel. |

---

## ✨ System Highlights ("Why this is Differentiated")

1.  **Thinking Agent (ReAct)**: It doesn't just guess SQL; it *plans, executes, and verifies*. (See "Thought Process" in UI).
2.  **The Shield (Vector Guardrails)**: Blocks semantic violations like "Politics" even without keywords.
3.  **The Brain (Synonyms)**: Knows "Earnings" = `revenue` via metadata enhancement.
4.  **The Joystick (Control Plane)**: Real-time kill switch and budget caps ($10/day).
5.  **Self-Correction**: Automatically fixes SQL syntax errors without user intervention.

### 🛡️ Enterprise Edition (New)
*   **Observability 2.0**: Full Sentry integration & JSON structured logging with trace IDs.
*   **Production Hardened**: Pydantic-based configuration management (`.env` support).
*   **Health Handling**: Kubernetes-ready `/health` endpoints and kill-switch logic.
*   **Secure**: Secrets management fully decoupled from code.

---

## 🚀 Quick Start (One-Click Setup)

### Prerequisites
*   Python 3.10+
*   Git

### Installation
```bash
# 1. Clone
git clone https://github.com/your-org/agentic-analytics-platform.git
cd agentic-analytics-platform

# 2. Install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure API Key
# (We use Groq for speed. Get a key at console.groq.com)
echo "GROQ_API_KEY=gsk_..." > .env

# 4. Run Application
streamlit run src/ui/streamlit_app.py
```

### Credentials (Login)
*   **User**: *[Provided Separately]*
*   **Pass**: *[Provided Separately]*

---

## 🛠️ Project Structure
```
├── docs/                 # <--- START HERE
├── src/
│   ├── agent/            # Core ReAct Logic
│   ├── retrieval/        # RAG Engine
│   ├── ui/               # Streamlit Frontend
│   └── data/             # Semantic Metadata
├── tests/                # Regression Suite
└── README.md
```

> **Built by Deepak MK**
