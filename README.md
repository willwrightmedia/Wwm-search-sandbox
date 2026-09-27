# wwm-search-sandbox

Prototype of the **Kat Intelligence Engine**, with two app layers:

- **Medierkat – media intelligence.** Coverage from official releases and newsrooms, news mastheads and wires, broadcast (TV, radio, podcasts) and trade press. No social media, forums or academic journals.
- **Markat – social customer sentiment.** How existing and prospective customers respond to a brand's marketing campaigns, and how they rate it against competitors, across Reddit, X, Threads, Facebook, Instagram, LinkedIn, TikTok, YouTube and community forums. No news or corporate media.

This is a private sandbox for invited testers, not a production service.

## How searches work

- **A new search runs two passes.** The selected channels are split across them, so every channel is covered.
- **"Find more"** runs one extra pass on a single channel, rotating through the channels on each click. It adds only new, non-duplicate results and refreshes the summary.

## How Markat scopes a search

Before searching, Markat works out where customers buy under the brand name itself:

- **Single country**, e.g. Telstra (Australia only): searches that country's customers.
- **Multiple countries:** searches each of those markets.
- **Global**, e.g. Coca-Cola: searches its largest customer markets.

It also identifies sub-brands in those markets (e.g. Belong for Telstra) and the main competitors. Subsidiaries trading under other names (e.g. Digicel) are left out. You can confirm or edit the scope, sub-brands and competitors before the search runs, or set them yourself in the sidebar.

## Reading Markat results

- **Signal strength** shows how widely each topic is discussed: ▮▯▯▯ single source, ▮▮▯▯ limited, ▮▮▮▯ moderate, ▮▮▮▮ widely discussed. It counts distinct sources and communities, plus any stated engagement.
- **"How representative is this?"** in each brief says whether sentiment looks broad or comes from a small, vocal group.
- **"Dig deeper"** on any topic runs a focused search for more discussion of it, to test how widespread it is.
- Social media over-represents digitally engaged and often dissatisfied customers, so use Markat alongside survey and NPS data.

## How results are checked

- Links appear only when they came from the search's own source list or were supplied by the user. Anything else is marked *Uncorroborated*.
- Each layer is held to its own source types: media only in Medierkat, social only in Markat.
- Items dated outside the selected time window are dropped.
- Duplicates are merged across search passes.
- Markat never records individuals' usernames, and customer views are paraphrased.
- If a search fails, the app says so. It never substitutes sample data.

## Known limitations

- Medierkat audience figures are model-reported masthead figures, summed without deduplication.
- Search coverage depends on what Google's index surfaces. Private groups, closed accounts and much of TikTok and Instagram are not indexed.
- Sentiment is assessed by AI and should be checked against the linked sources.
- Saved searches and briefs in the Library last only for the current session.

## Access

Access is by invitation. The administrator sets up the accounts; testers receive their login details directly.

## Running the app

Deployed on Streamlit Community Cloud from this repository. Configuration lives in the app's **Secrets** settings, never in the repository.

| Secret | Purpose |
|---|---|
| `GEMINI_API_KEY` | Gemini API key used for all searches |
| `GEMINI_MODEL` | Optional: Gemini model name |
| `KATADMIN_PASSWORD_HASH`, `KATGUEST_PASSWORD_HASH` | Keep passwords after the app restarts (the app shows these values when a password is set) |

Locally: `pip install -r requirements.txt`, then `streamlit run app.py`, with secrets in `.streamlit/secrets.toml` (listed in `.gitignore`).

## Repository contents

- `app.py` – the Streamlit application
- `requirements.txt` – Python dependencies
- `.gitignore` – keeps secrets and local data out of the repository
