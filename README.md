# InterviewIQ – AI Interview Trainer

**Prepare Smarter. Interview Better.**

An AI-powered interview preparation platform built with IBM Granite, Flask, and RAG.

---

## Features

- 📄 **Resume Intelligence** – Paste or upload your resume; IBM Granite extracts skills, strengths, and role alignment.
- 🎯 **Personalized Questions** – Technical, behavioral, and situational questions tailored to your profile via RAG.
- 🤖 **AI Mock Interview** – Live evaluation of every answer with scoring, follow-up questions, and keyword analysis.
- 📊 **Performance Report** – Overall scores, skill gap table, 6-week improvement plan, and resource recommendations.

## Tech Stack

| Layer | Technology |
|---|---|
| AI Model | IBM Granite (`ibm/granite-4-h-small`) via watsonx.ai |
| Backend | Python 3.10+ / Flask 3 |
| RAG | Lightweight in-memory knowledge base (7 roles) |
| Frontend | Vanilla HTML / CSS / JS (dark SaaS theme) |

## Quick Start

```bash
# 1. Clone the repo and install dependencies
pip install -r requirements.txt

# 2. Create a .env file (copy from .env.example and fill in your values)
IBM_API_KEY=your_ibm_api_key_here
IBM_PROJECT_ID=your_project_id_here
IBM_MODEL_ID=ibm/granite-4-h-small
IBM_API_URL=https://us-south.ml.cloud.ibm.com/ml/v1/text/chat?version=2023-05-29
IBM_TOKEN_URL=https://iam.cloud.ibm.com/identity/token

# 3. Run (development)
python app.py
# → Open http://localhost:5000

# 3b. Run (production — Windows/Linux)
python server.py
```

## Project Structure

```
InterviewIQ/
├── app.py                    # Flask app — all API routes + IBM Granite + RAG
├── server.py                 # Production WSGI entry point (waitress)
├── requirements.txt
├── .env.example              # Environment variable template (copy to .env)
├── README.md
├── templates/
│   └── index.html            # Single-page application shell
├── static/
│   ├── css/style.css         # Dark SaaS UI
│   └── js/app.js             # Frontend state + API calls
└── docs/
    └── architecture/
        ├── blueprint.html    # Visual architecture diagram
        └── blueprint.md      # Mermaid + Markdown architecture reference
```

## Supported Roles

- Software Developer
- Data Analyst
- Python Developer
- Business Analyst
- Power BI Developer
- AI/ML Engineer
- Other

## AI Workflow (Agentic RAG)

```
Resume Input
    ↓
RAG Knowledge Base (role-specific context)
    ↓
IBM Granite → Resume Analysis JSON
    ↓
Question Generation (Technical + Behavioral + Situational)
    ↓
Per-answer Evaluation → Score / Feedback / Follow-up
    ↓
Final Report → Skill Gaps + Improvement Plan
```

---

*Powered by IBM Granite · IBM watsonx.ai*
