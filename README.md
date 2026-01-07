# 🚀 Agentic Analytics Platform (Enterprise Edition)

> **Interview Panel Welcome**: This repository contains the complete source code, documentation, and "One-Click" setup for the Agentic SQL Platform.

---

## 📚 Documentation Package

We have prepared a complete documentation suite for your review:

| Document | Audience | Description |
| :--- | :--- | :--- |
| **[📄 Project Proposal](docs/project_proposal.md)** | **Product/Exec** | Executive summary, Problem/Solution, ROI, and Roadmap. |
| **[🏗️ System Architecture](docs/architecture.md)** | **Architects** | Component diagrams, Data Flow, and Tech Stack. |
| **[📖 User Manual](docs/user_manual.md)** | **End Users** | Step-by-step guide to using the Chat & Observability features. |
| **[⚙️ Technical Deep Dive](docs/technical_implementation_guide.md)** | **Engineers** | Detailed breakdown of the RAG pipeline, Guardrails, and "War Stories". |
| **[📊 Evaluation Scorecard](docs/custom_evaluation_scorecard.md)** | **QA/Trust** | Automated test results proving 100% accuracy and safety. |

---

## ✨ System Highlights ("Why this is Differentiated")

1.  **Thinking Agent (ReAct)**: It doesn't just guess SQL; it *plans, executes, and verifies*. (See "Thought Process" in UI).
2.  **The Shield (Vector Guardrails)**: Blocks semantic violations like "Politics" even without keywords.
3.  **The Brain (Synonyms)**: Knows "Earnings" = `revenue` via metadata enhancement.
4.  **The Joystick (Control Plane)**: Real-time kill switch and budget caps ($10/day).
5.  **Self-Correction**: Automatically fixes SQL syntax errors without user intervention.

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
