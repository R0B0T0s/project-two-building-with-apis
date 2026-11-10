# Free "Rental" APIs for a Search → Save → Notes/Ratings/Progress Django App

*Researched 2026-11-09. All sources accessed 2026-11-09. Claims are cited to official provider pages. Anything I could not confirm from an official source is marked **unverified**.*

## Summary

- **Best overall fit: TMDB** (movies and TV, with "where to rent or stream" data supplied by JustWatch). It's free for non-commercial use, offers a rich search, item detail and image API, and gives every title a stable integer ID. Two catches: you must attribute TMDB, and you may not cache TMDB data for more than 6 months. Store the TMDB ID and the user's own data, and treat any copied metadata as a cache you refresh.
- **Best "rental availability" add-on: Streaming Availability API** (Movie of the Night). It shows rent, buy and subscription options per country. The free tier is 1,000 requests/month with no card, it allows local storage for as long as you need, and it accepts IMDb or TMDB IDs, so it pairs well with TMDB. **Watchmode** is similar but smaller (2,500 credits/month) and has a 30-day cache limit on the free plan.
- **Best non-movie option: Open Library** (book "rentals", meaning library lending). It needs no key, covers are free, and work keys like `OL27448W` are stable. Its rate limits are low (1–3 req/s), so identify your app with a `User-Agent` header.
- **Housing rentals: RentCast** is the only realistic free, self-serve option for long-term rental listings. It allows only **50 requests/month** free and charges overage fees, so it's risky for a class project. Zillow/Bridge requires approval. **Avoid** both as a primary API.
- **Car rentals: Amadeus Self-Service is gone.** Its GitHub org was archived and marked deprecated on 2026-07-17. Don't use it.
- **Bike share (CityBikes / GBFS):** free and keyless, but it returns live station status, not items people save and rate. It's a weak fit for this pattern.

---

## Per-provider findings

### 1. TMDB (The Movie Database): movies and TV, plus where-to-watch, rent or buy

- **Data:** Search endpoint `GET https://api.themoviedb.org/3/search/movie` takes `query`, `year`, `primary_release_year`, `region`, `include_adult`, `language` and `page`. Each result includes `id` (integer), `title`, `original_title`, `overview`, `release_date`, `poster_path`, `backdrop_path`, `genre_ids`, `vote_average`, `vote_count` and `popularity` [S1]. Watch providers per title: `GET /3/movie/{movie_id}/watch/providers` [S2], plus a provider list at `/3/watch/providers/movie` [S3].
- **Images:** URL = base + size + `poster_path`, e.g. `https://image.tmdb.org/t/p/w500/<path>.jpg`. The base URL and sizes come from `/configuration` [S4].
- **Free tier / limits:** "free to use for non-commercial purposes as long as you attribute TMDB" [S5]. Rate limit is "somewhere in the 40 requests per second range". The old 40-per-10-seconds limit was disabled in 2019. On HTTP 429, back off [S6].
- **Signup:** Request an API key from your account settings ("API" link) [S5]. No credit card is required for non-commercial use (the FAQ only mentions paid licensing for commercial use) [S5].
- **Auth:** v3 accepts either an `api_key` query parameter or a Bearer "API Read Access Token" in the `Authorization` header [S7].
- **Terms that matter:**
  - Attribution is a license condition. Use the TMDB logo (less prominent than your own branding) and the notice "This product uses the TMDB API but is not endorsed or certified by TMDB", ideally on an About/Credits page [S5][S8 §1.B, §3].
  - **Caching:** you must not "Cache, for longer than 6 months, any information obtained through or from TMDB" [S8 §1.C]. On termination you must purge all cached TMDB content [S8 §1.D].
  - No commercial use without a separate written agreement. TMDB decides at its sole discretion what counts as commercial [S8 §2.A]. No ML/AI training use [S8 §1.C].
  - **Watch-provider data:** "In order to use this data you must attribute the source of the data as JustWatch" [S2].
  - The terms don't explicitly say whether storing bare TMDB IDs is allowed (**unverified**). The common practice is to store the ID plus your own user data and refetch or refresh metadata.
