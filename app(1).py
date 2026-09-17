from datetime import date
import io
import json
import os
from google import genai
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer
import streamlit as st

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Pakistani Entrance Test Preparation Roadmap",
    page_icon="📚",
    layout="wide",
)

st.title("📚 AI Entrance Test Preparation Roadmap")
st.write(
    "Generate a personalized preparation roadmap and continuous practice"
    " test suites for Pakistani entrance tests."
)

# ============================================================
# HELPER FUNCTIONS & TEST SPECIFICATIONS
# ============================================================


def get_gemini_api_key():
  """Retrieve API key from Streamlit secrets, environment variables, or session state."""
  if "api_key" in st.session_state and st.session_state["api_key"]:
    return st.session_state["api_key"]

  try:
    if "GEMINI_API_KEY" in st.secrets:
      return st.secrets["GEMINI_API_KEY"]
  except Exception:
    pass

  return os.getenv("GEMINI_API_KEY", "")


def get_test_pattern_info(test_name):
  """Returns strict pattern metadata for official Pakistani entrance tests."""
  patterns = {
      "MDCAT": (
          "180 MCQs total (3 Hours, No Negative Marking). Breakdown: Biology 81"
          " MCQs (45%), Chemistry 45 MCQs (25%), Physics 36 MCQs (20%),"
          " English 9 MCQs (5%), Logical Reasoning 9 MCQs (5%)."
      ),
      "ECAT / Engineering Tests": (
          "100 MCQs total (100 Minutes, 400 Marks). Breakdown: Mathematics 30"
          " MCQs, Physics 30 MCQs, Chemistry/CS 30 MCQs, English 10 MCQs."
      ),
      "NUST NET": (
          "200 MCQs total (3 Hours, No Negative Marking). Breakdown:"
          " Mathematics 100 MCQs (50%), Physics 60 MCQs (30%), English 40 MCQs"
          " (20%)."
      ),
      "FAST": (
          "120 MCQs total across Advanced Math, Basic Math, Physics, English,"
          " and IQ/Analytical with negative marking applied to specific"
          " sections."
      ),
      "NTS NAT": (
          "90 MCQs total (2 Hours). Breakdown: Verbal 20 MCQs, Analytical 20"
          " MCQs, Quantitative 20 MCQs, Subject Specific 30 MCQs."
      ),
      "ISSB Initial Computer Test": (
          "Computerized timed test: Verbal Intelligence Test (approx 84"
          " questions / 30 mins) + Non-Verbal Intelligence Test (approx 64"
          " questions / 30 mins) + Academic Test (50 questions / 25 mins)."
      ),
      "Army Medical College (AMC) Test": (
          "Intelligence Test (Verbal + Non-Verbal) followed by Academic Test"
          " covering Biology, Chemistry, Physics, and English."
      ),
  }
  return patterns.get(
      test_name,
      "Follow official standard test distribution and pattern for this"
      " specific university/test.",
  )


def build_roadmap_prompt(
    test_name, exam_date, days_remaining, level, hours_per_day
):
  pattern_info = get_test_pattern_info(test_name)
  return f"""
You are an expert Pakistani entrance-test preparation strategist, academic planner, and curriculum specialist.

Create a practical personalized preparation roadmap for:

Target Test: {test_name}
Official Pattern Details: {pattern_info}
Target Exam Date: {exam_date}
Days Remaining: {days_remaining}
Current Preparation Level: {level}
Daily Available Study Hours: {hours_per_day}

CRITICAL ACCURACY REQUIREMENT:
You MUST strictly adhere to the exact official paper pattern provided above.

Include:
1. Executive summary
2. Official Exam structure & Exact Section Distribution
3. High-yield subjects and topics
4. Phase-wise plan:
   - Phase 1: Syllabus Coverage / Concept Building
   - Phase 2: Revision / Weak Area Improvement
   - Phase 3: Mock Practice / Exam Simulation
5. Day-by-day roadmap
6. Daily study schedule based on {hours_per_day} hours
7. MCQ and mock-test strategy
8. Time-management strategy
9. Negative-marking strategy (only where applicable)
10. Computer-based-test strategy where relevant
11. Weekly performance tracking framework
12. Final 7-day strategy
13. Exam-day strategy
14. Top 10 personalized priorities
15. Five common mistakes to avoid
16. Five measurable preparation targets

Use clear Markdown, headings, and bullet points. Avoid vague advice.
Today's date is {date.today()}.
"""


