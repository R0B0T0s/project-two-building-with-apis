# PRD: Movie Rental

*Written 2026-11-09 from the grill-me design session. Technology: Django, Django REST Framework, SQLite, uv, Ruff. External provider: TMDB.*

## Problem Statement

People who want to rent movies have to deal with cluttered storefronts that push upsells and default to sharing their activity. They have no simple, private place to find a movie, mark it for rental, keep track of what they currently have rented and when it's due, and record what they thought of it afterward. When the movie database behind a service is down, their own list often becomes unavailable too. Users who *do* want to share a review, or show a friend what they're watching, have no control over exactly who sees what.

## Solution

Movie Rental is a website and API where signed-in users search TMDB for movies, save them to a personal library in one click, and move each one through a simulated rental: *Want to rent → Rented → Watched*. A rental has a length the user picks (1, 2 or 7 days), a due date and an overdue flag. Users can rate a movie (1–5 stars) and write notes that act as their review.

Everything a user saves is stored locally, so their library keeps working when TMDB is unavailable. Each saved movie is **Private by default**. The user can make it **Public** (anyone, including signed-out visitors, can view it) or **Shared** with specific usernames. Users browse their own **My Library** and a **Community** page of other people's visible items, with search, filters, sorting and pagination that run on local data. The same data and the same privacy rules are available through a REST API.

Employees and admins can view and edit all data for support, and the About page says so openly. The About page also carries the required TMDB attribution.

## User Stories

### Accounts
1. As a visitor, I want to sign up with a username and password, so that I can start a movie library.
2. As a user, I want to log in and log out, so that only I can manage my saved movies.
3. As a user, I want to change my password, so that I can keep my account secure.
4. As a user, I want to edit my first name, last name and email on a My Account page, so that my account information stays current.
5. As a privacy-conscious user, I want the sign-up page to tell me my username is shown publicly, so that I can pick a name that doesn't identify me.

### Finding and saving movies (TMDB)
6. As a user, I want to search TMDB for movies by title from the navbar, so that I can find movies to rent.
7. As a user, I want search results shown as poster cards with title, year and overview, so that I can preview a movie before saving it.
8. As a user, I want to page through TMDB search results, so that I can find movies beyond the first page.
9. As a user, I want to save a movie to my library with one click, so that adding movies is as easy as possible.
10. As a user, I want a newly saved movie to default to *Want to rent* and *Private*, so that nothing I save is public unless I choose.
11. As a user, I want to stay on the search results page after saving and see a confirmation with an "Edit details" link, so that I can save several movies in a row.
12. As a user, I want movies already in my library to show "In your library ✓" in search results instead of a Save button, so that I don't try to save the same movie twice.
13. As a user, I want a clear, friendly message when TMDB is unreachable, slow, rate-limited or failing, so that I know search is temporarily unavailable and that my saved movies still work.
14. As a user, I want a clear message when a save fails because TMDB couldn't be reached, so that I know the movie was not saved and I can try again.

### Library data that survives TMDB outages
15. As a user, I want my saved movies' title, year, overview, poster and genres stored locally, so that my library still displays when TMDB is down.
16. As a user, I want the detail page to show when the movie's information was last updated, so that I know how current it is.

### Renting (simulated) and tracking status
17. As a user, I want to set a saved movie's status to *Want to rent*, *Rented* or *Watched*, so that I can track where each movie stands.
18. As a user, I want to choose a rental length of 1, 2 or 7 days (default 2) when I rent, so that the due date fits how long I need the movie.
19. As a user, I want the rental start and due dates set automatically when I rent, so that I don't have to enter dates and they can't be wrong.
20. As a user, I want to change status freely in any direction, so that I can fix a mistake without being locked in.
21. As a user, I want ending a rental to clear the due date but keep the date I last rented, so that I can see "last rented" history.
22. As a user, I want to re-rent a movie I've already watched by setting it back to *Rented*, so that a new rental period starts without saving the movie again.
23. As a user, I want rentals past their due date clearly labelled *Overdue*, so that I notice them. (A rental due today is not yet overdue.)

### Ratings and reviews
24. As a user, I want to give a saved movie an optional 1–5 whole-star rating at any status, so that I can record my opinion.
25. As a user, I want to write notes about a movie, so that I can keep a reminder or write a review.
26. As a user, I want my notes to follow the item's visibility, so that a Public item's notes act as a public review and a Private item's notes stay private.

### Privacy and sharing
27. As a user, I want each saved movie to be Private by default, so that my activity isn't exposed without my choice.
28. As a user, I want to mark a saved movie Public, so that anyone, including signed-out visitors, can see it.
29. As a user, I want to mark a saved movie Shared and list specific usernames, so that only those people can see it.
30. As a user, I want only myself, employees and admins to be able to edit or delete my saved movies, so that nobody else can change my data.
31. As a user, I want the About page to state plainly that staff can see all data for support, so that I understand who can access my information.

