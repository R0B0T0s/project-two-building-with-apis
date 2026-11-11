import logging
from unittest.mock import patch

import requests
import responses
from django.test import TestCase, override_settings

from rentals import tmdb


@override_settings(TMDB_READ_TOKEN="test-token")
class SearchFailureTests(TestCase):
    def setUp(self):
        # These failures are expected; keep their log lines out of the test output.
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    @responses.activate
    def test_every_failure_raises_tmdb_unavailable_with_its_kind(self):
        cases = [
            ("timeout", {"body": requests.exceptions.Timeout()}, True),
            ("connection error", {"body": requests.exceptions.ConnectionError()}, True),
            ("401 bad token", {"status": 401, "json": {}}, False),
            ("429 rate limit", {"status": 429, "json": {}}, False),
            ("500 server error", {"status": 500, "json": {}}, False),
            ("bad JSON", {"status": 200, "body": "not json"}, False),
        ]
        for name, reply, unreachable in cases:
            with self.subTest(name):
                responses.upsert(responses.GET, tmdb.SEARCH_URL, **reply)

                with self.assertRaises(tmdb.TMDBUnavailable) as caught:
                    tmdb.search_movies("alien")

                self.assertEqual(caught.exception.unreachable, unreachable)


@override_settings(TMDB_READ_TOKEN="test-token")
class SearchSuccessTests(TestCase):
    @responses.activate
    def test_search_sends_bearer_token_and_returns_results_page(self):
        responses.get(
            tmdb.SEARCH_URL,
            json={"page": 2, "total_pages": 7, "results": [{"id": 348}]},
            match=[
                responses.matchers.query_param_matcher(
                    {"query": "alien", "page": "2", "include_adult": "false"}
                ),
                responses.matchers.header_matcher(
                    {"Authorization": "Bearer test-token"}
                ),
            ],
        )

        with patch("rentals.tmdb.requests.get", wraps=requests.get) as get:
            data = tmdb.search_movies("alien", page=2)

        self.assertEqual(data, {"results": [{"id": 348}], "page": 2, "total_pages": 7})
        self.assertEqual(get.call_args.kwargs["timeout"], tmdb.TIMEOUT_SECONDS)

    @responses.activate
    def test_missing_fields_fall_back_to_empty_results(self):
        responses.get(tmdb.SEARCH_URL, json={})

        data = tmdb.search_movies("zzzz")

        self.assertEqual(data, {"results": [], "page": 1, "total_pages": 0})


@override_settings(TMDB_READ_TOKEN="test-token")
class FailureLoggingTests(TestCase):
    @responses.activate
    def test_technical_cause_is_logged(self):
        responses.get(tmdb.SEARCH_URL, status=429, json={"status_message": "slow down"})

        with (
            self.assertLogs("rentals.tmdb", level="WARNING") as logs,
            self.assertRaises(tmdb.TMDBUnavailable),
        ):
            tmdb.search_movies("alien")

        self.assertIn("429", logs.output[0])


@override_settings(TMDB_READ_TOKEN="test-token")
class MovieDetailsTests(TestCase):
    @responses.activate
    def test_details_returns_tmdb_movie_json(self):
        movie = {"id": 348, "title": "Alien", "genres": [{"id": 27, "name": "Horror"}]}
        responses.get(f"{tmdb.API_ROOT}/movie/348", json=movie)

        self.assertEqual(tmdb.get_movie_details(348), movie)

    @responses.activate
    def test_details_failure_raises_tmdb_unavailable(self):
        responses.get(f"{tmdb.API_ROOT}/movie/348", status=503)

        with self.assertLogs("rentals.tmdb"), self.assertRaises(tmdb.TMDBUnavailable):
            tmdb.get_movie_details(348)