def build_mcq_prompt(test_name, phase_name, subject, count=10):
  pattern_info = get_test_pattern_info(test_name)
  return f"""
Generate {count} unique high-yield multiple choice questions (MCQs) for Pakistani entrance test preparation matching the official exam format.

Target Exam: {test_name} ({pattern_info})
Study Phase: {phase_name}
Subject/Topic: {subject}

Return ONLY valid JSON with this exact structure:
{{
  "questions": [
    {{
      "question": "Question text here?",
      "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
      "answer": "A) Option 1",
      "explanation": "Brief explanation of why this answer is correct."
    }}
  ]
}}
"""


# ============================================================
# PDF GENERATOR (REPORTLAB)
# ============================================================


def generate_pdf_from_text(test_name, exam_date, roadmap_text):
  buffer = io.BytesIO()
  doc = SimpleDocTemplate(
      buffer,
      pagesize=letter,
      rightMargin=36,
      leftMargin=36,
      topMargin=36,
      bottomMargin=36,
  )
  styles = getSampleStyleSheet()

  title_style = ParagraphStyle(
      "DocTitle",
      parent=styles["Heading1"],
      fontSize=18,
      leading=22,
      textColor=colors.HexColor("#1E3A8A"),
      spaceAfter=6,
  )
  subtitle_style = ParagraphStyle(
      "DocSubTitle",
      parent=styles["Normal"],
      fontSize=10,
      leading=14,
      textColor=colors.HexColor("#4B5563"),
      spaceAfter=12,
  )
  h1_style = ParagraphStyle(
      "H1",
      parent=styles["Heading2"],
      fontSize=13,
      leading=17,
      textColor=colors.HexColor("#1E40AF"),
      spaceBefore=12,
      spaceAfter=6,
  )
  h2_style = ParagraphStyle(
      "H2",
      parent=styles["Heading3"],
      fontSize=11,
      leading=15,
      textColor=colors.HexColor("#1F2937"),
      spaceBefore=10,
      spaceAfter=4,
  )
  body_style = ParagraphStyle(
      "Body",
      parent=styles["BodyText"],
      fontSize=9,
      leading=13,
      textColor=colors.HexColor("#374151"),
      spaceAfter=4,
  )
  bullet_style = ParagraphStyle(
      "Bullet",
      parent=body_style,
      leftIndent=15,
      firstLineIndent=-10,
      spaceAfter=3,
  )

  story = [
      Paragraph("AI Entrance Test Preparation Roadmap", title_style),
      Paragraph(
          f"<b>Target Test:</b> {test_name} &nbsp;|&nbsp; <b>Exam Date:</b>"
          f" {exam_date}",
          subtitle_style,
      ),
      HRFlowable(
          width="100%",
          thickness=1,
          color=colors.HexColor("#CBD5E1"),
          spaceAfter=10,
      ),
  ]

  for line in roadmap_text.split("\n"):
    clean = line.strip()
    if not clean:
      story.append(Spacer(1, 4))
      continue

    clean_text = (
        clean.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )

    if clean_text.startswith("# "):
      story.append(Paragraph(clean_text[2:], title_style))
    elif clean_text.startswith("## "):
      story.append(Paragraph(clean_text[3:], h1_style))
    elif clean_text.startswith("### "):
      story.append(Paragraph(clean_text[4:], h2_style))
    elif clean_text.startswith("- ") or clean_text.startswith("* "):
      story.append(Paragraph(f"• {clean_text[2:]}", bullet_style))
    else:
      story.append(Paragraph(clean_text, body_style))

  doc.build(story)
  buffer.seek(0)
  return buffer.getvalue()


# ============================================================
# SIDEBAR CONFIGURATION
# ============================================================

