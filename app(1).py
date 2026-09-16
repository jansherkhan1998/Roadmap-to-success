from datetime import date
import json
import os
from fpdf import FPDF
from google import genai
from google.genai import types
import streamlit as st

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Roadmap to success", page_icon="📚", layout="wide"
)


# ============================================================
# AVAILABLE TESTS
# ============================================================

EXAMS = [
    "MDCAT",
    "ECAT",
    "NUST NET",
    "NTS NAT",
    "NTS GAT",
    "ISSB Initial Test",
    "FAST-NU Admission Test",
    "COMSATS Admission Test",
    "ETEA Engineering",
    "ETEA Medical",
    "UET Entrance Test",
    "Other / Custom Test",
]

LEVELS = ["Beginner", "Intermediate", "Advanced"]

SUBJECTS = [
    "Mathematics",
    "Physics",
    "Chemistry",
    "Biology",
    "English",
    "IQ / Analytical Reasoning",
    "General Knowledge",
    "Mixed",
]


# ============================================================
# GEMINI API
# ============================================================


def get_api_key():
  """Read the Gemini API key from Streamlit secrets or an environment variable."""
  try:
    key = st.secrets.get("GEMINI_API_KEY")
  except Exception:
    key = None

  return key or os.getenv("GEMINI_API_KEY")


@st.cache_resource
def get_client(api_key):
  return genai.Client(api_key=api_key)


def ask_gemini(prompt, json_mode=False):
  api_key = get_api_key()

  if not api_key:
    raise RuntimeError(
        "Gemini API key is missing. Add GEMINI_API_KEY to Streamlit Secrets."
    )

  client = get_client(api_key)

  config = types.GenerateContentConfig(
      temperature=0.7,
      response_mime_type="application/json" if json_mode else "text/plain",
  )

  response = client.models.generate_content(
      model="gemini-3.6-flash", contents=prompt, config=config
  )

  return response.text


# ============================================================
# JSON CLEANER
# ============================================================


def clean_json(text):
  text = text.strip()

  if text.startswith("```"):
    lines = text.splitlines()

    if lines[-1].strip().startswith("```"):
      lines = lines[1:-1]
    else:
      lines = lines[1:]

    text = "\n".join(lines).strip()

  return json.loads(text)


# ============================================================
# PDF GENERATOR
# ============================================================


def generate_roadmap_pdf(data, exam_name):
  pdf = FPDF()
  pdf.add_page()
  pdf.set_auto_page_break(auto=True, margin=15)

  # Title
  pdf.set_font("Helvetica", "B", 16)
  pdf.cell(
      0, 10, f"Preparation Roadmap: {exam_name}", new_x="LMARGIN", new_y="NEXT"
  )
  pdf.ln(5)

  # Summary
  pdf.set_font("Helvetica", "B", 12)
  pdf.cell(0, 8, "Executive Summary", new_x="LMARGIN", new_y="NEXT")
  pdf.set_font("Helvetica", "", 10)
  summary_text = data.get("summary", "").encode("latin-1", "replace").decode("latin-1")
  pdf.multi_cell(0, 5, summary_text)
  pdf.ln(5)

  # Schedule Table
  schedule = data.get("day_by_day_schedule", [])
  if schedule:
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Day-by-Day Schedule", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Render Table
    with pdf.table(
        col_widths=(15, 25, 45, 80, 20), text_align="LEFT"
    ) as table:
      header = table.row()
      header.cell("Day #")
      header.cell("Subject")
      header.cell("Topic")
      header.cell("Action Items")
      header.cell("Hours")

      for row_data in schedule:
        row = table.row()
        row.cell(str(row_data.get("day_number", "")))
        row.cell(
            str(row_data.get("subject", ""))
            .encode("latin-1", "replace")
            .decode("latin-1")
        )
        row.cell(
            str(row_data.get("topic", ""))
            .encode("latin-1", "replace")
            .decode("latin-1")
        )
        row.cell(
            str(row_data.get("action_items", ""))
            .encode("latin-1", "replace")
            .decode("latin-1")
        )
        row.cell(str(row_data.get("hours", "")))

  # PDF Output
  return bytes(pdf.output())


# ============================================================
# ROADMAP PROMPT
# ============================================================