- **Status:** Active. Docs are live at developer.themoviedb.org [S1].
- **Python friendliness:** Plain JSON REST, so `requests` works fine. There's no official Python SDK (none is mentioned in the official docs; third-party wrappers exist but are **unverified**).
- **Stable ID to store:** `tmdb_id` (integer) plus `media_type` (`movie` or `tv`), because movie and TV IDs are separate namespaces (the separate `/movie/` and `/tv/` paths are shown in [S2][S3]).

### 2. Streaming Availability API (Movie of the Night): rent, buy and stream options per country

- **Data:** Covers 65 countries, 2,304 streaming catalogs and 200k+ titles. Each title has streaming options with deep links, price, quality, audio/subtitles, expiry date and type (rent, buy, subscription, free), plus title, overview, genres, cast, rating, seasons, episodes and IMDb/TMDB IDs. There are four image types in five sizes on a CDN [S9].
- **Endpoints:** The base URL is `https://api.movieofthenight.com/v4`. `GET /shows/{id}` returns one title. `GET /shows/search/title` requires `title` and `country`, returns up to 20 results and has no paging. `GET /shows/search/filters` requires `country` and uses cursor paging. `/shows/{id}` accepts an IMDb ID (`tt0120338`) or a TMDB ID (`movie/<id>`, `tv/<id>`). Key fields are `streamingOptions` (keyed by country), `imageSet` and `showType` [S10].
- **Free tier:** **1,000 requests/month**, $0, "No payment information required". The quota is a hard limit with no overage fees. Paid plans: Starter $49 (25k), Growth $99 (100k), Scale $299 (1M) [S11].
- **Signup and auth:** Sign up at the developer portal (developers.movieofthenight.com) and get a key from the console. Send it in the `X-API-Key` header. The API is also sold on RapidAPI (`streaming-availability.p.rapidapi.com`, header `X-RapidAPI-Key`) [S10][S12].
- **Terms:** Commercial use is allowed on all plans, including free. Attribution is required if the data (including images) is shown publicly. **You may store retrieved data locally for as long as needed** [S11]. I couldn't find a standalone terms page (the URL I tried returned 404), so these terms come from the official pricing FAQ.
- **Status:** Active. v4 docs are live [S10].
- **Python:** JSON REST. Official clients exist for Go and TypeScript/JS only. For Python, the docs suggest generating a client from the OpenAPI spec [S13], or you can just use `requests`.
- **Stable ID to store:** Store `imdb_id` and/or `tmdb_id`. The API returns both [S9], and `/shows/{id}` accepts both [S10]. Whether its own internal `id` is stable is **unverified**.

### 3. Watchmode: streaming, rental and purchase sources

- **Data:** OpenAPI spec v1.10.1, base URL `https://api.watchmode.com/v1` [S14]. Relevant endpoints:
  - `/search` with `search_field` and `search_value`, which matches by name, IMDb ID or TMDB ID
  - `/autocomplete-search`, which returns thumbnails
  - `/title/{id}/details`, which returns metadata, ratings, artwork and similar titles, and supports `append_to_response`
  - `/title/{id}/sources`, which lists subscription, **rental**, purchase and free options per region
  - seasons, episodes and cast endpoints [S14]

  There are also daily ID-map CSVs that map Watchmode IDs to IMDb and TMDB IDs [S14][S15].
- **Free tier:** **2,500 credits/month**, no credit card, sources for up to 3 countries [S15]. Most calls cost 1 credit. Title calls made with an IMDb or TMDB ID cost +1 credit (for ID resolution), and each `append_to_response` item costs +1 [S14]. Rate limits vary by plan and are reported in the `X-RateLimit-*` headers, but the exact free-plan per-minute number isn't stated (**unverified**) [S14]. Paid plans start at $349/month [S15].
- **Auth:** `X-API-Key` header (recommended), `Authorization: Bearer`, or the legacy `apiKey` query parameter [S14].
- **Terms:** The free plan is "Non-commercial use, with attribution" [S15]. On the free plan you "may cache non-image data for up to 30 days", then you must refresh or delete it. You must delete all stored data when your account ends. You may not resell or share the data with third parties [S16]. Images may be third-party URLs with no license granted [S14].
- **Status:** Active. The spec is current [S14].
- **Python:** JSON REST. The docs show Python code samples, but there's no official Python SDK (the docs list a "TypeScript SDK" sample language) [S14].
- **Stable ID:** The Watchmode `id` (integer), which is "universally unique across titles and people" [S14]. Store the `imdb_id` and `tmdb_id` alongside it.

