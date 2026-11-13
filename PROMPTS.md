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

## 2026-11-12 — API tour (endpoints, `/api/saved/5/` walkthrough) and `scripts/api_client.py`

### Prompts
1. Show me the API endpoints in my project in table format. Choose a list endpoint and a related detail endpoint for me to open in the browser. Explain any authentication needed and give me the URLs for viewing JSON.
2. Walk me through the api/saved/5 endpoint. Show me the associated model, serializer, and view
3. Create a Python script in the scripts/ directory that consumes my projects API. The script should have two behaviors: 1. Call one list endpoint with query parameters and print the results. 2. Call one update endpoint that updates one field through the API. Print the before and after results.
4. Update PROMPTS.md, also include the scripts run instructions.

### Running the script

Start the dev server first (`uv run python manage.py runserver`), then run these from the repo root:

```
# 1. List (GET /api/saved/) with query parameters. Community works signed out.
uv run python scripts/api_client.py list
uv run python scripts/api_client.py list --scope community --q alien --sort title
uv run python scripts/api_client.py --username tester1 list --scope mine --status rented

# 2. Update one field (PATCH /api/saved/<id>/), printing before and after.
uv run python scripts/api_client.py --username tester1 update 5 --notes "Family movie night pick"
uv run python scripts/api_client.py --username tester1 update 5 --rating 4
```

- **List options:** `--scope mine|community` (default `community`), `--q`, `--status want|rented|watched`, `--genre <TMDB genre ID>`, `--min-rating 1-5`, `--overdue`, `--sort` (one of the `SORT_ORDERINGS` keys, default `title`) and `--page`.
- **Update options:** the entry ID, then exactly one of `--notes "<text>"` or `--rating 1-5`. Only the owner or staff can update an entry; anyone else gets the API's 404.
- **Signing in:** `--scope mine` and `update` need an account. `--username` asks for the password and gets a token from `/api/token/`; `--token <key>` uses an existing token. `API_USERNAME`, `API_PASSWORD`, `API_TOKEN` and `API_BASE_URL` (default `http://127.0.0.1:8000`) work as environment variables too.
- **Windows:** if the ★ ratings fail to print, set `PYTHONIOENCODING=utf-8` first.

### Summary
- **Outcome:**
  - **Prompt 1:** a table of the API endpoints (`/api/`, `/api/saved/` list and create, `/api/saved/<id>/` retrieve, update and delete, `/api/token/`, `/api-auth/`). I picked the community list and Public entry #5 as URLs that work signed out, gave `?format=json` links, and explained Token and Session auth with `IsAuthenticatedOrReadOnly`.
  - **Prompt 2:** a walkthrough of `GET /api/saved/5/`: the router, `ModelViewSet.retrieve` with `get_queryset` using `visible_to` (404, not 403), the `SavedMovie`/`Movie`/`Genre` models, and `SavedMovieSerializer` (nested movie, write-only `tmdb_id`/`rental_days`, `shared_with` dropped for non-editors). It included the real JSON from a signed-out request.
  - **Prompt 3:** `scripts/api_client.py`, a `requests`-based client with `list` and `update` subcommands that talks to the API over HTTP only and imports no project code. Ruff format and check pass. Tested on a dev server on port 8765: the community list returned #7 and #5, signed-out `--scope mine` gave a clear error, the #5 notes update showed before and after, and updating Employee's #1 as tester1 gave a 404.
- **Deviations:** None from the user. Choices of mine:
  - The list defaults to `--scope community` and `--sort title` so it works with no account.
  - The update covers `notes` or `rating` (one field per run).
  - No tests were added for the script; it was checked by hand against a live server.
- **Sideways:**
  - The first printed list URL joined parameters with `, ` instead of `&`; it was fixed after the first test run.
  - The update test changed real dev data. #5's notes were set back to empty afterward, and a DRF token for tester1 was got or created in `db.sqlite3`.
  - My first attempt to stop the test server used PowerShell through Bash, so `$_` was mangled. It was stopped with the PowerShell tool, which triggered a "failed, exit code 127" notification for the killed server, not a real failure.

