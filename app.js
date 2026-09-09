/* ═══════════════════════════════════════════════
   InterviewIQ – Frontend Application Logic
   ═══════════════════════════════════════════════ */

// ── State ─────────────────────────────────────────
const state = {
  analysisData: null,
  questions: [],       // flat list after merging categories
  currentQ: 0,
  scores: [],          // raw /10 scores per question
  evaluations: [],     // full eval objects
  candidateName: '',
  role: '',
  experience: '',
  interviewType: ''
};

// ── Navigation ────────────────────────────────────
function scrollToSection(id) {
  const el = document.getElementById(id);
  if (!el) return;
  // Show/hide sections
  document.querySelectorAll('.section').forEach(s => {
    s.classList.remove('active-section');
    s.classList.add('hidden-section');
  });
  el.classList.remove('hidden-section');
  el.classList.add('active-section');
  // Update nav
  document.querySelectorAll('.nav-link').forEach(l => {
    l.classList.toggle('active', l.dataset.section === id);
  });
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Wire nav links
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    scrollToSection(link.dataset.section);
  });
});

// ── Loading overlay ───────────────────────────────
function showLoading(msg) {
  document.getElementById('loading-text').textContent = msg || 'Processing with IBM Granite...';
  document.getElementById('loading-overlay').classList.remove('hidden');
}
function hideLoading() {
  document.getElementById('loading-overlay').classList.add('hidden');
}

// ── Toast ─────────────────────────────────────────
let toastTimeout;
function showToast(msg, isError) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.borderLeftColor = isError ? '#ff5252' : '#6c63ff';
  t.classList.add('show');
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => t.classList.remove('show'), 3500);
}

// ── Resume Analysis ───────────────────────────────
async function analyzeResume() {
  const name = document.getElementById('inp-name').value.trim();
  const role = document.getElementById('inp-role').value;
  const experience = document.getElementById('inp-exp').value;
  const itype = document.getElementById('inp-type').value;
  const resumeText = document.getElementById('inp-resume').value.trim();
  const pdfFile = document.getElementById('inp-pdf').files[0];

  if (!resumeText && !pdfFile) {
    showToast('Please paste your resume text or upload a PDF.', true);
    return;
  }
  if (!name) {
    showToast('Please enter your name.', true);
    return;
  }

  setBtn('analyze-btn-text', 'analyze-spinner', true, 'Analyzing...');
  showLoading('IBM Granite is analyzing your resume...');

  const fd = new FormData();
  fd.append('name', name || 'Candidate');
  fd.append('role', role);
  fd.append('experience', experience);
  fd.append('interview_type', itype);
  fd.append('resume_text', resumeText);
  if (pdfFile) fd.append('resume_file', pdfFile);

  try {
    const res = await fetch('/api/analyze-resume', { method: 'POST', body: fd });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    state.analysisData = data;
    state.candidateName = data.candidate_name || name;
    state.role = role;
    state.experience = experience;
    state.interviewType = itype;

    // Sync interview setup selects
    document.getElementById('q-role').value = role;
    document.getElementById('q-exp').value = experience;
    document.getElementById('q-type').value = itype;

    renderAnalysisResults(data);
    showToast('✅ Resume analyzed successfully!');
  } catch (err) {
    showToast('Analysis failed: ' + err.message, true);
  } finally {
    setBtn('analyze-btn-text', 'analyze-spinner', false, '🔍 Analyze with IBM Granite');
    hideLoading();
  }
}

