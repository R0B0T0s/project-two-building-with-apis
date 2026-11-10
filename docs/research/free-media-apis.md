# Free Media APIs for a Search → Save → Notes/Ratings/Progress Django App (Recipes, Books, Games, Music, TV, Anime, Podcasts, and Borrowing)

*Researched 2026-11-09. All sources accessed 2026-11-09. Claims are cited to official provider pages. Anything I could not confirm from an official source is marked **unverified**. This file adds to [free-rental-apis.md](free-rental-apis.md), which already covers TMDB, Streaming Availability, Watchmode, OMDb, Open Library, RentCast, CityBikes, GBFS, Amadeus and Zillow/Bridge. Those providers are only briefly re-checked here; see that file [R] for full details.*

## Summary

- **Overall best fit is still TMDB, plus Streaming Availability for "rent it here" prices** (movies/TV). I re-checked today: TMDB is free for non-commercial use with attribution [S40], and Streaming Availability's free tier is 1,000 requests/month with no payment info, and you may store data as long as you need [S41]. Details are in [R].
- **Best borrowing/lending angle: Open Library.** It needs no key [S11]. Its Read API reports a per-edition `status` of `full access`, `lendable`, `checked out` or `restricted`, plus a borrow link [S13]. That fits a "want to borrow / borrowed / returned" progress field.
- **Library e-book lending (OverDrive/Libby) is not self-serve.** OverDrive's APIs (search, library availability, checkouts, holds) require you to request credentials [S17]. They're not usable for a class project without a library partner.
- **Easiest keyless options:** TVmaze (TV, CC BY-SA, images can be cached indefinitely) [S33], TheMealDB/TheCocktailDB (test key `1`, allowed for educational use) [S1][S3], MusicBrainz plus the Cover Art Archive (music, CC0 core data) [S24][S25][S26], CheapShark (game deals) [S19], and the iTunes Search API (podcasts/music/books, about 20 calls/min) [S39].
- **New restrictions to flag (2025–2026):**
  - **Spotify:** Since 2026-02-11 (new apps) and 2026-03-09 (existing apps), Development Mode apps need the owner to have **Spotify Premium**. They're capped at 5 allowlisted users, and search returns at most 10 results per page. Extended quota has been limited to organizations with ≥250k MAU since 2025-05-15 [S29][S30]. **Avoid.**
  - **BoardGameGeek:** The XML API now requires app registration and a Bearer token (policy dated 2025-07-02, per search-indexed copy of the official page; **unverified** directly because the page returned 403) [S23].
  - **AniList:** Its terms **prohibit use "within competing … anime and manga list or tracker services"**, which is exactly this app's pattern. It's also in a "degraded state" limited to 30 req/min [S35][S36]. **Avoid for this project.**
- **Couldn't verify today:**
  - RAWG returned HTTP 522 again (it was also down in [R]).
  - Giant Bomb, Discogs and BoardGameGeek pages returned 403 to my fetcher.
  - `api.jikan.moe` timed out from my machine (its docs loaded fine).
  - Treat those providers' live status as **unverified**.

---

## Per-provider findings

### Recipes

#### 1. TheMealDB (recipes)

- **Data:**
  - Search with `search.php?s=NAME` or by first letter with `?f=a`.
  - Look up one meal with `lookup.php?i=ID`.
  - Filter by ingredient, category or area with `filter.php?i= / c= / a=`.
  - Get a random meal with `random.php`.
  - IDs are numeric (e.g. `52772`) [S1].
- **Images:** Add `/small`, `/medium` or `/large` to the meal image URL. Ingredient images are at `images/ingredients/{name}-medium.png` [S1].
- **Free limits:** Use test key `1` (in the URL path) "for development and educational use". Free list queries return at most 100 items. No rate limit is stated [S1].
- **Signup / auth:** None for the test key. A paid "supporter" key (a one-off payment via PayPal) is required to release an app publicly on an app store, and it unlocks the v2 endpoints [S1][S2].
- **Terms:** You may copy and modify API content obtained through official endpoints. Scraping isn't allowed. Credit TheMealDB if you use its artwork, and don't resell the API. The terms say nothing explicit about caching [S2].
- **Status:** Active.
- **Stable ID:** `idMeal`, the numeric ID used by `lookup.php?i=` [S1]. (The field name `idMeal` is from the JSON response and isn't spelled out on the docs page, so it's **unverified** from docs.)

#### 2. TheCocktailDB (drinks), a sister site of TheMealDB

