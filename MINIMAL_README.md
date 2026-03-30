# Minimal Read Me (Streamlit Link-First)

## Local run

```bash
python3 -m pip install -r requirements.txt
streamlit run app.py
```

Users upload CSV files directly in the app UI.

## Team search in app

Use the **Team filter** field in the sidebar:
- acronym example: `VCU`
- full/partial name example: `Saint Joseph`

## Send users a public link

1. Push project to GitHub.
2. Open Streamlit Community Cloud.
3. Create new app and select repo + branch.
4. Set main file path to `app.py`.
5. Deploy and share the generated URL.

That URL is all users need.