### Browsing My Library
32. As a user, I want a My Library page that shows only my saved movies as a poster grid, so that I can browse what I've saved.
33. As a user, I want to search my library by title and notes, so that I can find a movie by name or by something I wrote.
34. As a user, I want to filter by status, genre, minimum rating ("N★ and up"), visibility and overdue-only, so that I can narrow my list.
35. As a user, I want to sort by date saved (newest first by default), title A–Z, release year or my rating, so that I can order my list the way I need.
36. As a user, I want unrated movies listed last when sorting by rating, so that rated movies are easy to compare.
37. As a user, I want results paginated 12 per page, and to go back to page 1 whenever I change a filter, so that I never land on an empty page.
38. As a user, I want quick Rent and Mark watched actions on each card, so that common status changes take one click.
39. As a user, I want a "No saved movies match these filters" message with a Clear filters link, so that I can recover from an over-narrow search.

### Browsing Community
40. As a user, I want a Community page showing other people's movies I'm allowed to see (Public, or Shared with me), so that I can discover what others are watching and reviewing.
41. As a signed-out visitor, I want to browse Community and see only Public items, so that I can see the site before signing up.
42. As a user, I want Community to have the same search, filters (except visibility), sorting and pagination as My Library, so that browsing feels consistent.
43. As a user, I want to see the owner's username on Community items, so that I know whose review I'm reading and whom to share with.

### Detail and editing
44. As a user who can view an item, I want a detail page showing the poster, overview, genres, status, due date, rating, notes, owner and visibility, so that I can see the full record.
45. As an owner, I want Edit and Delete controls on the detail page, shown only to the owner and staff, so that I can manage my entry.
46. As an owner, I want an edit form for status, rental length, rating, notes, visibility and shared-with usernames, so that I can update everything in one place.
47. As an owner, I want to remove a movie from my library, so that my library only holds what I care about.

### Employees and admins
48. As an employee, I want to view and edit any user's saved movies, including Private ones, so that I can help users and moderate content.
49. As an admin, I want full access to all data, including through the Django admin site, so that I can run the application.
50. As an admin, I want to grant employee status to an account, so that support staff can help users.

### API
51. As an API client, I want to get a token by sending my username and password, so that scripts and tools like curl or Postman can authenticate.
52. As an API client, I want to list my saved entries, so that I can use my library outside the website.
53. As an API client, I want to list Community entries visible to me, so that the API matches the website's Community page.
54. As an API client, I want the same search, filter, sort and pagination parameters as the website, so that results are consistent.
55. As an API client, I want to create a saved entry by sending a TMDB ID (with optional status, rental length, rating, notes, visibility and shared-with), so that I can save movies programmatically.
56. As an API client, I want to update and delete my saved entries, so that I can fully manage my library.
57. As an API client, I want the TMDB ID to be settable only when creating an entry, so that an entry can't be quietly switched to a different movie.
58. As an API client, I want movie details embedded read-only in each entry, so that I get title, year, poster and genres without separate calls and can't alter shared movie data.
59. As an API client, I want a 503 response with a clear message when TMDB is unavailable during a create, so that I can retry later.
60. As a signed-out API caller, I want read-only access to Public entries, so that public data is available, while any write returns 401.
61. As a signed-in user using the browser, I want DRF's browsable API to work with my existing login, so that I can explore the API without a token.

### Maintenance and compliance
62. As the site operator, I want a command that re-fetches movie information older than about five months, so that the site complies with TMDB's six-month caching limit.
63. As the site operator, I want that command to keep existing data when TMDB fails for a movie, so that a refresh never breaks anyone's library.
64. As the site operator, I want that command to delete movies no user has saved, so that the site doesn't keep TMDB data nobody uses.
65. As any visitor, I want an About page with the TMDB logo and the notice "This product uses the TMDB API but is not endorsed or certified by TMDB", linked in every page footer, so that the site meets TMDB's attribution terms.

## Implementation Decisions

### Project structure
- One Django project with its settings package named `config`, created at the repository root so the management entry point sits next to the existing uv project files.
- One main domain app, **rentals**, holds the movie and library models, views, forms, filters, serializers, permissions, the TMDB service module, the management command and tests (tests split into several modules by area).
- One small **accounts** app holds sign-up and My Account. Django's built-in auth views provide login, logout and password change, with their templates in a project-level templates directory alongside the base layout and About page.
- `SECRET_KEY`, `DEBUG` and `TMDB_READ_TOKEN` are read from `.env` with python-dotenv. Ruff is configured in the uv project file.
- The existing console script stays as the original proof of concept. Its request and error-handling logic moves into a TMDB service module inside the rentals app.
- New dependencies: Django, Django REST Framework (including its authtoken app) and django-filter. Dev dependency: responses.