- **Data:** The same shape as TheMealDB: `search.php?s=`, `lookup.php?i=` (drink) or `?iid=` (ingredient), `filter.php?i=/a=/c=/g=` and `random.php`. Drink images come in `/small` (200 px), `/medium` (350 px) and `/large` (500 px) [S3].
- **Free limits / auth:** Use test key `1` for development and education. Publishing to an app store requires Premium ($10 one-off). Multi-ingredient filtering and full listings are Premium-only [S3].
- **Stable ID:** Drink ID (e.g. `11007`) [S3].

#### 3. Spoonacular

- **Data:** `GET https://api.spoonacular.com/recipes/complexSearch` takes `query`, `cuisine`, `diet`, `intolerances`, `includeIngredients`, `maxReadyTime`, `number` (1–100) and `offset`. Results include `id`, `title`, `image` and `imageType`. Images are at `https://img.spoonacular.com/recipes/{id}-{w}x{h}.{type}` [S5].
- **Free limits:** **50 points/day**. A search costs about 1 point plus 0.01 per result. When points run out you get HTTP 402 until midnight UTC. The limit is 1 req/s with 2 concurrent requests [S4].
- **Signup / auth:** No card is needed when you sign up directly (RapidAPI requires one) [S4]. Pass the key as the `apiKey` query parameter [S5].
- **Terms:** A **backlink is required** on the free plan. **You may cache data for only 1 hour**, then must delete or refresh it. Delete all data when you stop using the API [S4].
- **Student plan:** $10/month for 5,000 req/day, reviewed manually (up to 72 h) [S4].
- **Fit note:** The 1-hour cache rule means a saved recipe can keep only the ID. Everything else must be refetched on every view, which eats the 50-point/day budget.
- **Stable ID:** `id` (integer).

#### 4. Edamam Recipe Search: no free tier

- The cheapest plan is Basic at **$9/month** (10,000 calls/month, 10/min), with a 10-day trial. Attribution is mandatory. Caching is limited to recipe ID and name on Basic [S6]. Whether the trial needs a card isn't stated (**unverified**). **Exclude.**

### Books and borrowing

#### 5. Open Library: re-checked, plus its lending status

- Re-confirmed today: no key. Anonymous requests get 1 req/s, or 3 req/s if you send a `User-Agent` with your app name and email [S11]. Full search, covers and licensing notes are in [R].
- **Borrowing data:**
  - Adding `fields=availability` to `search.json` pulls archive.org lending availability for the first `ia` item [S12].
  - The **Read API** (`/api/volumes/brief/{isbn|lccn|oclc|olid}/{value}.json`) returns `items[]` with `status` (`full access` / `lendable` / `checked out` / `restricted`), `itemURL` (a read or borrow page), `cover`, `ol-edition-id` and `ol-work-id` [S13].
  - The developer index now lists the Read API as the "Legacy Partner API" [S11], so it may be retired later (**watch**).
  - Actual borrowing happens on archive.org through the user's own account. There is no borrow endpoint (none is listed [S11]).
- **Stable ID:** Work key `OL…W`. Optionally add an edition `OL…M` for the specific copy whose lending status you show.

#### 6. Google Books API

- **Data:** `GET https://www.googleapis.com/books/v1/volumes?q=…` supports `intitle:`, `inauthor:`, `isbn:` and similar keywords. `filter` can be `free-ebooks`, `ebooks`, `full` and so on, and `maxResults` is ≤40. Each result has an `id` (e.g. `_LettPDhwR0C`) and `volumeInfo` (title, authors, pageCount, categories and `imageLinks` thumbnails). `accessInfo` has `viewability`, `epub.isAvailable`/`pdf.isAvailable`, `publicDomain` and `embeddable` [S7][S8].
- **Bookshelves:** Google has its own user shelves (To Read, Reading Now, Have Read). Changing them needs OAuth [S7]. You don't need them, because your Django models hold the user's list.
- **Auth:** An API key (`key=`) is enough for public data [S7].
- **Free limits:** No quota number appears on the docs pages I read. The quota is per Google Cloud project, visible in the Console (**unverified** number).
- **Terms:** The Books-specific terms (last modified 2012) forbid charging users without Google's permission and require removing infringing content on request. The general Google APIs ToS also applies (not reviewed) [S9]. Whether a Google Cloud project needs billing set up for this API is **unverified** (I didn't see it stated).
- **Stable ID:** Volume `id` (string). Store the ISBN too.

