This is a new Django application called "Movie Rental". This project will allow users to select movies and preview, rent, and review them. 

Technology Requirements: Django, Django REST Framework (DRF), SQLite, uv, Ruff

Business Requirements:

1. This project's purpose is to allow users to rent movies in the easiest possible manner while also providing the most pro-consumer service possible. 

2. Users can find items through an external API (TMDB). 

3. Users can save selected items to your application. Store enough information locally for saved items to remain accessible when the external API is unavailable.

4. Users can add and edit their own information. This might include notes, ratings, status, or progress.

5. Users can browse their saved items on a website. Include search, filtering, sorting, and pagination. These features must operate on locally saved data.

6. Users must sign in to manage their saved data. Any user can view published data, while only the same user, employees, or admins can modify it. Users can choose having private data, public viewing, or selective sharing. Enforce those rules through both the website and the API.

7. Your application provides its own API. Support listing, creating, updating, and deleting saved entries.

8. The application handles unsuccessful external requests. Show a useful message when the provider is unavailable or a request fails. 