with st.sidebar:
  st.header("⚙️ Preparation Settings")

  target_test = st.selectbox(
      "Target Test",
      [
          "MDCAT",
          "ECAT / Engineering Tests",
          "ISSB Initial Computer Test",
          "Army Medical College (AMC) Test",
          "NUST NET",
          "FAST",
          "NTS NAT",
          "Custom / Other Entrance Test",
      ],
  )

  custom_test = ""
  if target_test == "Custom / Other Entrance Test":
    custom_test = st.text_input(
        "Enter Test Name", placeholder="e.g., GIKI, PIEAS, UET Taxila"
    )

  target_date = st.date_input("Target Exam Date", min_value=date.today())

  preparation_level = st.selectbox(
      "Current Preparation Level", ["Beginner", "Intermediate", "Advanced"]
  )

  study_hours = st.slider(
      "Daily Available Study Hours", min_value=1, max_value=16, value=6
  )

  st.divider()
  st.header("🔑 Gemini API Settings")

  auto_key = get_gemini_api_key()
  if auto_key:
    st.success("✅ API Key automatically loaded.")
    api_key_input = auto_key
  else:
    api_key_input = st.text_input(
        "Gemini API Key",
        type="password",
        placeholder="Enter your Gemini API key",
    )
    if api_key_input:
      st.session_state["api_key"] = api_key_input.strip()

  generate_button = st.button(
      "🚀 Generate Roadmap", type="primary", use_container_width=True
  )

# ============================================================
# METRICS & CALCULATIONS
# ============================================================

today = date.today()
remaining_days = (target_date - today).days

selected_test = (
    custom_test.strip()
    if target_test == "Custom / Other Entrance Test"
    else target_test
)

col1, col2, col3 = st.columns(3)
with col1:
  st.metric("Days Remaining", max(remaining_days, 0))
with col2:
  st.metric("Study Hours / Day", study_hours)
with col3:
  st.metric("Preparation Level", preparation_level)

# ============================================================
# ROADMAP GENERATION LOGIC
# ============================================================

if generate_button:
  current_key = get_gemini_api_key()

  if not current_key:
    st.error("❌ No Gemini API key found.")
    st.stop()

  if target_date <= today:
    st.error("❌ Please select a future exam date.")
    st.stop()

  if target_test == "Custom / Other Entrance Test" and not custom_test.strip():
    st.error("❌ Please enter your custom test name.")
    st.stop()

  try:
    with st.spinner("🤖 Generating your roadmap using Gemini 3.5 Flash..."):
      client = genai.Client(api_key=current_key)
      response = client.models.generate_content(
          model="gemini-3.5-flash",
          contents=build_roadmap_prompt(
              selected_test,
              target_date.strftime("%d %B %Y"),
              remaining_days,
              preparation_level,
              study_hours,
          ),
      )
      roadmap = response.text

    if not roadmap:
      st.error("❌ Gemini returned an empty response.")
      st.stop()

    st.session_state["roadmap"] = roadmap
    st.session_state["test"] = selected_test
    st.session_state["exam_date"] = target_date.strftime("%d %B %Y")
    st.session_state["phase_mcqs"] = []  # Clear previous quiz pool

  except Exception as error:
    st.error(f"❌ Unable to generate the roadmap: {error}")

# ============================================================
# MAIN CONTENT TABS
# ============================================================

