# 🚀 Pre-Deployment Checklist

> **Goal**: Ensure the live URL works perfectly for the Interview Panel.

---

## 1. Environment Variables (Critical)
When deploying to **Streamlit Cloud** (or Render/Heroku), you must set these inside the dashboard (not locally):

*   `GROQ_API_KEY`: `gsk_...` (Your key)
*   **Recommendation**: Create a fresh API Key just for this interview so you can revoke it later.

## 2. Secrets Management
The app uses `src/ui/auth.py` which checks for credentials.
*   **Default**: It defaults to `admin@admin.com` / `Admin@123` if you don't set secrets.
*   **Security**: Since you are sending the credentials separately, **DO NOT change them now**. Stick to the default or the ones you documented in the redacted files.

## 3. "Smoke Test" (After Deploying)
Run this sequence immediately after the URL is live:
1.  **Login**: Verify credentials work.
2.  **Indexing**: Checks the Sidebar. Does it say "48 Documents"? If it says "0", click **🧠 Rebuild AI Memory**.
3.  **Sanity Check**: Ask `Show revenue by region`. Does the chart load?
4.  **Guardrail Check**: Ask `Democrats vs Republicans`. Does it block?

## 4. The "About" Section
*   Consider editing `.streamlit/config.toml` (if it exists) to hide the "Manage App" footer code if you want a cleaner look, but it's not strictly necessary.

---
**Status**: You are ready to ship. 🚢
