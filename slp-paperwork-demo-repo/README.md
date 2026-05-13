# SLP Paperwork MVP

A local-first Streamlit prototype to help an SLP track:

- Session logs and end-of-year billing cleanup
- ARD paperwork readiness
- Evaluation / FIIE / re-evaluation paperwork readiness
- Missing documentation, unsigned notes, unbilled sessions
- Exportable Excel packets
- Local redaction sandbox placeholder

## Important privacy note

Do **not** put real student/client PHI/education records into cloud tools during testing.

This MVP stores data locally in CSV files under `data/`. It does not call OpenAI, ChatGPT, or any external API.

The included redaction tool is a conservative regex fallback for prototyping only. It is **not** HIPAA/FERPA de-identification and should be replaced or augmented with a stronger local redaction model before real use.

## Install

```bash
cd slp_paperwork_mvp
python -m venv .venv
```

### macOS/Linux

```bash
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Data model

### Sessions

Core fields:

- `student_id`
- `student_initials`
- `campus`
- `date_of_service`
- `service_type`
- `delivery_model`
- `minutes`
- `attendance`
- `goal_area`
- `note_status`
- `billing_code`
- `payer_program`
- `billed`
- `signed`
- `notes`

### ARD tracker

Core fields:

- `student_id`
- `student_initials`
- `campus`
- `ard_type`
- `meeting_date`
- `due_date`
- `notice_sent`
- `draft_goals_ready`
- `present_levels_updated`
- `service_minutes_verified`
- `accommodations_reviewed`
- `parent_input_added`
- `signatures_complete`
- `status`
- `notes`

### Evaluation tracker

Core fields:

- `student_id`
- `student_initials`
- `campus`
- `eval_type`
- `consent_or_referral_date`
- `report_due_date`
- `ard_due_date`
- `teacher_input_received`
- `parent_input_received`
- `observations_complete`
- `testing_complete`
- `scores_entered`
- `report_drafted`
- `report_finalized`
- `parent_copy_provided_date`
- `status`
- `notes`

## Suggested next features

1. Add local encrypted storage instead of plain CSV.
2. Add role-based login if anyone other than your girlfriend uses it.
3. Add district-specific templates/checklists.
4. Add calendar reminders for due dates.
5. Add local OpenAI Privacy Filter integration.
6. Add AI draft helper only after redaction + human review.
7. Add PDF report generator.
8. Add import mappings for whatever system she currently uses.