def roadmap_prompt(exam, exam_date, level, hours, focus):
  days = max(1, (exam_date - date.today()).days)

  return f"""
You are an elite, high-stakes Academic Strategist for Pakistani Competitive Exams ({exam}). 
The student wants to score maximum/perfect marks in {days} days.

Create an INTENSE, non-casual, highly motivating, and granular 90-day execution roadmap.

STUDENT PROFILE:
- Target Exam: {exam}
- Time Horizon: {days} Days
- Starting Level: {level}
- Daily Commitment: {hours} Hours/day
- Focus Area: {focus or "Overall High-Yield Mastery"}

CORE DIRECTIVES FOR THE ROADMAP:
1. Divide the {days} days into 3 distinct gamified phases:
   - Phase 1: Foundation & Chapter Crucible (Days 1 to 45) -> Deep FSc/A-Level textbook coverage.
   - Phase 2: High-Speed Practice & Topic Blitz (Days 46 to 75) -> Past papers, numerical tricks, and error logging.
   - Phase 3: Simulated Exam Execution & Revision (Days 76 to {days}) -> Full-length mock tests and rapid review.
2. Provide a sample WEEK-BY-WEEK and DAY-BY-DAY schedule table. Every day MUST specify:
   - Specific FSc/A-Level Chapter names (e.g., "Physics: Work & Energy", "Biology: Biological Molecules").
   - Concrete daily goals (e.g., "Solve 80 MCQs under timed conditions", "Memorize 15 organic reaction mechanisms").
   - Daily morning vs. evening time allocation.

Return ONLY valid JSON with this exact schema:

{{
    "strategy_title": "Game Plan Title",
    "target_score_mentality": "Executive strategy statement to hit top marks",
    "phases": [
        {{
            "phase_name": "Phase 1: Foundation Crucible",
            "duration": "Days 1-45",
            "primary_goal": "Goal description",
            "daily_target_mcqs": 60
        }},
        {{
            "phase_name": "Phase 2: Speed & MCQ Mastery",
            "duration": "Days 46-75",
            "primary_goal": "Goal description",
            "daily_target_mcqs": 100
        }},
        {{
            "phase_name": "Phase 3: Full Mock Execution",
            "duration": "Days 76-90",
            "primary_goal": "Goal description",
            "daily_target_mcqs": 180
        }}
    ],
    "day_by_day_schedule": [
        {{
            "day_number": 1,
            "phase": "Phase 1",
            "subject": "Biology & Physics",
            "topics": "Bio: Cell Structure & Function | Phys: Scalars & Vectors",
            "morning_session": "Read textbook chapters thoroughly & annotate key terms (2.5 hrs)",
            "evening_session": "Solve 50 topic-wise MCQs & update Error Log (1.5 hrs)",
            "daily_mcq_target": 50,
            "hours": {hours}
        }}
    ],
    "error_log_protocol": [
        "Rule 1 for tracking wrong answers",
        "Rule 2 for spaced repetition"
    ],
    "final_week_rules": [
        "Rule 1 for mock exams",
        "Rule 2 for stress management"
    ]
}}
"""

# ============================================================
# MCQ PROMPT
# ============================================================


def mcq_prompt(exam, subject, difficulty, count, level):
  return f"""
Create {count} original practice MCQs for Pakistani entrance test preparation.

Exam: {exam}
Subject: {subject}
Difficulty: {difficulty}
Student Level: {level}

Return ONLY valid JSON:
{{
    "questions": [
        {{
            "question": "Question text",
            "options": {{
                "A": "Option A",
                "B": "Option B",
                "C": "Option C",
                "D": "Option D"
            }},
            "answer": "A",
            "explanation": "Short explanation",
            "topic": "Topic"
        }}
    ]
}}
"""


# ============================================================
# DISPLAY ROADMAP
# ============================================================


def show_roadmap(data, exam_name):
  st.subheader("🗺️ Your Detailed AI Preparation Roadmap")

  st.info(data.get("summary", ""))

  if data.get("assumptions"):
    with st.expander("Notes & Verification"):
      for item in data["assumptions"]:
        st.write("• " + item)

  # Render Day-by-Day Schedule as a Table
  schedule = data.get("day_by_day_schedule", [])
  if schedule:
    st.subheader("📅 Day-by-Day Detailed Schedule")
    st.table(schedule)

  if data.get("final_week"):
    st.subheader("🔥 Final Week Plan")
    for item in data["final_week"]:
      st.write("• " + item)

  if data.get("exam_day"):
    st.subheader("🎯 Exam-Day Strategy")
    for item in data["exam_day"]:
      st.write("• " + item)

  # Download PDF Section
  st.divider()
  st.subheader("📥 Download Roadmap")
  try:
    pdf_bytes = generate_roadmap_pdf(data, exam_name)
    st.download_button(
        label="📄 Download Detailed PDF Roadmap",
        data=pdf_bytes,
        file_name=f"{exam_name}_Roadmap.pdf",
        mime="application/pdf",
        type="primary",
    )
  except Exception as e:
    st.error(f"Could not generate PDF download: {e}")


