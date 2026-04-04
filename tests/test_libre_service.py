# tests/test_libre_service.py
import unittest
from services.libre_service import _map_trend, REGION_ENDPOINTS


class TestMapTrend(unittest.TestCase):
    """Testes para mapeamento de tendencia do sensor."""

    def test_trend_falling_fast(self):
        self.assertEqual(_map_trend(1), "FALLING_FAST")

    def test_trend_falling(self):
        self.assertEqual(_map_trend(2), "FALLING")

    def test_trend_stable(self):
        self.assertEqual(_map_trend(3), "STABLE")

    def test_trend_rising(self):
        self.assertEqual(_map_trend(4), "RISING")

    def test_trend_rising_fast(self):
        self.assertEqual(_map_trend(5), "RISING_FAST")

    def test_trend_unknown_int(self):
        self.assertEqual(_map_trend(99), "UNKNOWN")

    def test_trend_none(self):
        self.assertEqual(_map_trend(None), "UNKNOWN")

    def test_trend_string(self):
        self.assertEqual(_map_trend("STABLE"), "STABLE")


class TestRegionEndpoints(unittest.TestCase):
    """Testes para endpoints regionais da Abbott."""

    def test_br_endpoint(self):
        self.assertIn("br", REGION_ENDPOINTS["BR"])

    def test_us_endpoint(self):
        self.assertIn("us", REGION_ENDPOINTS["US"])

    def test_eu_endpoint(self):
        self.assertIn("eu", REGION_ENDPOINTS["EU"])

    def test_all_regions_have_valid_urls(self):
        for region, url in REGION_ENDPOINTS.items():
            self.assertTrue(url.startswith("api-"), f"Regiao {region}: {url}")
            self.assertIn("libreview.io", url)


if __name__ == '__main__':
    unittest.main()
