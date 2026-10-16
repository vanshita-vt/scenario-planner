# scenario-planner
Type a scenario. See its parts. Change one thing. Watch the ripple.
A planning tool that breaks any scenario into its key components and shows how one change affects everything else.

---

## 👥 Team

- Vanshita Thapliyal
- Aaryan Singh
- Niharika Negi
- Shristi Pandey
- Minakshi Tiwari

---

## 🎯 What It Does

1. Type a scenario — like "college fest" or "wedding"
2. See it broken into 8 components with a dependency graph
3. Change one thing — like "budget cut by 50%"
4. Watch which parts break directly and which break downstream
5. Get a plain-English recovery plan

---

## ✨ Features

- 🧩 8 components per scenario, each with a description
- 🕸️ Visual dependency graph
- ⚡ Real ripple tracing — follows actual dependencies
- 🔴🟠 Shows what broke directly vs. what broke because of it
- ✏️ Assign owners, set status, write notes per component
- 🛠️ Plain-English recovery plan
- 🌐 Works offline — no API keys needed

---

## 🚀 How to Run

```bash
pip install -r requirements.txt
streamlit run app.py
