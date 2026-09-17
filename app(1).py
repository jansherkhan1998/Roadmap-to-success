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

import time
from google.genai.errors import APIError


def ask_gemini(prompt, json_mode=False, max_retries=5):
  api_key = get_api_key()

  if not api_key:
    raise RuntimeError(
        "Gemini API key is missing. Add GEMINI_API_KEY to Streamlit Secrets."
    )

  client = get_client(api_key)

  config = types.GenerateContentConfig(
      temperature=0.3,
      max_output_tokens=8192,  # Ensures long structured outputs fit
      response_mime_type="application/json" if json_mode else "text/plain",
  )

  # Automatic retry logic for temporary server-side spikes (503/429 errors)
  for attempt in range(max_retries):
    try:
      response = client.models.generate_content(
          model="gemini-3.5-flash", contents=prompt, config=config
      )
      return response.text

    except APIError as e:
      # If it's a 503 (Overloaded) or 429 (Rate Limit) error, retry automatically
      if ("503" in str(e) or "429" in str(e)) and attempt < max_retries - 1:
        wait_time = (2**attempt) + 1  # Waits 2s, 3s, 5s, 9s...
        time.sleep(wait_time)
      else:
        raise e  # If retries run out or it's a different error, raise it


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

  try:
    return json.loads(text)
  except json.JSONDecodeError as e:
    st.error(
        f"Failed to parse AI output into JSON: {e}. Please click 'Generate' again."
    )
    return {}


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
  weeks = max(1, days // 7)

  # 1. Dynamic Granularity Rule to prevent Token Errors
  if weeks > 16:
    structure_type = "Macro-Phases (Block of Weeks)"
    granularity_instruction = f"""
        Given the long preparation window ({days} days / {weeks} weeks), group the output into 4-6 MACRO PHASES.
        Do NOT write individual days. Write structured blocks (e.g. Phase 1: Weeks 1-6, Phase 2: Weeks 7-12...).
        """
  elif weeks > 4:
    structure_type = "Weekly Schedule"
    granularity_instruction = f"""
        Group the schedule into WEEKLY blocks ({weeks} Weeks total).
        For each week, specify exact chapter targets and MCQ quotas.
        """
  else:
    structure_type = "Daily Schedule"
    granularity_instruction = (
        f"Provide a granular DAY-BY-DAY schedule covering all {days} days."
    )

  return f"""
You are the Chief Academic Strategist for Pakistani Competitive & University Entrance Exams.

STUDENT & EXAM SPECIFICATIONS:
- Target Test: {exam}
- Target Date: {exam_date.isoformat()} ({days} days / {weeks} weeks remaining)
- Starting Level: {level}
- Commitment: {hours} hours/day
- Focus Area: {focus or "Full Syllabus High-Yield Coverage"}

TEST-SPECIFIC SYLLABUS DIRECTIVES:
- If MDCAT: Prioritize Biology (81 MCQs), Chemistry (45 MCQs), Physics (36 MCQs), English & Logical Reasoning.
- If ECAT/UET: Prioritize Math (30 MCQs), Physics (30 MCQs), Chemistry/CS (30 MCQs), English (10 MCQs).
- If NUST NET: Focus on Math (50%), Physics (30%), English (20%) time-management (~50s per MCQ).
- If NTS NAT/GAT/FAST: Heavy focus on Analytical Reasoning, Quantitative, Verbal, and IQ.

FORMAT INSTRUCTIONS:
{granularity_instruction}

Return ONLY valid JSON matching this schema:
{{
    "exam_name": "{exam}",
    "timeframe_type": "{structure_type}",
    "strategy_title": "Target 100% Mastery Plan for {exam}",
    "exam_breakdown_notes": "Key paper pattern and weightage strategy",
    "phases": [
        {{
            "phase_name": "Phase Name",
            "duration": "e.g. Weeks 1-6 or Days 1-10",
            "primary_goal": "Phase Focus Goal",
            "weekly_mcq_target": 500
        }}
    ],
    "schedule": [
        {{
            "time_block": "Week 1 (or Phase 1: W1-W6)",
            "subject_focus": "Primary & Secondary Subjects",
            "chapters_to_cover": "Exact Chapter Names (e.g. Bio Ch 1-3, Phys Vectors)",
            "recommended_books": "e.g. Punjab/KPK Textbooks, KIPS, STEP, Past Papers",
            "action_tasks": "Specific daily morning/evening study tasks",
            "practice_target": "Exact MCQ count and timed drills",
            "priority_yield": "High / Medium / Very High"
        }}
    ],
    "error_log_protocol": ["Rule 1 for tracking mistakes", "Rule 2"],
    "test_day_strategy": ["Tip 1 for time management on test day", "Tip 2"]
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


import pandas as pd
import streamlit as st


def show_roadmap(data, exam_name):
  if not data:
    st.warning("⚠️ No roadmap data available. Please regenerate.")
    return

  # Strategy Header & Mentality Card
  title = data.get("strategy_title", f"Target 100% Mastery Plan for {exam_name}")
  mentality = data.get("target_score_mentality") or data.get(
      "exam_breakdown_notes", ""
  )

  st.subheader(f"🔥 {title}")
  if mentality:
    st.info(f"🎯 **Strategy & Breakdown:** {mentality}")

  # Render Preparation Phases Summary Cards
  phases = data.get("phases", [])
  if phases:
    st.markdown("### 🏆 Preparation Phases")
    cols = st.columns(len(phases))
    for idx, phase in enumerate(phases):
      with cols[idx]:
        st.metric(
            label=phase.get("phase_name", f"Phase {idx+1}"),
            value=phase.get("duration", ""),
            delta=f"Target: {phase.get('weekly_mcq_target', phase.get('daily_target_mcqs', 0))} MCQs/block",
        )
        st.caption(phase.get("primary_goal", ""))

  st.divider()

  # High-Yield Interactive Table
  schedule_data = data.get("schedule") or data.get("day_by_day_schedule", [])

  if schedule_data:
    st.markdown("### 📅 Comprehensive Preparation Plan & Interactive Tracker")
    st.caption("💡 Check off completed blocks as you finish studying!")

    # Convert to pandas DataFrame for st.data_editor
    df = pd.DataFrame(schedule_data)

    # Ensure Completed column exists for interactive tracking
    if "completed" not in df.columns:
      df.insert(0, "completed", False)

    # Define exact Streamlit Column Configuration
    column_config = {
        "completed": st.column_config.CheckboxColumn(
            "Status", help="Mark off completed study blocks", default=False
        ),
        "time_block": st.column_config.TextColumn(
            "Timeline", help="Day/Week/Phase Identifier"
        ),
        "subject_focus": st.column_config.TextColumn(
            "Subject Focus", help="Main subject focus for this block"
        ),
        "chapters_to_cover": st.column_config.TextColumn(
            "Exact FSc/A-Level Chapters", help="Specific textbook chapters"
        ),
        "recommended_books": st.column_config.TextColumn(
            "Recommended Books & Resources", help="Suggested reference books"
        ),
        "action_tasks": st.column_config.TextColumn(
            "Primary Study Tasks", help="Morning theory & evening practice"
        ),
        "practice_target": st.column_config.TextColumn(
            "MCQ Target", help="Target questions to solve"
        ),
        "active_recall": st.column_config.TextColumn(
            "Active Recall Technique", help="Method for revision"
        ),
        "examiner_trap": st.column_config.TextColumn(
            "Exam Shortcut / Trap", help="Common traps and shortcuts"
        ),
        "target_accuracy": st.column_config.TextColumn(
            "Accuracy Checkpoint", help="Benchmark score goal"
        ),
        "error_log_focus": st.column_config.TextColumn(
            "Error Log Focus Area", help="What mistakes to log"
        ),
        "priority_yield": st.column_config.TextColumn(
            "Yield Priority", help="Weightage level"
        ),
    }

    # Render interactive table
    edited_df = st.data_editor(
        df,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        key=f"roadmap_editor_{exam_name}",
    )

    # Display completion metric based on user checks
    completed_count = edited_df["completed"].sum()
    total_count = len(edited_df)
    progress_pct = (
        int((completed_count / total_count) * 100) if total_count > 0 else 0
    )

    st.progress(
        progress_pct / 100, text=f"Progress: {progress_pct}% Completed"
    )

  else:
    st.warning("⚠️ Schedule items could not be loaded. Please regenerate.")

  st.divider()

  # Error Protocol & Test Day Rules
  col1, col2 = st.columns(2)

  with col1:
    st.markdown("### ⚠️ Error Log Protocol")
    for rule in data.get("error_log_protocol", []):
      st.write("• " + rule)

  with col2:
    st.markdown("### 🎯 Test Day Strategy & Rules")
    rules = data.get("test_day_strategy") or data.get("final_execution_rules", [])
    for rule in rules:
      st.write("• " + rule)

  # Download Section
  st.divider()
  st.markdown("### 📥 Export Execution Plan")
  try:
    pdf_bytes = generate_roadmap_pdf(data, exam_name)
    st.download_button(
        label="📄 Download Detailed PDF Roadmap",
        data=pdf_bytes,
        file_name=f"{exam_name}_Mastery_Plan.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True,
    )
  except Exception as e:
    st.error(f"Could not generate PDF: {e}")
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