function renderAnalysisResults(d) {
  // Scores row
  const scoreData = [
    { val: d.readiness_score || d.interview_readiness_score || 70, label: 'Readiness' },
    { val: d.technical_score || 65, label: 'Technical' },
    { val: d.communication_indicators || 75, label: 'Communication' },
    { val: d.role_relevance_score || 70, label: 'Role Fit' }
  ];
  document.getElementById('score-row').innerHTML = scoreData.map(s => `
    <div class="score-pill">
      <div class="sp-val">${s.val}<span style="font-size:14px">%</span></div>
      <div class="sp-label">${s.label}</div>
    </div>`).join('');

  // Skills
  document.getElementById('skills-block').innerHTML = blockHtml(
    '✅ Detected Skills',
    renderTags(d.detected_skills || [], '')
  );

  // Strengths
  document.getElementById('strengths-block').innerHTML = blockHtml(
    '💪 Strengths',
    renderTags(d.strengths || [], 'strength')
  );

  // Areas to improve / gaps
  document.getElementById('gaps-block').innerHTML = blockHtml(
    '⚠️ Areas to Improve',
    renderTags(d.areas_to_improve || d.skill_gaps || [], 'gap')
  );

  // Recommended topics
  document.getElementById('topics-block').innerHTML = blockHtml(
    '📚 Recommended Topics',
    renderTags(d.recommended_topics || [], 'topic')
  );

  // Relevance
  const rel = d.role_relevance_score || d.role_relevance || 70;
  document.getElementById('relevance-block').innerHTML = `
    <h4>🎯 Role Relevance — ${rel}%</h4>
    <div class="relevance-wrap">
      <div class="relevance-bar-bg"><div class="relevance-bar-fill" style="width:${rel}%"></div></div>
    </div>
    <p style="margin-top:8px;font-size:13px;color:var(--muted)">${d.role_relevance_summary || ''}</p>`;

  showEl('analysis-results');
}

function blockHtml(title, inner) {
  return `<div class="result-block"><h4>${title}</h4><div class="tag-cloud">${inner}</div></div>`;
}
function renderTags(arr, cls) {
  return (arr || []).map(t => `<span class="tag ${cls}">${t}</span>`).join('');
}

function proceedToInterview() {
  scrollToSection('interview');
  if (state.role) document.getElementById('q-role').value = state.role;
  if (state.experience) document.getElementById('q-exp').value = state.experience;
}

// ── Generate Questions ────────────────────────────
async function generateQuestions() {
  const role = document.getElementById('q-role').value;
  const experience = document.getElementById('q-exp').value;
  const itype = document.getElementById('q-type').value;

  state.role = role;
  state.experience = experience;
  state.interviewType = itype;

  setBtn('gen-btn-text', 'gen-spinner', true, 'Generating...');
  showLoading('IBM Granite is generating your personalized questions...');

  try {
    const res = await fetch('/api/generate-questions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        role, experience, interview_type: itype,
        skills: state.analysisData?.detected_skills || []
      })
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    // Flatten questions
    state.questions = [
      ...(data.technical || []).map(q => ({ ...q, category: 'Technical' })),
      ...(data.behavioral || []).map(q => ({ ...q, category: 'Behavioral' })),
      ...(data.situational || []).map(q => ({ ...q, category: 'Situational' }))
    ];
    state.currentQ = 0;
    state.scores = [];
    state.evaluations = [];

    startInterviewArena();
    showToast(`✅ ${state.questions.length} questions generated!`);
  } catch (err) {
    showToast('Failed to generate questions: ' + err.message, true);
  } finally {
    setBtn('gen-btn-text', 'gen-spinner', false, '⚡ Generate Questions');
    hideLoading();
  }
}

function startInterviewArena() {
  hideEl('interview-setup');
  showEl('interview-arena');
  renderQuestion();
}

function renderQuestion() {
  const q = state.questions[state.currentQ];
  if (!q) { finishInterview(); return; }

  const total = state.questions.length;
  const num = state.currentQ + 1;

  document.getElementById('q-counter').textContent = `Question ${num} of ${total}`;
  document.getElementById('q-type-badge').textContent = q.category || q.type || 'General';
  document.getElementById('q-difficulty').textContent = q.difficulty || 'Medium';
  document.getElementById('q-topic').textContent = `Topic: ${q.topic || q.competency || q.scenario || q.category || 'General'}`;
  document.getElementById('current-question').textContent = q.question;
  document.getElementById('answer-input').value = '';
  document.getElementById('interview-progress').style.width = `${(num / total) * 100}%`;

  hideEl('live-feedback');
  document.getElementById('answer-input').focus();
  renderScoreTracker();
}

