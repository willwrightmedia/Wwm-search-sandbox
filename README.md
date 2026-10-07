# wwm-search-sandbox

Prototype of the **Kat Intelligence Engine**, with two app layers:

- **Medierkat – media intelligence.** Coverage from official releases and newsrooms, news mastheads and wires, broadcast (TV, radio, podcasts) and trade press. Social posts are never reported as coverage; X, Reddit and LinkedIn are used only as evidence that a TV or radio appearance happened (see below). No forums or academic journals.
- **Markat – social customer sentiment.** How existing and prospective customers respond to a brand's marketing campaigns, and how they rate it against competitors, across Reddit, X, Threads, Facebook, Instagram, LinkedIn, TikTok, YouTube and community forums. No news or corporate media.

This is a private sandbox for invited testers, not a production service.

## How searches work

- **A new search runs two passes.** The selected channels are split across them, so every channel is covered. In Medierkat, three follow-up searches then chase the biggest stories (see below), and a final pass checks X, Reddit and LinkedIn for TV and radio appearances. Both can be switched off in the sidebar.
- Searches look for the subject's names and key terms separately and together, not only as one exact phrase, so "Sumeet Walia, RMIT" also finds stories that name him and RMIT in different sentences.
- **"Find more"** runs one extra pass on a single channel, rotating through the channels on each click. In Medierkat the rotation includes "Story pickups" (three searches) and "X, Reddit and LinkedIn broadcast mentions". It adds only new, non-duplicate results and refreshes the summary.

## Medierkat: following up the biggest stories

One search only returns a handful of sources, and a story that's widely picked up (a university release, say) can run in dozens of places. Once the first passes have found the stories, Medierkat follows up the two most widely covered with three more searches:

- **Republished and rewritten copies:** syndicated copies (MSN, Yahoo), science and technology news sites, release reposting services, trade and specialist press, regional and international sites. Republished copies usually keep the original headline, so every article's headline is now recorded and searched for in quotation marks.
- **Other languages:** the story's key terms and headline translated and searched in Spanish, Portuguese, French, Italian, German, Chinese, Japanese and other languages (or the languages of your priority markets).
- **Radio, TV and podcast pages:** stories on broadcasters' own websites, program and episode pages, show notes and podcast listings.

Everything found goes through the same checks as any other result and joins the story's campaign. The brief and exports say what the follow-ups added ("How this search was built"), and the spreadsheet export now includes each article's headline. "Find more: Story pickups" follows up again, digging deeper; each time it favours big stories that have been followed up less.

## Medierkat: guiding a search with a document

Under the search bar, **📎 Guide this search with a document** accepts Word (.docx and older .doc), PDF, Excel (.xlsx and .xls), CSV, text and Markdown files, up to 10 MB: for example a media plan, a list of spokespeople, or your own notes on interviews booked.

- The AI engine reads the document for **leads**: related names (people and organisations involved in the work, not the journalists or bloggers who covered it), projects and campaigns, outlets and programs, story headlines, extra search terms, possible media appearances, and links. These guide every pass, including the story follow-ups, the X, Reddit and LinkedIn check, Find more and smart search. Headlines are searched in quotation marks to catch republished copies.
- **Nothing from the document is reported as coverage unless the search finds it, or you add it.** Media appearances the document describes are listed for you to review and add (see "Medierkat: reported coverage"). Links in the document are checked and reviewed like links pasted into the Brief builder.
- **Material from other monitoring and listening services is refused.** Before a search starts, the document and its file name are checked for Meltwater, Isentia/Media Monitors/Mediaportal, Streem, Cision, Brandwatch, Talkwalker, Onclusive, Muck Rack, Signal AI, Agility PR, Critical Mention, TVEyes, Truescope, Sprinklr, Sprout Social, YouScan, Pulsar, NetBase Quid, Synthesio, Digimind, Determ, Factiva, LexisNexis, Kantar Media, CARMA, Notified and Mention, and for Meltwater's export column headings. Exports with the service's name removed are refused too when they show a monitoring service's fingerprints: radio or TV clips timed to the second, Copyright Agency licence tags, or print editions listed as "(Print version)". Users must also tick a box confirming the document is their own material.
- The document's text is sent to the AI engine (Claude or Gemini) to read but isn't stored. The brief keeps only the file name and the leads that were used, shown under "Guided by your document" and in the exports' "How this search was built".

