# wwm-search-sandbox

Prototype of the **Kat Intelligence Engine**, with two app layers:

- **Medierkat – media intelligence.** Coverage from official releases and newsrooms, news mastheads and wires, broadcast (TV, radio, podcasts) and trade press. Social posts are never reported as coverage; X and Reddit are used only as evidence that a TV or radio appearance happened (see below). No forums or academic journals.
- **Markat – social customer sentiment.** How existing and prospective customers respond to a brand's marketing campaigns, and how they rate it against competitors, across Reddit, X, Threads, Facebook, Instagram, LinkedIn, TikTok, YouTube and community forums. No news or corporate media.

This is a private sandbox for invited testers, not a production service.

## How searches work

- **A new search runs two passes.** The selected channels are split across them, so every channel is covered. In Medierkat, a third pass checks X and Reddit for TV and radio appearances (this can be switched off in the sidebar).
- **"Find more"** runs one extra pass on a single channel, rotating through the channels on each click. In Medierkat the rotation includes "X & Reddit broadcast mentions". It adds only new, non-duplicate results and refreshes the summary.

## Medierkat: guiding a search with a document

Under the search bar, **📎 Guide this search with a document** accepts Word (.docx and older .doc), PDF, Excel (.xlsx and .xls), CSV, text and Markdown files, up to 10 MB: for example a media plan, a list of spokespeople, or your own notes on interviews booked.

- Gemini reads the document for **leads**: related names, projects and campaigns, outlets and programmes, extra search terms, possible media appearances, and links. These guide every pass, including the X and Reddit check, Find more and smart search.
- **Nothing from the document is reported as coverage.** Only what the searches themselves find and verify appears in the brief. Links in the document are checked and reviewed like links pasted into the Brief builder.
- **Material from other monitoring and listening services is refused.** Before a search starts, the document and its file name are checked for Meltwater, Isentia/Media Monitors/Mediaportal, Streem, Cision, Brandwatch, Talkwalker, Onclusive, Muck Rack, Signal AI, Agility PR, Critical Mention, TVEyes, Truescope, Sprinklr, Sprout Social, YouScan, Pulsar, NetBase Quid, Synthesio, Digimind, Determ, Factiva, LexisNexis, Kantar Media, CARMA, Notified and Mention, and for Meltwater's export column headings. Users must also tick a box confirming the document is their own material.
- The document's text is sent to Gemini to read but isn't stored. The brief keeps only the file name and the leads that were used, shown under "Guided by your document" and in the exports' "How this search was built".

## Medierkat: TV and radio appearances confirmed on X and Reddit

Broadcast coverage is often missing from the web. Medierkat now searches X and Reddit for posts saying the subject (and any smart-search terms or document leads) appeared on TV or radio.

- **An appearance counts only when at least 3 different users say it aired**, across X and Reddit combined, with **at most 1 of them belonging to the subject or their organisation** (the broadcaster's own account counts as one user). Each user's post must be a link found by the search itself; invented links are discarded.
- Users are told apart by account. On X the account comes from the post's own address; on Reddit it's the username shown. Bots (such as AutoModerator) don't count. Handles are never stored: only a one-way fingerprint, the post link and date.
- Posts are grouped by broadcast: the same programme and medium, aired within 3 days. Podcasts, online-only video, broadcasts outside the time frame and likely namesakes are left out.
- **Confirmed appearances** join the matching coverage milestone as a TV or radio outlet, graded like any other coverage, and marked "Confirmed by N users on X and Reddit" with links to the posts in the app, PDF, Word, Markdown and spreadsheet exports.
- **Mentions with fewer confirmations** are listed in the brief under "TV and radio mentions awaiting confirmation". They aren't counted in grades, charts or exports. "Find more: X & Reddit broadcast mentions" looks specifically for more posts about them, and promotes any that reach 3 users.
- Smart-search terms get credit for broadcasts found this way, so a term isn't cancelled when its finds came from social posts.

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

Earned outlets score by tier: general national or international news 4, regional or metro news 2.5, major trade or specialist 2, niche trade 1, aggregators 0.5. The total is weighted by prominence (feature 1.5x, segment 1x, mention 0.6x).

**Breadth counts.** People follow a small number of outlets and formats, so coverage across different media reaches different audiences. Each additional medium (TV, radio, podcast, print, online, trade, wire) adds a bonus, and repeat coverage only counts for less within the same tier and the same medium, where audiences overlap. Grade 10 needs general national or international news. Grade 9 needs that too, unless coverage is broad: three or more media types and six or more earned outlets. Owned channels (the organisation's newsroom, paid wires such as Business Wire, release reposting sites such as ScienceDaily and EurekAlert) add nothing. Government, minister and regulator announcements count as modest endorsements, so an official-only milestone grades 3 to 5.

**The grading learns.** An outlet register records how every outlet has been classified across all searches. The agreed classification is applied every time, so the same outlet is always graded the same way, and older briefs update as the register improves. Well-known outlets start with a head start. The admin console lists every outlet, where you can correct a tier or type: your corrections always win. Download the register now and then, since Streamlit Community Cloud clears the app's files on restart, and restore it afterwards.

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
- A TV or radio appearance without an article link is included only when at least 3 different users on X or Reddit confirm it.
- Documents used to guide a search are never reported as coverage, and documents from other monitoring services are refused.

## Known limitations

- Medierkat audience figures are model-reported masthead figures, summed without deduplication.
- Search coverage depends on what Google's index surfaces. Private groups, closed accounts and much of TikTok and Instagram are not indexed.
- Sentiment is assessed by AI and should be checked against the linked sources.
- Saved searches and briefs in the Library last only for the current session.
- X and Reddit pages block automated access, so the app relies on what Google's search shows of them. It can't open every Reddit comment itself to confirm who wrote it; each confirmed appearance lists its post links so you can check. Much of X isn't indexed by Google, so some genuine appearances will stay unconfirmed.
- The same person posting on both X and Reddit counts as two users, because accounts on different platforms can't be linked.
- Old Word (.doc) files are read on a best-effort basis; if one reads poorly, save it as .docx.

## Background searches and notifications

- Searches run on the server in the background. You can switch tabs, lock your phone or refresh the page, and the results will be waiting when you return.
- Refreshing doesn't log you out, and your current briefs are restored. Share the app's base address with testers, not the address shown after you log in: that includes your login token.
- Tick "Notify me when a search finishes" in the sidebar to get a chime, a changed tab title and (with your browser's permission) a system notification when results arrive. If email is set up in Secrets (SMTP settings), you can also get an email.

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