// ── Submit Answer ─────────────────────────────────
async function submitAnswer() {
  const answer = document.getElementById('answer-input').value.trim();
  if (!answer) { showToast('Please type your answer before submitting.', true); return; }

  const q = state.questions[state.currentQ];
  setBtn('submit-btn-text', 'submit-spinner', true, 'Evaluating...');
  showLoading('IBM Granite is evaluating your answer...');

  try {
    const res = await fetch('/api/evaluate-answer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: q.question,
        answer,
        role: state.role,
        question_type: q.category || 'technical'
      })
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    state.scores.push(data.score);
    state.evaluations.push({ ...data, question: q.question, answer });
    renderFeedback(data);
  } catch (err) {
    showToast('Evaluation failed: ' + err.message, true);
  } finally {
    setBtn('submit-btn-text', 'submit-spinner', false, 'Submit Answer');
    hideLoading();
  }
}

function renderFeedback(d) {
  const score = d.score || 0;
  const grade = d.grade || 'Average';
  const pct = Math.round(score * 10);
  const color = pct >= 80 ? 'var(--accent3)' : pct >= 60 ? 'var(--warning)' : 'var(--danger)';

  document.getElementById('feedback-content').innerHTML = `
    <div class="feedback-score" style="color:${color}">${pct}/100</div>
    <div class="feedback-grade" style="color:${color}">${grade}</div>

    <div class="fb-section">
      <h4>✅ What You Did Well</h4>
      <ul>${(d.strengths || []).map(s => `<li>${s}</li>`).join('')}</ul>
    </div>

    <div class="fb-section">
      <h4>💡 Areas to Improve</h4>
      <ul>${(d.improvements || []).map(s => `<li>${s}</li>`).join('')}</ul>
    </div>

    ${d.model_answer_hint ? `
    <div class="fb-section">
      <h4>🎯 Model Answer Hint</h4>
      <p style="font-size:13px;color:var(--muted)">${d.model_answer_hint}</p>
    </div>` : ''}

    ${d.follow_up ? `
    <div class="follow-up-box">
      <strong>🔄 Follow-up Question</strong>
      ${d.follow_up}
    </div>` : ''}`;

  showEl('live-feedback');
  document.getElementById('next-q-btn').textContent =
    state.currentQ + 1 >= state.questions.length ? 'Finish Interview 🏁' : 'Next Question →';
  renderScoreTracker();
}

function renderScoreTracker() {
  const list = document.getElementById('tracker-list');
  if (!state.scores.length) { list.innerHTML = '<p style="color:var(--muted);font-size:13px">No answers yet</p>'; return; }
  list.innerHTML = state.scores.map((s, i) => {
    const pct = s * 10;
    const cls = pct >= 80 ? 'ts-good' : pct >= 60 ? 'ts-avg' : 'ts-bad';
    const q = state.questions[i];
    return `<div class="tracker-item">
      <span>Q${i + 1} · ${q?.category || 'General'}</span>
      <span class="tracker-score ${cls}">${pct}/100</span>
    </div>`;
  }).join('');
}

function nextQuestion() {
  state.currentQ++;
  if (state.currentQ >= state.questions.length) {
    finishInterview();
  } else {
    renderQuestion();
  }
}

function skipQuestion() {
  state.scores.push(0);
  state.evaluations.push({ question: state.questions[state.currentQ]?.question, skipped: true, score: 0 });
  nextQuestion();
}

// ── Finish Interview ──────────────────────────────
function finishInterview() {
  hideEl('interview-arena');
  scrollToSection('report');
  generateReport();
}

// ── Generate Report ───────────────────────────────
async function generateReport() {
  document.getElementById('report-placeholder').style.display = 'none';
  showLoading('IBM Granite is generating your performance report...');

  const avgScore = state.scores.length
    ? (state.scores.reduce((a, b) => a + b, 0) / state.scores.length)
    : 5;

  try {
    const res = await fetch('/api/generate-report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        candidate_name: state.candidateName || 'Candidate',
        role: state.role,
        scores: state.scores,
        answers_summary: state.evaluations.map(e => ({
          question: e.question,
          score: e.score,
          grade: e.grade
        }))
      })
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    renderReport(data);
    showToast('✅ Report generated!');
  } catch (err) {
    showToast('Report generation failed: ' + err.message, true);
  } finally {
    hideLoading();
  }
}

