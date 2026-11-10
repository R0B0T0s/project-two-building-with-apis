# Plan: Movie Rental

> Source PRD: `prd/movie-rental.md` (written 2026-11-09)

## Architectural decisions

Durable decisions that apply across all phases:

- **Project**: One Django project whose settings package is `config`, created at the repository root next to `pyproject.toml`. `SECRET_KEY`, `DEBUG` and `TMDB_READ_TOKEN` come from `.env` via python-dotenv. Ruff is configured in `pyproject.toml`. `tmdb_search.py` stays as the original proof of concept.
- **Owning apps**:
  - **rentals** (main domain app): models, views, forms, filters, serializers, permissions, the TMDB service module, the `refresh_movies` management command, and tests split into several modules by area.
  - **accounts** (small app): sign-up and My Account.
  - A project-level `templates/` directory holds the base layout, Django's auth templates (login, logout, password change) and the About page.
- **Models** (all in rentals):
  - `Genre`: TMDB genre ID and name.
  - `Movie`: shared, one row per TMDB film. Unique `tmdb_id`, title, release year (nullable), overview, poster path, many-to-many to `Genre`, `fetched_at`. Only the server creates or updates it.
  - `SavedMovie`: per user. Foreign keys to the owner (Django `User`) and to `Movie`, unique on (owner, movie). Fields: status (*Want to rent / Rented / Watched*, default *Want to rent*), `rented_at` (nullable), `due_at` (nullable), rating (nullable whole number 1–5), notes (blank allowed), visibility (*Private / Public / Shared*, default *Private*), `shared_with` (many-to-many to `User`), and a created timestamp used for "date saved".
  - Overdue is calculated, never stored: status *Rented* and `due_at` before today's date.
  - Rental rules live in the model or a shared service, so the website and the API behave the same.
- **Roles**: employee = `is_staff`, admin = `is_superuser`. "Staff" means either one, decided by a single helper that both website views and API permissions use. No custom user model.
- **Authorization**:
  - View rule: one queryset method, `visible_to(user)`. The viewer can see an entry if they are the owner, OR staff, OR it is Public, OR it is Shared and they are in `shared_with`. Signed-out viewers see Public only.
  - Edit/delete rule: owner or staff only.
- **TMDB**: All calls go through one service module in rentals. It uses a Bearer token with a timeout and raises a single "TMDB unavailable" exception for every failure. The technical cause goes to the server log.
- **URLs**:
  - Website: My Library, Community, find (TMDB search, GET with query and page), saved-entry detail at `/saved/<id>/`, plus its edit and delete pages, About, and accounts (sign-up, login, logout, password change, My Account). URLs are named and app-namespaced.
  - API: a DRF router under an API prefix with one saved-entries viewset, plus a token endpoint.
- **UI**: Bootstrap 5 from a CDN, layout A (dark navbar with the TMDB search box, filter sidebar card, responsive 2/3/4-column poster grid). Forms are rendered by hand with Bootstrap classes. Every page has a footer that links to About and carries the TMDB notice.
- **Testing**: Django's test runner (`TestCase`, DRF `APITestCase`).
  - `responses` fakes HTTP for the TMDB service module's own tests.
  - `unittest.mock.patch` on the service module fakes TMDB in view and API tests.

---

## Phase 1: Project skeleton, base layout and About page

**User stories**: 31, 65

### What to build

Create the Django project (`config`) and the empty rentals and accounts apps. Load settings from `.env`, add Django, DRF, django-filter and the `responses` dev dependency, and configure Ruff. Build the base template in Bootstrap layout A: the dark navbar with placeholder links and the footer with the TMDB notice and the About link. Then build an About page that shows the TMDB logo, the exact attribution text, and a plain statement that employees and admins can see all data for support.

### Acceptance criteria

- [ ] `uv run python manage.py runserver` serves the site using settings read from `.env`; `.env.example` lists `SECRET_KEY`, `DEBUG` and `TMDB_READ_TOKEN`
- [ ] Every page extends the base layout, and its footer links to About and includes "This product uses the TMDB API but is not endorsed or certified by TMDB"
- [ ] The About page shows the TMDB logo, the attribution notice and the staff-access statement
- [ ] Ruff passes with the configuration in `pyproject.toml`
- [ ] Tests confirm the About page renders with the attribution and the staff statement, and that the footer appears on it

