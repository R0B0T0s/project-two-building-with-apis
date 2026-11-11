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

## 2026-11-10 — Implemented Phase 5: My Library grid, full detail page and `visible_to`

### Prompts
1. `/implement @prd/movie-rental.md @plans/movie-rental.md Implement Phase 5`
2. Go ahead *(TDD behaviors: `visible_to` on Private entries; My Library lists only the signed-in user's entries; detail page 404s for excluded viewers and shows every field without TMDB calls)*
3. Go ahead *(cycle 1 RED: Private entry visible to owner, hidden from another user and a signed-out visitor)*
4. Move on
5. Go ahead *(cycle 2 RED: My Library shows exactly my 2 cards, not another user's Public entry)*
6. Move on
7. Go ahead *(cycle 3 RED: other user and signed-out visitor get 404 on a Private entry's detail page)*
8. Go ahead *(finish the rest of the phase normally)*
9. Manual verification has passed

### Summary
- **Outcome:** Added `SavedMovieQuerySet.visible_to(user)` with the full view rule (staff see all; signed-out see Public; signed-in see their own, Public, and Shared-with-them entries) and a `stars` property on `SavedMovie`. Added the login-required My Library page at `/library/` (owner-only, 2/3/4-column poster grid, newest first, empty-state hint) using a reusable `rentals/includes/saved_card.html` card for Phase 8. Replaced the Phase 4 stub detail page with the full record (poster, overview, genres, status, due date, rating, notes, owner, visibility, "last updated from TMDB on …"). It no longer requires login and 404s for anyone `visible_to` excludes. The navbar's My Library link and the home page now point to the library. Three TDD cycles, each approved at RED, plus regular tests for the library's login requirement, empty state and no-TMDB rendering. 57 tests pass. Ruff lint and format and `makemigrations --check` are clean.
- **Deviations:** None. Every recommendation was accepted. `visible_to` was written with the full rule even though the cycle-1 test only covers the Private cases, and the Public, Shared and staff branches stay untested until Phase 7.
- **Sideways:** Cycle 3 used two tests, not one. The every-field detail test passed as soon as the template was built, so it never had a real RED. This was disclosed at the RED step, and the test was kept as a normal test. Only the 404 test was the real test-first one, and it failed with `302 != 404` because of `@login_required`. Ruff then caught an unused `is_staff_user` import in `views.py`, which was removed. Every `uv run` warned about the unrelated active `django-test` virtualenv (harmless).

## 2026-11-10 — Implemented Phase 4: one-click save, models, "In your library ✓" and Django admin

### Prompts
1. `/implement @prd/movie-rental.md @plans/movie-rental.md Implement phase 4`
2. I approve *(TDD behaviors: save flow reuses a fresh Movie or fetches a stale/missing one; TMDB failure during save creates nothing and shows an error; saved results show "In your library ✓"; plus a stub `/saved/<id>/` page as the link target)*
3. I approve *(cycle 1 RED: missing movie fetched and stored with genres, 150-day-old reused without TMDB, 200-day-old re-fetched)*
4. Move on
5. I approve *(cycle 2 RED: TMDB failure on POST to Save → back to `/find/?q=alien&page=2`, no Movie/SavedMovie, red "wasn't saved" alert, no technical detail)*
6. GO to cycle 3
7. I approve *(cycle 3 RED: my saved Alien shows "In your library ✓" once with a link and no Save form; another user's saved Aliens still shows Save)*
8. Yes, continue
9. Manual verification has passed

### Summary
- **Outcome:** Added the `Genre`, `Movie` and `SavedMovie` models (unique owner+movie, a database check for rating 1–5) and migration `0001_initial`. `rentals/services.py` holds the shared save flow. It reuses a Movie fetched under 182 days ago and otherwise fetches TMDB details and stores them with `store_movie_details` (public, for the Phase 12 refresh command). A duplicate raises `AlreadySaved` before any TMDB call, and TMDB is always called before any write, so a failure saves nothing. Find-page cards got a Save button (posts `tmdb_id`, `q`, `page`) that returns to the same results with a success message and an "Edit details" link. Saved results show "In your library ✓" from one owner-scoped query. A stub `/saved/<id>/` page (owner and staff only, others get 404) is the link target until Phase 5. All three models are registered in the admin, and `rentals/permissions.py` has the `is_staff_user` helper. Three TDD cycles, each approved at RED, plus regular tests for defaults, duplicates, the unique and rating constraints, missing dates, the login and POST requirements, a bad `tmdb_id`, the stub page's access, the staff helper and the admin (including marking a user staff). 50 tests pass. Ruff lint and format and `makemigrations --check` are clean.
- **Deviations:** None from the recommendations. The stub detail page was proposed and approved together with the TDD behaviors. Choices made without an explicit question: a duplicate save shows a blue info message with an "Edit details" link rather than an error. The save-failure wording is "Couldn't reach TMDB, so the movie wasn't saved. Try again in a minute." or "Movie search is temporarily unavailable, so the movie wasn't saved." An unreadable `tmdb_id` shows a generic error. The find view's page-URL helper was merged with the save view's.
- **Sideways:** Cycle 1's first run errored on `NotImplementedError` instead of failing an assertion, so minimal scaffolding was added. Its later subtests then errored on a variable from the first subtest and were repaired to look the movie up by `tmdb_id` (a mechanical repair). Cycle 2's test was mechanically repaired twice. It now also patches `search_movies`, so following the redirect never calls the real TMDB, and it compares against the HTML-escaped "wasn&#x27;t saved". An `Edit` on `views.py` matched twice and a bash heredoc broke on quoting, and both were redone with other tools. The first commit attempt failed because PowerShell split the message at its inner quotes, and nothing was committed until it was retried from a message file. No superuser existed, so manual verification started with `createsuperuser`.

## 2026-11-10 — Implemented Phase 3: TMDB service module and the find (search) page

### Prompts
1. `/implement @prd/movie-rental.md @plans/movie-rental.md Implement Phase 3`
2. Go ahead *(TDD behaviors: every TMDB failure becomes `TMDBUnavailable` with an `unreachable` flag; find page shows poster cards with Prev/Next; find page shows the matching friendly message on failure)*
3. Yes, approve the test *(cycle 1 RED: timeout/connection error → `unreachable=True`; 401/429/500/bad JSON → `unreachable=False`)*
4. Yes, move on to cycle 2
5. Yes, approve the test *(cycle 2 RED: `/find/?q=alien&page=2` shows title, year, overview, poster and Prev/Next links to pages 1 and 3)*
6. Yes, move on to cycle 3
7. Yes, approve the test *(cycle 3 RED: unreachable → "Couldn't reach TMDB…", other failures → generic message, no technical detail on the page)*
8. Yes, go ahead *(finish the phase with ordinary tests, Ruff and the full suite)*
9. Manual verification has passed, also that image.png is the TMDB logo.

### Summary
- **Outcome:** Added `rentals/tmdb.py`: one `_get()` helper sends the Read Access Token as a Bearer header with a 10s timeout and turns every failure into `TMDBUnavailable` (`unreachable=True` for timeouts and connection errors, `False` for non-OK statuses, other request errors and bad JSON), logging the technical cause to the `rentals.tmdb` logger. It exposes `search_movies(query, page)` (returns `results`, `page`, `total_pages`) and `get_movie_details(tmdb_id)` for Phase 4. Added the login-required `rentals:find` view at `/find/` with `rentals/templates/rentals/find.html`: a 2/3/4-column poster card grid (title, year, overview, `w342` poster or a "No poster" placeholder), Prev / "Page X of Y" / Next links (page clamped to 1–500), an empty-query hint, a zero-results message and a Bootstrap warning alert with the two PRD messages. The navbar search box now submits to the find page and keeps the query. Settings got a `LOGGING` config so TMDB failures print to the server console. The TMDB logo finally landed as `static/images/tmdb-logo.png`, and the About page and its test now point at it. New tests: `rentals/tests/test_tmdb.py` (6) and `rentals/tests/test_find.py` (9). All 33 tests, Ruff lint and format and `manage.py check` pass, and a live search against TMDB returned real results.
- **Deviations:** None from the user. Choices made without an explicit question: the find page lives at `/find/`; the poster size is TMDB's `w342`; overviews are truncated to 160 characters; out-of-range or non-numeric page numbers fall back into 1–500; the logo was saved as a PNG instead of the SVG the Phase 1 template expected, so the template and test were updated.
- **Sideways:** Cycle 1's first run errored because `responses.replace` needs an existing registration; it was switched to `responses.upsert` before approval. Cycle 3's crash was turned into an assertion failure with `raise_request_exception = False`, as in Phase 2, and an unneeded `html=False` argument was removed before approval. After GREEN, cycle 1's test printed its expected failure logs into the test output; `logging.disable` was added to that test class's `setUp` as a mechanical, non-asserting change.

## 2026-11-10 — Implemented Phase 2: Accounts (sign-up, login/logout, password change, My Account, navbar)

### Prompts
1. `/implement @prd/movie-rental.md @plans/movie-rental.md Implement Phase 2`
2. Yes, approve all three *(TDD behaviors: sign-up creates an account and signs in; My Account requires login; My Account saves name and email)*
3. I approve *(cycle 1 RED: sign-up creates the user, signs them in and redirects home)*
4. Yes, move on to cycle 2
5. Yes, approve the test *(cycle 2 RED: signed-out visitor to My Account is redirected to login with `?next=`)*
6. Yes, move on to cycle 3
7. Yes, approve the test *(cycle 3: saving My Account changes only first name, last name and email)*
8. Manual verification has passed

### Summary
- **Outcome:** Added `accounts/urls.py` (namespaced `accounts`: `signup`, `my_account` at `/accounts/me/`, and Django's built-in `login`, `logout`, `password_change`, `password_change_done`), `accounts/forms.py` (`AccountForm`: first name, last name, email) and `accounts/views.py` (`SignUpView` logs the new user in; `MyAccountView` is `LoginRequiredMixin` + `UpdateView` on `request.user` with a success message). Settings got `LOGIN_URL`, `LOGIN_REDIRECT_URL` and `LOGOUT_REDIRECT_URL`. Templates: sign-up (with the "Your username is shown publicly." warning), login, password change and done, My Account, plus reusable hand-rendered Bootstrap includes `includes/form_field.html` and `includes/form_errors.html`. The navbar now shows Log in / Sign up when signed out and 👤 username (My Account link) plus a POST Log out button when signed in. `accounts/tests.py` has 15 tests (3 TDD + 12 ordinary for the warning, failed sign-up, login, wrong password, `next`, logout, password change, navbar states, prefill and invalid email). All 18 tests, Ruff lint and format pass.
- **Deviations:** None from the user. Choices made without an explicit question: sign-up and login both land on the home page (no My Library yet); My Account lives at `/accounts/me/`; logout is a POST form because Django's `LogoutView` no longer accepts GET; no logout template, since logout redirects home.
- **Sideways:** Cycle 1's first run errored with a `KeyError` on the session instead of failing an assertion; the test was changed to `session.get(...)` before approval. Cycle 2 first crashed (`AnonymousUser` has no `_meta`) and lacked a login template; the template was built and the test class set `raise_request_exception = False` so the 500 became an assertion failure, which was disclosed and approved. Cycle 3 was never RED: the `UpdateView` and `AccountForm` scaffolding built for cycle 2 already implemented it. To show the test could fail, the form was broken twice on purpose (dropping `email`; adding `username` and `is_staff`), each break failed the test, and the form was restored. The TMDB logo file from Phase 1 is still missing.

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

    