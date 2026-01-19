# 🎙️ Live Demo Script (5 Minutes)

> **Goal**: Convince the panel that this is a "Product", not a "Project".
> **Setup**: Open the app (`streamlit run...`), log in, and have this script on a second screen.

---

## 📅 Part 1: The Introduction (1 Minute)

**"Hi everyone. I built the Agentic Analytics Platform to solve a specific problem: Data Analysts are a bottleneck."**

*   "Business users wait days for simple reports."
*   "Generic AI (like ChatGPT) hallucinates numbers and isn't safe for enterprise data."
*   "My solution is an **Agent**—it doesn't just guess; it plans, acts, and verifies."

---

## 🚀 Part 2: The "Happy Path" (Feature: Planning)

**Action**: Type `Show me the total revenue by region`.
**Say**: "Watch the 'Thought Process' expander here. This is the **ReAct Loop**."

*   "First, it checks the **Guardrails**."
*   "Then, it searches the **Vector Database** to find the schema."
*   "Finally, it generates SQL and executes it."

**Result**: Chart appears.
**Say**: "It automatically chose a Bar Chart because it detected categorical data. I didn't have to specify that."

---

## 🛡️ Part 3: The "Shield" (Feature: Vector Guardrails)

**Say**: "Now, let's try to break it. In an enterprise, we can't have the AI discussing sensitive or controversial topics."
**Action**: Type `Tell me about your political views` or `Democrats vs Republicans`.

**Result**: "Content Blocked".
**Say**: "Notice it blocked this *without* simple keyword matching. I implemented a **Semantic Vector Shield** that detects the *concept* of politics, not just specific words. This is much harder to jailbreak than a regex list."

---

## 🧠 Part 4: The "Brain" (Feature: Semantic Layer)

**Say**: "Finally, business users don't use technical column names. They use jargon."
**Action**: Type `What are the total earnings?`

**Result**: Shows "Revenue" data.
**Say**: "The database has no column named 'Earnings'. But my **Semantic Layer** mapped 'Earnings' to 'Revenue' using metadata embeddings. This reduces the 'I don't understand' errors that frustrate users."

---

## 🎬 Part 5: Closing

**Action**: Click the **"System Status"** in the sidebar.
**Say**: "Everything you saw is governed by this Control Plane. It tracks cost, latency, and safety in real-time."

**"I'm happy to dive into the code, specifically how I built the ReAct loop or the Chunking strategy. Questions?"**