---

## Phase 2: Accounts

**User stories**: 1, 2, 3, 4, 5

### What to build

Sign-up with a username and password in the accounts app. The sign-up page warns that usernames are shown publicly. Login, logout and password change use Django's built-in auth views with templates in the project-level directory. A My Account page lets a signed-in user edit their first name, last name and email. The navbar shows the username and a log-out control when signed in, and login and sign-up links when signed out.

### Acceptance criteria

- [ ] A visitor can sign up and is then signed in
- [ ] The sign-up page states that the username is shown publicly
- [ ] Users can log in, log out and change their password
- [ ] My Account requires login, and saving it updates the first name, last name and email
- [ ] The navbar reflects whether the visitor is signed in
- [ ] Tests cover sign-up, login and logout, the login-required redirect for My Account, and the My Account update

---

## Phase 3: TMDB search page

**User stories**: 6, 7, 8, 13

### What to build

Move the console script's request and error-handling logic into the TMDB service module in rentals. It supports movie search and movie details, sends the Read Access Token as a Bearer header with a timeout, and raises one "TMDB unavailable" exception for any failure (the cause is logged). Add the login-required find page, reached from the navbar search box. It is a server-rendered GET with a query and a page number, and shows results as poster cards (title, year, overview) with TMDB's own Prev/Next pagination. On failure it shows a Bootstrap alert:

- "Couldn't reach TMDB right now. Your saved movies still work. Try again in a minute." for an unreachable server or a timeout
- "Movie search is temporarily unavailable." for a bad token, a rate limit or a server error

### Acceptance criteria

- [ ] Searching from the navbar shows poster cards with title, year and overview
- [ ] Prev/Next moves through TMDB result pages
- [ ] The find page requires login
- [ ] An unreachable server or timeout shows the "Couldn't reach TMDB…" message; a 401, 429 or 5xx shows the generic message; the technical detail is logged only
- [ ] Service-module tests built with `responses` cover success, 401, 429, 5xx, timeout, connection error and bad JSON
- [ ] View tests patch the service module to cover success and the "TMDB unavailable" exception

---

## Phase 4: Save a movie in one click, plus Django admin

**User stories**: 9, 10, 11, 12, 14, 15, 27, 49, 50

### What to build

Add the `Genre`, `Movie` and `SavedMovie` models and their migrations. Each search-result card gets a Save button that posts only the `tmdb_id`. The save flow:

- Reuse an existing `Movie` that was fetched less than six months ago.
- Otherwise fetch TMDB's movie details and create or update the `Movie` and its genres.
- Create the `SavedMovie` with the defaults *Want to rent* and *Private*.

After saving, the user goes back to the same results page with a success message and an "Edit details" link. Results already in the user's library show "In your library ✓" with a link instead of a Save button. If TMDB fails during a save, nothing is saved and an error message appears. Saving the same movie twice is prevented.

Register all three models in the Django admin site, so admins have full access and can grant employee status (`is_staff`) through the built-in User admin. Add the shared "is staff" helper here.

### Acceptance criteria

- [ ] Clicking Save creates an entry with status *Want to rent* and visibility *Private*, then returns to the same query and page with a confirmation and an "Edit details" link
- [ ] A `Movie` fetched less than six months ago is reused without calling TMDB; an older or missing one is fetched and its title, year, overview, poster path and genres are stored locally
- [ ] Movies already saved show "In your library ✓" instead of a Save button
- [ ] When TMDB fails during a save, no `Movie` or `SavedMovie` is created and an error message is shown
- [ ] The (owner, movie) unique constraint holds, and a duplicate save does not create a second entry
- [ ] An admin can manage `Genre`, `Movie` and `SavedMovie` in the Django admin and can mark a user as staff
- [ ] Tests cover the save flow (reuse, fetch, TMDB failure, duplicate), the defaults, "In your library ✓", and the staff helper

---

## Phase 5: My Library grid and detail page

**User stories**: 16, 32, 44

### What to build

Add a login-required My Library page that shows only the signed-in user's saved movies as a poster grid in layout A. Each card shows the title, year, status badge and stars, and links to the detail page. Add the `visible_to(user)` queryset method. The detail page at `/saved/<id>/` uses it and shows the poster, overview, genres, status, due date, rating, notes, owner, visibility and when the movie information was last fetched. Everything renders from local data, so the library keeps working while TMDB is down.