### 4. OMDb API: movie and TV metadata keyed by IMDb ID

- **Data:** Search by title with `s=` (plus `type`, `y` and `page` 1–100), or look up a single title with `i=` (IMDb ID) or `t=` (title), plus `plot=short|full`. JSON is the default format [S17]. The page doesn't fully list response fields. Posters via `img.omdbapi.com` are **patrons only** [S17].
- **Free tier:** "FREE! (1,000 daily limit)". Signup is by email, and the key arrives by email [S18].
- **Auth:** API key as a query parameter (`apikey`) [S17].
- **Terms:** The site content is licensed CC BY-NC 4.0 [S18]. The general legal terms limit use to "personal use" and forbid "any commercial endeavors". They don't mention caching specifically [S19]. The terms read as written for the website rather than the API, so how they apply to API use is **unverified** [S19].
- **Status:** Active (key signup page live) [S18].
- **Python:** Simple JSON GET. No SDK.
- **Stable ID:** `imdbID` (e.g. `tt1285016`) [S17].
- **Fit note:** It has no rental or availability data and no free posters, so it's weaker than TMDB.

### 5. Open Library (Internet Archive): books and library lending

- **Data:** Search API at `https://openlibrary.org/search.json` takes `q`, `title`, `author`, `fields`, `sort`, `lang` and `page`/`limit`. Results include `key` (e.g. `OL27448W`), `title`, `author_name`, `cover_i`, `first_publish_year`, `edition_count` and `ia`. `fields=availability` returns archive.org lending availability [S20]. There are also Works/Editions, Authors, Subjects, Lists and **"Your Books"** (reading log) APIs [S21].
- **Images:** `https://covers.openlibrary.org/b/{key}/{value}-{S|M|L}.jpg`, where the key can be ISBN, OCLC, LCCN, OLID or ID. Add `?default=false` to get a 404 instead of a blank image. Lookups by ISBN, OCLC or LCCN are limited to 100 requests/IP per 5 minutes; lookups by cover ID or OLID aren't limited this way. Hotlinking covers into public pages is the intended use [S22].
- **Free tier / limits:** No API key is mentioned. Anonymous requests get 1 req/s. Requests that send a `User-Agent` with your app name and contact email get 3 req/s. Don't bulk-download (use the monthly dumps instead) [S21].
- **Signup:** None required. There's an optional use-case registration form [S21].
- **Terms:** The Internet Archive "does not assert any new copyright or other proprietary rights" over the database [S23]. A link back is "appreciated but not required" for covers [S22].
- **Status:** Active [S21].
- **Python:** JSON REST. The search schema is "not guaranteed to be stable", though common fields are safe [S20]. No SDK is mentioned.
- **Stable ID:** The work key (`/works/OL…W`), with an edition key (`OL…M`) or ISBN if you track a specific copy. Users' reading progress maps naturally to a work.

### 6. RentCast: US long-term rental listings and rent estimates

- **Data:**
  - `GET https://api.rentcast.io/v1/listings/rental/long-term`, filtered by `city`, `state`, `zipCode`, `address`, lat/long/`radius`, `bedrooms`, `bathrooms`, `propertyType`, `price`, `status` and `daysOld`, with `limit` (≤500) and `offset` [S24]. Fields include `id`, `formattedAddress`, `price`, `status`, `listedDate`, `daysOnMarket`, `bedrooms`, `bathrooms`, `squareFootage`, `listingAgent` and `history`. **No photos** appear in the spec [S24].
  - Other endpoints: property records, a single rental listing by ID, rent estimate (AVM) and market statistics [S25].
