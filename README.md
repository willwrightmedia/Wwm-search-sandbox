# Wwm-search-sandbox

Media intelligence prototype for World Wide Monitor (WWM), running the Kat Intelligence Engine with two app layers:

Medierkat – PR and media: research and institutional coverage, reach, and executive reporting.
Markat – marketing and competitors: campaign impact, share of voice, and community sentiment.

This is a sandbox for invited testers. It's an early prototype shared to gather feedback on the user experience, not a production service.

What it does

Enter a person, organisation, product or topic. The app searches for coverage within the time window you choose, groups it into campaign milestones (an official release and the stories that followed it), and produces an executive brief you can export as PDF, Word or Markdown.

Each search runs four passes, each from a different angle:

Official media releases and announcements
Mainstream news mastheads, broadcasters and wire services
Trade press, specialist outlets and peer-reviewed publications
Social media and Reddit discussion (Reddit is shown in Markat only)

Each pass performs a live Google-grounded search with Gemini, then turns the findings into structured records.

How results are checked
Links are shown only when they came from the search's own source list or were supplied by the user. Anything else is marked Uncorroborated and shown without a link.
Recency is enforced in code. Items dated outside the selected window are dropped.
Duplicates are merged per campaign, by URL and outlet, so the same story isn't listed twice.
Altmetric scores appear only for peer-reviewed journal articles, looked up from Altmetric using the paper's DOI.
If a search fails, the app says so. It never substitutes sample or placeholder data.
Known limitations
Audience figures are masthead figures reported by the model, not independently verified. The combined figure adds outlet audiences together, so it overstates true unique reach.
Search quality depends on what Google's index surfaces for each pass. Niche or paywalled coverage may be missed.
Saved queries and briefs in the Library last only for the current session.
Only English-language search terms have been tested extensively, though briefs can be written in ten languages.
For testers

Your login details will be sent to you directly. Useful feedback includes:

anything confusing, slow or hard to find;
results that look wrong, missing or out of date;
what you'd expect a brief to include that it doesn't;
how the exports look when shared with others.
Running the app
Streamlit Community Cloud

The app is deployed from this repository. Configuration lives in the app's Secrets settings on Community Cloud, never in the repository. Do not commit a .streamlit/secrets.toml file.

Secrets used:

Name	Purpose
GEMINI_API_KEY	Gemini API key for search and writing
GEMINI_MODEL	Gemini model name
GUEST_ENABLED	"true" or "false" to switch the tester login on or off
ADMIN_SETUP_CODE	Required once, to create the admin account
ADMIN_EMAIL, ADMIN_PASSWORD_HASH	Keep the admin login working after the app restarts
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM	Email for admin password reset codes
Locally
bash
pip install -r requirements.txt
streamlit run app.py

Put the secrets in .streamlit/secrets.toml inside the project folder. It is listed in .gitignore so it won't be uploaded.

Repository contents
app.py – the Streamlit application
requirements.txt – Python dependencies
.gitignore – keeps secrets and local data out of the repository
