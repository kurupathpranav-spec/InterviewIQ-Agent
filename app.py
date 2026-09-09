import os
import json
import re
import time
import requests
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB limit
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# IBM Granite config — loaded from .env (see .env.example)
IBM_API_KEY    = os.getenv('IBM_API_KEY', '')
IBM_PROJECT_ID = os.getenv('IBM_PROJECT_ID', '')
IBM_MODEL_ID   = os.getenv('IBM_MODEL_ID', 'ibm/granite-4-h-small')
IBM_API_URL    = os.getenv('IBM_API_URL', 'https://us-south.ml.cloud.ibm.com/ml/v1/text/chat?version=2023-05-29')
IBM_TOKEN_URL  = os.getenv('IBM_TOKEN_URL', 'https://iam.cloud.ibm.com/identity/token')

# RAG knowledge base – concise reference per role
RAG_KNOWLEDGE = {
    "Data Analyst": {
        "key_skills": ["SQL", "Python/Pandas", "Excel", "Tableau/Power BI", "Statistics", "Data Cleaning", "ETL"],
        "common_topics": ["VLOOKUP vs INDEX-MATCH", "Window functions", "Hypothesis testing", "Data storytelling"],
        "behavioral_focus": ["Problem framing", "Stakeholder communication", "Attention to detail"]
    },
    "Python Developer": {
        "key_skills": ["Python OOP", "REST APIs", "Django/Flask", "Git", "Unit Testing", "SQL"],
        "common_topics": ["Decorators", "List comprehensions", "Async/await", "SOLID principles", "Design patterns"],
        "behavioral_focus": ["Code quality", "Debugging mindset", "Collaboration"]
    },
    "Software Developer": {
        "key_skills": ["Data structures", "Algorithms", "System design", "Git", "Testing", "CI/CD"],
        "common_topics": ["Big-O", "REST vs GraphQL", "Database indexing", "Microservices", "CAP theorem"],
        "behavioral_focus": ["Trade-off analysis", "Teamwork", "Deadline management"]
    },
    "Business Analyst": {
        "key_skills": ["Requirements gathering", "Process mapping", "SQL", "Stakeholder management", "Agile/Scrum"],
        "common_topics": ["User stories", "Gap analysis", "UML diagrams", "KPI definition", "Change management"],
        "behavioral_focus": ["Communication", "Conflict resolution", "Analytical thinking"]
    },
    "Power BI Developer": {
        "key_skills": ["DAX", "Power Query (M)", "Data modeling", "Row-level security", "SQL"],
        "common_topics": ["Star schema vs snowflake", "Calculated columns vs measures", "Incremental refresh"],
        "behavioral_focus": ["Requirement clarification", "Visual storytelling", "Documentation"]
    },
    "AI/ML": {
        "key_skills": ["Python", "Scikit-learn", "TensorFlow/PyTorch", "Statistics", "Feature engineering", "MLOps"],
        "common_topics": ["Bias-variance trade-off", "Cross-validation", "Gradient descent", "Transformer architecture", "RAG"],
        "behavioral_focus": ["Experimentation mindset", "Communicating results", "Ethical AI"]
    },
    "Other": {
        "key_skills": ["Problem solving", "Communication", "Adaptability", "Technical fundamentals"],
        "common_topics": ["General coding", "System design basics", "Project management"],
        "behavioral_focus": ["Teamwork", "Learning agility", "Initiative"]
    }
}


# ── IBM IAM token cache ──────────────────────────────────────────────────────
_iam_token = None
_iam_token_expiry = 0

