from datetime import date
import io
import json
import os
import re

from groq import Groq
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
import streamlit as st

# Default Groq model (Llama 3.3 70B Versatile is recommended for fast, high-quality reasoning)
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"

# ============================================================
# SECTION 1: STREAMLIT PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Entrance Test Preparation Roadmap",
    page_icon="📚",
    layout="wide",
)

st.title("📚 Entrance Test Preparation Roadmap & Practice Engine")
st.write(
    "Generate a personalized preparation roadmap and practice extensive"
    " topic-wise MCQs aligned with official Pakistani entrance tests."
)

# ============================================================
# SECTION 2: HELPER FUNCTIONS & EXAM PATTERNS
# ============================================================


def get_groq_api_key():
    """Retrieve API key strictly from Streamlit secrets or environment variables."""
    try:
        if "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass

    return os.getenv("GROQ_API_KEY", "")


def get_test_pattern_info(test_name):
    """Returns strict pattern metadata for official Pakistani entrance tests."""
    patterns = {
        "KMU CAT": (
            "100 MCQs total (90 Minutes, No Negative Marking). Breakdown:"
            " Biology 35 MCQs (35%), Chemistry 30 MCQs (30%), Physics 20 MCQs"
            " (20%), English 10 MCQs (10%), Logical Reasoning 5 MCQs (5%)."
        ),
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


# ============================================================
# SECTION 3: GROQ PROMPT GENERATORS
# ============================================================


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
   - Phase 1: Conceptual Foundation
   - Phase 2: Targeted Revision & Gaps
   - Phase 3: High-Fidelity Mock Exams
   - Phase 4: Final Taper & Exam Day Prep
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


def build_mcq_prompt(test_name, subject, count=10):
    pattern_info = get_test_pattern_info(test_name)
    return f"""
Generate {count} unique, high-yield, exam-standard multiple choice questions (MCQs) for Pakistani entrance test preparation matching the exact official syllabus and pattern.

Target Exam: {test_name} ({pattern_info})
Subject / Topic: {subject}

Requirements:
1. Ensure conceptual depth and variety (conceptual, numerical, definition-based).
2. Exactly 4 clear options per MCQ (A, B, C, D).
3. Clear explanations for the correct options.

Return ONLY valid JSON wrapped in no extra text or markdown formatting:
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
# SECTION 4: PDF GENERATOR (REPORTLAB)
# ============================================================


def sanitize_text(text):
    if not text:
        return ""
    text = re.sub(r"[■▼▲─│┌┐└┘├┤┼═#`]+", "", text)
    text = text.replace("*", "")
    text = re.sub(r"\$([A-Za-z0-9_\-\+\=\s\(\)\/\.,]+)\$", r"<i>\1</i>", text)
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
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"&lt;i&gt;(.*?)&lt;/i&gt;", r"<i>\1</i>", text)
    text = re.sub(r"&lt;b&gt;(.*?)&lt;/b&gt;", r"<b>\1</b>", text)
    text = re.sub(r"&lt;sub&gt;(.*?)&lt;/sub&gt;", r"<sub>\1</sub>", text)
    return text.strip()


def parse_markdown_table(table_lines, body_style):
    table_data = []
    for line in table_lines:
        clean_line = line.strip()
        if not clean_line or "---" in clean_line or "===" in clean_line:
            continue
        cols = [col.strip() for col in clean_line.strip("|").split("|")]
        if any(cols):
            formatted_row = [
                Paragraph(sanitize_text(col), body_style) for col in cols
            ]
            table_data.append(formatted_row)

    if not table_data:
        return None

    max_cols = max(len(row) for row in table_data)
    for row in table_data:
        while len(row) < max_cols:
            row.append(Paragraph("", body_style))

    col_width = 540.0 / max_cols

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

        if "|" in raw_line and not raw_line.startswith("#"):
            table_buffer.append(raw_line)
            continue

        if table_buffer:
            compiled_table = parse_markdown_table(table_buffer, table_body_style)
            if compiled_table:
                story.append(Spacer(1, 3))
                story.append(compiled_table)
                story.append(Spacer(1, 5))
            table_buffer = []

        is_bullet = raw_line.startswith(("•", "-", "*", "1.", "2.", "3.", "4."))
        clean_line = sanitize_text(raw_line)
        if not clean_line:
            continue

        if raw_line.startswith("# "):
            story.append(Paragraph(clean_line, title_style))
        elif raw_line.startswith("## "):
            story.append(Paragraph(clean_line, h1_style))
        elif raw_line.startswith("### ") or raw_line.startswith("#### "):
            story.append(Paragraph(clean_line, h2_style))
        elif is_bullet:
            clean_bullet_text = re.sub(r"^[\•\*\-\d\.\s]+", "", clean_line)
            story.append(Paragraph(f"• {clean_bullet_text}", bullet_style))
        else:
            story.append(Paragraph(clean_line, body_style))

    if table_buffer:
        compiled_table = parse_markdown_table(table_buffer, table_body_style)
        if compiled_table:
            story.append(compiled_table)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# ============================================================
# SECTION 5: SIDEBAR CONFIGURATION
# ============================================================

with st.sidebar:
    st.header("⚙️ Preparation Settings")

    target_test = st.selectbox(
        "Target Test",
        [
            "KMU CAT",
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

    # Automatically handle secret API key loading for Groq
    auto_key = get_groq_api_key()
    if auto_key:
        st.success("⚡ Groq API Key connected from secrets.")
    else:
        st.error(
            "⚠️ No API key found in `.streamlit/secrets.toml` under"
            " `GROQ_API_KEY`."
        )

    generate_button = st.button(
        "🚀 Generate Roadmap", type="primary", use_container_width=True
    )

# ============================================================
# SECTION 6: METRICS & CALCULATIONS
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
# SECTION 7: ROADMAP GENERATION LOGIC (GROQ API CALL)
# ============================================================

if generate_button:
    current_key = get_groq_api_key()

    if not current_key:
        st.error("❌ No Groq API key configured in secrets.")
        st.stop()

    if target_date <= today:
        st.error("❌ Please select a future exam date.")
        st.stop()

    if target_test == "Custom / Other Entrance Test" and not custom_test.strip():
        st.error("❌ Please enter your custom test name.")
        st.stop()

    try:
        with st.spinner("⚡ Generating your roadmap using Groq..."):
            client = Groq(api_key=current_key)
            completion = client.chat.completions.create(
                model=DEFAULT_GROQ_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": build_roadmap_prompt(
                            selected_test,
                            target_date.strftime("%d %B %Y"),
                            remaining_days,
                            preparation_level,
                            study_hours,
                        ),
                    }
                ],
                temperature=0.6,
            )
            roadmap = completion.choices[0].message.content

        if not roadmap:
            st.error("❌ Groq returned an empty response.")
            st.stop()

        st.session_state["roadmap"] = roadmap
        st.session_state["test"] = selected_test
        st.session_state["exam_date"] = target_date.strftime("%d %B %Y")
        st.session_state["topic_mcqs"] = []

    except Exception as error:
        st.error(f"❌ Unable to generate the roadmap via Groq: {error}")

# ============================================================
# SECTION 8: MAIN CONTENT TABS (2 TABS ONLY)
# ============================================================

if "roadmap" in st.session_state:
    st.success(
        f"Roadmap ready for {st.session_state['test']} — Exam Date:"
        f" {st.session_state['exam_date']}"
    )

    tab1, tab2 = st.tabs([
        "🗺️ Preparation Roadmap",
        "📝 Comprehensive Topic MCQs",
    ])

    # ------------------------------------------------------------
    # TAB 1: ROADMAP VIEW & DOWNLOAD
    # ------------------------------------------------------------
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

    # ------------------------------------------------------------
    # TAB 2: COMPREHENSIVE TOPIC MCQS (GROQ API CALL)
    # ------------------------------------------------------------
    with tab2:
        st.subheader("🎯 Extensive Topic-Wise MCQ Practice")
        st.caption(
            "Generate lots of targeted practice MCQs for any subject or topic"
            " mentioned in your roadmap."
        )

        col1, col2 = st.columns([2, 1])
        with col1:
            quiz_subject = st.text_input(
                "Subject / Specific Topic",
                placeholder="e.g. Biology - Cell Structure, Chemistry - Stoichiometry, Physics - Vectors",
            )
        with col2:
            mcq_batch_size = st.select_slider(
                "MCQs to Generate", options=[5, 10, 15, 20, 25]
            )

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            gen_batch = st.button(
                "➕ Generate MCQ Practice Set",
                type="primary",
                use_container_width=True,
            )
        with btn_col2:
            clear_pool = st.button(
                "🗑️ Clear Practice Set",
                type="secondary",
                use_container_width=True,
            )

        if clear_pool:
            st.session_state["topic_mcqs"] = []
            st.rerun()

        if gen_batch:
            if not quiz_subject.strip():
                st.error("Please specify a subject or topic to practice.")
            else:
                current_key = get_groq_api_key()
                try:
                    with st.spinner(
                        f"Generating {mcq_batch_size} practice MCQs for"
                        f" {quiz_subject} using Groq..."
                    ):
                        client = Groq(api_key=current_key)
                        mcq_res = client.chat.completions.create(
                            model=DEFAULT_GROQ_MODEL,
                            response_format={"type": "json_object"},
                            messages=[
                                {
                                    "role": "user",
                                    "content": build_mcq_prompt(
                                        st.session_state["test"],
                                        quiz_subject,
                                        mcq_batch_size,
                                    ),
                                }
                            ],
                            temperature=0.4,
                        )

                        clean_json = mcq_res.choices[0].message.content.strip()
                        if clean_json.startswith("```"):
                            clean_json = clean_json.split("\n", 1)[1].rsplit(
                                "\n", 1
                            )[0]

                        new_questions = json.loads(clean_json).get(
                            "questions", []
                        )

                        if "topic_mcqs" not in st.session_state:
                            st.session_state["topic_mcqs"] = []

                        for q in new_questions:
                            q["subject"] = quiz_subject

                        st.session_state["topic_mcqs"].extend(new_questions)
                        st.success(
                            f"Added {len(new_questions)} MCQs for"
                            f" '{quiz_subject}'! Total available practice"
                            f" questions: {len(st.session_state['topic_mcqs'])}."
                        )

                except Exception as e:
                    st.error(f"Failed to generate practice MCQs: {e}")

        # Render active MCQ bank
        if "topic_mcqs" in st.session_state and st.session_state["topic_mcqs"]:
            questions = st.session_state["topic_mcqs"]
            st.divider()
            st.markdown(
                f"### 📋 Active MCQ Practice Bank ({len(questions)} Questions)"
            )

            with st.form("interactive_quiz_form"):
                user_answers = {}
                for idx, q in enumerate(questions):
                    st.markdown(
                        f"**Q{idx+1} [{q.get('subject', 'General')}]:"
                        f" {q['question']}**"
                    )
                    user_answers[idx] = st.radio(
                        "Options:",
                        q["options"],
                        key=f"q_pool_{idx}",
                        index=None,
                        label_visibility="collapsed",
                    )
                    st.write("")

                submitted = st.form_submit_button("Submit & Evaluate Answers")

            if submitted:
                score = 0
                st.divider()
                st.subheader("📊 Practice Results & Detailed Explanations")

                for idx, q in enumerate(questions):
                    selected = user_answers.get(idx)
                    correct = q["answer"]

                    if selected == correct:
                        score += 1
                        st.success(f"**Q{idx+1}**: Correct! ({correct})")
                    else:
                        st.error(
                            f"**Q{idx+1}**: Incorrect. You selected"
                            f" '{selected or 'No Answer'}'. Correct Answer:"
                            f" **{correct}**"
                        )

                    st.caption(f"💡 Explanation: {q['explanation']}")
                    st.write("---")

                percentage = round((score / len(questions)) * 100, 1)
                st.info(
                    f"**Final Score:** {score} / {len(questions)} ({percentage}%)"
                )
