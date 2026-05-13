import io
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st


APP_TITLE = "SLP Paperwork MVP"
DATA_DIR = Path(__file__).parent / "data"

SESSION_COLUMNS = [
    "student_id", "student_initials", "campus", "date_of_service", "service_type",
    "delivery_model", "minutes", "attendance", "goal_area", "note_status",
    "billing_code", "payer_program", "billed", "signed", "notes"
]

ARD_COLUMNS = [
    "student_id", "student_initials", "campus", "ard_type", "meeting_date",
    "due_date", "notice_sent", "draft_goals_ready", "present_levels_updated",
    "service_minutes_verified", "accommodations_reviewed", "parent_input_added",
    "signatures_complete", "status", "notes"
]

EVAL_COLUMNS = [
    "student_id", "student_initials", "campus", "eval_type", "consent_or_referral_date",
    "report_due_date", "ard_due_date", "teacher_input_received",
    "parent_input_received", "observations_complete", "testing_complete",
    "scores_entered", "report_drafted", "report_finalized",
    "parent_copy_provided_date", "status", "notes"
]


def ensure_data_files():
    DATA_DIR.mkdir(exist_ok=True)
    defaults = {
        "sessions.csv": pd.DataFrame(columns=SESSION_COLUMNS),
        "ard_tracker.csv": pd.DataFrame(columns=ARD_COLUMNS),
        "eval_tracker.csv": pd.DataFrame(columns=EVAL_COLUMNS),
    }
    for filename, df in defaults.items():
        path = DATA_DIR / filename
        if not path.exists():
            df.to_csv(path, index=False)


def load_csv(filename: str, columns: list[str]) -> pd.DataFrame:
    ensure_data_files()
    path = DATA_DIR / filename
    try:
        df = pd.read_csv(path, dtype=str).fillna("")
    except pd.errors.EmptyDataError:
        df = pd.DataFrame(columns=columns)
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    return df[columns]


def save_csv(filename: str, df: pd.DataFrame, columns: list[str]):
    DATA_DIR.mkdir(exist_ok=True)
    df = df.copy()
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    df[columns].to_csv(DATA_DIR / filename, index=False)