- **Free tier:** "Developer" plan, $0, **50 requests/month**, then **$0.20 per request** in overage fees [S26]. Billing docs say an active subscription is required to activate keys, and the first-month charge doesn't apply to the Developer plan [S27]. Whether a card is required for the free plan is **unverified**, because neither official page says so.
- **Rate limit:** 20 req/s [S25].
- **Auth:** `X-Api-Key` header [S28].
- **Terms:** No attribution required [S26][S29 §3.4]. You may store data internally and may "display, resell and distribute" it [S29 §1]. Access requires an "active, recurring, auto-renewing subscription", and charges are non-refundable [S29 §13].
- **Status:** Active.
- **Stable ID:** Listing `id` is an address-derived string (e.g. `2005-Arborside-Dr,-Austin,-TX-78754`) [S24]. Listings go `Inactive` over time, so snapshot the key fields you display.
- **Fit note:** 50 calls/month runs out after a few demo sessions, and overages cost money. Only use it with aggressive caching and a hard call cap in your code.

### 7. CityBikes API: bike-share networks and stations

- **Data:** `GET /v2/networks` returns every network's `id`, `name`, `company`, `location` and `href`. `GET /v2/networks/{id}` returns that network's stations with `id`, `name`, `free_bikes`, `empty_slots`, lat/long and `timestamp`. A `?fields=` filter is supported [S30].
- **Free tier / auth:** "CityBikes is a free service". No key is mentioned. Rate limits aren't documented (**unverified**) [S30].
- **Terms:** Attribution is required: "indicate it on your app and website, linking the project page". The project also says "this is not exactly open data" [S30]. No license is named.
- **Python:** JSON REST. Data is scraped via the PyBikes library [S30].
- **Stable ID:** `network.id` plus `station.id`.
- **Fit note:** You'd be saving "favorite stations". Notes and ratings work, but "progress" doesn't really fit.

### 8. GBFS (General Bikeshare Feed Specification) feeds

- **Data:** The open standard for shared-mobility availability. The current version is v3.1 (released 2026-11-04). A catalog of public feeds lives in `systems.csv` (which it admits is incomplete) [S31]. Each system has its own `gbfs.json` auto-discovery file. Auth varies by feed: type 0 is none, type 1 is a key in the URL, type 2 is a header [S31]. Licenses are set per dataset [S31].
- **Fit note:** Like CityBikes, but you'd have to deal with each feed separately. Not recommended over CityBikes for this project.

### 9. Amadeus Self-Service (car rental and transfers): discontinued

- The official `amadeus4dev` GitHub org reads "[DEPRECATED]" and was "marked as archived by an administrator on Jul 17, 2026" [S32]. Amadeus's official statement says only that its "Enterprise Portal and Enterprise APIs remain fully available" [S33].
- Reports that self-service keys were disabled and the token endpoint returns 410 come only from third-party GitHub issues and news (**unverified** from official sources).
- **Verdict:** Not usable for a student project. Enterprise access is contract-based.

### 10. Zillow / Bridge Interactive (housing): not self-serve

- The official Bridge pages returned 403 to my fetcher, so nothing here is verified from Bridge or Zillow directly.
- Secondary sources say access is approved per dataset, generally needs an MLS, IDX or partner relationship, and is not granted to products behind a login or paywall. They also say Zillow's original public API shut down in 2021 (**all unverified**).
- **Verdict:** Exclude.

### Not verified (excluded from ranking)

- **RAWG (video games):** rawg.io and api.rawg.io returned HTTP 522 on every attempt on 2026-11-09, so its limits and terms are **unverified**.
- **HUD Fair Market Rents API:** the official page didn't render for my fetcher (**unverified**). It's aggregate rent data by area, not item listings, so it's a poor fit anyway.
- **Library of Congress loc.gov JSON API:** "accessible to the public with no API key". Requests that exceed what it can handle are blocked. Paging past 100,000 results isn't supported [S34]. The detailed endpoints and terms weren't reviewed. It's usable, but less "rental"-shaped than Open Library.