## 2026-11-12 — Implemented Phase 12: `refresh_movies` management command

### Prompts
1. `/implement @prd/movie-rental.md @plans/movie-rental.md Implement phase 12`
2. I approve *(TDD behaviors: stale movies refresh and fresh ones are untouched; a TMDB failure keeps data and the command continues; movies with no saved entries are deleted)*
3. I approve *(cycle 1 RED: `get_movie_details` called 0 times, since the command was an empty stub)*
4. Move on
5. I approve *(cycle 2 "RED" was an uncaught `TMDBUnavailable` error, not an assertion failure)*
6. Move on
7. I approve *(cycle 3 RED: all three movies remained instead of only the saved one)*
8. Go ahead *(normal implementation: console output with a summary, the Windows-safe output test, Ruff)*
9. Manual verification passed

### Summary
- **Outcome:**
  - **`rentals/management/commands/refresh_movies.py`**:
    - It first deletes movies with no saved entries (`saves__isnull=True`), so TMDB is never called for them. Genre rows are kept.
    - It then re-fetches every movie older than 150 days (`REFRESH_AFTER`, about five months) through `services.store_movie_details`, the save flow's own write path.
    - On `TMDBUnavailable` it logs a warning with the movie's ID, keeps the existing data and continues.
  - **Output:** one line per refreshed or failed movie, plus a summary of counts. Each line is encoded with the console's encoding using `errors="replace"`, so ★ and non-Latin titles print as `?` instead of crashing.
  - **Tests and checks:** `rentals/tests/test_refresh.py` adds 4 tests (the 3 TDD behaviors and a cp1252 output test). 134 tests pass, Ruff and the migration check are clean, and the user passed manual verification.
- **Deviations:** None from the user. Choices of mine:
  - Orphans are deleted before the refresh rather than after.
  - Errors other than `TMDBUnavailable` still stop the command, so real bugs aren't hidden.
- **Sideways:**
  - Cycle 2 couldn't fail on an assertion, because the missing behavior was the exception handling itself. This was explained and approved as RED, as in Phase 11.
  - Cycle 3's first run errored, because the mock returned a `MagicMock` for the stale orphan. Giving it a real return value was a setup fix only, noted before approval.
  - The output test's first expected string had one `?` too many, because I miscounted the Japanese title's characters. Only the expected string was corrected.

## 2026-11-12 — Implemented Phase 11: API write access (create, update, delete, 503, edit rule)

### Prompts
1. `/implement @prd/movie-rental.md @plans/movie-rental.md Implement Phase 11`
2. yes, approved *(TDD behaviors: create runs the shared save flow and rental rules; a TMDB failure on create is a 503 that saves nothing; update and delete follow the edit rule across the matrix)*
3. yes, approved *(cycle 1 RED: POST returned 405, since the viewset was read-only)*
4. Move on
5. Approved *(cycle 2 "RED" was an uncaught `TMDBUnavailable` error, not an assertion failure)*
6. move on
7. Approved *(cycle 3 RED: 3 of 18 cases were `200 != 404`, for viewers who could see but not edit)*
8. GO ahead *(normal implementation: duplicate, missing `tmdb_id`, bad values, usernames, Shared with no usernames, generic 503, update rental rules, ignored `tmdb_id`, PUT)*
9. Manual verification passed

