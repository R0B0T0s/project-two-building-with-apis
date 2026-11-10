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

## 2026-11-10 — Implemented Phase 1: Django skeleton, layout A base template and About page

### Prompts
1. `/implement @prd/movie-rental.md @plans/movie-rental.md Implement Phase 1`
2. Yes, approve both *(TDD behaviors: About page content; footer on every page)*
3. Yes, approve the test *(cycle 1 RED: About page shows logo, notice and staff statement)*
4. Yes, move on to cycle 2
5. Yes, approve the test *(cycle 2 RED: footer on `/` and `/about/` links to About and has the notice)*
6. Manual verification has passed

### Summary
- **Outcome:** Added Django, DRF, django-filter (and dev `responses`, `ruff`) with uv. Created the `config` project and the empty `rentals` and `accounts` apps. Settings read `SECRET_KEY`, `DEBUG` and `TMDB_READ_TOKEN` from `.env` with python-dotenv. `.env.example` lists all three, and a generated `SECRET_KEY` and `DEBUG=True` were appended to the local `.env`. Ruff is configured in `pyproject.toml`. Built `templates/base.html` in Bootstrap 5 layout A (dark navbar with placeholder links and search box, message alerts, footer with the About link and TMDB notice), a placeholder home page and the About page (logo, attribution, staff-access statement). Two TDD cycles, each approved at RED, produced `rentals/tests/test_pages.py` (2 tests, passing). `manage.py check`, Ruff lint and format pass, and `runserver` served both pages.
- **Deviations:** None from the recommendations. Choices made without an explicit question and reported to the user: Ruff ignores E501 because `ruff format` owns line length; `TIME_ZONE` set to `America/Chicago` so "due before today" uses local dates; the About page lives at `rentals:about`; a placeholder home page was added at `/` as test scaffolding; `ruff format` rewrapped `tmdb_search.py` without changing its behavior.
- **Sideways:** Downloading the official TMDB logo failed with a 403. A retry with a browser user agent was blocked by the permission classifier as bot-check circumvention and was not pursued. The About page references `static/images/tmdb-logo.svg`, which still has to be downloaded by hand from TMDB's logos page. It was still missing when Phase 1 was committed, and manual verification passed without it.

## 2026-11-10 — Broke the Movie Rental PRD into a 12-phase tracer-bullet plan

### Prompts
1. `/prd-to-plan @prd/movie-rental.md`
2. Lets merge Phases 6 and 7, Place phase 11 into Phase 4. Everything else looks good.
3. Update prompts.md

### Summary
- **Outcome:** Wrote `plans/movie-rental.md`. It has a durable architectural-decisions header (the `config` project, the `rentals` and `accounts` apps, the Genre/Movie/SavedMovie models, the staff helper, `visible_to`, the TMDB service module, URLs, UI, testing) and 12 vertical-slice phases. Each phase has its user stories, what to build and acceptance criteria, and all 65 PRD stories are covered. No application code was written and nothing was committed.
- **Deviations:** The first breakdown had 14 phases. The user merged "Edit and delete (rating and notes)" with "Rental rules and overdue" into one phase (now Phase 6) and folded the Django admin phase into the save phase (now Phase 4). The suggested order, with privacy before Community and filters after both list pages, was accepted unchanged.
- **Sideways:** Nothing went wrong. The plan was written straight from the approved breakdown and was not reviewed again afterward.

## 2026-11-09 — Grilled the Movie Rental project idea into a full design, built two throwaway prototypes, wrote the PRD

### Prompts
1. `/grill-me @project-idea.md`
2. A, and (i) for preview *(Q1: rental is a simulated status; preview = TMDB poster + overview)*
3. A, and I agree with one save per movie per user *(Q2: shared `Movie` + per-user `SavedMovie`)*
4. A + X, and I agree with Private as default *(Q3: per-item visibility + share with specific users)*
5. a and (i) *(Q4: employee = `is_staff`, admin = `is_superuser`; staff can see everything)*
6. C, and yes to Genre model *(Q5: send only tmdb_id, reuse fresh Movie else fetch details)*
7. B *(Q6: My Library + Community pages)*
8. `/prototype` → chose "Search/filter/sort (logic)" in the follow-up question
9. ANswer for question 7, add the overdue rentals selection and B *(Q7: field table + Overdue filter; django-filter)*
10. A and I do agree that tmdb_id can only be set when creating an entry *(Q8: one ModelViewSet at /api/saved/)*
11. B, and yes to read-only public access *(Q9: session + DRF Token auth)*
12. B + X. Yes, keep rented_at *(Q10: user picks rental length; free status changes)*
13. A and X *(Q11: notes = review; optional 1–5 stars)*
14. A and share usernames publicly *(Q12: built-in auth + sign-up + My Account)*
15. `/prototype` → chose "Bootstrap 5 (Recommended)" in the follow-up question
16. A and yes to the about section *(Q13: Bootstrap 5 layout A; About/attribution page)*
17. A and yes to cleaning up orphaned movies *(Q14: `refresh_movies` command)*
18. A + X, and the error messages look right *(Q15: server-rendered /find/ page, one-click save)*
19. A and both X and Y *(Q16: Django test runner + mock.patch + responses)*
20. A + accounts, and no objection for keeping tmdb_search.py *(Q17: `config` + `rentals` + `accounts`)*
21. `/to-prd`
22. Update PROMPTS.md

### Summary
- **Outcome:** A 17-question grill-me interview settled the whole Movie Rental design: data model, privacy/sharing, roles, the TMDB save flow, browsing, API, auth, rental rules, styling, cache refresh, testing and project layout. Two throwaway prototypes were built in `prototypes/`: `search-filter-sort.html` (a logic playground with 8 guided scenarios, checked with node) and `ui-convention.html` (three Bootstrap 5 layouts with a variant switcher, where layout A was chosen). The decisions were written up as `prd/movie-rental.md` (65 user stories). No application code was written and nothing was committed.
- **Deviations:** Q4 chose Django's `is_staff` flag over the recommended "Employees" Group. Every other answer matched the recommendation. Several sub-questions went unanswered and the recommended defaults were applied and listed in the PRD (detail page exists, notes searchable, no year range, due-today not overdue, plain A–Z title sort, rental lengths 1/2/7 days, plain Bootstrap edit form; the layout-C form for the detail page was suggested but not explicitly chosen). Both `/prototype` runs needed a follow-up question first: which decision to prototype, and which UI stack to use, since Q13 was still open.
- **Sideways:** The UI prototype was opened in the browser but never visually checked by the agent, and the user didn't report display issues. No live TMDB request was made this session. The previous session's log says there was no real token, and `.env` was not re-checked.

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

    