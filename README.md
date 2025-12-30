# 🚀 Agentic Analytics Platform (Enterprise Edition)

**"The AI Analyst that doesn't just talk, but acts."**

This platform is a production-grade **Agentic SQL System** designed to bridge the gap between natural language questions and enterprise data warehouses. It features a robust governance layer ("The Joystick"), a self-improving feedback loop, and deep observability.

---

## ✨ Key Features

### 🧠 1. The Agentic Core
*   **Zero-Shot ReAct Loop**: Autonomously plans and executes analysis steps.
*   **Context-Aware Memory**: Inherits data results across conversation turns (e.g., "Compare that to Q2").
*   **RAG-Powered**: Retrieval Augmented Generation ensures 100% schema accuracy.

### 🛡️ 2. The Joystick (Governance)
*   **Kill Switch**: Instant manual or automated system halt.
*   **Cost Budgeting**: Hard stops at daily dollar limits (e.g., $10/day).
*   **Policy Guardrails**: Regex-fenced read-only access (No `DROP`/`DELETE`).

### 🔄 3. Self-Learning Feedback Loop
*   **RLHF-Lite**: Thumbs Up/Down interface for user feedback.
*   **Few-Shot Injection**: Automatically converts positive examples into prompt context for future improvement.

### 📊 4. Deep Observability
*   **Metrics Panel**: Real-time Cost ($), Latency (ms), and Query Counts.
*   **Structured Logs**: DataFrame-based log viewer with filtering and sorting.
*   **Traceability**: Every action is linked via a unique `trace_id`.

### 🏗️ 5. Semantic Abstraction
*   **Semantic Layer**: Decoupled schema logic aimed at future integration with **Cube.js** or **dbt**.

---

## 🛠️ Architecture

For a deep dive into the 0-to-1 build process, see the **[Technical Implementation Guide](docs/technical_implementation_guide.md)**.

![Architecture](docs/images/architecture_diagram.png) *(Placeholder)*

---

## 🚀 Getting Started

### Prerequisites
*   Python 3.10+
*   `GROQ_API_KEY` (in `.env`)

### Installation

```bash
# 1. Clone & Install
git clone https://github.com/your-org/agentic-analytics-platform.git
cd agentic-analytics-platform
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your API keys

# 3. Run
streamlit run src/ui/streamlit_app.py
```

### CI/CD
This project uses **GitHub Actions** for:
*   ✅ Python Linting (Ruff/Flake8)
*   ✅ Unit Tests (Pytest)
*   ✅ Security Scanning

See `.github/workflows/ci.yml` for details.

---

## 📂 Project Structure

```
├── .github/workflows/    # CI/CD Pipelines
├── data/                 # Metadata & Feedback Store
├── docs/                 # Technical Documentation
├── src/
│   ├── agent/            # Core Thinking & Feedback Logic
│   ├── retrieval/        # RAG & Embeddings
│   ├── observablity/     # Telemetry & Tracing
│   └── ui/               # Streamlit Frontend
└── requirements.txt
```

---

> Built with ❤️ by Deepak MK