---

## Comparison table

| Provider | Domain | Free limit | Card? | Auth | Cache / storage rule | Attribution | Commercial on free? | Status | Stable ID to store |
|---|---|---|---|---|---|---|---|---|---|
| **TMDB** | Movies/TV + JustWatch providers | ~40 req/s, no monthly cap stated [S6] | No [S5] | `api_key` param or Bearer [S7] | ≤ 6 months [S8] | Logo + disclaimer; "JustWatch" for providers [S2][S8] | No [S8] | Active | `tmdb_id` + `media_type` |
| **Streaming Availability** | Rent/buy/stream by country | 1,000 req/month, hard cap [S11] | No [S11] | `X-API-Key` [S12] | Store as long as needed [S11] | Required if public [S11] | Yes [S11] | Active | `imdb_id` / `tmdb_id` |
| **Watchmode** | Rent/buy/stream sources | 2,500 credits/month, 3 countries [S15] | No [S15] | `X-API-Key` [S14] | Free: ≤ 30 days (non-image) [S16] | Required on free [S15] | No [S15] | Active | Watchmode `id` (+ imdb/tmdb) |
| **OMDb** | Movies/TV metadata | 1,000/day [S18] | No (email) [S18] | `apikey` param | Not stated | Keep notices [S19] | No (personal use) [S19] | Active | `imdbID` |
| **Open Library** | Books / lending | 1 req/s (3 with User-Agent) [S21] | No key [S21] | None | No new rights asserted [S23] | Appreciated [S22] | Not restricted (per [S23]) | Active | Work key `OL…W` |
| **RentCast** | US rental listings | 50 req/month, then $0.20 each [S26] | Unverified | `X-Api-Key` [S28] | Internal storage OK [S29] | None [S29] | Yes [S29] | Active | Listing `id` (address string) |
| **CityBikes** | Bike-share stations | Not stated | No key | None | Not stated | Required link [S30] | Not stated | Active | `network.id` + `station.id` |
| **GBFS feeds** | Bike/scooter share | Varies by feed | Varies | Varies [S31] | Per-dataset license [S31] | Per feed | Per feed | Active (v3.1) | `system_id` + `station_id` |
| **Amadeus Self-Service** | Car rental/transfers | — | — | — | — | — | — | **Deprecated 2026-07-17** [S32] | — |
| **Zillow / Bridge** | Housing | Approval-gated (unverified) | — | — | — | — | — | Not self-serve | — |

---

## Recommendation (ranked)

**1. TMDB as the core catalog, optionally with Streaming Availability for "where can I rent this?"**

- **Search:** `/3/search/movie` (and the TV search), with posters straight from `image.tmdb.org`.
- **Save:** a `SavedItem(user, tmdb_id, media_type, title, poster_path, cached_at)` model with `unique_together = (user, tmdb_id, media_type)`. Notes, rating (1–5) and status/progress ("want to rent", "watching", "watched", or episode N) all live in your own tables. That content is yours, so no API terms limit it.
- **Terms:** Refresh cached `title`/`poster_path` before 6 months [S8]. Add an About page with the TMDB logo, the disclaimer, and "Watch provider data by JustWatch" [S2][S5]. A class project is non-commercial.
- **Optional rental add-on:** On the detail page, call Streaming Availability `/shows/movie/{tmdb_id}?country=us` to list rent and buy prices [S10]. Its 1,000/month hard cap means no surprise bills [S11]. Cache the result per title to save quota (storage is allowed [S11]).

**2. Open Library as a books "library rental" app (the strongest non-movie alternative)**

- It needs no key or signup [S21], covers are free [S22], work keys are stable, and the "availability" field connects to real lending [S20].
- "Progress" fits naturally as pages read or a reading status.
- **Downsides:** a low rate limit, so set a `User-Agent` and cache search results [S21], and a search schema that isn't guaranteed to be stable [S20].