def parse_date(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return None


def days_until(value):
    d = parse_date(value)
    if not d:
        return ""
    return (d - date.today()).days


def status_from_due_date(value, complete=False):
    if complete:
        return "Complete"
    days = days_until(value)
    if days == "":
        return "No due date"
    if days < 0:
        return "Overdue"
    if days <= 7:
        return "Due soon"
    return "On track"


def boolish(value):
    return str(value).strip().lower() in {"true", "yes", "y", "1", "checked", "complete", "completed"}


def add_deadline_columns(df: pd.DataFrame, due_col: str, complete_col=None) -> pd.DataFrame:
    out = df.copy()
    out["days_until_due"] = out[due_col].apply(days_until) if due_col in out.columns else ""
    if complete_col and complete_col in out.columns:
        out["deadline_status"] = out.apply(
            lambda row: status_from_due_date(row.get(due_col, ""), boolish(row.get(complete_col, ""))),
            axis=1
        )
    else:
        out["deadline_status"] = out[due_col].apply(lambda x: status_from_due_date(x, False)) if due_col in out.columns else ""
    return out


def simple_pii_redact(text: str) -> str:
    """
    Conservative local fallback redactor for MVP prototyping only.
    This is NOT a HIPAA/FERPA de-identification guarantee.
    Later: replace or augment with OpenAI Privacy Filter running locally.
    """
    if not text:
        return ""

    redacted = text

    patterns = [
        (r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", "[NAME]"),
        (r"\b[A-Z][a-z]+, [A-Z][a-z]+\b", "[NAME]"),
        (r"\b[\w\.-]+@[\w\.-]+\.\w+\b", "[EMAIL]"),
        (r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE]"),
        (r"\b\d{1,5}\s+[A-Za-z0-9\.\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Court|Ct|Boulevard|Blvd)\b", "[ADDRESS]"),
        (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]"),
        (r"\b\d{2}/\d{2}/\d{4}\b", "[DATE]"),
        (r"\b\d{4}-\d{2}-\d{2}\b", "[DATE]"),
    ]

    for pattern, replacement in patterns:
        redacted = re.sub(pattern, replacement, redacted)

    return redacted


def to_excel_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            safe_name = sheet_name[:31]
            df.to_excel(writer, sheet_name=safe_name, index=False)
    return output.getvalue()


def missing_count(df: pd.DataFrame, columns: list[str]) -> int:
    if df.empty:
        return 0
    total = 0
    for col in columns:
        if col in df.columns:
            total += (df[col].astype(str).str.strip() == "").sum()
    return int(total)


def render_editor(df: pd.DataFrame, key: str, columns: list[str]) -> pd.DataFrame:
    return st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        key=key,
        hide_index=True,
    )[columns]


def import_csv_widget(expected_columns: list[str], key: str):
    uploaded = st.file_uploader("Import CSV", type=["csv"], key=key)
    if not uploaded:
        return None
    imported = pd.read_csv(uploaded, dtype=str).fillna("")
    for col in expected_columns:
        if col not in imported.columns:
            imported[col] = ""
    return imported[expected_columns]


def sidebar():
    st.sidebar.title("SLP MVP")
    st.sidebar.caption("Local-first prototype. No cloud sync. Do not use as the official record.")
    return st.sidebar.radio(
        "Go to",
        [
            "Dashboard",
            "Session & Billing Tracker",
            "ARD Tracker",
            "Evaluation Tracker",
            "Privacy Redaction Sandbox",
            "Export Packet",
            "Setup Notes",
        ]
    )


def dashboard():
    st.header("Dashboard")

    sessions = load_csv("sessions.csv", SESSION_COLUMNS)
    ard = load_csv("ard_tracker.csv", ARD_COLUMNS)
    evals = load_csv("eval_tracker.csv", EVAL_COLUMNS)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sessions", len(sessions))
    c2.metric("ARD items", len(ard))
    c3.metric("Eval items", len(evals))

    unsigned = 0
    if not sessions.empty:
        unsigned = ((sessions["signed"].astype(str).str.lower() != "yes") & (sessions["attendance"].isin(["Seen", "Makeup"]))).sum()
    c4.metric("Unsigned billable notes", int(unsigned))

    st.subheader("Billing snapshot")
    if sessions.empty:
        st.info("No sessions yet. Add rows in Session & Billing Tracker or import a CSV.")
    else:
        s = sessions.copy()
        s["minutes_num"] = pd.to_numeric(s["minutes"], errors="coerce").fillna(0)
        s["billable_minutes"] = s.apply(
            lambda row: row["minutes_num"] if str(row.get("attendance", "")).lower() in {"seen", "makeup"} else 0,
            axis=1,
        )
        by_student = (
            s.groupby(["student_id", "student_initials"], dropna=False)
            .agg(
                sessions=("date_of_service", "count"),
                billable_minutes=("billable_minutes", "sum"),
                incomplete_notes=("note_status", lambda x: int((x.astype(str).str.lower() != "complete").sum())),
                unbilled=("billed", lambda x: int((x.astype(str).str.lower() != "yes").sum())),
            )
            .reset_index()
            .sort_values(["unbilled", "incomplete_notes", "billable_minutes"], ascending=[False, False, False])
        )
        st.dataframe(by_student, use_container_width=True, hide_index=True)

    st.subheader("Upcoming / overdue ARD paperwork")
    if not ard.empty:
        ard_due = add_deadline_columns(ard, "due_date", "signatures_complete")
        st.dataframe(
            ard_due.sort_values("days_until_due", key=lambda s: pd.to_numeric(s, errors="coerce")),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No ARD paperwork rows yet.")

    st.subheader("Upcoming / overdue evaluations")
    if not evals.empty:
        eval_due = add_deadline_columns(evals, "report_due_date", "report_finalized")
        st.dataframe(
            eval_due.sort_values("days_until_due", key=lambda s: pd.to_numeric(s, errors="coerce")),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No evaluation rows yet.")


def session_tracker():
    st.header("Session & Billing Tracker")
    st.caption("Track service delivery, documentation, signatures, and billing status.")

    df = load_csv("sessions.csv", SESSION_COLUMNS)

    with st.expander("Add a session", expanded=True):
        with st.form("add_session_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            student_id = c1.text_input("Student ID / local alias")
            student_initials = c2.text_input("Initials")
            campus = c3.text_input("Campus")

            c1, c2, c3 = st.columns(3)
            dos = c1.date_input("Date of service", value=date.today())
            service_type = c2.selectbox("Service type", ["Speech therapy", "Language therapy", "Articulation", "Fluency", "Pragmatics", "Consult", "Evaluation", "Other"])
            delivery_model = c3.selectbox("Delivery model", ["Individual", "Group", "Classroom", "Consult", "Teletherapy", "Other"])

            c1, c2, c3 = st.columns(3)
            minutes = c1.number_input("Minutes", min_value=0, max_value=300, value=30)
            attendance = c2.selectbox("Attendance", ["Seen", "Makeup", "Absent", "Cancelled", "No show", "Other"])
            goal_area = c3.text_input("Goal area")

            c1, c2, c3, c4 = st.columns(4)
            note_status = c1.selectbox("Note status", ["Draft", "Complete", "Needs edit", "Not started"])
            billing_code = c2.text_input("Billing code")
            payer_program = c3.text_input("Payer/program")
            billed = c4.selectbox("Billed?", ["No", "Yes"])

            c1, c2 = st.columns(2)
            signed = c1.selectbox("Signed?", ["No", "Yes"])
            notes = c2.text_area("Notes")

            submitted = st.form_submit_button("Add session")
            if submitted:
                new_row = pd.DataFrame([{
                    "student_id": student_id,
                    "student_initials": student_initials,
                    "campus": campus,
                    "date_of_service": dos.isoformat(),
                    "service_type": service_type,
                    "delivery_model": delivery_model,
                    "minutes": str(minutes),
                    "attendance": attendance,
                    "goal_area": goal_area,
                    "note_status": note_status,
                    "billing_code": billing_code,
                    "payer_program": payer_program,
                    "billed": billed,
                    "signed": signed,
                    "notes": notes,
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                save_csv("sessions.csv", df, SESSION_COLUMNS)
                st.success("Session added.")

    imported = import_csv_widget(SESSION_COLUMNS, "import_sessions")
    if imported is not None:
        df = pd.concat([df, imported], ignore_index=True)
        save_csv("sessions.csv", df, SESSION_COLUMNS)
        st.success("Imported sessions.")

    edited = render_editor(df, "session_editor", SESSION_COLUMNS)

    c1, c2 = st.columns(2)
    if c1.button("Save session table"):
        save_csv("sessions.csv", edited, SESSION_COLUMNS)
        st.success("Saved.")
    c2.download_button(
        "Download sessions CSV",
        edited.to_csv(index=False).encode("utf-8"),
        "sessions.csv",
        "text/csv",
    )

    st.subheader("Issues to resolve")
    if edited.empty:
        st.info("No data yet.")
    else:
        issues = edited.copy()
        issues["minutes_num"] = pd.to_numeric(issues["minutes"], errors="coerce").fillna(0)

        unsigned = issues[(issues["attendance"].isin(["Seen", "Makeup"])) & (issues["signed"].str.lower() != "yes")]
        unbilled = issues[(issues["attendance"].isin(["Seen", "Makeup"])) & (issues["billed"].str.lower() != "yes")]
        incomplete = issues[(issues["attendance"].isin(["Seen", "Makeup"])) & (issues["note_status"].str.lower() != "complete")]
        missing_codes = issues[(issues["attendance"].isin(["Seen", "Makeup"])) & (issues["billing_code"].astype(str).str.strip() == "")]

        st.write(f"Unsigned billable notes: **{len(unsigned)}**")
        st.write(f"Unbilled billable sessions: **{len(unbilled)}**")
        st.write(f"Incomplete notes: **{len(incomplete)}**")
        st.write(f"Missing billing codes: **{len(missing_codes)}**")


def ard_tracker():
    st.header("ARD Tracker")
    st.caption("Track Admission, Review, and Dismissal paperwork tasks. This is a checklist tool, not legal advice.")

    df = load_csv("ard_tracker.csv", ARD_COLUMNS)

    with st.expander("Add ARD item", expanded=True):
        with st.form("add_ard_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            student_id = c1.text_input("Student ID / local alias")
            student_initials = c2.text_input("Initials")
            campus = c3.text_input("Campus")

            c1, c2, c3 = st.columns(3)
            ard_type = c1.selectbox("ARD type", ["Annual", "Initial", "Review/Revision", "Reevaluation", "Dismissal", "Transition", "Other"])
            meeting_date = c2.date_input("Meeting date", value=date.today())
            due_date = c3.date_input("Due date", value=date.today())

            c1, c2, c3 = st.columns(3)
            notice_sent = c1.selectbox("Notice sent?", ["No", "Yes"])
            draft_goals_ready = c2.selectbox("Draft goals ready?", ["No", "Yes"])
            present_levels_updated = c3.selectbox("Present levels updated?", ["No", "Yes"])

            c1, c2, c3 = st.columns(3)
            service_minutes_verified = c1.selectbox("Service minutes verified?", ["No", "Yes"])
            accommodations_reviewed = c2.selectbox("Accommodations reviewed?", ["No", "Yes"])
            parent_input_added = c3.selectbox("Parent input added?", ["No", "Yes"])

            c1, c2 = st.columns(2)
            signatures_complete = c1.selectbox("Signatures complete?", ["No", "Yes"])
            status = c2.selectbox("Status", ["Not started", "In progress", "Waiting on input", "Complete"])

            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Add ARD item")

            if submitted:
                new_row = pd.DataFrame([{
                    "student_id": student_id,
                    "student_initials": student_initials,
                    "campus": campus,
                    "ard_type": ard_type,
                    "meeting_date": meeting_date.isoformat(),
                    "due_date": due_date.isoformat(),
                    "notice_sent": notice_sent,
                    "draft_goals_ready": draft_goals_ready,
                    "present_levels_updated": present_levels_updated,
                    "service_minutes_verified": service_minutes_verified,
                    "accommodations_reviewed": accommodations_reviewed,
                    "parent_input_added": parent_input_added,
                    "signatures_complete": signatures_complete,
                    "status": status,
                    "notes": notes,
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                save_csv("ard_tracker.csv", df, ARD_COLUMNS)
                st.success("ARD item added.")

    imported = import_csv_widget(ARD_COLUMNS, "import_ard")
    if imported is not None:
        df = pd.concat([df, imported], ignore_index=True)
        save_csv("ard_tracker.csv", df, ARD_COLUMNS)
        st.success("Imported ARD rows.")

    with_deadlines = add_deadline_columns(df, "due_date", "signatures_complete")
    st.subheader("ARD table")
    edited = render_editor(with_deadlines[ARD_COLUMNS], "ard_editor", ARD_COLUMNS)

    c1, c2 = st.columns(2)
    if c1.button("Save ARD table"):
        save_csv("ard_tracker.csv", edited, ARD_COLUMNS)
        st.success("Saved.")
    c2.download_button(
        "Download ARD CSV",
        edited.to_csv(index=False).encode("utf-8"),
        "ard_tracker.csv",
        "text/csv",
    )

    st.subheader("ARD readiness")
    if edited.empty:
        st.info("No ARD rows yet.")
    else:
        checklist_cols = [
            "notice_sent", "draft_goals_ready", "present_levels_updated",
            "service_minutes_verified", "accommodations_reviewed",
            "parent_input_added", "signatures_complete"
        ]
        readiness = edited.copy()
        readiness["missing_items"] = readiness[checklist_cols].apply(
            lambda row: ", ".join([col for col in checklist_cols if str(row[col]).lower() != "yes"]),
            axis=1,
        )
        readiness = add_deadline_columns(readiness, "due_date", "signatures_complete")
        st.dataframe(
            readiness[["student_id", "student_initials", "ard_type", "meeting_date", "due_date", "deadline_status", "missing_items"]],
            use_container_width=True,
            hide_index=True,
        )


def eval_tracker():
    st.header("Evaluation Tracker")
    st.caption("Track evaluation/FIIE/re-evaluation paperwork, inputs, testing, reports, and ARD deadlines.")

    df = load_csv("eval_tracker.csv", EVAL_COLUMNS)

    with st.expander("Add evaluation item", expanded=True):
        with st.form("add_eval_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            student_id = c1.text_input("Student ID / local alias")
            student_initials = c2.text_input("Initials")
            campus = c3.text_input("Campus")

            c1, c2, c3 = st.columns(3)
            eval_type = c1.selectbox("Eval type", ["FIIE", "Speech-only eval", "Reevaluation", "Review of existing evaluation data", "Other"])
            consent_or_referral_date = c2.date_input("Consent/referral date", value=date.today())
            report_due_date = c3.date_input("Report due date", value=date.today())

            c1, c2 = st.columns(2)
            ard_due_date = c1.date_input("ARD due date", value=date.today() + timedelta(days=30))
            status = c2.selectbox("Status", ["Not started", "In progress", "Waiting on input", "Report drafting", "Complete"])

            c1, c2, c3 = st.columns(3)
            teacher_input_received = c1.selectbox("Teacher input received?", ["No", "Yes"])
            parent_input_received = c2.selectbox("Parent input received?", ["No", "Yes"])
            observations_complete = c3.selectbox("Observations complete?", ["No", "Yes"])

            c1, c2, c3 = st.columns(3)
            testing_complete = c1.selectbox("Testing complete?", ["No", "Yes"])
            scores_entered = c2.selectbox("Scores entered?", ["No", "Yes"])
            report_drafted = c3.selectbox("Report drafted?", ["No", "Yes"])

            c1, c2 = st.columns(2)
            report_finalized = c1.selectbox("Report finalized?", ["No", "Yes"])
            parent_copy_provided_date = c2.text_input("Parent copy provided date")

            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Add evaluation item")

            if submitted:
                new_row = pd.DataFrame([{
                    "student_id": student_id,
                    "student_initials": student_initials,
                    "campus": campus,
                    "eval_type": eval_type,
                    "consent_or_referral_date": consent_or_referral_date.isoformat(),
                    "report_due_date": report_due_date.isoformat(),
                    "ard_due_date": ard_due_date.isoformat(),
                    "teacher_input_received": teacher_input_received,
                    "parent_input_received": parent_input_received,
                    "observations_complete": observations_complete,
                    "testing_complete": testing_complete,
                    "scores_entered": scores_entered,
                    "report_drafted": report_drafted,
                    "report_finalized": report_finalized,
                    "parent_copy_provided_date": parent_copy_provided_date,
                    "status": status,
                    "notes": notes,
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                save_csv("eval_tracker.csv", df, EVAL_COLUMNS)
                st.success("Evaluation item added.")

    imported = import_csv_widget(EVAL_COLUMNS, "import_evals")
    if imported is not None:
        df = pd.concat([df, imported], ignore_index=True)
        save_csv("eval_tracker.csv", df, EVAL_COLUMNS)
        st.success("Imported evaluation rows.")

    with_deadlines = add_deadline_columns(df, "report_due_date", "report_finalized")
    st.subheader("Evaluation table")
    edited = render_editor(with_deadlines[EVAL_COLUMNS], "eval_editor", EVAL_COLUMNS)

    c1, c2 = st.columns(2)
    if c1.button("Save evaluation table"):
        save_csv("eval_tracker.csv", edited, EVAL_COLUMNS)
        st.success("Saved.")
    c2.download_button(
        "Download evaluations CSV",
        edited.to_csv(index=False).encode("utf-8"),
        "eval_tracker.csv",
        "text/csv",
    )

    st.subheader("Evaluation readiness")
    if edited.empty:
        st.info("No evaluation rows yet.")
    else:
        checklist_cols = [
            "teacher_input_received", "parent_input_received", "observations_complete",
            "testing_complete", "scores_entered", "report_drafted", "report_finalized"
        ]
        readiness = edited.copy()
        readiness["missing_items"] = readiness[checklist_cols].apply(
            lambda row: ", ".join([col for col in checklist_cols if str(row[col]).lower() != "yes"]),
            axis=1,
        )
        readiness = add_deadline_columns(readiness, "report_due_date", "report_finalized")
        st.dataframe(
            readiness[["student_id", "student_initials", "eval_type", "report_due_date", "ard_due_date", "deadline_status", "missing_items"]],
            use_container_width=True,
            hide_index=True,
        )


def redaction_sandbox():
    st.header("Privacy Redaction Sandbox")
    st.warning(
        "Prototype only. This fallback regex redactor is not HIPAA/FERPA de-identification. "
        "For real use, run a proper local PII/PHI redaction model and require human review."
    )

    text = st.text_area(
        "Paste sample text here",
        height=220,
        placeholder="Example: Jane Smith was seen on 04/12/2026 for articulation therapy..."
    )
    if st.button("Redact locally"):
        redacted = simple_pii_redact(text)
        st.subheader("Redacted output")
        st.code(redacted)

    st.markdown(
        """
        **Planned production privacy layer**

        1. Keep raw student/client records local and encrypted.
        2. Run local redaction before any AI drafting.
        3. Show a side-by-side review screen before sending text to any external API.
        4. Never send PHI/education records to a cloud API unless the district/employer policy and required agreements allow it.
        """
    )


def export_packet():
    st.header("Export Packet")

    sessions = load_csv("sessions.csv", SESSION_COLUMNS)
    ard = load_csv("ard_tracker.csv", ARD_COLUMNS)
    evals = load_csv("eval_tracker.csv", EVAL_COLUMNS)

    st.write("Generate an Excel workbook with sessions, ARD items, evaluation items, and issue summaries.")

    if sessions.empty and ard.empty and evals.empty:
        st.info("No data yet.")
        return

    issue_rows = []

    if not sessions.empty:
        s = sessions.copy()
        for _, row in s.iterrows():
            billable = str(row.get("attendance", "")).lower() in {"seen", "makeup"}
            if billable and str(row.get("signed", "")).lower() != "yes":
                issue_rows.append({"area": "Session", "student_id": row.get("student_id", ""), "issue": "Unsigned billable note", "date": row.get("date_of_service", "")})
            if billable and str(row.get("billed", "")).lower() != "yes":
                issue_rows.append({"area": "Session", "student_id": row.get("student_id", ""), "issue": "Unbilled billable session", "date": row.get("date_of_service", "")})
            if billable and str(row.get("note_status", "")).lower() != "complete":
                issue_rows.append({"area": "Session", "student_id": row.get("student_id", ""), "issue": "Incomplete note", "date": row.get("date_of_service", "")})

    if not ard.empty:
        checklist_cols = [
            "notice_sent", "draft_goals_ready", "present_levels_updated",
            "service_minutes_verified", "accommodations_reviewed",
            "parent_input_added", "signatures_complete"
        ]
        for _, row in ard.iterrows():
            for col in checklist_cols:
                if str(row.get(col, "")).lower() != "yes":
                    issue_rows.append({"area": "ARD", "student_id": row.get("student_id", ""), "issue": f"Missing: {col}", "date": row.get("meeting_date", "")})

    if not evals.empty:
        checklist_cols = [
            "teacher_input_received", "parent_input_received", "observations_complete",
            "testing_complete", "scores_entered", "report_drafted", "report_finalized"
        ]
        for _, row in evals.iterrows():
            for col in checklist_cols:
                if str(row.get(col, "")).lower() != "yes":
                    issue_rows.append({"area": "Evaluation", "student_id": row.get("student_id", ""), "issue": f"Missing: {col}", "date": row.get("report_due_date", "")})

    issues = pd.DataFrame(issue_rows)

    excel_bytes = to_excel_bytes({
        "Sessions": sessions,
        "ARD Tracker": ard,
        "Evaluation Tracker": evals,
        "Issues": issues,
    })

    st.download_button(
        "Download Excel packet",
        excel_bytes,
        "slp_paperwork_packet.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    if not issues.empty:
        st.subheader("Issues preview")
        st.dataframe(issues, use_container_width=True, hide_index=True)


def setup_notes():
    st.header("Setup Notes")
    st.markdown(
        """
        ## What this MVP does

        - Tracks sessions, service minutes, documentation status, signatures, and billing status.
        - Tracks ARD paperwork readiness.
        - Tracks evaluation/FIIE/re-evaluation paperwork readiness.
        - Exports a consolidated Excel packet.
        - Includes a local redaction sandbox placeholder.

        ## What it does not do yet

        - It does not replace the district's official documentation system.
        - It does not calculate every Texas special education deadline automatically.
        - It does not guarantee HIPAA, FERPA, Medicaid, or district compliance.
        - It does not send anything to OpenAI or any cloud service.

        ## Recommended workflow

        1. Use student aliases or local IDs instead of full names.
        2. Import existing session logs as CSV.
        3. Use due dates from the district's official system.
        4. Export the issue packet before end-of-year closeout.
        5. Use the redaction sandbox only for testing; production should use a stronger local redaction model.
        """
    )


def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="🗂️", layout="wide")
    ensure_data_files()

    page = sidebar()
    st.title(APP_TITLE)

    if page == "Dashboard":
        dashboard()
    elif page == "Session & Billing Tracker":
        session_tracker()
    elif page == "ARD Tracker":
        ard_tracker()
    elif page == "Evaluation Tracker":
        eval_tracker()
    elif page == "Privacy Redaction Sandbox":
        redaction_sandbox()
    elif page == "Export Packet":
        export_packet()
    elif page == "Setup Notes":
        setup_notes()


if __name__ == "__main__":
    main()