### Summary
- **Outcome:**
  - **`SavedMovieViewSet`** is now a `ModelViewSet`. Update, partial update and delete start from `editable_by`, so a viewer who isn't the owner or staff gets 404. Signed-out writes stay 401 through `IsAuthenticatedOrReadOnly`.
  - **Create** calls `services.save_movie` inside a transaction, applies the optional fields, and calls `change_status` for the rental rule. `perform_create` turns `TMDBUnavailable` into a new `TMDBServiceUnavailable` (503) using the website's wording.
  - **`SavedMovieSerializer`** gains a write-only `tmdb_id` (required on create, dropped on update) and a write-only `rental_days` (1/2/7, default 2). `status`, `rating`, `notes`, `visibility` and `shared_with` become writable, using a `UsernameField` with the edit form's unknown-username message.
  - **Validation:**
    - A duplicate returns 400 before TMDB is called, with an `AlreadySaved` fallback for races.
    - Shared needs at least one username.
  - **Update** follows the edit form's rules: only a real status change starts or ends a rental, and `rental_days` alone moves a current rental's due date.
  - **Tests and checks:** `rentals/tests/test_api_write.py` adds 17 tests. 130 tests pass, Ruff and the migration check are clean, and the user passed manual verification.
- **Deviations:** None from the user. Choices of mine:
  - Viewers who can't edit get 404, not 403, following the project convention.
  - `tmdb_id` on an update is silently ignored rather than rejected.
- **Sideways:**
  - Cycle 2 couldn't fail on an assertion, because the missing behavior was the exception handling itself. This was explained and approved as RED.
  - I first set the unknown-username message by changing the field's error messages in the class body. DRF rebuilds fields for each serializer, so that change would have been lost, and it became a `SlugRelatedField` subclass.
  - A combined shell heredoc failed to parse and nothing ran. The edits were redone with the file tools.
  - A test helper named `patch` hid `unittest.mock.patch` inside the class (`TypeError`), and it was renamed `patch_entry`.

## 2026-11-12 — Implemented Phase 10: API read access and authentication (scopes, view rule, shared filters, tokens)