function renderReport(d) {
  // Score cards
  const scores = [
    { val: d.overall_score || 70, label: 'Overall Score' },
    { val: d.technical_score || 65, label: 'Technical' },
    { val: d.behavioral_score || 70, label: 'Behavioral' },
    { val: d.communication_score || 72, label: 'Communication' }
  ];
  document.getElementById('report-scores').innerHTML = scores.map(s => `
    <div class="report-score-card">
      <div class="rsc-val">${s.val}</div>
      <div class="rsc-label">${s.label}</div>
    </div>`).join('');

  // Summary
  document.getElementById('report-summary').textContent = d.executive_summary || d.performance_summary || '';
  const rec = d.hire_recommendation || 'Maybe';
  const recClass = rec.toLowerCase().includes('yes') ? 'hire-yes' : rec.toLowerCase() === 'no' ? 'hire-no' : 'hire-maybe';
  document.getElementById('hire-badge').innerHTML = `<span class="hire-badge ${recClass}">Hire Recommendation: ${rec}</span>`;

  // Strengths & Gaps
  document.getElementById('report-strengths').innerHTML = (d.top_strengths || []).map(s => `<li>${s}</li>`).join('');
  document.getElementById('report-gaps').innerHTML = (d.critical_gaps || d.key_skill_gaps || []).map(s => `<li>${s}</li>`).join('');

  // Skill gap table
  const gaps = d.skill_gap_analysis || [];
  document.getElementById('skill-gap-table').innerHTML = gaps.length ? `
    <table class="gap-table">
      <thead><tr><th>Skill</th><th>Current</th><th>Required</th><th>Priority</th></tr></thead>
      <tbody>${gaps.map(g => `
        <tr>
          <td>${g.skill}</td>
          <td>${g.current_level}</td>
          <td>${g.required_level}</td>
          <td class="priority-${(g.priority || 'medium').toLowerCase()}">${g.priority}</td>
        </tr>`).join('')}
      </tbody>
    </table>` : '<p style="color:var(--muted)">No skill gap data available.</p>';

  // Improvement plan
  const plan = d.improvement_plan || [];
  document.getElementById('improvement-plan').innerHTML = plan.map(p => `
    <div class="plan-row">
      <div class="plan-week">${p.week}</div>
      <div>
        <div class="plan-focus">${p.focus}</div>
        <div class="plan-action">${p.action || (p.actions || []).join(', ')}</div>
      </div>
    </div>`).join('');

  // Resources
  const resources = d.recommended_resources || [];
  document.getElementById('resources-list').innerHTML = resources.map(r => {
    if (typeof r === 'string') return `<div class="resource-item"><span class="resource-type">Resource</span><div><div class="resource-title">${r}</div></div></div>`;
    return `<div class="resource-item">
      <span class="resource-type">${r.type || 'Resource'}</span>
      <div>
        <div class="resource-title">${r.title}</div>
        <div class="resource-reason">${r.reason || ''}</div>
      </div>
    </div>`;
  }).join('');

  showEl('report-content');
}

// ── Restart ───────────────────────────────────────
function restartInterview() {
  state.questions = [];
  state.currentQ = 0;
  state.scores = [];
  state.evaluations = [];
  hideEl('report-content');
  document.getElementById('report-placeholder').style.display = '';
  // Reset interview UI
  showEl('interview-setup');
  hideEl('interview-arena');
  scrollToSection('interview');
}

// ── Helpers ───────────────────────────────────────
function setBtn(textId, spinnerId, loading, text) {
  const t = document.getElementById(textId);
  const s = document.getElementById(spinnerId);
  if (t) t.textContent = text;
  if (s) s.classList.toggle('hidden', !loading);
}
function showEl(id) {
  const el = document.getElementById(id);
  if (el) { el.classList.remove('hidden-section'); el.style.display = ''; }
}
function hideEl(id) {
  const el = document.getElementById(id);
  if (el) { el.classList.add('hidden-section'); }
}