if "roadmap" in st.session_state:
  st.success(
      f"Roadmap ready for {st.session_state['test']} — Exam Date:"
      f" {st.session_state['exam_date']}"
  )

  tab1, tab2 = st.tabs(["🗺️ Preparation Roadmap", "📝 Practice Quiz Suite"])

  with tab1:
    st.markdown(st.session_state["roadmap"])
    st.divider()
    st.subheader("📥 Download Roadmap")

    try:
      pdf_bytes = generate_pdf_from_text(
          st.session_state["test"],
          st.session_state["exam_date"],
          st.session_state["roadmap"],
      )
      st.download_button(
          "📄 Download Complete PDF Roadmap",
          pdf_bytes,
          file_name=f"{st.session_state['test'].replace(' ', '_')}_Roadmap.pdf",
          mime="application/pdf",
          type="primary",
          use_container_width=True,
      )
    except Exception as pdf_err:
      st.error(f"Failed to compile PDF: {pdf_err}")

  with tab2:
    st.subheader("🎯 Scalable Practice Engine")
    st.write(
        "Build a multi-question test bank by generating MCQs in structured"
        " batches."
    )

    col1, col2, col3 = st.columns(3)
    with col1:
      selected_phase = st.selectbox(
          "Preparation Phase",
          [
              "Phase 1: Syllabus Coverage & Concepts",
              "Phase 2: Revision & Weak Areas",
              "Phase 3: Mock Exams & Speed",
          ],
      )
    with col2:
      quiz_subject = st.text_input(
          "Subject / Topic", placeholder="e.g. Physics - Vectors"
      )
    with col3:
      mcq_batch_size = st.select_slider(
          "MCQs to Add per Batch", options=[5, 10, 15, 20, 25]
      )

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
      gen_batch = st.button(
          "➕ Generate MCQ Batch", type="primary", use_container_width=True
      )
    with btn_col2:
      clear_pool = st.button(
          "🗑️ Reset Quiz Pool", type="secondary", use_container_width=True
      )

    if clear_pool:
      st.session_state["phase_mcqs"] = []
      st.rerun()

    if gen_batch:
      if not quiz_subject.strip():
        st.error("Please specify a subject or topic.")
      else:
        current_key = get_gemini_api_key()
        try:
          with st.spinner(
              f"Generating {mcq_batch_size} MCQs using Gemini 3.5 Flash..."
          ):
            client = genai.Client(api_key=current_key)
            mcq_res = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=build_mcq_prompt(
                    st.session_state["test"],
                    selected_phase,
                    quiz_subject,
                    mcq_batch_size,
                ),
            )

            clean_json = mcq_res.text.strip()
            if clean_json.startswith("```"):
              clean_json = clean_json.split("\n", 1)[1].rsplit("\n", 1)[0]

            new_questions = json.loads(clean_json).get("questions", [])

            if "phase_mcqs" not in st.session_state:
              st.session_state["phase_mcqs"] = []

            # Append new questions into session pool
            st.session_state["phase_mcqs"].extend(new_questions)
            st.success(
                f"Added {len(new_questions)} MCQs to pool! Total pool size:"
                f" {len(st.session_state['phase_mcqs'])} MCQs."
            )

        except Exception as e:
          st.error(f"Failed to generate quiz: {e}")

    # Render accumulated quiz bank
    if "phase_mcqs" in st.session_state and st.session_state["phase_mcqs"]:
      questions = st.session_state["phase_mcqs"]
      st.divider()
      st.markdown(f"### 📋 Active Quiz Bank ({len(questions)} Questions)")

      with st.form("interactive_quiz_form"):
        user_answers = {}
        for idx, q in enumerate(questions):
          st.markdown(f"**Q{idx+1}: {q['question']}**")
          user_answers[idx] = st.radio(
              "Options:",
              q["options"],
              key=f"q_pool_{idx}",
              index=None,
              label_visibility="collapsed",
          )
          st.write("")

        submitted = st.form_submit_button("Submit & Evaluate Test")

      if submitted:
        score = 0
        st.divider()
        st.subheader("📊 Quiz Results & Diagnostics")

        for idx, q in enumerate(questions):
          selected = user_answers.get(idx)
          correct = q["answer"]

          if selected == correct:
            score += 1
            st.success(f"**Q{idx+1}**: Correct! ({correct})")
          else:
            st.error(
                f"**Q{idx+1}**: Incorrect. You selected '{selected or 'No Answer'}'. "
                f"Correct Answer: **{correct}**"
            )

          st.caption(f"💡 Explanation: {q['explanation']}")
          st.write("---")

        percentage = round((score / len(questions)) * 100, 1)
        st.info(
            f"**Final Score:** {score} / {len(questions)} ({percentage}%)"
        )
else:
  st.info(
      "👈 Configure your settings in the sidebar and click **Generate"
      " Roadmap**."
  )
