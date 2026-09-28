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

# Default Groq model
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
    "Generate a personalized preparation roadmap, attempt structured mock"
    " tests (up to 60 MCQs), practice topic-wise MCQs, and track your progress."
)

# ============================================================
# SECTION 2: HELPER FUNCTIONS & CLEAN PARSING
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
    """Returns strict pattern metadata for official entrance tests."""
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


def clean_extracted_topic(text):
    """Removes leftover markdown syntax like **, headers, and metadata tags for clean selectbox labels."""
    cleaned = re.sub(r"\*\*|\*|#", "", text)
    cleaned = re.sub(r"Target date:.*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"Days left:.*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"Current level:.*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"Study time per day:.*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def extract_clean_topics(roadmap_text):
    """Extracts high-yield topics clearly from the generated roadmap without unwanted markdown artifacts."""
    topics = []
    lines = roadmap_text.split("\n")
    for line in lines:
        line_clean = line.strip()

        if any(
            k in line_clean.lower()
            for k in ["target date", "days left", "current level", "study time"]
        ):
            continue

        if line_clean.startswith(("-", "*", "•")) or re.match(
            r"^\d+\.", line_clean
        ):
            item = clean_extracted_topic(line_clean)
            item = re.sub(r"^[\•\*\-\d\.\s]+", "", item).strip()
            if "–" in item:
                item = item.split("–")[0].strip()
            elif "-" in item and len(item.split("-")[0].strip()) > 3:
                item = item.split("-")[0].strip()

            if 3 < len(item) < 60 and not item.lower().startswith("phase"):
                topics.append(item)

    default_topics = [
        "Biology - Core Concepts",
        "Chemistry - Reaction Mechanics",
        "Physics - Principles & Equations",
        "English - Vocabulary & Grammar",
        "Logical & Analytical Reasoning",
    ]
    unique_topics = list(dict.fromkeys(topics))
    return unique_topics if unique_topics else default_topics


# ============================================================
# SECTION 3: PROMPT GENERATORS & BATCH GENERATION
# ============================================================


def build_roadmap_prompt(
    test_name, exam_date, days_remaining, level, hours_per_day
):
    pattern_info = get_test_pattern_info(test_name)
    return f"""
You are an expert entrance-test preparation strategist and curriculum specialist.

Create a practical personalized preparation roadmap for:

Target Test: {test_name}
Official Pattern Details: {pattern_info}
Target Exam Date: {exam_date}
Days Remaining: {days_remaining}
Current Preparation Level: {level}
Daily Available Study Hours: {hours_per_day}

CRITICAL REQUIREMENT:
Adhere strictly to the official paper pattern provided above.

Include:
1. Executive summary
2. Official Exam structure & Section Weightages
3. Subject & High-Yield Topic breakdown
4. Phase-wise roadmap:
   - Phase 1: Foundation (Test 1 Target)
   - Phase 2: Intermediate Revision (Test 2 Target)
   - Phase 3: High-Fidelity Mock Practice (Test 3 Target)
   - Phase 4: Final Taper & Exam Day Prep (Test 4 Target)
5. Daily study schedule based on {hours_per_day} hours
6. Time-management & negative-marking strategies
7. Top priorities & common mistakes to avoid

Use clear Markdown with concise section headers. Today's date is {date.today()}.
"""


def build_roadmap_mock_prompt(test_name, test_number, count=10):
    pattern_info = get_test_pattern_info(test_name)
    return f"""
Generate {count} unique multiple choice questions (MCQs) for a full scheduled practice test: "Test {test_number}".

Target Exam: {test_name}
Official Exam Pattern: {pattern_info}

STRICT REQUIREMENTS:
1. Distribute questions proportionally across all official subjects/sections according to test weightage.
2. Provide exactly 4 options per question (A, B, C, D).
3. Include clear answer keys and explanations.

Return ONLY valid JSON matching this exact structure:
{{
  "test_title": "Test {test_number}",
  "questions": [
    {{
      "subject": "Subject Name",
      "question": "Question text here?",
      "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
      "answer": "A) Option 1",
      "explanation": "Explanation here."
    }}
  ]
}}
"""


def build_custom_mcq_prompt(test_name, topic, count=10):
    pattern_info = get_test_pattern_info(test_name)
    return f"""
Generate {count} high-yield MCQs for the specific topic: "{topic}".

Target Exam: {test_name}
Exam Context: {pattern_info}

Return ONLY valid JSON matching this exact structure:
{{
  "questions": [
    {{
      "subject": "{topic}",
      "question": "Question text here?",
      "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
      "answer": "A) Option 1",
      "explanation": "Brief explanation of correct answer."
    }}
  ]
}}
"""


def batch_generate_mcqs(
    client, prompt_builder, test_name, identifier, total_count, is_mock=True
):
    """Generates MCQs safely in chunks of up to 15 to allow up to 60 MCQs without hitting token limits."""
    all_questions = []
    chunk_size = 15
    chunks = [
        chunk_size if total_count - i >= chunk_size else total_count - i
        for i in range(0, total_count, chunk_size)
    ]

    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, num_q in enumerate(chunks):
        status_text.text(
            f"⚡ Generating question batch {idx + 1} of {len(chunks)} ({len(all_questions)}/{total_count} completed)..."
        )
        prompt = (
            prompt_builder(test_name, identifier, num_q)
            if is_mock
            else prompt_builder(test_name, identifier, num_q)
        )

        res = client.chat.completions.create(
            model=DEFAULT_GROQ_MODEL,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )

        data = json.loads(res.choices[0].message.content)
        questions = data.get("questions", [])
        all_questions.extend(questions)

        progress = (idx + 1) / len(chunks)
        progress_bar.progress(progress)

    status_text.empty()
    progress_bar.empty()
    return all_questions


# ============================================================
# SECTION 4: PDF EXPORT ENGINES
# ============================================================


def sanitize_text(text):
    if not text:
        return ""
    text = re.sub(r"[■▼▲─│┌┐└┘├┤┼═#`]+", "", text)
    text = text.replace("*", "")
    text = re.sub(r"\$([A-Za-z0-9_\-\+\=\s\(\)\/\.,]+)\$", r"<i>\1</i>", text)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return text.strip()


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
    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#374151"),
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
            thickness=1.5,
            color=colors.HexColor("#1E3A8A"),
            spaceAfter=10,
        ),
    ]

    for line in roadmap_text.split("\n"):
        clean_line = sanitize_text(line)
        if clean_line:
            story.append(Paragraph(clean_line, body_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_mcqs_pdf(title, test_name, mcq_list):
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
        fontSize=16,
        leading=20,
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
    q_style = ParagraphStyle(
        "QuestionText",
        parent=styles["Heading3"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#1E40AF"),
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )
    opt_style = ParagraphStyle(
        "OptionText",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#374151"),
        leftIndent=12,
        spaceAfter=2,
    )
    ans_style = ParagraphStyle(
        "AnswerText",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#065F46"),
        leftIndent=12,
        spaceBefore=2,
        spaceAfter=2,
    )

    story = [
        Paragraph(f"{test_name} — {title}", title_style),
        Paragraph(
            f"<b>Total Questions:</b> {len(mcq_list)} &nbsp;|&nbsp;"
            f" <b>Generated Date:</b> {date.today().strftime('%d %B %Y')}",
            subtitle_style,
        ),
        HRFlowable(
            width="100%",
            thickness=1.5,
            color=colors.HexColor("#1E3A8A"),
            spaceAfter=10,
        ),
    ]

    for idx, q in enumerate(mcq_list):
        story.append(
            Paragraph(
                f"<b>Q{idx+1} [{q.get('subject', 'General')}]:</b>"
                f" {sanitize_text(q['question'])}",
                q_style,
            )
        )
        for opt in q.get("options", []):
            story.append(Paragraph(f"• {sanitize_text(opt)}", opt_style))
        story.append(Spacer(1, 2))
        story.append(
            Paragraph(
                f"<b>Correct Answer:</b> {sanitize_text(q['answer'])}",
                ans_style,
            )
        )
        story.append(
            Paragraph(
                f"<b>Explanation:</b> {sanitize_text(q['explanation'])}",
                opt_style,
            )
        )
        story.append(Spacer(1, 6))

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
            "Custom Entrance Test",
        ],
    )

    custom_test = ""
    if target_test == "Custom Entrance Test":
        custom_test = st.text_input(
            "Enter Test Name", placeholder="e.g. GIKI, PIEAS"
        )

    target_date = st.date_input("Target Exam Date", min_value=date.today())
    preparation_level = st.selectbox(
        "Current Preparation Level", ["Beginner", "Intermediate", "Advanced"]
    )
    study_hours = st.slider(
        "Daily Available Study Hours", min_value=1, max_value=16, value=6
    )

    st.divider()

    auto_key = get_groq_api_key()
    if auto_key:
        st.success("⚡ Groq API Key connected from secrets.")
    else:
        st.error("⚠️ GROQ_API_KEY missing in secrets.")

    generate_button = st.button(
        "🚀 Generate Roadmap", type="primary", use_container_width=True
    )

# ============================================================
# SECTION 6: INITIAL STATE INITIALIZATION
# ============================================================

if "test_history" not in st.session_state:
    st.session_state["test_history"] = []

today = date.today()
remaining_days = (target_date - today).days
selected_test = (
    custom_test.strip()
    if target_test == "Custom Entrance Test"
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
# SECTION 7: ROADMAP GENERATION
# ============================================================

if generate_button:
    current_key = get_groq_api_key()
    if not current_key:
        st.error("❌ API Key missing.")
        st.stop()

    try:
        with st.spinner("⚡ Generating your personalized roadmap..."):
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

        st.session_state["roadmap"] = roadmap
        st.session_state["test"] = selected_test
        st.session_state["exam_date"] = target_date.strftime("%d %B %Y")
        st.session_state["extracted_topics"] = extract_clean_topics(roadmap)

    except Exception as error:
        st.error(f"❌ Failed to generate roadmap: {error}")

# ============================================================
# SECTION 8: MAIN NAVIGATION TABS
# ============================================================

if "roadmap" in st.session_state:
    tab1, tab2, tab3, tab4 = st.tabs([
        "🗺️ Preparation Roadmap",
        "🧪 Roadmap Mock Tests",
        "🎯 Custom / Topic MCQs",
        "📊 Progress & Analytics",
    ])

    # ------------------------------------------------------------
    # TAB 1: ROADMAP VIEW
    # ------------------------------------------------------------
    with tab1:
        st.markdown(st.session_state["roadmap"])
        st.divider()
        try:
            pdf_bytes = generate_pdf_from_text(
                st.session_state["test"],
                st.session_state["exam_date"],
                st.session_state["roadmap"],
            )
            st.download_button(
                "📄 Download Complete Roadmap PDF",
                pdf_bytes,
                file_name=f"{st.session_state['test'].replace(' ', '_')}_Roadmap.pdf",
                mime="application/pdf",
                type="primary",
            )
        except Exception as pdf_err:
            st.error(f"Error compiling PDF: {pdf_err}")

    # ------------------------------------------------------------
    # TAB 2: SCHEDULED ROADMAP MOCK TESTS (UP TO 60 MCQs)
    # ------------------------------------------------------------
    with tab2:
        st.subheader("🧪 Scheduled Roadmap Mock Tests")
        st.caption(
            "Attempt structured mock tests corresponding to your roadmap"
            " milestone phases (Up to 60 questions per test)."
        )

        col_t1, col_t2 = st.columns([2, 2])
        with col_t1:
            test_num = st.selectbox(
                "Select Scheduled Test Stage",
                options=[1, 2, 3, 4, 5],
                format_func=lambda x: f"Test {x} (Phase {x} Evaluation)",
            )
        with col_t2:
            mock_size = st.select_slider(
                "Number of MCQs to Generate",
                options=[5, 10, 15, 20, 30, 45, 60],
                value=20,
                key="mock_sz_slider",
            )

        if st.button(
            f"⚡ Generate Test {test_num} ({mock_size} MCQs)",
            type="primary",
            use_container_width=True,
        ):
            current_key = get_groq_api_key()
            try:
                client = Groq(api_key=current_key)
                questions = batch_generate_mcqs(
                    client,
                    build_roadmap_mock_prompt,
                    st.session_state["test"],
                    test_num,
                    mock_size,
                    is_mock=True,
                )
                st.session_state["current_mock"] = {
                    "name": f"Test {test_num}",
                    "questions": questions,
                }
            except Exception as e:
                st.error(f"Error generating test: {e}")

        if "current_mock" in st.session_state:
            mock = st.session_state["current_mock"]
            st.divider()

            col_h1, col_h2 = st.columns([3, 1])
            with col_h1:
                st.markdown(
                    f"### 📝 {mock['name']} in Progress ({len(mock['questions'])} Questions)"
                )
            with col_h2:
                try:
                    mock_pdf_bytes = generate_mcqs_pdf(
                        mock["name"],
                        st.session_state["test"],
                        mock["questions"],
                    )
                    st.download_button(
                        "📄 Download Test PDF",
                        mock_pdf_bytes,
                        file_name=f"{st.session_state['test'].replace(' ', '_')}_{mock['name'].replace(' ', '_')}.pdf",
                        mime="application/pdf",
                    )
                except Exception as pdf_err:
                    st.error(f"Error generating PDF: {pdf_err}")

            with st.form("mock_quiz_form"):
                answers = {}
                for idx, q in enumerate(mock["questions"]):
                    st.markdown(
                        f"**Q{idx+1} [{q.get('subject', 'General')}]:"
                        f" {q['question']}**"
                    )
                    answers[idx] = st.radio(
                        "Options",
                        q["options"],
                        key=f"mock_q_{idx}",
                        index=None,
                        label_visibility="collapsed",
                    )
                    st.write("")

                submit_mock = st.form_submit_button("Submit Test")

            if submit_mock:
                score = 0
                for idx, q in enumerate(mock["questions"]):
                    if answers.get(idx) == q["answer"]:
                        score += 1

                total = len(mock["questions"])
                percentage = round((score / total) * 100, 1)

                st.session_state["test_history"].append({
                    "test_name": mock["name"],
                    "score": score,
                    "total": total,
                    "percentage": percentage,
                    "date": date.today().strftime("%Y-%m-%d"),
                })

                st.success(f"🎉 Completed {mock['name']}!")
                st.metric("Your Score", f"{score} / {total}", f"{percentage}%")

                with st.expander("🔍 Review Detailed Explanations"):
                    for idx, q in enumerate(mock["questions"]):
                        st.write(f"**Q{idx+1}: {q['question']}**")
                        st.write(f"Your Answer: {answers.get(idx)}")
                        st.write(f"Correct Answer: {q['answer']}")
                        st.caption(f"Explanation: {q['explanation']}")
                        st.divider()

    # ------------------------------------------------------------
    # TAB 3: CUSTOM / TOPIC MCQS (UP TO 60 MCQs)
    # ------------------------------------------------------------
    with tab3:
        st.subheader("🎯 Custom & Topic-Wise MCQ Practice")
        st.caption(
            "Select topics from your roadmap or type custom subjects (Up to 60"
            " MCQs)."
        )

        clean_topics = st.session_state.get("extracted_topics", [])
        topic_mode = st.radio(
            "Topic Selection Mode",
            ["Select from Roadmap Topics", "Enter Custom Topic Manually"],
            horizontal=True,
        )

        if topic_mode == "Select from Roadmap Topics":
            selected_topic = st.selectbox(
                "Select Topic", options=clean_topics
            )
        else:
            selected_topic = st.text_input(
                "Enter Custom Topic",
                placeholder="e.g. Organic Chemistry Reactions, Thermodynamics",
            )

        custom_count = st.select_slider(
            "MCQs to Generate",
            options=[5, 10, 15, 20, 30, 45, 60],
            value=15,
            key="custom_cnt_slider",
        )

        if st.button(
            f"➕ Generate {custom_count} Topic MCQs",
            type="primary",
            use_container_width=True,
        ):
            if not selected_topic or not selected_topic.strip():
                st.error("Please specify a valid topic.")
            else:
                current_key = get_groq_api_key()
                try:
                    client = Groq(api_key=current_key)
                    questions = batch_generate_mcqs(
                        client,
                        build_custom_mcq_prompt,
                        st.session_state["test"],
                        selected_topic,
                        custom_count,
                        is_mock=False,
                    )
                    st.session_state["custom_mcqs"] = {
                        "topic": selected_topic,
                        "questions": questions,
                    }
                except Exception as e:
                    st.error(f"Failed to generate topic MCQs: {e}")

        if "custom_mcqs" in st.session_state:
            c_data = st.session_state["custom_mcqs"]
            st.divider()

            col_t, col_d = st.columns([3, 1])
            with col_t:
                st.markdown(
                    f"### 📋 Practice: {c_data['topic']} ({len(c_data['questions'])} Questions)"
                )
            with col_d:
                try:
                    pdf_data = generate_mcqs_pdf(
                        f"Topic: {c_data['topic']}",
                        st.session_state["test"],
                        c_data["questions"],
                    )
                    st.download_button(
                        "📄 Download MCQs PDF",
                        pdf_data,
                        file_name=f"{c_data['topic'].replace(' ', '_')}_MCQs.pdf",
                        mime="application/pdf",
                    )
                except Exception as pdf_err:
                    st.error(f"PDF Error: {pdf_err}")

            with st.form("custom_topic_form"):
                topic_answers = {}
                for idx, q in enumerate(c_data["questions"]):
                    st.markdown(f"**Q{idx+1}: {q['question']}**")
                    topic_answers[idx] = st.radio(
                        "Options",
                        q["options"],
                        key=f"custom_q_{idx}",
                        index=None,
                        label_visibility="collapsed",
                    )
                    st.write("")

                submit_custom = st.form_submit_button("Evaluate Answers")

            if submit_custom:
                c_score = 0
                for idx, q in enumerate(c_data["questions"]):
                    if topic_answers.get(idx) == q["answer"]:
                        c_score += 1

                c_total = len(c_data["questions"])
                c_perc = round((c_score / c_total) * 100, 1)

                st.session_state["test_history"].append({
                    "test_name": f"Topic: {c_data['topic']}",
                    "score": c_score,
                    "total": c_total,
                    "percentage": c_perc,
                    "date": date.today().strftime("%Y-%m-%d"),
                })

                st.info(
                    f"**Score:** {c_score} / {c_total} ({c_perc}%) — Recorded in"
                    " Progress Tab!"
                )

                with st.expander("💡 View Explanations"):
                    for idx, q in enumerate(c_data["questions"]):
                        st.write(f"**Q{idx+1}: {q['question']}**")
                        st.write(f"Your Answer: {topic_answers.get(idx)}")
                        st.write(f"Correct Answer: {q['answer']}")
                        st.caption(f"Explanation: {q['explanation']}")
                        st.divider()

    # ------------------------------------------------------------
    # TAB 4: PROGRESS & ANALYTICS
    # ------------------------------------------------------------
    with tab4:
        st.subheader("📊 Performance Analytics & Progress Tracker")

        history = st.session_state.get("test_history", [])

        if not history:
            st.info(
                "No attempt history found yet. Complete mock tests in Tab 2 or"
                " topic practice in Tab 3 to see your progress metrics here!"
            )
        else:
            total_tests = len(history)
            total_questions = sum(h["total"] for h in history)
            total_correct = sum(h["score"] for h in history)
            avg_accuracy = round(
                (total_correct / total_questions) * 100
                if total_questions > 0
                else 0,
                1,
            )

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Tests Completed", total_tests)
            m2.metric("Questions Attempted", total_questions)
            m3.metric("Correct Answers", total_correct)
            m4.metric("Overall Accuracy", f"{avg_accuracy}%")

            st.divider()
            st.markdown("### 📜 Test History Log")
            st.dataframe(history, use_container_width=True)

            if st.button("🗑️ Reset Progress History"):
                st.session_state["test_history"] = []
                st.rerun()