**3. Watchmode (an alternative to Streaming Availability)**

- It's useful if you want IMDb/TMDB-to-Watchmode ID mapping and `/title/{id}/sources` rental data [S14].
- The 30-day cache limit on the free plan [S16] means saved snapshots must be refreshed or deleted. Store the Watchmode `id` plus `tmdb_id`, and keep user-generated fields separate.

**Not recommended as the primary API:** RentCast (50 calls/month plus overage billing), Zillow/Bridge (approval-gated), Amadeus (deprecated), and CityBikes/GBFS (live status data, not savable "items").

---

## Sources (all accessed 2026-11-09)

- [S1] TMDB, Search Movie reference: https://developer.themoviedb.org/reference/search-movie
- [S2] TMDB, Movie Watch Providers reference: https://developer.themoviedb.org/reference/movie-watch-providers
- [S3] TMDB, Watch Providers movie list: https://developer.themoviedb.org/reference/watch-providers-movie-list
- [S4] TMDB, Image Basics: https://developer.themoviedb.org/docs/image-basics
- [S5] TMDB, FAQ: https://developer.themoviedb.org/docs/faq
- [S6] TMDB, Rate Limiting: https://developer.themoviedb.org/docs/rate-limiting
- [S7] TMDB, Application Authentication: https://developer.themoviedb.org/docs/authentication-application
- [S8] TMDB, API Terms of Use: https://www.themoviedb.org/api-terms-of-use
- [S9] Movie of the Night, Streaming Availability API overview: https://www.movieofthenight.com/about/api
- [S10] Streaming Availability docs, Shows resource: https://docs.movieofthenight.com/resource/shows
- [S11] Streaming Availability, Pricing and FAQ: https://www.movieofthenight.com/about/api/pricing
- [S12] Streaming Availability docs, Authentication: https://docs.movieofthenight.com/guide/authentication
- [S13] Streaming Availability docs, Client Libraries: https://docs.movieofthenight.com/guide/client-libraries
- [S14] Watchmode, OpenAPI spec v1.10.1: https://api.watchmode.com/openapi.json (rendered at https://api.watchmode.com/docs)
- [S15] Watchmode, API home and pricing: https://api.watchmode.com/
- [S16] Watchmode, Terms & Conditions: https://api.watchmode.com/tc
- [S17] OMDb, API home and parameters: https://www.omdbapi.com/
- [S18] OMDb, API key signup: https://www.omdbapi.com/apikey.aspx
- [S19] OMDb, Legal: https://www.omdbapi.com/legal.htm
- [S20] Open Library, Search API: https://openlibrary.org/dev/docs/api/search
- [S21] Open Library, Developers / API: https://openlibrary.org/developers/api
- [S22] Open Library, Covers API: https://openlibrary.org/dev/docs/api/covers
- [S23] Open Library, Licensing: https://openlibrary.org/developers/licensing
- [S24] RentCast, Rental Listings (long-term) reference: https://developers.rentcast.io/reference/rental-listings-long-term
- [S25] RentCast, docs index (endpoints, rate limit): https://developers.rentcast.io/llms.txt
- [S26] RentCast, API product and pricing page: https://www.rentcast.io/api
- [S27] RentCast, Billing and Pricing: https://developers.rentcast.io/reference/billing-and-pricing
- [S28] RentCast, Getting Started: https://developers.rentcast.io/reference/getting-started-guide
- [S29] RentCast, API Terms of Use: https://www.rentcast.io/terms-api
- [S30] CityBikes, API v2 docs and terms: https://api.citybik.es/v2/
- [S31] MobilityData, GBFS repository and systems catalog: https://github.com/MobilityData/gbfs
- [S32] Amadeus for Developers, GitHub org (archived notice): https://github.com/amadeus4dev
- [S33] Amadeus, Statement regarding Amadeus for Developers portal: https://amadeus.com/en/industry-messaging/statement-regarding-amadeus-for-developers-portal
- [S34] Library of Congress, loc.gov JSON/YAML API: https://www.loc.gov/apis/json-and-yaml/