### Models
- **Genre**: a TMDB genre ID and name.
- **Movie** (shared, one row per TMDB film): unique `tmdb_id`, title, release year (nullable, since some movies have no release date), overview, poster path, many-to-many genres, and `fetched_at`. Only the server creates or updates it. Users never edit it.
- **SavedMovie** (per user): foreign keys to the owner and to Movie, with a unique constraint on (owner, movie).
  - Fields: status (*Want to rent / Rented / Watched*, default *Want to rent*), `rented_at` (nullable), `due_at` (nullable), rating (nullable whole number 1–5), notes (text, blank allowed), visibility (*Private / Public / Shared*, default *Private*), `shared_with` (many-to-many to users), and a created timestamp used for "date saved".
- **Rental rules** live in the model or a shared service, so the website and API behave the same:
  - Changing status to *Rented* requires a rental length of 1, 2 or 7 days (default 2) and sets `rented_at` to now and `due_at` to now plus that length.
  - Changing to any other status clears `due_at` and keeps `rented_at`.
  - Any status can change to any other status. Setting *Rented* again starts a fresh rental.
- **Overdue** is calculated rather than stored: status *Rented* and `due_at` before today's date (a rental due today is not overdue). Overdue only labels and filters a rental. It never blocks or penalizes anything.

### Roles and permissions
- Employee = Django `is_staff`. Admin = Django `is_superuser`. ("Staff" below means either.) A single helper decides "is employee or admin", and both website views and API permissions use it.
- **View rule**, written once as a queryset method (`visible_to(user)`) and reused everywhere: the viewer is the owner, OR is staff, OR visibility is Public, OR visibility is Shared and the viewer is in `shared_with`. Signed-out viewers see Public only.
- **Edit/delete rule:** owner or staff only. Others who can view get read-only access.
- Staff can see Private items, including notes. This is disclosed on the About page.
- Employees can also reach the Django admin site because of `is_staff`. Admin permissions on the shared Movie data can be restricted later if needed.
- Usernames are public. Sharing is done by entering usernames.

### Saving flow and TMDB integration
- The TMDB service module wraps all TMDB calls (movie search and movie details), uses the Read Access Token as a Bearer header with a timeout, and turns every failure into one "TMDB unavailable" exception type. The technical cause (timeout, connection error, 401, 429, 5xx, unreadable JSON) is logged on the server.
- Saving sends only a `tmdb_id`.
  - If a Movie with that ID exists and was fetched under six months ago, it is reused.
  - Otherwise the server fetches TMDB's movie details and creates or updates the Movie and its Genres from them.
  - If TMDB fails, nothing is saved and the user sees an error (the website shows a message, the API returns 503).
- The **find page** is a server-rendered GET with a query and a page number.
  - It shows TMDB results as poster cards with TMDB's own Prev/Next pagination.
  - Each card's Save button posts the `tmdb_id` and creates the entry with the defaults (*Want to rent*, *Private*), then returns to the same results with a success message and an "Edit details" link.
  - Results already in the user's library show "In your library ✓" with a link instead of a Save button.
  - The page and saving require login.
- **User-facing TMDB messages:**
  - Unreachable or timeout: "Couldn't reach TMDB right now. Your saved movies still work. Try again in a minute."
  - Bad token, rate limit or server error: a generic "Movie search is temporarily unavailable." The technical detail goes only to the log.

### Browsing: search, filter, sort, pagination
- Every browse feature works on local data only.
- One django-filter filter set is shared by the website and the API:
  - search: case-insensitive match on movie title or notes
  - status
  - genre
  - minimum rating: excludes unrated
  - visibility: My Library only
  - overdue only
- Sorting options: date saved (newest first, the default), title A–Z (plain alphabetical, no article handling), release year, and my rating (unrated last in either direction). A stable tie-breaker keeps page contents consistent.
- 12 results per page. Any change to search, filters or sort returns to page 1, and a page number past the end shows the last page.
- **My Library** (login required): the owner's own entries. **Community**: other users' entries that pass the view rule. Signed-out visitors can access Community and see Public items only. One reusable list view serves both pages and differs only in its starting queryset.
- Search runs only over rows the viewer is allowed to see, so Private notes never match for other users.

