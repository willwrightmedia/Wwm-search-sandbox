# wwm-search-sandbox

Prototype of the **Kat Intelligence Engine**, with two app layers:

- **Medierkat – media intelligence.** Coverage from official releases and newsrooms, news mastheads and wires, broadcast (TV, radio, podcasts) and trade press. No social media, forums or academic journals.
- **Markat – social customer sentiment.** How existing and prospective customers respond to a brand's marketing campaigns, and how they rate it against competitors, across Reddit, X, Threads, Facebook, Instagram, LinkedIn, TikTok, YouTube and community forums. No news or corporate media.

This is a private sandbox for invited testers, not a production service.

## How searches work

- **A new search runs two passes.** The selected channels are split across them, so every channel is covered.
- **"Find more"** runs one extra pass on a single channel, rotating through the channels on each click. It adds only new, non-duplicate results and refreshes the summary.

## Smart search

After each search, the app finds related terms in the results (named people, projects, products, spin-offs, campaigns or hashtags tied to the original search) and offers to search them too. For example, "RMIT AND innovation" might suggest "Rajeev Roychand" or "Atmo Biosciences".

- You can untick any suggested term before it runs. Up to three terms are searched together, so a round usually costs one or two searches.
- Every new result must link back to the original search. Results that don't are rejected: the result needs a relevance score of at least 0.7 plus a mention of the original subject, or 0.85 on its own.
- Terms whose results mostly fail that check cancel themselves and are never suggested again. Productive terms can lead to further suggestions, for up to three rounds.
- A **search map** in each brief, and in the PDF, shows which terms were added, why, how many results each contributed, and which were cancelled.
- Turn suggestions off in the sidebar under "Smart search".

## Medierkat visibility grades

Instead of audience figures, which are usually estimates, each coverage milestone gets a visibility grade from 1 to 10, calculated from the coverage itself:

| Grade | Label | Roughly means |
|---|---|---|
| 10 | Exceptional | Feature coverage across several national or international outlets |
| 9 | Very high | Multiple national outlets, or a national feature plus wide pick-up |
| 8 | High | A national outlet feature, or several strong outlets |
| 7 | Good | A national outlet story, or strong regional or trade coverage |
| 6 | Moderate | Solid regional, metro or leading trade coverage |
| 5 | Modest | A mention in a national outlet, or a few trade outlets |
| 4 | Low | Niche trade or specialist coverage |
| 3 | Very low | Aggregators and syndication sites only |
| 2 | Minimal | Promoted through owned channels only (own newsroom, paid wires such as Business Wire) |
| 1 | None | No coverage or promotion found |

Earned outlets score by tier (national or international 4, regional, metro or leading trade 2.5, niche trade 1, aggregators 0.5), weighted by prominence (feature 1.5x, segment 1x, mention 0.6x). Owned channels (the organisation's newsroom, paid wires like Business Wire, release reposting sites) don't add to the score. Government, minister and regulator announcements count as modest third-party endorsements (1.5 points), so an official-only milestone grades 3 to 5 rather than 2. Each milestone also gets a grade per country where it appeared. Reports also split coverage into **earned vs owned**, and tag each milestone by type (research finding, expert commentary, partnership or funding, launch, award, issue).

## How Markat scopes a search

Before searching, Markat works out where customers buy under the brand name itself:

- **Single country**, e.g. Telstra (Australia only): searches that country's customers.
- **Multiple countries:** searches each of those markets.
- **Global**, e.g. Coca-Cola: searches its largest customer markets.

It also identifies sub-brands in those markets (e.g. Belong for Telstra) and the main competitors. Subsidiaries trading under other names (e.g. Digicel) are left out. You can confirm or edit the scope, sub-brands and competitors before the search runs, or set them yourself in the sidebar.

## Reading Markat results

- **Signal strength** shows how widely each topic is discussed: ▮▯▯▯ single source, ▮▮▯▯ limited, ▮▮▮▯ moderate, ▮▮▮▮ widely discussed. It counts distinct sources and communities, plus any stated engagement.
- **Themes grid:** net sentiment for each brand on themes such as price, service and reliability, from -1 (all negative) to +1 (all positive).
- **Confidence:** each topic shows how sure the sentiment call is, the evidence behind it, and a flag for possible sarcasm. You can correct any call; corrections are kept.
- **"How representative is this?"** in each brief says whether sentiment looks broad or comes from a small, vocal group.
- **"Dig deeper"** on any topic runs a focused search for more discussion of it.
- **Campaign mode:** enter a campaign name and launch date to compare discussion before and after the launch.
- **Review sites and app stores** can be added as an optional channel.
- Social media over-represents digitally engaged and often dissatisfied customers, so use Markat alongside survey and NPS data.

## Features in both layers

- **Ask this report:** type a question and get an answer drawn from the brief. In Markat, it can run a focused search when the brief doesn't cover the question.
- **Noise filter:** exclude results that mention particular terms.
- **Exports:** visual PDF and Word reports with charts and headline figures, Markdown, and a spreadsheet of every source.
- **Medierkat people searches:** "Also known as" (e.g. Oli Jones) and "Context" (e.g. RMIT chemistry professor) keep results to the right person.

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