#### 7. Gutendex (Project Gutenberg catalog)

- **Data:** `/books?search=…` matches title and author, with filters `languages`, `topic`, `copyright`, `ids` and `sort`. `/books/{id}` returns one book. Fields include `id`, `title`, `authors[]`, `subjects`, `languages`, `formats` (MIME type → URL) and `download_count`. Pages hold up to 32 results [S10].
- **Auth / limits:** No key is mentioned. Rate limits, the operator and the license aren't stated (**unverified**). The docs recommend self-hosting for long-term use (code at `garethbjohnson/gutendex`) [S10].
- **Fit:** Public-domain books are always "borrowable" (free to read), and "page N" progress works well. Whether a cover image is in `formats` isn't documented (**unverified**).
- **Stable ID:** Gutenberg `id` (integer).

#### 8. OverDrive (Libby/Sora library e-book and audiobook lending): approval-gated

- The APIs include Discovery (Search, Metadata, Library Availability), Circulation (Patron Information, Checkouts, Holds) and Reporting. To use them you must "Request API credentials". Libraries can also get access through vendors like BiblioCommons [S17]. No self-serve or free public key is described. **Exclude** for a class project. A "Libby availability" feature isn't possible without a library partner.

#### 9. Internet Archive APIs

- The Metadata read API is `GET https://archive.org/metadata/{identifier}`. It returns `metadata` (title, mediatype, collection) and `files[]`. The example request shows no credentials [S15].
- "Many operations" need no authentication. IA-S3 keys are listed for "uploading, searching, and modifying metadata" [S16], so whether search needs keys is ambiguous (**unverified**).
- There's no lending API on the developer index [S14]. For books, Open Library is the better front door to archive.org lending.
- **Stable ID:** Item `identifier` (string) [S15].

### Video games and board games

#### 10. IGDB (Twitch)

- **Signup:** You need a Twitch account with **two-factor authentication enabled**. Register an app in the Twitch Developer Console as a Confidential client, set the OAuth redirect to `localhost` (unused), and generate a client secret [S18].
- **Auth:** Use the OAuth2 **client-credentials** flow: `POST https://id.twitch.tv/oauth2/token?client_id=…&client_secret=…&grant_type=client_credentials`. It returns a bearer token with `expires_in` (≈64 days in the example). Every request sends `Client-ID` and `Authorization: Bearer …` headers [S18].
- **Data:**
  - Make POST requests to `https://api.igdb.com/v4/games` with an Apicalypse body, e.g. `search "Halo"; fields name,cover.image_id,first_release_date;`.
  - `/v4/search` searches across entity types [S18].
  - Browsers get CORS errors, so call it server-side from Django, which suits this app [S18].
- **Images:** `https://images.igdb.com/igdb/image/upload/t_{size}/{image_id}.jpg`. Sizes include `cover_small` (90×128), `cover_big` (264×374), `screenshot_big`, `720p` and `1080p`. Add `_2x` for retina [S18].
- **Limits:** **4 req/s**, up to 8 open requests, HTTP 429 when exceeded [S18].
- **Terms:** "Free for non-commercial usage under the terms of the Twitch Developer Service Agreement". Commercial use needs a partnership, which asks for user-facing attribution to IGDB.com [S18]. I didn't find the agreement's caching clause (**unverified**).
- **Status:** Active. The docs announce an upcoming migration from enums to tables [S18].
- **Stable ID:** IGDB game `id` (integer).

#### 11. RAWG: unreachable today (**unverified**)

- `rawg.io/apidocs` and `rawg.io/tos_api` returned **HTTP 522** on 2026-11-09, as they did in [R] [S20][S21].
- A search engine's index of those official pages describes a free tier of **20,000 requests/month** with a required backlink. The docs page says non-commercial use only, while the ToS describes free commercial use up to limits. The two **contradict** each other. **All unverified.**
- **Verdict:** Don't build on it until the site is back up and the terms are re-read.

#### 12. CheapShark: PC game deals, the "rent-or-buy price" angle for games

- **Data:**
  - `GET https://www.cheapshark.com/api/1.0/games?title=batman` lists games with the cheapest current deal.
  - `/games?id=612` returns every store deal for one game. `/games?ids=…` looks up a batch of up to 25.
  - `/deals?…` filters deals by store, price and so on. `/stores` returns store names and logos.
  - Prices are in USD and update about hourly [S19].