# ============================================================
# QUIZ ENGINE
# ============================================================


def run_quiz(questions):
  if (
      "quiz_answers" not in st.session_state
      or len(st.session_state.quiz_answers) != len(questions)
  ):
    st.session_state.quiz_answers = [None for _ in questions]

  for i, question in enumerate(questions):
    st.markdown(f"### Q{i + 1}. {question['question']}")

    answer = st.radio(
        "Select an answer",
        options=["A", "B", "C", "D"],
        format_func=lambda x, options=question["options"]: f"{x}. {options[x]}",
        key=f"question_{i}",
        index=None,
    )

    st.session_state.quiz_answers[i] = answer

  if st.button("Submit Test", type="primary"):
    score = sum(
        answer == question["answer"]
        for answer, question in zip(
            st.session_state.quiz_answers, questions
        )
    )

    percentage = (score / len(questions)) * 100

    st.success(f"Score: {score}/{len(questions)} ({percentage:.1f}%)")

    st.subheader("📊 Answer Review")

    for i, question in enumerate(questions):
      user_answer = st.session_state.quiz_answers[i]
      correct_answer = question["answer"]

      if user_answer == correct_answer:
        st.write(f"✅ Q{i + 1}: Correct")
      else:
        st.write(
            f"❌ Q{i + 1}: Correct answer = **{correct_answer}**"
        )
        st.caption(question["explanation"])


# ============================================================
# HEADER & SIDEBAR
# ============================================================

st.title("📚 Roadmap to success")
st.caption(
    "AI-powered preparation roadmaps and practice MCQs for Pakistani entrance"
    " tests."
)

with st.sidebar:
  st.header("👨‍🎓 Student Profile")
  exam = st.selectbox("Select Test", EXAMS)
  custom_exam = st.text_input(
      "Custom Test Name", disabled=(exam != "Other / Custom Test")
  )

  exam_name = (
      custom_exam.strip()
      if (exam == "Other / Custom Test" and custom_exam.strip())
      else exam
  )
  exam_date = st.date_input("Target Test Date", min_value=date.today())
  level = st.selectbox("Preparation Level", LEVELS)
  hours = st.slider("Study Hours Per Day", 1, 12, 4)
  focus = st.text_input("Special Focus", placeholder="e.g. Physics numericals")


# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3 = st.tabs(
    ["🗺️ Preparation Roadmap", "📝 Practice MCQs", "ℹ️ How It Works"]
)

with tab1:
  days = max(0, (exam_date - date.today()).days)
  col1, col2, col3 = st.columns(3)
  col1.metric("Test", exam_name)
  col2.metric("Days Remaining", days)
  col3.metric("Level", level)

  if st.button(
      "🚀 Generate My Complete Roadmap",
      type="primary",
      use_container_width=True,
  ):
    with st.spinner("Building your personalized day-by-day roadmap..."):
      try:
        response = ask_gemini(
            roadmap_prompt(exam_name, exam_date, level, hours, focus),
            json_mode=True,
        )
        data = clean_json(response)
        st.session_state.roadmap = data
      except Exception as error:
        st.error(f"Could not generate roadmap: {error}")

  if "roadmap" in st.session_state:
    show_roadmap(st.session_state.roadmap, exam_name)

with tab2:
  st.subheader("📝 AI Practice Test Generator")
  col1, col2, col3, col4 = st.columns(4)
  subject = col1.selectbox("Subject", SUBJECTS)
  difficulty = col2.selectbox("Difficulty", ["Easy", "Medium", "Hard", "Mixed"])
  count = col3.selectbox("Number of Questions", [5, 10, 15, 20], index=1)
  quiz_level = col4.selectbox("Student Level", LEVELS, key="quiz_level")

  if st.button(
      "🎯 Generate New MCQ Test", type="primary", use_container_width=True
  ):
    with st.spinner("Generating practice questions..."):
      try:
        response = ask_gemini(
            mcq_prompt(exam_name, subject, difficulty, count, quiz_level),
            json_mode=True,
        )
        data = clean_json(response)
        questions = data.get("questions", [])
        st.session_state.questions = questions
        st.session_state.quiz_answers = [None for _ in questions]
      except Exception as error:
        st.error(f"Could not generate test: {error}")

  if "questions" in st.session_state and st.session_state.questions:
    run_quiz(st.session_state.questions)

with tab3:
  st.markdown("""
### 🚀 PakPrep AI Features
1. **Day-by-Day Table Schedule**: Generates explicit topics, chapters, and hours per day.
2. **Downloadable PDF**: Export your personalized roadmap to a clean PDF file to read later.
3. **Interactive MCQ Engine**: Generate original practice MCQs with explanations and answer keys.
""")