### Prompts
1. `/implement @prd/movie-rental.md @plans/movie-rental.md Implement phase 10`
2. I approve *(design, including 401 for signed-out `scope=mine` and 400 for an unknown scope; TDD behaviors: `scope=community` matches the website's Community page; retrieve follows `visible_to` across the view matrix; search/filter/sort/page parameters match My Library, including an out-of-range page)*
3. Yes, make it pass *(cycle 1 RED: `scope=community` returned only my own entry)*
4. Move on
5. Yes, make it pass *(cycle 2 RED: 9 of 18 viewer × visibility cases got 404, and 3 signed-out cases crashed on `owner=AnonymousUser`)*
6. Move on
7. Yes, make it pass *(cycle 3 RED: sort, search and min_rating were ignored, and page 99 was a 404)*
8. Go ahead *(normal implementation: scope errors, signed-out reads, tokens, browsable API, embedding, `shared_with` hiding)*
9. Manual verification passed

### Summary
- **Outcome:**
  - **New files:** `rentals/serializers.py`, `rentals/api.py` and `rentals/api_urls.py`. A read-only `SavedMovieViewSet` is mounted at `/api/saved/`. `/api/token/` uses DRF's `obtain_auth_token`, and `/api-auth/` provides the browsable API's login links.
  - **Movie embedding:** each entry embeds the movie read-only (`tmdb_id`, title, year, overview, poster path/url, genres, `fetched_at`). `shared_with` usernames are shown only to the owner and staff, matching the detail page.
  - **Scopes:** list takes `scope=mine` (the default) or `scope=community`. A new `SavedMovie.objects.community_for(user)` method now backs both the website's Community view and the API.
  - **Retrieve** uses `visible_to`, so hidden entries are 404s.
  - **Filtering:** the API reuses `SavedMovieFilter` / `CommunitySavedMovieFilter` through `DjangoFilterBackend`.
  - **Pagination:** `SavedMoviePagination` uses `PAGE_SIZE` and `Paginator.get_page`, so an out-of-range page gives the last page, like the website.
  - **Settings:** `REST_FRAMEWORK` sets Token then Session authentication with `IsAuthenticatedOrReadOnly`.
  - **Tests and checks:** `rentals/tests/test_api.py` adds 16 tests. 113 tests pass, Ruff and the migration check are clean, and the user passed manual verification.
- **Deviations:** None from the user. Two choices of mine the user approved: a signed-out `scope=mine` returns 401, and an unknown scope returns 400. Token authentication is listed before Session so that "not signed in" is a 401 rather than DRF's 403.
- **Sideways:** Cycle 1's first run errored, because pagination wasn't wired yet and `response.data` was a list. Plain 12-per-page pagination was added as scaffolding before the real RED. Cycle 2's RED included 3 `TypeError` crashes for signed-out viewers; these were accepted as real behavior failures, not missing scaffolding. Cycle 3's count assertion was tidied to `paginator.count` before approval. One shell heredoc failed to parse while adding the remaining tests, nothing ran, and the edits were redone with the file tools.

## 2026-11-12 — Implemented Phase 9: search, filter, sort and pagination (shared filter set, 12 per page)

### Prompts
1. `/implement @prd/movie-rental.md @plans/movie-rental.md Implement phase 9`
2. Go ahead *(TDD behaviors: rating sort puts unrated last in both directions with stable ties; Community search never matches other users' Private notes; "overdue only" keeps only rentals due before today)*
3. Go ahead *(cycle 1 RED: the placeholder `sort` filter left the default newest-first order)*
4. Go ahead *(cycle 2 RED: searching Community for "Secret" returned both Alien and Heat)*
5. Continue
6. Go ahead *(cycle 3 RED: "overdue only" returned all four entries)*
7. move on *(normal implementation: remaining sorts, filter/sort/pagination/empty-state tests, Ruff)*
8. Manual verification has passed.

### Summary
- **Outcome:** New `rentals/filters.py` holds one django-filter `SavedMovieFilter`, ready for the API to reuse. It has search (title or notes, any capitalisation), status, genre, minimum rating (excludes unrated), visibility, overdue only, and a `sort` filter with seven options taken from the prototype. Rating and release year put empty values last in both directions, title sort ignores capitalisation, and every sort ends with newest-saved-first as the tie-breaker. `CommunitySavedMovieFilter` drops visibility. The shared `_saved_list` view runs the filter over its starting queryset (still `visible_to` for Community, so search can't reach Private notes) and paginates 12 per page with `Paginator.get_page`, so bad pages show page 1 and pages past the end show the last page. `saved_list.html` gained a filter sidebar card, Prev/Next links that keep the filters, and a "No saved movies match these filters" state with a Clear filters link. The filter form has no page field, so applying filters resets to page 1. `rentals/tests/test_browse.py` adds 10 tests. 97 tests pass, Ruff and the migration check are clean, and the user passed manual verification.
- **Deviations:** None from the user. The PRD lists four sorts; the prototype's seven (newest/oldest for date saved and year, highest/lowest for rating) were used, and title sort ignores capitalisation. Both were called out at manual verification.
- **Sideways:** The first scaffold used `TypedChoiceFilter(empty_label=...)`, which crashed 15 existing tests; it was switched to a `ChoiceFilter`. Cycle 2's Private title "Ran" was renamed "Rashomon" before approval, because a three-letter string could match unrelated page text in `assertNotContains`. The search code adds no privacy check of its own; the privacy comes from narrowing the `visible_to` queryset, which was explained at GREEN. The user's "move on" after cycle 3's RED was taken as approval to continue, so GREEN was reported without a separate stop before the normal implementation.

## 2026-11-12 — Implemented Phase 8: Community page (shared list view, owner on cards, edit-only actions)

### Prompts
1. `/implement @prd/movie-rental.md @plans/movie-rental.md Implement phase 8`
2. I approve *(TDD behaviors: a signed-in user sees others' Public and shared-with-them entries only; signed-out visitors see Public only; cards show the owner and actions only where the viewer can edit)*
3. I approve *(cycle 1 RED: Community, still starting from an empty placeholder queryset, listed nothing)*
4. Yes, go on to cycle 2 *(the signed-out test passed on its first run; no RED)*
5. Yes, go on to cycle 3 *(cycle 3 RED: no `card-owner` line on any card)*
6. I approve
7. Yes, go ahead with those *(normal implementation: navbar link, return to Community after a quick action, Ruff)*
8. Manual verification passed

### Summary
- **Outcome:** My Library and Community are now served by one `_saved_list` view and a shared `saved_list.html` template (renamed from `library.html`). Community starts from `visible_to(user)` minus the viewer's own entries and doesn't require login, so signed-out visitors see Public entries only. Community cards show "by @username". Rent, Mark watched and Edit render only when `can_edit` is true for the viewer, so regular users and signed-out visitors get read-only cards and staff get the actions. One-click actions now send a `next` value checked with `url_has_allowed_host_and_scheme`, so staff return to Community, and an unsafe `next` falls back to My Library. The navbar Community link works and highlights when active, and the home page's "coming soon" note became a "Browse Community" button. `rentals/tests/test_community.py` adds 6 tests. 87 tests pass, Ruff and the migration check are clean, and the user passed manual verification in the browser.
- **Deviations:** None. All recommendations were accepted as proposed. The `next` redirect wasn't in the plan; it was proposed as follow-up work and approved.
- **Sideways:** Cycle 2's test passed on its first run, because cycle 1's code (no `@login_required`, plus `visible_to` for anonymous users) already covered it. This was reported rather than hidden. The test was then shown to catch a mistake by briefly adding `@login_required` to the view (it failed with 302 != 200) and removing it again. Cycle 1's RED came from a deliberate empty placeholder queryset. By the plan's wording, staff see other users' Private entries on Community too, and this was noted at cycle 1.

## 2026-11-12 — Implemented Phase 7: privacy and sharing (visibility, shared-with usernames, permission matrix)

### Prompts
1. `/implement @prd/movie-rental.md @plans/movie-rental.md Implement Phase 7`
2. I approve *(TDD behaviors: sharing with usernames lets exactly those users view; an unknown username is a form error and nothing changes; Shared needs at least one username)*
3. Go ahead *(cycle 1 RED: posting Shared with "alice, bob" left `shared_with` empty)*
4. Move on
5. Go ahead *(cycle 2 RED: "alice, nobody" was accepted and redirected instead of showing an error)*
6. Move on
7. Go ahead *(cycle 3 RED: Shared with " , " was accepted)*
8. Move on *(normal implementation: visibility icons, detail-page share list, permission matrix and display tests)*
9. Manual verification passed

### Summary
- **Outcome:** The edit form gained a visibility radio group (🔒 Private / 🌐 Public / 👥 Shared) and a comma-separated "Shared with" usernames field. Unknown usernames and Shared-with-nobody are rejected with field errors, and an invalid form changes nothing. The edit page now explains the Private default and staff access. Cards and the detail page show a visibility icon, and the detail page lists who an entry is shared with, but only to the owner and staff. `visible_to`, `editable_by` and `can_edit` from Phases 5–6 already covered the access rules, so no model or migration changes were needed. A new `rentals/tests/test_privacy.py` holds the three TDD tests and the full website matrix (owner, other user, shared-with user, employee, admin, signed-out × Private/Public/Shared × view/edit, plus delete). 81 tests pass, Ruff is clean, and the user passed manual verification in the browser.
- **Deviations:** The third TDD behavior ("Shared needs at least one username") was the agent's own addition, not in the plan, and the user approved it. The permission matrix was written as normal tests rather than TDD, since the rules it checks already existed.
- **Sideways:** Adding the required `visibility` field broke 14 Phase 6 tests whose `edit_data()` helper didn't send it. This was a mechanical repair: the helper now defaults to `"visibility": "private"`. The cycle 2 check `assertContains(response, "nobody")` is weak, because the redisplayed input also contains "nobody". The form-errors assertion is the real proof. Ruff reformatted two files after the tests were written.

## 2026-11-10 — Implemented Phase 6: edit, delete, rental rules, overdue and one-click card actions

### Prompts
1. `/implement @prd/movie-rental.md @plans/movie-rental.md Implement Phase 6`
2. I approve *(TDD behaviors: rental rules on rent/leave/re-rent; overdue only when due before today; owner-and-staff-only edit and delete)*
3. Go ahead *(cycle 1 RED: `change_status` sets `rented_at`/`due_at` from the length, clears `due_at` but keeps `rented_at` on leaving Rented, re-rent starts a new 2-day period)*
4. Move on
5. Go ahead *(cycle 2 RED: six overdue cases with "now" frozen at 8 am Nov 10 Chicago time, including due earlier today and due yesterday evening)*
6. Move on
7. Go ahead *(cycle 3 RED: another user gets 404 on edit/delete of a Public entry; owner, employee and admin allowed; signed-out sent to login)*
8. Go ahead *(finish the rest of the phase normally)*
9. Everything but step 3 works.
10. Step 3 works now. Manual verification has passed

### Summary
- **Outcome:** Added the rental rules to `SavedMovie` so the API can reuse them: `change_status()` (Rented starts a fresh rental of 1/2/7 days; any other status clears `due_at` and keeps `rented_at`), `change_rental_length()` (moves the due date of a current rental and keeps its start), `rental_days`, a calculated `is_overdue` (compares local dates, so due today isn't overdue), `can_edit()`, and an `editable_by(user)` queryset (owner or staff). Added `rentals/forms.py` with `SavedMovieForm` (status, rental length, rating as empty or 1–5, notes). It starts a new rental only on an actual status change, so a notes-only edit keeps the due date. New pages: edit at `/saved/<id>/edit/` and delete confirmation at `/saved/<id>/delete/`. One-click POST actions Rent (2 days) and Mark watched (`/saved/<id>/rent/`, `/saved/<id>/watched/`) return to My Library. All four views use `editable_by`, so anyone else gets a 404 and signed-out visitors go to login. The detail page shows Edit/Delete only to the owner and staff, plus an Overdue badge, the due date with its time, and "Last rented". Cards use a shared `rental_badges.html` include (status, "Due Nov 12" or Overdue) and have a footer with the actions and an Edit link, raised above the title's stretched link. Three TDD cycles, each approved at RED, plus normal tests for rating validation at every status, rental-length validation, the chosen length on the edit page, card actions (POST-only, owner-only), the Overdue badge and the detail-page controls. 70 tests pass. Ruff lint and format and `makemigrations --check` are clean.
- **Deviations:** None. Every recommendation was accepted. A 404, not a 403, is used for users who can't edit (the plan allowed either) so Private entries aren't revealed. Visibility and shared-with stay out of the edit form until Phase 7, as planned.
- **Sideways:** Manual verification step 3 failed. Changing the rental length of a movie that was already Rented was silently ignored, because the form only applied the length on a status change, and the length dropdown always showed "2 days". It was reproduced with a scratch Django test-client script, then fixed test-first: a new test failed `2 != 7`, then `change_rental_length()` was added and the form now opens on the current length. That fix broke one earlier test from this phase, whose "notes-only" edit sent a different length than the rental had (a browser never does). The test data was corrected to send the current length. In cycle 3, the test first used the wrong login URL name (`login` instead of `accounts:login`), a mechanical fix noted at RED. The signed-out access test passed before the fix because `@login_required` was already in place, which was disclosed at RED. The first repro attempt was piped into `manage.py shell` and broke on the console's multi-line parsing, so it was rerun with `shell -c exec(...)`. Every `uv run` warned about the unrelated active `django-test` virtualenv (harmless).

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

    