- **Auth / limits:** **No key**. You must send a descriptive `User-Agent`. Unpublished rate limits return 429 with `Retry-After` [S19].
- **Terms:**
  - Free, as long as you **link users to deals through `https://www.cheapshark.com/redirect?dealID={id}`** and use no affiliate links of your own. Credit is appreciated.
  - The API "is designed to be called directly in response to user input". Building a cached catalog risks a **permanent block** [S19].
- **Fit:** It's good as a "where's it cheapest right now" add-on on a game detail page. It's thin as the primary catalog (no rich metadata).
- **Stable ID:** `gameID`, plus `steamAppID` when present [S19].
- **Game rental services (GameFly etc.):** I found no official public API (**unverified**).

#### 13. Giant Bomb: **unverified**

- The official API page returned 403 [S22]. Old forum posts on giantbomb.com describe the API as non-commercial only, with per-resource hourly limits of about 200/hour, but they're years old. **All unverified.** Exclude.

#### 14. BoardGameGeek XML API2: registration now required

- The official page (403 to my fetcher, so its content comes from search-indexed text) says "Registration and authorization is required for use of the XML API". You register at `boardgamegeek.com/applications` and send `Authorization: Bearer <token>` to `boardgamegeek.com` without `www`. Usage limits are "still being determined". End-user apps should use the developer's own token [S23]. The policy version is dated 2025-07-02 (**unverified** directly).
- The approval time and the license for non-commercial use are **unverified**. It returns XML, not JSON.
- **Stable ID:** BGG thing `id` (integer).

### Music

#### 15. MusicBrainz plus the Cover Art Archive

- **Data:**
  - Search with `/ws/2/<entity>?query=…&limit=&offset=` (entities include release, release-group, artist and recording).
  - Look up by MBID with `/ws/2/<entity>/<mbid>?inc=…` [S24].