### Website pages and UI
- Bootstrap 5 from a CDN, using **layout A**: dark top navbar (brand, My Library, Community, the TMDB search box, username and log out), a filter sidebar card, and a responsive poster card grid (2/3/4 columns).
- Each card shows the title, year, status badge (with an Overdue badge or the due date), stars, and a visibility icon, plus a one-click Rent (2 days) or Mark watched action and an Edit link. Community cards also show the owner's username.
- TMDB failures and other notices use Bootstrap alerts.
- Detail page at `/saved/<id>/`: follows the view rule, and shows Edit/Delete only to the owner and staff.
- The edit page is a plain Bootstrap form with status, rental length, rating, notes, visibility and shared-with usernames. It explains the Private default and staff access.
- A footer on every page links to the About page and includes the TMDB notice. The About page shows the TMDB logo and the attribution text, plus the staff-access statement.
- Forms are rendered by hand with Bootstrap classes (no crispy-forms at first).

### API
- One DRF ModelViewSet for saved entries, registered with a router, under the API prefix.
- **List:** a scope parameter, `mine` (default) or `community`, plus the shared filter set, sorting and pagination (12 per page).
- **Create:** a write-only `tmdb_id` (allowed only on create), plus optional status, write-only `rental_days`, rating, notes, visibility and shared-with usernames. It runs the same save flow and returns 503 with a message if TMDB fails. Saving a movie already in the user's library is rejected with a validation error.
- **Retrieve:** follows the view rule. **Update and partial update:** owner or staff only, and `tmdb_id` can't be changed. **Delete:** owner or staff only.
- Movie details (title, year, overview, poster path, genres, `fetched_at`) are embedded read-only.
- **Authentication:** session (browsable API) plus DRF Token, with a token endpoint that accepts a username and password. Signed-out callers can read Public entries, and writes return 401.

### Cache refresh and cleanup
- A `refresh_movies` management command:
  - re-fetches every Movie whose `fetched_at` is older than about five months, updating the fields and genres
  - on a TMDB failure for a movie, keeps the existing data, logs it and continues
  - deletes Movie rows that have no saved entries
- It is meant to be scheduled in a real deployment and run manually for the class.

### Testing
- Django's built-in test runner (TestCase and DRF's APITestCase). The repo's TDD skill is used during implementation.
- The `responses` library fakes HTTP for tests of the TMDB service module itself: success, 401, 429, 5xx, timeout, connection error and bad JSON.
- `unittest.mock.patch` on the TMDB service module fakes TMDB in view and API tests (success, and the "TMDB unavailable" exception).
- Permission tests cover each row of the view and edit rules (owner, other user, shared-with user, employee, admin, signed-out × Private/Public/Shared × view/edit) on both the website and the API.
- Further tests cover: the rental rules (dates set on rent, due date cleared when a rental ends, re-rent), overdue calculation (including due today), each filter and sort (including unrated ordering), pagination reset, the unique save rule, the read-only TMDB ID, and the refresh command (stale refresh, failure keeps data, orphan cleanup).

## Out of Scope

- Real payments, prices, checkout or order records. Renting is a status only.
- Streaming or playing movies, and trailer embedding (a possible stretch goal later).
- TV shows and other media types (movies only).
- Penalties, blocking or late fees for overdue rentals.
- Separate private-notes and public-review fields, a standalone Review model, or more than one review per movie (two fields is a possible stretch goal).
- Saving the same movie more than once per user, or changing an existing entry to a different movie.
- Secret share links, follower/friend systems or groups for sharing.
- Email verification, password reset by email, or social login.
- A custom user model or role field. A Groups-based employee role was considered and not chosen.
- Live search-as-you-type, a JSON TMDB-search endpoint, a TMDB search proxy in the API, or a read-only movies endpoint.
- Release-year range filtering, and title sorting that ignores leading "The/A/An".
- JWT authentication.
- Automatic scheduling of the refresh command, and production deployment.
- Restricting what employees can do in the Django admin site.

## Further Notes

- **TMDB terms (from prior research):** use is non-commercial only. Attribution with the TMDB logo and the exact notice is required, and cached data may not be kept longer than six months. The refresh command and the "reuse if under six months" check cover the caching rule.
- **Earlier work:** the existing console script already handles a missing token, a rejected token (tested against TMDB's real 401), no connection, display and zero results. Its 429, 5xx, timeout and bad-JSON paths have never been tested, and the `responses` tests close that gap. No successful live search has run yet because no real token is in `.env`, so a real TMDB Read Access Token is needed before manual end-to-end testing.
- **Prototypes:** two throwaway prototypes in the prototypes directory informed these decisions: a search/filter/sort logic playground and a three-layout UI comparison in which layout A was chosen. They are reference material only and must not be promoted into the application.
- **Defaults applied without an explicit answer:** the detail page exists, notes are included in search, there is no year-range filter, a rental due today is not overdue, title sort is plain A–Z, the rental lengths are 1/2/7 days, and the edit page is a plain Bootstrap form.
- Windows consoles can fail to print some characters (★, non-Latin titles). The console script already guards against this, and management command output should do the same.
- **Next step:** break this PRD into tracer-bullet phases with the repo's prd-to-plan skill.
