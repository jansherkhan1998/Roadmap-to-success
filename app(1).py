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

st.title("📚 Entrance Test Preparation Road")
st.write(
    "Generate a personalized preparation roadmap, continuous practice"
    " suites, and track your overall readiness for Pakistani entrance tests."
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
#######################################################
#Propmt generator
######################################################3
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
############################################################################
#MCQs Making Code
############################################################################
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

from datetime import date
import io
import re
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def sanitize_text(text):
  """Aggressively strips code fence artifacts, fixes broken markdown,

  and translates LaTeX math into ReportLab XML format.
  """
  if not text:
    return ""

  # 1. Strip raw code fence indicators and unicode glyph box characters
  text = re.sub(r"[■▼▲─│┌┐└┘├┤┼═#`]+", "", text)

  # 2. Fix dangling or unbalanced Markdown asterisks/underscores
  text = text.replace("*", "")

  # 3. Translate LaTeX math expressions and Greek variables to HTML
  text = re.sub(
      r"\$([A-Za-z0-9_\-\+\=\s\(\)\/\.,]+)\$", r"<i>\1</i>", text
  )  # Strip $...$
  text = (
      text.replace("_c", "<sub>c</sub>")
      .replace("_p", "<sub>p</sub>")
      .replace("_0", "<sub>0</sub>")
  )
  text = (
      text.replace(r"\epsilon", "ε")
      .replace("ε■", "ε₀")
      .replace(r"\approx", "≈")
      .replace(r"\rightarrow", "→")
  )

  # 4. XML Escape reserved characters for ReportLab
  text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

  # 5. Restore clean formatting tags
  text = re.sub(r"&lt;i&gt;(.*?)&lt;/i&gt;", r"<i>\1</i>", text)
  text = re.sub(r"&lt;b&gt;(.*?)&lt;/b&gt;", r"<b>\1</b>", text)
  text = re.sub(r"&lt;sub&gt;(.*?)&lt;/sub&gt;", r"<sub>\1</sub>", text)

  return text.strip()


def parse_markdown_table(table_lines, body_style):
  """Parses raw pipe-table lines into a styled ReportLab Table."""
  table_data = []
  for line in table_lines:
    clean_line = line.strip()
    if not clean_line or "---" in clean_line or "===" in clean_line:
      continue  # Ignore structural header separators

    cols = [col.strip() for col in clean_line.strip("|").split("|")]
    if any(cols):
      formatted_row = [
          Paragraph(sanitize_text(col), body_style) for col in cols
      ]
      table_data.append(formatted_row)

  if not table_data:
    return None

  # Uniform column width calculation
  max_cols = max(len(row) for row in table_data)
  for row in table_data:
    while len(row) < max_cols:
      row.append(Paragraph("", body_style))

  col_width = 540.0 / max_cols  # Fits standard Letter printable canvas (612 - 72)

  t = Table(table_data, colWidths=[col_width] * max_cols)
  t.setStyle(
      TableStyle([
          ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
          ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
          ("ALIGN", (0, 0), (-1, -1), "LEFT"),
          ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
          ("TOPPADDING", (0, 0), (-1, -1), 5),
          ("LEFTPADDING", (0, 0), (-1, -1), 5),
          ("RIGHTPADDING", (0, 0), (-1, -1), 5),
          (
              "ROWBACKGROUNDS",
              (0, 1),
              (-1, -1),
              [colors.white, colors.HexColor("#F8FAFC")],
          ),
          ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
      ])
  )
  return t


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
      spaceAfter=4,
  )
  subtitle_style = ParagraphStyle(
      "DocSubTitle",
      parent=styles["Normal"],
      fontSize=10,
      leading=14,
      textColor=colors.HexColor("#4B5563"),
      spaceAfter=10,
  )
  h1_style = ParagraphStyle(
      "H1",
      parent=styles["Heading2"],
      fontSize=12,
      leading=16,
      textColor=colors.HexColor("#1E40AF"),
      spaceBefore=10,
      spaceAfter=4,
      keepWithNext=True,
  )
  h2_style = ParagraphStyle(
      "H2",
      parent=styles["Heading3"],
      fontSize=10,
      leading=14,
      textColor=colors.HexColor("#1F2937"),
      spaceBefore=8,
      spaceAfter=3,
      keepWithNext=True,
  )
  body_style = ParagraphStyle(
      "Body",
      parent=styles["BodyText"],
      fontSize=8.5,
      leading=12,
      textColor=colors.HexColor("#374151"),
      spaceAfter=3,
  )
  table_body_style = ParagraphStyle(
      "TableBody", parent=body_style, fontSize=8, leading=11
  )
  bullet_style = ParagraphStyle(
      "Bullet",
      parent=body_style,
      leftIndent=12,
      firstLineIndent=-8,
      spaceAfter=2,
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
          thickness=1.5,
          color=colors.HexColor("#1E3A8A"),
          spaceAfter=10,
      ),
  ]

  lines = roadmap_text.split("\n")
  table_buffer = []

  for line in lines:
    raw_line = line.strip()

    # Collect Markdown table rows
    if "|" in raw_line and not raw_line.startswith("#"):
      table_buffer.append(raw_line)
      continue

    # Process and append accumulated table buffer
    if table_buffer:
      compiled_table = parse_markdown_table(table_buffer, table_body_style)
      if compiled_table:
        story.append(Spacer(1, 3))
        story.append(compiled_table)
        story.append(Spacer(1, 5))
      table_buffer = []

    # Detect bullet items
    is_bullet = raw_line.startswith(("•", "-", "*", "1.", "2.", "3.", "4."))

    clean_line = sanitize_text(raw_line)
    if not clean_line:
      continue

    # Format document elements
    if raw_line.startswith("# "):
      story.append(Paragraph(clean_line, title_style))
    elif raw_line.startswith("## "):
      story.append(Paragraph(clean_line, h1_style))
    elif raw_line.startswith("### ") or raw_line.startswith("#### "):
      story.append(Paragraph(clean_line, h2_style))
    elif is_bullet:
      # Strip bullet prefix before adding uniform dot marker
      clean_bullet_text = re.sub(r"^[\•\*\-\d\.\s]+", "", clean_line)
      story.append(Paragraph(f"• {clean_bullet_text}", bullet_style))
    else:
      story.append(Paragraph(clean_line, body_style))

  # Process trailing table buffer
  if table_buffer:
    compiled_table = parse_markdown_table(table_buffer, table_body_style)
    if compiled_table:
      story.append(compiled_table)

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
    st.session_state["quiz_history"] = []  # Reset analytics history

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

  tab1, tab2, tab3 = st.tabs([
      "🗺️ Preparation Roadmap",
      "📝 Practice Quiz Suite",
      "📈 Progress & Analytics",
  ])

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

            # Attach metadata to questions
            for q in new_questions:
              q["phase"] = selected_phase
              q["subject"] = quiz_subject

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

        # Save result attempt to global session state analytics
        if "quiz_history" not in st.session_state:
          st.session_state["quiz_history"] = []

        st.session_state["quiz_history"].append({
            "subject": (
                questions[0].get("subject", "General") if questions else "General"
            ),
            "phase": (
                questions[0].get("phase", "Phase 1") if questions else "Phase 1"
            ),
            "total": len(questions),
            "correct": score,
            "percentage": percentage,
        })

  # ============================================================
  # TAB 3: PROGRESS & ANALYTICS DASHBOARD
  # ============================================================
  with tab3:
    st.subheader("📊 Preparation Progress & Readiness Analytics")

    history = st.session_state.get("quiz_history", [])

    if not history:
      st.info(
          "💡 No quiz data collected yet! Take a few practice tests in Tab 2 to"
          " populate your progress analytics."
      )
    else:
      total_attempted = sum(h["total"] for h in history)
      total_correct = sum(h["correct"] for h in history)
      overall_accuracy = (
          round((total_correct / total_attempted) * 100, 1)
          if total_attempted > 0
          else 0.0
      )

      # Key Metric Cards
      m1, m2, m3, m4 = st.columns(4)
      with m1:
        st.metric("Total Quizzes Attempted", len(history))
      with m2:
        st.metric("Total MCQs Solved", total_attempted)
      with m3:
        st.metric("Overall Accuracy", f"{overall_accuracy}%")
      with m4:
        readiness = (
            "🚀 High"
            if overall_accuracy >= 75
            else "🟡 Moderate" if overall_accuracy >= 50 else "🔴 Requires Focus"
        )
        st.metric("Exam Readiness", readiness)

      st.divider()

      # Visual Progress Bar
      st.markdown("### 🎯 Exam Readiness Bar")
      st.progress(
          min(overall_accuracy / 100.0, 1.0),
          text=f"Mastery Level: {overall_accuracy}%",
      )

      st.divider()

      # Detailed Attempt Breakdown Table
      st.markdown("### 📋 Quiz Attempt History")
      history_data = []
      for idx, item in enumerate(reversed(history)):
        history_data.append({
            "Attempt #": len(history) - idx,
            "Subject / Topic": item["subject"],
            "Phase": item["phase"],
            "Score": f"{item['correct']} / {item['total']}",
            "Accuracy": f"{item['percentage']}%",
        })

      st.table(history_data)

else:
  st.info(
      "👈 Configure your settings in the sidebar and click **Generate"
      " Roadmap**."
  )