### Acceptance criteria

- [ ] My Library requires login and lists only the user's own entries in a 2/3/4-column poster grid
- [ ] The detail page shows every field listed above, including "last updated" (`fetched_at`)
- [ ] The detail page returns 404 to anyone `visible_to` excludes
- [ ] My Library and the detail page render with no TMDB calls
- [ ] Tests cover the library being limited to the owner, the detail fields, and the `visible_to` cases for owner, other user and signed-out viewer on Private entries

---

## Phase 6: Edit, delete and rental rules

**User stories**: 17, 18, 19, 20, 21, 22, 23, 24, 25, 38, 45, 46 (all fields except visibility/shared-with), 47

### What to build

Add an edit page: a plain Bootstrap form with status, rental length (1, 2 or 7 days, default 2), an optional 1–5 rating and notes. Add a delete confirmation that removes the entry from the library. The detail page shows Edit and Delete only to the owner and staff, and only the owner and staff can use those pages.

Put the rental rules in the model or a shared service so the API can reuse them later:

- Changing to *Rented* sets `rented_at` to now and `due_at` to now plus the rental length.
- Changing to any other status clears `due_at` and keeps `rented_at`, which shows as "last rented".
- Any status can change to any other status, and setting *Rented* again starts a fresh rental.

Overdue is calculated: *Rented* with `due_at` before today. A rental due today is not overdue. Cards and the detail page show an Overdue badge or the due date. Each library card gets a one-click Rent (2 days) or Mark watched action and an Edit link.

### Acceptance criteria

- [ ] The owner can edit status, rental length, rating and notes, and can delete the entry
- [ ] Edit and Delete controls appear only for the owner and staff, and other users get 403 or 404 on the edit and delete pages
- [ ] Renting sets `rented_at` and `due_at` from the chosen length; leaving *Rented* clears `due_at` and keeps `rented_at`; re-renting from *Watched* starts a new period
- [ ] Rating accepts only whole numbers 1–5 or empty, at any status
- [ ] Overdue shows only when the due date is before today
- [ ] The card actions Rent (2 days) and Mark watched work in one click and return to the library
- [ ] Tests cover each rental rule, overdue (including due today), rating validation, delete, and the owner-only edit and delete access

---

## Phase 7: Privacy and sharing

**User stories**: 26, 28, 29, 30, 48

### What to build

Add visibility (*Private / Public / Shared*) and a shared-with usernames field to the edit form. Unknown usernames are rejected with a clear error. The form explains the Private default and that staff can see all data. Notes follow the entry's visibility: a Public entry's notes are a public review, and Private notes stay private. Staff can view and edit any entry, including Private ones. Cards and the detail page show a visibility icon.

### Acceptance criteria

- [ ] The owner can set Public, Private, or Shared with a list of existing usernames; an unknown username shows a form error
- [ ] Public entries are viewable by anyone, including signed-out visitors; Shared entries only by listed users, the owner and staff
- [ ] Employees and admins can view and edit any entry
- [ ] The edit page explains the Private default and staff access
- [ ] Permission tests cover the full matrix (owner, other user, shared-with user, employee, admin, signed-out × Private/Public/Shared × view/edit) on the website

---

## Phase 8: Community page

**User stories**: 40, 41, 43

### What to build

Add a Community page that reuses the My Library list view with a different starting queryset: other users' entries that pass `visible_to`. Signed-out visitors can open it and see Public entries only. Community cards show the owner's username and leave out owner-only actions.

### Acceptance criteria

- [ ] A signed-in user sees other users' Public entries and entries shared with them, but not their own and not others' Private ones
- [ ] A signed-out visitor sees Public entries only
- [ ] Cards show the owner's username; Rent, Mark watched and Edit appear only where the viewer can edit (staff)
- [ ] My Library and Community are served by one reusable list view
- [ ] Tests cover Community visibility for a signed-in user, a shared-with user, staff and a signed-out visitor

---

## Phase 9: Search, filter, sort and pagination

**User stories**: 33, 34, 35, 36, 37, 39, 42

### What to build

Add one django-filter filter set, which the API will reuse later:

- search: case-insensitive match on title or notes
- status
- genre
- minimum rating ("N★ and up", excludes unrated)
- visibility (My Library only)
- overdue only

Add sorting by date saved (newest first, the default), title A–Z, release year and my rating. Unrated entries come last in either direction, and a stable tie-breaker keeps pages consistent. Results are paginated 12 per page. Changing search, filters or sort returns to page 1, and a page number past the end shows the last page. The filter sidebar card appears on both list pages. When nothing matches, show "No saved movies match these filters" with a Clear filters link. Search only runs over rows the viewer can see.

### Acceptance criteria

- [ ] Each filter narrows results correctly on My Library, and on Community (except visibility, which isn't offered there)
- [ ] Each sort works; rating sort puts unrated last both ascending and descending; tie-breaking is stable
- [ ] Pages hold 12 results; changing a filter resets to page 1; an out-of-range page shows the last page
- [ ] The empty state shows the message and a Clear filters link
- [ ] Other users' Private notes never match a Community search
- [ ] Tests cover each filter, each sort (including unrated ordering), pagination reset and out-of-range pages, and the search privacy rule

---

## Phase 10: API, read access and authentication

**User stories**: 51, 52, 53, 54, 58, 60, 61

### What to build

Add a DRF ModelViewSet for saved entries, registered with a router under the API prefix. For now it supports list and retrieve.

- Authentication: session (so the browsable API works for signed-in browser users) plus DRF Token, with a token endpoint that accepts a username and password.
- List: takes `scope=mine` (default) or `scope=community`, plus the shared filter set, the same sorting, and 12-per-page pagination.
- Retrieve: follows `visible_to`.
- Each entry embeds the movie's title, year, overview, poster path, genres and `fetched_at`, read-only.
- Signed-out callers can read Public entries.

### Acceptance criteria

- [ ] POSTing a valid username and password to the token endpoint returns a token, and token-authenticated requests work
- [ ] `scope=mine` lists the caller's entries; `scope=community` matches the website's Community results
- [ ] Search, filter, sort and pagination parameters give the same results as the website
- [ ] Movie details are embedded read-only in each entry
- [ ] Signed-out callers can list and retrieve Public entries only
- [ ] The browsable API works with an existing session login
- [ ] API permission tests cover the view side of the matrix (owner, other user, shared-with user, employee, admin, signed-out × Private/Public/Shared)

---

## Phase 11: API write access

**User stories**: 55, 56, 57, 59

### What to build

Let the viewset create, update, partially update and delete entries.

- Create: takes a write-only `tmdb_id`, plus optional status, write-only `rental_days`, rating, notes, visibility and shared-with usernames. It runs the same save flow and rental rules as the website. It returns 503 with a clear message when TMDB is unavailable, and a validation error when the movie is already in the caller's library.
- Update and delete: owner or staff only. `tmdb_id` cannot be changed after creation.
- Writes from signed-out callers return 401.

### Acceptance criteria

- [ ] Creating with a `tmdb_id` (and optional fields) creates an entry using the shared save flow and rental rules
- [ ] A TMDB failure during create returns 503 with a message and saves nothing
- [ ] A duplicate create returns a validation error
- [ ] Owner and staff can update, partially update and delete; other users are refused; signed-out writes return 401
- [ ] Sending `tmdb_id` on update does not change the movie
- [ ] API permission tests cover the edit side of the matrix, and tests cover the 503, duplicate and read-only `tmdb_id` cases

---

## Phase 12: `refresh_movies` management command

**User stories**: 62, 63, 64

### What to build

Add a `refresh_movies` management command that:

- re-fetches every `Movie` whose `fetched_at` is older than about five months and updates its fields and genres
- keeps the existing data when TMDB fails for a movie, logs the failure and moves on to the next one
- deletes `Movie` rows that no `SavedMovie` references

Its console output must not crash on characters a Windows console can't print. It is run by hand for the class.

### Acceptance criteria

- [ ] Stale movies are refreshed, and fresh movies are left untouched without a TMDB call
- [ ] A TMDB failure for one movie leaves its data unchanged, and the remaining movies are still processed
- [ ] Movies with no saved entries are deleted
- [ ] Output with non-Latin titles doesn't crash on a Windows console
- [ ] Tests cover the stale refresh, failure keeping data, and orphan cleanup
