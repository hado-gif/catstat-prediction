# Streamlit Deployment (Public Link)

## 1) Push to GitHub

Push this project to a GitHub repository.

## 2) Deploy on Streamlit Community Cloud

1. Go to https://share.streamlit.io/
2. Click **New app**
3. Select your GitHub repo and branch
4. Set **Main file path** to `app.py`
5. Click **Deploy**

## 3) Share link

After deploy, Streamlit gives a public URL.
Share that URL with users.

## 4) How users add CSV files

Inside the app, users use **Upload one or more CSV files** in the sidebar.
No local Python, no VS Code, no terminal needed for end users.

## Notes

- Upload limit is set in `.streamlit/config.toml`.
- Team filter supports case-insensitive partial match (acronym or name).
