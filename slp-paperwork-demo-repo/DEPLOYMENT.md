# Deploying the SLP Paperwork Demo to Streamlit Community Cloud

This is the public/fake-data demo path. Do not enter real student/client information into the deployed app.

## Files Streamlit needs

The repo should contain:

```text
app.py
requirements.txt
README.md
data/
  sessions.csv
  ard_tracker.csv
  eval_tracker.csv
.streamlit/
  config.toml
```

## Deploy steps

1. Create a new GitHub repository named `slp-paperwork-demo`.
2. Upload all files from this folder into the repository.
3. Go to Streamlit Community Cloud: https://share.streamlit.io
4. Click **Create app**.
5. Choose **Yup, I have an app**.
6. Select:
   - Repository: `your-github-username/slp-paperwork-demo`
   - Branch: `main`
   - Main file path: `app.py`
7. Optional: choose a custom URL like `slp-paperwork-demo`.
8. Click **Deploy**.
9. Send the resulting `.streamlit.app` link to your girlfriend.

## Safety text to send with the link

“Here’s a rough demo with fake data. Don’t enter real student info yet — I just want your feedback on whether the workflow matches your ARD/eval/billing paperwork pain.”
