# PROMPTS.md — AI Usage Log

This file is the record of AI use on this codebase. At the end of every
agent session, direct the agent to write the session log with this prompt:

> Append a session log to PROMPTS.md at the repo root, under today's date,
> newest entry at the top. Record every prompt I gave you this session, in
> order, including any corrections. End the entry with a short summary:
> the outcome, any places where I deviated from a recommended answer or
> asked follow-up questions, and anything that went sideways.

Two rules:

- Entries are added only by that prompt, never unprompted.
- New entries go at the top. Never rewrite or delete an old entry — the
  log is part of your work, and an honest log of a session that went
  sideways is worth more than a tidy one.

Each entry has this shape:

    ## YYYY-MM-DD — <one-line summary>

    ### Prompts
    1. ...

    ### Summary
    - **Outcome:** what was built and what was kept
    - **Deviations:** recommendations overridden, follow-up questions asked
    - **Sideways:** failures, wrong turns, and how they were caught

## 2026-11-09 — Researched free media/rental APIs; planned and built a TMDB console search script with uv

### Prompts
1. `/research` Find free external APIs for a Django application where users search for items, save them, and add their own notes, ratings, or progress. Explore topics such as recipes, books, movies, television, games, music, and more. Focus on rental services. Compare promising providers using official documentation, including available data, free limits, signup requirements, etc...
2. `/grill-me` Write a short console script that makes a real request to TMDB, or https://api.themoviedb.org/ ,that can accept user input such as a search phrase, make a request to external API, display results in the console, handle unsuccessfull requests with usefull messages, and uses credentials if the provider needs them. This script is for a future Django project that will use "uv", so when setting up this script please use "uv" to avoid future conflict.
3. a *(project setup: `uv init` at the repo root)*
4. a *(HTTP library: `requests`)*
5. a *(credentials: TMDB Read Access Token as a Bearer header)*
6. a *(token storage: `.env` loaded with `python-dotenv`)*
7. a *(search scope: movies only, `/3/search/movie`)*
8. a *(input: `input()` loop, blank line quits)*
9. a, no objections on how it is displayed. *(errors: specific message per failure; display format accepted)*
10. yes, go ahead and build it
11. Update PROMPTS.md

### Summary
- **Outcome:** A background agent wrote `docs/research/free-media-apis.md` (24 providers across recipes, books/borrowing, games, music, TV, anime, podcasts; top 3: TMDB + Streaming Availability, Open Library, TVmaze), building on the existing `docs/research/free-rental-apis.md` without editing it. A seven-question grill-me interview settled the script design, then the repo root became a uv project (`pyproject.toml`, `uv.lock`, `.venv`) with `requests` and `python-dotenv`, plus `tmdb_search.py` and `.env.example`. Nothing committed.
- **Deviations:** None — every recommended option was chosen. The question "do you already have a TMDB account?" went unanswered, so no real token was available.
- **Sideways:** Testing found that the ★ and non-Latin titles crashed the script with `UnicodeEncodeError` when output was piped on Windows (cp1252); fixed with `sys.stdout.reconfigure(errors="replace")`. A successful search was never run because there's no token; only the missing-token, rejected-token (real 401 from TMDB), no-connection, display and zero-result paths were tested — 429, 5xx, timeout and bad-JSON messages are untested. Research agent couldn't load RAWG, Giant Bomb, Discogs or BoardGameGeek pages and relied on search-engine copies for those. Every `uv run` warned about an unrelated active `django-test` virtualenv (harmless).

    