- **Images:** The Cover Art Archive serves `/release-group/{mbid}/front-250|500|1200` (it redirects, or returns 404 if there's no art). It has "no rate limiting rules in place" and no auth [S26].
- **Limits / auth:** No key for read-only lookups. Make no more than **1 req/s** and send a proper `User-Agent`, or your IP may be blocked. OAuth is needed only for user data or submissions. Digest auth is deprecated and goes away in August 2027 [S24].
- **Terms:** Core data is **CC0**. Supplementary data is CC BY-NC-SA 3.0. The dataset doesn't include cover art, and the Cover Art Archive's image license isn't stated there (**unverified**) [S25]. Non-commercial use of the web service is free. Commercial use requires a plan [S24].
- **Stable ID:** Release-group MBID (UUID) for "albums". Use a recording MBID for tracks.

#### 16. Discogs: partly verified

- Search-indexed text from the official docs says authenticated requests get **60/min per IP** and unauthenticated ones 25/min, tracked with `X-Discogs-Ratelimit*` headers. Image URLs need at least key/secret auth [S27].
- The docs pages returned 403 to my fetcher, so the endpoint details and the data license are **unverified**.
- **Stable ID:** Release `id` or master `id`.

#### 17. Last.fm

- **Terms that block this app pattern:**
  - Non-commercial only.
  - Total stored data is capped at **100 MB**, and you must cache according to the HTTP headers.
  - You need the "powered by AudioScrobbler" button and links back to Last.fm.
  - **Public pages need Last.fm's prior written approval.**
  - **Images and artwork are excluded from the license** [S28].
- **Verdict:** Weak fit, since there are no usable images.

#### 18. Spotify Web API: heavily restricted

- Since the February 2026 Dev Mode changes (new apps 2026-02-11, existing apps 2026-03-09):
  - The app owner must have **Spotify Premium**.
  - Apps get 5 users and 1 Client ID (raised to 25 in July 2026).
  - Batch `GET /albums`, `/artists` and similar endpoints are removed. Search `limit` drops to a max of 10.
  - Fields like `popularity`, `label` and `followers` are removed [S30].
- Extended quota is for organizations with ≥250k MAU only (since 2025-05-15) [S29].
- **Verdict: avoid** for a student app.

#### 19. Deezer

- The developer terms limit use to **non-commercial** "Webpages and/or Personal Applications" and say Deezer may restrict access at any time. No rate limits are stated in the terms [S31]. The developer FAQ says there's a "query quota" but gives no number [S32].
- Whether public search needs a key, and the quota figure, are **unverified**.

### Television

#### 20. TVmaze

- **Data:**
  - `GET https://api.tvmaze.com/search/shows?q=…` returns fuzzy, ranked results. `/singlesearch/shows?q=` returns a single best match.
  - `/lookup/shows?imdb=…|thetvdb=…` maps external IDs.
  - Shows carry `image.medium` and `image.original` [S33].
- **Auth / limits:** No key for the public API. "At least 20 calls every 10 seconds" per IP, with 429 when exceeded [S33].
- **Terms:** **CC BY-SA 4.0**. The data "can freely be used for any purpose" if you credit TVmaze with a link and follow ShareAlike. API responses are cached 60 min server-side. **Images may be cached indefinitely** [S33].
- **Fit:** "Episode N watched" progress fits well. Episodes come from `/shows/{id}/episodes` (that endpoint wasn't in my extract, so it's **unverified** from today's read).
- **Stable ID:** TVmaze show `id` (integer). Store `externals.imdb` too.
- **Rental note:** TVmaze has no rent/buy data. Pair it with Streaming Availability or Watchmode through the IMDb ID [R].

### Anime and manga

#### 21. Jikan (unofficial MyAnimeList API)

- **Data:** v4 REST API, GET only. Search is `/anime?q=` or `/manga?q=`, detail is `/anime/{id}/full`, plus episodes, characters and more [S34].
- **Limits / auth:** **No key**. 3 req/s, 60 req/min, unlimited per day, but MyAnimeList may rate-limit Jikan upstream. Responses are cached 24 h, with `ETag`/`If-None-Match` support [S34].
- **Terms:** Jikan is "Unofficial" and scrapes MyAnimeList. It isn't affiliated with MAL and can't update a user's MAL list [S34]. Jikan's own terms page wasn't reviewed.
- **Status:** The docs are current (spec 4.0.0), but `api.jikan.moe` timed out from my machine today (**unverified** live).
- **Stable ID:** `mal_id` (MyAnimeList ID).

#### 22. AniList GraphQL: **terms conflict with this app**

- The terms prohibit use "within competing, non-complementary services of the same nature … including … anime and manga list or tracker services", applied to both media and user data. They also ban using the API as a backup or storage service. They're lenient on mass collection for school assignments [S35]. Commercial use is free under $150/month revenue [S35].
- The API is in a "degraded state … limited to 30 requests per minute" (normally 90), and rate-limit raises aren't being accepted [S36].
- **Verdict:** A search→save→progress anime list is a tracker. **Avoid.**

### Podcasts

#### 23. Podcast Index

- **Data:** `GET https://api.podcastindex.org/api/1.0/search/byterm?q=…` searches title, author and owner. There are also `/podcasts/byfeedid`, `/byguid`, `/byitunesid`, and episode endpoints. Fields include feed `id`, `podcastGuid`, `title`, `image`, `artwork` and `episodeCount` [S37].
- **Auth:** **Free key and secret** from api.podcastindex.org. Each request needs `User-Agent`, `X-Auth-Key`, `X-Auth-Date` (Unix time) and `Authorization: sha1(key+secret+date)` [S37]. That's slightly more work than a plain key, but it's three lines of Python (`hashlib.sha1`).
- **Limits:** The ToS reserves the right to set limits. No number is published (**unverified**) [S38].
- **Terms:** ToS v1.1 (2021) says don't "build databases, or otherwise create permanent copies … or keep cached copies longer than permitted by the cache header", and show any required attribution [S38]. The docs are MIT-licensed.
- **Stable ID:** `podcastGuid`, which stays the same across feed moves. Store the Podcast Index feed `id` as well.

#### 24. Apple iTunes Search API (podcasts, music, audiobooks, e-books)

- **Data:**
  - `https://itunes.apple.com/search?term=…&media=podcast&entity=podcast&country=US&limit=…` (up to 200 results).
  - Look up by ID with `lookup?id=…`. ISBN and UPC lookups are also supported.
  - Artwork comes in `artworkUrl60` and `artworkUrl100` [S39].
- **Auth / limits:** **No key**. About **20 calls/min**, subject to change [S39].
- **Terms:** Content is promotional. Show assets near a store badge that links to Apple. Previews need "provided courtesy of iTunes" and must be streamed, not cached [S39].
- **Stable ID:** `collectionId` / `trackId` (integer). For podcasts, `collectionId` is also accepted by Podcast Index `/podcasts/byitunesid` [S37].

### Movies/TV rent-or-buy (already in [R], briefly re-checked)

- **TMDB:** "free to use for non-commercial purposes as long as you attribute TMDB", with the required disclaimer. No credit card is mentioned [S40]. Full details (6-month cache cap, JustWatch credit) are in [R].
- **Streaming Availability:** Free tier is 1,000 req/month as a hard cap with "No payment information required". Commercial use is allowed, attribution is required if shown publicly, and "you can cache any data you retrieved locally as long as you need" [S41]. Rent and buy prices per country are covered in [R].
- **Watchmode:** 2,500 credits/month, "No credit card required", non-commercial with attribution, 3 countries. Its source types include "Rent & buy" [S42]. The 30-day cache rule is covered in [R].

---

## Comparison table

| Provider | Topic | Free limit | Card? | Auth | Cache / storage rule | Attribution | Commercial on free? | Status | Stable ID |
|---|---|---|---|---|---|---|---|---|---|
| **TheMealDB** | Recipes | Test key `1`, 100-item lists [S1] | No | Key in URL path | Copy/modify OK; caching not stated [S2] | Credit artwork [S2] | No app-store release [S1] | Active | `idMeal` |
| **TheCocktailDB** | Drinks | Test key `1` [S3] | No | Key in URL path | Not stated | Not stated | No app-store release [S3] | Active | drink id |
| **Spoonacular** | Recipes | 50 points/day, 1 req/s [S4] | No (direct) [S4] | `apiKey` param [S5] | **≤ 1 hour** [S4] | Backlink [S4] | Not stated | Active | `id` |
| **Edamam** | Recipes | No free tier ($9+) [S6] | Unverified | — | ID + name only (Basic) [S6] | Required [S6] | Paid | Active | — |
| **Open Library** | Books / **lending status** | 1–3 req/s [S11] | No key | None (`User-Agent`) | No new rights asserted [R] | Appreciated [R] | Not restricted [R] | Active (Read API "legacy") | Work `OL…W` (+ edition `OL…M`) |
| **Google Books** | Books / e-book access | Unverified (per project) | Unverified | API key [S7] | Not stated [S9] | Not stated | Can't charge users [S9] | Active | volume `id` + ISBN |
| **Gutendex** | Public-domain books | Not stated | No key | None | Not stated | Not stated | Not stated | Active | Gutenberg `id` |
| **OverDrive** | Library e-book lending | Credential request [S17] | — | Approval | — | — | — | Gated | — |
| **IGDB** | Video games | 4 req/s [S18] | No | Twitch OAuth client-credentials + 2FA [S18] | Unverified | Required if commercial [S18] | No (partnership) [S18] | Active | game `id` |
| **RAWG** | Video games | 20k/month (unverified) | Unverified | Key (unverified) | Unverified | Backlink (unverified) | Conflicting (unverified) | **522 today** | game `id` |
| **CheapShark** | Game deals | Unpublished; 429s [S19] | No key | None (`User-Agent`) | **No catalog building** [S19] | Must use redirect links [S19] | Yes (no own affiliate links) [S19] | Active | `gameID` |
| **BoardGameGeek** | Board games | "Being determined" [S23] | Unverified | Registration + Bearer [S23] | Unverified | Unverified | Unverified | Changed 2025 | thing `id` |
| **MusicBrainz + CAA** | Music | 1 req/s [S24]; CAA none [S26] | No key | None (`User-Agent`) | Core CC0 [S25] | For CC BY-NC-SA parts [S25] | No (needs plan) [S24] | Active | release-group MBID |
| **Discogs** | Music/vinyl | 60/min auth (search-indexed) [S27] | Unverified | Key/secret or token | Unverified | Unverified | Unverified | Active (unverified) | release/master `id` |
| **Last.fm** | Music | Discretionary [S28] | No | API key | ≤100 MB total, follow headers [S28] | Button + links + approval [S28] | No [S28] | Active | MBID / name |
| **Spotify** | Music | Dev mode: 5 users, Premium owner [S30] | Premium sub | OAuth | Not reviewed | Not reviewed | — | **Restricted 2026** | Spotify ID |
| **Deezer** | Music | Unstated quota [S32] | Unverified | Unverified | Not stated [S31] | Trademark rules [S31] | No [S31] | Active | Deezer `id` |
| **TVmaze** | TV | ≥20 calls/10 s [S33] | No key | None | Images cacheable indefinitely [S33] | Link back, CC BY-SA [S33] | "Any purpose" [S33] | Active | show `id` |
| **Jikan** | Anime/manga | 3/s, 60/min [S34] | No key | None | 24 h server cache [S34] | Not stated | Not stated | Docs active; API timed out (unverified) | `mal_id` |
| **AniList** | Anime/manga | 30/min (degraded) [S36] | No | OAuth/none | **No storage-backup use** [S35] | Naming rules [S35] | < $150/month [S35] | Degraded | AniList `id` |
| **Podcast Index** | Podcasts | Unpublished [S38] | No | Key + secret + SHA-1 headers [S37] | Per cache headers [S38] | As required [S38] | Not restricted (unverified) | Active | `podcastGuid` |
| **iTunes Search** | Podcasts/music/books | ~20/min [S39] | No key | None | Previews not cached [S39] | Store badge [S39] | Promotional use [S39] | Active | `collectionId` |
| **TMDB** (+JustWatch) | Movies/TV, where to rent | See [R] | No [S40] | Key/Bearer | ≤ 6 months [R] | Required [S40] | No | Active | `tmdb_id` + type |
| **Streaming Availability** | Rent/buy/stream prices | 1,000/month [S41] | No [S41] | `X-API-Key` | As long as needed [S41] | If public [S41] | Yes [S41] | Active | `imdb_id`/`tmdb_id` |
| **Watchmode** | Rent/buy/stream sources | 2,500 credits/month [S42] | No [S42] | `X-API-Key` | ≤ 30 days [R] | Required [S42] | No [S42] | Active | Watchmode `id` |

---

## Recommendation (ranked)

### Top pick per topic

| Topic | Top pick | Why | Runner-up |
|---|---|---|---|
| Movies (rent/buy) | **TMDB + Streaming Availability** | Free with no card, strong search and posters, stable IDs, and real rent/buy prices with permissive storage [S40][S41][R] | Watchmode (30-day cache) |
| TV | **TVmaze** | No key, CC BY-SA "any purpose", images cacheable forever, episode lists for progress [S33] | TMDB TV |
| Books / borrowing | **Open Library** | No key, stable work keys, and lending status (`lendable` / `checked out`) via the Read API and `availability` [S11][S13] | Google Books (e-book `accessInfo`) |
| Recipes | **TheMealDB** | Test key `1` is meant for educational use, with search, images and numeric IDs, and no caching limit stated [S1][S2] | Spoonacular (1-hour cache, 50 points/day) |
| Video games | **IGDB** | Fully documented, 4 req/s, great cover images, stable IDs. The cost is a one-time Twitch 2FA and OAuth setup [S18] | CheapShark as a "cheapest price" add-on [S19] |
| Board games | *None recommended* | BGG now needs registration and a token, with limits not yet set [S23] | — |
| Music | **MusicBrainz + Cover Art Archive** | No key, CC0 core data, free covers with MBIDs [S24][S25][S26] | Discogs (partly unverified) |
| Anime/manga | **Jikan** | No key, read-only search with images, `mal_id` (but unofficial, and live status unverified today) [S34] | *Not AniList (tracker ban)* |
| Podcasts | **Podcast Index** | Free key, `podcastGuid` is the most stable ID, no promo-only terms [S37][S38] | iTunes Search (keyless, 20/min) |

### Overall top 3 for this Django search → save → notes app

1. **TMDB, with Streaming Availability for rent/buy prices.** It's the strongest "rental" story: users search movies, save them, mark "want to rent → rented → watched", rate them, and see where each one can be rented and for how much. Neither needs a card. Streaming Availability lets you store responses indefinitely, so a per-title cache of rent options is allowed [S40][S41][R].
2. **Open Library.** It's the best "borrowing" story and needs no key. Store the work key, show live `lendable`/`checked out` status from the Read API, and track pages read. Watch the low rate limit (send a `User-Agent`, cache searches) and the "legacy" label on the Read API [S11][S13].
3. **TVmaze.** It's the friendliest terms and setup of anything reviewed: no key, CC BY-SA, images cacheable indefinitely, and episode-level progress. Add rent/buy via Streaming Availability using `externals.imdb` if you want the rental angle [S33][S41]. (**TheMealDB** is a close 4th if the project leans toward recipes, as in "cooked it".)

**Avoid for this project:** AniList (tracker ban), Spotify (Premium, 5-user cap and 2026 endpoint cuts), Last.fm (no images, approval for public pages), Edamam (no free tier), OverDrive (approval-gated), BGG (registration, XML), RAWG and Giant Bomb (unverifiable today).

---

## Sources (all accessed 2026-11-09)

- [R] Companion file: [free-rental-apis.md](free-rental-apis.md) (TMDB, Streaming Availability, Watchmode, OMDb, Open Library, etc.)
- [S1] TheMealDB, API docs: https://www.themealdb.com/api.php
- [S2] TheMealDB, Terms of Use: https://www.themealdb.com/terms_of_use.php
- [S3] TheCocktailDB, API docs: https://www.thecocktaildb.com/api.php
- [S4] Spoonacular, Pricing and FAQ: https://spoonacular.com/food-api/pricing
- [S5] Spoonacular, API docs: https://spoonacular.com/food-api/docs
- [S6] Edamam, Recipe Search API: https://developer.edamam.com/edamam-recipe-api
- [S7] Google Books APIs, Using the API: https://developers.google.com/books/docs/v1/using
- [S8] Google Books APIs, Volumes: list reference: https://developers.google.com/books/docs/v1/reference/volumes/list
- [S9] Google Books APIs, Terms of Service: https://developers.google.com/books/terms
- [S10] Gutendex, API docs: https://gutendex.com/
- [S11] Open Library, Developers / API: https://openlibrary.org/developers/api
- [S12] Open Library, Search API: https://openlibrary.org/dev/docs/api/search
- [S13] Open Library, Read API: https://openlibrary.org/dev/docs/api/read
- [S14] Internet Archive, Developer docs index: https://archive.org/developers/index.html
- [S15] Internet Archive, Item Metadata API (read): https://archive.org/developers/md-read.html
- [S16] Internet Archive, Get your IA credentials: https://archive.org/developers/tutorial-get-ia-credentials.html
- [S17] OverDrive, Developer portal: https://developer.overdrive.com/
- [S18] IGDB, API docs: https://api-docs.igdb.com/
- [S19] CheapShark, API docs (Postman collection behind the page): https://apidocs.cheapshark.com/
- [S20] RAWG, API docs (HTTP 522 on access): https://rawg.io/apidocs
- [S21] RAWG, API Terms (HTTP 522 on access): https://rawg.io/tos_api
- [S22] Giant Bomb, API page (HTTP 403 on access): https://www.giantbomb.com/api/
- [S23] BoardGameGeek, Using the XML API (HTTP 403 on access; content from search index): https://boardgamegeek.com/using_the_xml_api
- [S24] MusicBrainz, API docs: https://musicbrainz.org/doc/MusicBrainz_API
- [S25] MusicBrainz, Data License: https://musicbrainz.org/doc/About/Data_License
- [S26] MusicBrainz, Cover Art Archive API: https://musicbrainz.org/doc/Cover_Art_Archive/API
- [S27] Discogs, API docs (HTTP 403 on access; content from search index): https://www.discogs.com/developers
- [S28] Last.fm, API Terms of Service: https://www.last.fm/api/tos
- [S29] Spotify for Developers, Quota modes: https://developer.spotify.com/documentation/web-api/concepts/quota-modes
- [S30] Spotify for Developers, February 2026 Dev Mode migration guide: https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide
- [S31] Deezer for Developers, Terms of use: https://developers.deezer.com/termsofuse
- [S32] Deezer, FAQs for Developers: https://support.deezer.com/hc/en-gb/articles/360011538897-Deezer-FAQs-For-Developers
- [S33] TVmaze, API docs: https://www.tvmaze.com/api
- [S34] Jikan, REST API v4 docs (https://docs.api.jikan.moe/), OpenAPI spec from the official repo: https://raw.githubusercontent.com/jikan-me/jikan-rest/master/storage/api-docs/api-docs.json
- [S35] AniList API docs, Terms of Use: https://docs.anilist.co/guide/terms-of-use
- [S36] AniList API docs, Rate Limiting: https://docs.anilist.co/guide/rate-limiting
- [S37] Podcast Index, API docs and OpenAPI spec v1.12.1: https://podcastindex-org.github.io/docs-api/ (spec: https://podcastindex-org.github.io/docs-api/pi_api.json)
- [S38] Podcast Index, Terms of Service v1.1: https://github.com/Podcastindex-org/legal/blob/main/TermsOfService.md
- [S39] Apple Performance Partners, iTunes Search API: https://performance-partners.apple.com/search-api
- [S40] TMDB, FAQ: https://developer.themoviedb.org/docs/faq
- [S41] Streaming Availability, Pricing and FAQ: https://www.movieofthenight.com/about/api/pricing
- [S42] Watchmode, API home and pricing: https://api.watchmode.com/