def get_iam_token():
    global _iam_token, _iam_token_expiry
    if not IBM_API_KEY:
        raise RuntimeError("IBM_API_KEY is not set. Create a .env file — see .env.example.")
    if _iam_token and time.time() < _iam_token_expiry - 60:
        return _iam_token
    resp = requests.post(
        IBM_TOKEN_URL,
        data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": IBM_API_KEY},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )
    resp.raise_for_status()
    data = resp.json()
    _iam_token = data["access_token"]
    _iam_token_expiry = time.time() + data.get("expires_in", 3600)
    return _iam_token


def call_granite(messages, max_tokens=1200, temperature=0.7):
    """Call IBM Granite chat endpoint and return text response."""
    token = get_iam_token()
    payload = {
        "model_id": IBM_MODEL_ID,
        "project_id": IBM_PROJECT_ID,
        "messages": messages,
        "parameters": {
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.9
        }
    }
    resp = requests.post(
        IBM_API_URL,
        json=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=60
    )
    resp.raise_for_status()
    data = resp.json()
    # Extract text from response
    choices = data.get("choices", [])
    if choices:
        return choices[0].get("message", {}).get("content", "").strip()
    return data.get("results", [{}])[0].get("generated_text", "").strip()


def extract_pdf_text(file_path):
    """Extract text from a PDF file."""
    try:
        import PyPDF2
        text_parts = []
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        return "\n".join(text_parts)
    except Exception as e:
        return f"[PDF extraction error: {str(e)}]"


def get_rag_context(role):
    """Return RAG knowledge context for the given role."""
    info = RAG_KNOWLEDGE.get(role, RAG_KNOWLEDGE["Other"])
    return (
        f"Role knowledge base for {role}:\n"
        f"Key skills: {', '.join(info['key_skills'])}\n"
        f"Common interview topics: {', '.join(info['common_topics'])}\n"
        f"Behavioral focus: {', '.join(info['behavioral_focus'])}"
    )


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/analyze-resume', methods=['POST'])
def analyze_resume():
    """Analyze resume text or uploaded PDF with IBM Granite."""
    resume_text = ""

    if 'resume_file' in request.files:
        f = request.files['resume_file']
        if f and f.filename.lower().endswith('.pdf'):
            filename = secure_filename(f.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            f.save(path)
            resume_text = extract_pdf_text(path)
            try:
                os.remove(path)
            except Exception:
                pass

    if not resume_text:
        resume_text = request.form.get('resume_text', '').strip()

    role = request.form.get('role', 'Software Developer')
    experience = request.form.get('experience', 'Mid-level')
    name = request.form.get('name', 'Candidate')

    if not resume_text:
        return jsonify({"error": "Please provide resume text or upload a PDF."}), 400

    rag_ctx = get_rag_context(role)

    system_msg = (
        "You are an expert HR consultant and technical interviewer specializing in resume analysis. "
        "Analyze resumes thoroughly and provide actionable, specific insights. "
        "Always respond in valid JSON as instructed."
    )

    user_msg = f"""Analyze this resume for a {experience} {role} position.

{rag_ctx}

RESUME:
{resume_text[:3000]}

Return ONLY valid JSON (no markdown, no explanation) with this exact structure:
{{
  "candidate_name": "{name}",
  "detected_skills": ["skill1", "skill2", ...],
  "strengths": ["strength1", "strength2", "strength3"],
  "areas_to_improve": ["area1", "area2", "area3"],
  "role_relevance_score": <0-100 integer>,
  "role_relevance_summary": "2-sentence summary of fit for the role",
  "recommended_topics": ["topic1", "topic2", "topic3", "topic4"],
  "readiness_score": <0-100 integer>,
  "technical_score": <0-100 integer>,
  "communication_indicators": <0-100 integer>
}}"""

    try:
        raw = call_granite([
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ], max_tokens=800, temperature=0.3)

        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            result = json.loads(json_match.group())
        else:
            raise ValueError("No JSON in response")
        return jsonify(result)
    except Exception as e:
        # Structured fallback
        return jsonify({
            "candidate_name": name,
            "detected_skills": ["Communication", "Problem Solving", "Technical Fundamentals"],
            "strengths": ["Strong profile", "Relevant experience", "Good educational background"],
            "areas_to_improve": ["Deepen technical depth", "Quantify achievements", "Add more keywords"],
            "role_relevance_score": 70,
            "role_relevance_summary": f"Candidate shows potential for {role} with room to grow.",
            "recommended_topics": ["Data Structures", "System Design", "Communication", "Domain Knowledge"],
            "readiness_score": 70,
            "technical_score": 65,
            "communication_indicators": 75,
            "_note": "Fallback data – AI analysis temporarily unavailable."
        })


@app.route('/api/generate-questions', methods=['POST'])
def generate_questions():
    """Generate personalized interview questions."""
    data = request.get_json()
    role = data.get('role', 'Software Developer')
    experience = data.get('experience', 'Mid-level')
    skills = data.get('skills', [])
    interview_type = data.get('interview_type', 'Mixed')

    rag_ctx = get_rag_context(role)

    system_msg = (
        "You are an expert technical interviewer. Generate realistic, challenging, and relevant "
        "interview questions. Respond ONLY in valid JSON."
    )

    user_msg = f"""Generate interview questions for a {experience} {role} ({interview_type} focus).

{rag_ctx}
Candidate's detected skills: {', '.join(skills[:10]) if skills else 'General'}

Return ONLY valid JSON:
{{
  "technical": [
    {{"id": 1, "question": "...", "difficulty": "Easy|Medium|Hard", "topic": "..."}},
    {{"id": 2, "question": "...", "difficulty": "Easy|Medium|Hard", "topic": "..."}},
    {{"id": 3, "question": "...", "difficulty": "Easy|Medium|Hard", "topic": "..."}},
    {{"id": 4, "question": "...", "difficulty": "Medium|Hard", "topic": "..."}},
    {{"id": 5, "question": "...", "difficulty": "Hard", "topic": "..."}}
  ],
  "behavioral": [
    {{"id": 6, "question": "...", "type": "STAR", "competency": "..."}},
    {{"id": 7, "question": "...", "type": "STAR", "competency": "..."}},
    {{"id": 8, "question": "...", "type": "STAR", "competency": "..."}}
  ],
  "situational": [
    {{"id": 9, "question": "...", "scenario": "..."}},
    {{"id": 10, "question": "...", "scenario": "..."}}
  ]
}}"""

    try:
        raw = call_granite([
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ], max_tokens=1000, temperature=0.8)
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            result = json.loads(json_match.group())
            return jsonify(result)
        raise ValueError("No JSON found")
    except Exception as e:
        return jsonify({
            "technical": [
                {"id": 1, "question": f"Explain the core concepts you'd apply in a {role} position.", "difficulty": "Medium", "topic": "Fundamentals"},
                {"id": 2, "question": "Walk me through how you'd approach debugging a complex issue in production.", "difficulty": "Hard", "topic": "Problem Solving"},
                {"id": 3, "question": "What design patterns have you used and why?", "difficulty": "Medium", "topic": "Design"},
                {"id": 4, "question": "How do you ensure code quality in your projects?", "difficulty": "Medium", "topic": "Quality"},
                {"id": 5, "question": f"Describe a challenging technical problem you solved relevant to {role}.", "difficulty": "Hard", "topic": "Experience"}
            ],
            "behavioral": [
                {"id": 6, "question": "Tell me about a time you had to meet a tight deadline. How did you handle it?", "type": "STAR", "competency": "Time Management"},
                {"id": 7, "question": "Describe a situation where you disagreed with a team decision. What did you do?", "type": "STAR", "competency": "Conflict Resolution"},
                {"id": 8, "question": "Give an example of when you had to learn a new skill quickly.", "type": "STAR", "competency": "Learning Agility"}
            ],
            "situational": [
                {"id": 9, "question": "If you joined a project with no documentation, how would you get up to speed?", "scenario": "Onboarding"},
                {"id": 10, "question": "How would you handle a stakeholder requesting a feature that conflicts with technical best practices?", "scenario": "Stakeholder Management"}
            ]
        })


@app.route('/api/evaluate-answer', methods=['POST'])
def evaluate_answer():
    """Evaluate a single interview answer."""
    data = request.get_json()
    question = data.get('question', '')
    answer = data.get('answer', '')
    role = data.get('role', 'Software Developer')
    q_type = data.get('question_type', 'technical')

    if not answer.strip():
        return jsonify({"error": "Please provide an answer."}), 400

    system_msg = (
        "You are an expert interviewer evaluating candidate answers. "
        "Be specific, constructive, and fair. Respond ONLY in valid JSON."
    )

    user_msg = f"""Evaluate this {q_type} interview answer for a {role} position.

Question: {question}
Answer: {answer[:1500]}

Return ONLY valid JSON:
{{
  "score": <0-10 integer>,
  "grade": "Excellent|Good|Average|Below Average",
  "strengths": ["what they did well"],
  "improvements": ["specific improvements needed"],
  "model_answer_hint": "1-2 sentences on what an ideal answer would cover",
  "keywords_covered": ["relevant terms they mentioned"],
  "keywords_missing": ["important terms they should have mentioned"],
  "follow_up": "A natural follow-up question the interviewer might ask"
}}"""

    try:
        raw = call_granite([
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ], max_tokens=700, temperature=0.4)
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            result = json.loads(json_match.group())
            return jsonify(result)
        raise ValueError("No JSON")
    except Exception:
        score = min(10, max(1, len(answer.split()) // 10 + 3))
        return jsonify({
            "score": score,
            "grade": "Good" if score >= 7 else "Average",
            "strengths": ["Attempted the question", "Provided a response"],
            "improvements": ["Add more specific examples", "Use the STAR method for behavioral questions", "Include technical depth"],
            "model_answer_hint": "An ideal answer would include concrete examples, relevant terminology, and measurable outcomes.",
            "keywords_covered": [],
            "keywords_missing": ["specific examples", "measurable outcomes"],
            "follow_up": "Can you elaborate on a specific example from your experience?"
        })


@app.route('/api/generate-report', methods=['POST'])
def generate_report():
    """Generate final interview performance report."""
    data = request.get_json()
    role = data.get('role', 'Software Developer')
    scores = data.get('scores', [])
    answers_summary = data.get('answers_summary', [])
    candidate_name = data.get('candidate_name', 'Candidate')

    avg_score = round(sum(scores) / len(scores), 1) if scores else 5.0
    technical_scores = [s for i, s in enumerate(scores) if i < 5]
    behavioral_scores = [s for i, s in enumerate(scores) if i >= 5]
    tech_avg = round(sum(technical_scores) / len(technical_scores) * 10, 0) if technical_scores else 60
    beh_avg = round(sum(behavioral_scores) / len(behavioral_scores) * 10, 0) if behavioral_scores else 65

    system_msg = (
        "You are a senior HR consultant generating interview feedback reports. "
        "Be professional, specific, and encouraging. Respond ONLY in valid JSON."
    )

    user_msg = f"""Generate a comprehensive interview report for {candidate_name} applying for {role}.

Average score: {avg_score}/10
Technical average: {tech_avg}/100
Behavioral average: {beh_avg}/100
Questions answered: {len(scores)}

Return ONLY valid JSON:
{{
  "overall_score": {round(avg_score * 10, 0)},
  "technical_score": {tech_avg},
  "behavioral_score": {beh_avg},
  "communication_score": <estimate 0-100>,
  "hire_recommendation": "Strong Yes|Yes|Maybe|No",
  "executive_summary": "3-sentence overall assessment",
  "top_strengths": ["strength1", "strength2", "strength3"],
  "critical_gaps": ["gap1", "gap2"],
  "skill_gap_analysis": [
    {{"skill": "...", "current_level": "Beginner|Intermediate|Advanced", "required_level": "...", "priority": "High|Medium|Low"}}
  ],
  "improvement_plan": [
    {{"week": "Week 1-2", "focus": "...", "action": "..."}},
    {{"week": "Week 3-4", "focus": "...", "action": "..."}},
    {{"week": "Week 5-6", "focus": "...", "action": "..."}}
  ],
  "recommended_resources": [
    {{"type": "Course|Book|Practice", "title": "...", "reason": "..."}}
  ]
}}"""

    try:
        raw = call_granite([
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ], max_tokens=1000, temperature=0.4)
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            result = json.loads(json_match.group())
            return jsonify(result)
        raise ValueError("No JSON")
    except Exception:
        overall = round(avg_score * 10)
        return jsonify({
            "overall_score": overall,
            "technical_score": int(tech_avg),
            "behavioral_score": int(beh_avg),
            "communication_score": 72,
            "hire_recommendation": "Yes" if overall >= 70 else "Maybe",
            "executive_summary": f"{candidate_name} demonstrated solid foundational knowledge for the {role} position with room for improvement in technical depth and answer structure.",
            "top_strengths": ["Good communication", "Relevant experience", "Problem-solving approach"],
            "critical_gaps": ["Technical depth on advanced topics", "Structured answer delivery (STAR method)"],
            "skill_gap_analysis": [
                {"skill": "Technical Depth", "current_level": "Intermediate", "required_level": "Advanced", "priority": "High"},
                {"skill": "Answer Structure", "current_level": "Beginner", "required_level": "Intermediate", "priority": "High"}
            ],
            "improvement_plan": [
                {"week": "Week 1-2", "focus": "Technical Foundations", "action": f"Review core {role} concepts and practice coding challenges daily."},
                {"week": "Week 3-4", "focus": "Behavioral Answers", "action": "Prepare 5 STAR stories covering leadership, conflict, deadlines, and teamwork."},
                {"week": "Week 5-6", "focus": "Mock Interviews", "action": "Conduct 3 full mock interviews and review recordings for improvement."}
            ],
            "recommended_resources": [
                {"type": "Practice", "title": "LeetCode / HackerRank", "reason": "Sharpen algorithmic thinking"},
                {"type": "Course", "title": f"{role} Mastery Course on Coursera", "reason": "Fill knowledge gaps"},
                {"type": "Book", "title": "Cracking the Coding Interview", "reason": "Structured interview preparation"}
            ]
        })


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "model": IBM_MODEL_ID})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
