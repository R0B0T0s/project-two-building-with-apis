from django.test import TestCase
from django.urls import reverse

TMDB_NOTICE = "This product uses the TMDB API but is not endorsed or certified by TMDB"


class AboutPageTests(TestCase):
    def test_about_page_shows_tmdb_logo_attribution_and_staff_statement(self):
        response = self.client.get(reverse("rentals:about"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'alt="TMDB logo"')
        self.assertContains(response, "images/tmdb-logo.png")
        self.assertContains(response, TMDB_NOTICE)
        self.assertContains(
            response,
            "Employees and admins can see all data, including Private movies "
            "and notes, so that they can support users.",
        )


class FooterTests(TestCase):
    def footer_of(self, response):
        html = response.content.decode()
        start, end = html.find("<footer"), html.find("</footer>")
        self.assertNotEqual(start, -1, "page has no <footer>")
        return html[start:end]

    def test_every_page_footer_links_to_about_and_shows_tmdb_notice(self):
        about_url = reverse("rentals:about")
        for url in [reverse("rentals:home"), about_url]:
            with self.subTest(url=url):
                footer = self.footer_of(self.client.get(url))

                self.assertIn(f'href="{about_url}"', footer)
                self.assertIn(TMDB_NOTICE, footer)