## Medierkat: TV and radio appearances confirmed on X, Reddit and LinkedIn

Broadcast coverage is often missing from the web. Medierkat now searches X, Reddit and LinkedIn for posts saying the subject (and any smart-search terms or document leads) appeared on TV or radio.

- **An appearance counts only when at least 3 different users say it aired**, across X, Reddit and LinkedIn combined, with **at most 1 of them belonging to the subject or their organisation** (the broadcaster's own account counts as one user). Each user's post must be a link found by the search itself; invented links are discarded.
- Users are told apart by account. On X, and on most LinkedIn posts, the account comes from the post's own address; on Reddit, and LinkedIn posts whose address doesn't show the author, it's the account name shown. LinkedIn profile and company pages don't count, because they aren't posts saying a broadcast aired; a post by an organisation's LinkedIn page counts as the organisation's own account. Bots (such as AutoModerator) don't count. Handles are never stored: only a one-way fingerprint, the post link and date.
- Posts are grouped by broadcast: the same program and medium, aired within 3 days. Podcasts, online-only video, broadcasts outside the time frame and likely namesakes are left out.
- **Confirmed appearances** join the matching campaign as a TV or radio outlet, graded like any other coverage, and marked with the platforms that confirmed them (for example "Confirmed by 4 users on X and LinkedIn"), with links to the posts in the app, PDF, Word, Markdown and spreadsheet exports.
- **Mentions with fewer confirmations** are listed in the brief under "TV and radio mentions awaiting confirmation". They aren't counted in grades, charts or exports. "Find more: X, Reddit and LinkedIn broadcast mentions" looks specifically for more posts about them, and promotes any that reach 3 users.
- Smart-search terms get credit for broadcasts found this way, so a term isn't cancelled when its finds came from social posts.

## Medierkat: reported coverage

The people running a campaign know what media it got, so Medierkat takes their word for it. In the **📄 Brief** tab, the box "Links or notes on media appearances (radio, TV, online and print)" takes links to coverage and plain notes, one per line, for example:

```
https://www.example.com.au/news/bionic-eye
3AW Breakfast, 9 September 2026: Sumeet Walia on the bionic eye
Geelong Advertiser (print), 9 September 2026, page 7
```

- With notes, the user ticks "These are media appearances I or my team know happened. Medierkat includes them as reported, without checking them, and isn't responsible for their accuracy." before the brief runs.
- **Print, radio and TV in the notes go straight into the brief as reported.** The web searches don't look for them. The AI engine reads each appearance (outlet, program, medium, date, spokesperson, topic) and places it in the campaign it belongs to, or a new one.
- **Online items** are searched for, so their links can be added. Any that aren't found still go in as reported.
- **X, LinkedIn and Reddit show resonance.** The social search looks for posts about every TV and radio appearance the user reported. Posts by independent people show the coverage resonated, and add to the campaign's visibility (see "Medierkat visibility grades"). A broadcast that 3 or more people post about becomes confirmed coverage, with its posts linked.
- Reported coverage counts in full, exactly like coverage found online. It's marked **Reported by user** in the app and in every export, and "How this search was built" says how many items were included as reported and how many were shared on social media.
- **Appearances in an uploaded document** are listed at the top of the brief for the user to review first, because a document such as a media plan can include appearances that were only planned. The user unticks any that didn't happen, ticks the same acknowledgement and presses **Add to report**.
- If the AI reports one of the user's appearances without a link, that copy is dropped, so nothing is counted twice.
- Notes are screened like documents: material from media monitoring services is refused.

## Medierkat reports: the Media brief

PDF, Word, Markdown and spreadsheet exports are called **Media brief** and carry no branding: no Medierkat or Kat Intelligence Engine name in titles, page headers, footers, file names (`Media_brief_<search>.pdf`) or document properties. The in-app brief keeps the app's name in its own notes.

- Headline cards: **No. of campaigns**, **Earned vs owned**, **Visibility**, and **Media breadth** (the number of earned outlets, with any reported by the user noted).
- Each news event and its coverage is called a **campaign** throughout (formerly "coverage milestone").

## Australian style

The app and its reports use Australian spelling (Macquarie Dictionary) and the Australian Government Style Manual: program, organisation, analyse; sentence-case headings; dates such as 9 September 2026 (with Sept, June and July in charts); times such as 3:26 pm (Melbourne time); words for zero and one and numerals from 2; spaced en dashes; "and" rather than "&". The AI engine is asked to write the same way, and a spelling check converts US spellings in AI-written text (titles, summaries, answers) without changing names, headlines or quotations. This applies when the report language is English (Australian).

## Smart search

After each search, the app finds related terms in the results (named people, projects, products, spin-offs, campaigns or hashtags tied to the original search) and offers to search them too. For example, "RMIT AND innovation" might suggest "Rajeev Roychand" or "Atmo Biosciences".

- You can untick any suggested term before it runs. Up to three terms are searched together, so a round usually costs one or two searches.
- Every new result must link back to the original search. Results that don't are rejected: the result needs a relevance score of at least 0.7 plus a mention of the original subject, or 0.85 on its own.
- Terms whose results mostly fail that check cancel themselves and are never suggested again. Productive terms can lead to further suggestions, for up to three rounds.
- A **search map** in each brief, and in the PDF, shows which terms were added, why, how many results each contributed, and which were cancelled.
- Turn suggestions off in the sidebar under "Smart search".

## Medierkat visibility grades

Instead of audience figures, which are usually estimates, each campaign gets a visibility grade from 1 to 10, calculated from the coverage itself:

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

**Breadth counts.** People follow a small number of outlets and formats, so coverage across different media reaches different audiences. Each additional medium (TV, radio, podcast, print, online, trade, wire) adds a bonus, and repeat coverage only counts for less within the same tier and the same medium, where audiences overlap. Grade 10 needs general national or international news. Grade 9 needs that too, unless coverage is broad: three or more media types and six or more earned outlets. Owned channels (the organisation's newsroom, paid wires such as Business Wire, release reposting sites such as ScienceDaily and EurekAlert) add nothing. Government, minister and regulator announcements count as modest endorsements, so an official-only campaign grades 3 to 5.

**Reported coverage** (see "Medierkat: reported coverage") counts in full, like coverage found online, including towards grades 9 and 10.

**Social resonance adds to the grade.** Each independent person who posts about a campaign's coverage on X, LinkedIn or Reddit adds 0.5 points, up to 2 points per campaign (about half a national news story). Posts by the subject, their organisation or the broadcaster don't count towards this.

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
- A TV or radio appearance without an article link is included only when at least 3 different users on X, Reddit or LinkedIn confirm it.
- Coverage the user reports is included as reported, marked "Reported by user", on the user's acknowledgement; appearances read from a document are reviewed by the user first. Documents and notes from other monitoring services are refused.

## Known limitations

- Medierkat audience figures are model-reported masthead figures, summed without deduplication.
- Search coverage depends on what Google's index surfaces. Private groups, closed accounts and much of TikTok and Instagram are not indexed.
- Sentiment is assessed by AI and should be checked against the linked sources.
- Saved searches and briefs in the Library last only for the current session.
- X, Reddit and LinkedIn block automated access, so the app relies on what Google's search shows of them. It can't open every Reddit comment itself to confirm who wrote it; each confirmed appearance lists its post links so you can check. Much of X, and most of LinkedIn (which needs a login), isn't indexed by Google, so some genuine appearances will stay unconfirmed.
- The same person posting on more than one platform counts once per platform, because accounts on different platforms can't be linked.
- Old Word (.doc) files are read on a best-effort basis; if one reads poorly, save it as .docx.
- **Radio news bulletins and talkback mentions are largely invisible to Medierkat's own searches.** Broadcast monitoring services record the stations themselves; most of those mentions never appear on the web or in social posts. Medierkat finds the ones that leave a trace (station web stories, program and podcast pages, or posts by 3 or more people); the rest come from the user's notes.
- Print-only and paywalled newspaper stories are found only when an online version is indexed.

## Background searches and notifications

- Searches run on the server in the background. You can switch tabs, lock your phone or refresh the page, and the results will be waiting when you return.
- Refreshing doesn't log you out, and your current briefs are restored. Share the app's base address with testers, not the address shown after you log in: that includes your login token.
- Tick "Notify me when a search finishes" in the sidebar to get a chime, a changed tab title and (with your browser's permission) a system notification when results arrive. If email is set up in Secrets (SMTP settings), you can also get an email.

## Access

Access is by invitation. The administrator sets up the accounts; testers receive their login details directly.

## Searching: Google results, read by AI

By default (when `SERPER_API_KEY` is in Secrets) every search pass runs **real Google searches** through [Serper](https://serper.dev), which returns Google's own results as data. Google's official Custom Search API is closed to new customers and shuts for everyone on 1 January 2027, so a results service like this is the way to get "normal Google search" into an app.

- **Time frame:** the sidebar's time frame is sent as Google's own date filter (a custom date range, with Google's preset ranges as a fallback if the range is refused). Dates are checked again when the results are read.
- **What gets searched:** the subject (a name with its qualifiers, e.g. `"Sumeet Walia" RMIT`, not one exact phrase) and its aliases across the four media channels, on Google's web and news results; headlines, outlets and search terms from the user's document; each big story's headline in quotes for republished copies, translated headlines for other-language coverage, and radio and podcast sites; and `site:x.com`, `site:reddit.com` and `site:linkedin.com/posts` searches for people talking about TV and radio appearances. Markat searches Reddit, X, Threads, Facebook, Instagram, LinkedIn, TikTok, YouTube and forums the same way. Media markets choose Google's country setting (Global searches Australia and the US; change with `SERPER_GL`).
- **Long time frames are searched in slices.** A window over about 14 months is split into consecutive date slices (about nine months each, up to five), and each slice gets its own page of Google results, so a single story from the middle of a long window isn't crowded out by years of other coverage. The number of Google searches stays about the same as before. If Google refuses the custom date range, slices are skipped.
- **Wire-site and topic follow-ups.** One query searches the subject on Reuters, AP, Bloomberg, BBC, the Guardian and ABC. After the first results come back, up to three two-word topics that several different sites' headlines share (such as "coffee concrete") are searched together with the subject, which finds a campaign that a name-only search buries.
- **Less for the AI to read.** Results are ranked by how clearly they are about the subject. Once 30 or more results mention the subject or its qualifier, the ones that mention neither are dropped before the AI reads them. The usage line (katadmin) shows slices, searches, results, dropped and read for each pass.
- **Headline visibility** is the average of the subject's three strongest campaigns, with the median and peak shown beside it, so a few major campaigns aren't pulled down by many small ones.
- **What the AI does:** it only reads the result titles, sites, dates and snippets and files them into campaigns. A page that wasn't in the results can't be reported. It doesn't read the full articles, so "what it said" is limited to the snippet.
- **Cost:** about one US cent per 10 Google searches (US$1 per 1,000 at Serper's entry price; 2,500 free on sign-up). A full search runs roughly 40 Google searches, about US$0.04, plus a few cents of AI reading. The usage line shows it.
- **Switching back:** katadmin can choose "AI web search" under *Search source*; searches then use Claude's or Gemini's own web search, as before. Without a Serper key everyone uses AI web search.

## The intelligence engine: Claude, Gemini or both

**Claude is for katadmin only.** Guests always search with Gemini, even when `ANTHROPIC_API_KEY` is in Secrets. katadmin chooses the engine in the sidebar ("AI engine"): **Claude** (the default when its key is in Secrets), **Gemini** or **Both (Claude + Gemini)**. "Both" roughly doubles the cost of a search, so it's for comparing the engines rather than everyday use.

- **Both:** each search pass is run by Claude (Anthropic's web search tool, up to 6 searches per pass, 10 in a Quick search) and by Gemini (Google Search) at the same time. The two sets of notes and sources are merged, and Claude reads them in a single extraction that lists each article and campaign once. Every source still has to appear in the combined search results, as before. If one engine fails, the other carries on and a warning says so.
- **Passes run at the same time.** The channel passes and the X, Reddit and LinkedIn check are searched together; the story follow-ups are searched together once the stories to follow are known. The slow part left is reading each pass's notes, one after another, so earlier finds guide the later ones.
- **Search depth (Medierkat):** **Quick (one pass)** runs one thorough pass over all selected channels. The document's leads, headlines and search terms, and the online items from the user's notes, are searched for in that same pass. It's the default for katadmin. **Full** keeps the two channel passes plus the story follow-ups, and is the default for guests. "Find more" and smart search work in both.
- **Keeping Claude's cost down.** Three things hold the per-search cost at a fraction of what the raw traffic would suggest: the search loop uses prompt caching, so when a long search turn pauses and continues, everything already exchanged is re-read at a tenth of the input price; the mechanical steps (turning search notes into structured campaigns, reading documents and notes, proposing search terms) run on Claude Haiku at a fifth of Sonnet's price, while the searches and the written summary stay on the main model; and Claude alone is the default engine, with "Both" kept for comparing the engines. Set `CLAUDE_FAST_MODEL` in Secrets to change the extraction model; if a key can't use it, the app quietly falls back to the main model.
- **Usage and cost:** after each search katadmin sees tokens (cached ones listed separately), web searches and an estimated cost, with a running total in the sidebar. Claude is priced from published rates (Sonnet 5.5: US$2 in / US$10 out per million tokens, cache reads at a tenth of the input price, plus US$10 per 1,000 searches; Haiku 4.5: US$1 / US$5). Gemini isn't priced unless `GEMINI_INPUT_PRICE` and `GEMINI_OUTPUT_PRICE` (US$ per million tokens) and optionally `GEMINI_SEARCH_PRICE` (US$ per 1,000 searches) are in Secrets. These are estimates: the Claude Console usage page is the record of what was billed.
- **Getting a Claude key:** Claude API access is separate from a Claude Pro or Max subscription. Create a key in the Claude Console (platform.claude.com) under API keys, add credits under Billing, and check web search is on under Settings > Capabilities.

## Running the app

Deployed on Streamlit Community Cloud from this repository. Configuration lives in the app's **Secrets** settings, never in the repository.

| Secret | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key (from the Claude Console). Used for katadmin only |
| `CLAUDE_MODEL` | Optional: Claude model; default `claude-sonnet-5-5`, falling back to `claude-opus-5-5` |
| `GEMINI_API_KEY` | Gemini API key. Required for guests, and used by katadmin for Gemini or Both |
| `GEMINI_MODEL` | Optional: Gemini model name |
| `GEMINI_INPUT_PRICE`, `GEMINI_OUTPUT_PRICE`, `GEMINI_SEARCH_PRICE` | Optional: Gemini prices (US$ per million tokens; per 1,000 searches), so the usage line can estimate Gemini's cost |
| `SERPER_API_KEY` | Serper key (serper.dev) for Google results. When set, everyone's searches use it |
| `SERPER_PRICE_PER_1000`, `SERPER_GL` | Optional: Serper's price per 1,000 searches (default 1.0) and the country codes searched for "Global" (default `au,us`) |
| `CLAUDE_FAST_MODEL` | Optional: the model for mechanical extraction steps; default `claude-haiku-4-5-20251001` |
| `ANTHROPIC_WORKSPACE_ID` | Optional: only needed when the Claude key isn't scoped to a workspace |
| `KATADMIN_PASSWORD_HASH`, `KATGUEST_PASSWORD_HASH` | Keep passwords after the app restarts (the app shows these values when a password is set) |

Locally: `pip install -r requirements.txt`, then `streamlit run app.py`, with secrets in `.streamlit/secrets.toml` (listed in `.gitignore`).

## Repository contents

- `app.py` – the Streamlit application
- `requirements.txt` – Python dependencies
- `.gitignore` – keeps secrets and local data out of the repository
