# tests/test_chart_service.py
import unittest
import io
from services.chart_service import generate_glucose_chart


class TestGenerateGlucoseChart(unittest.TestCase):
    """Testes para a geracao de graficos de glicemia."""

    def test_chart_generation(self):
        logs = [
            {"glucose_level": 120, "timestamp": "2026-03-20T08:00:00+00:00"},
            {"glucose_level": 180, "timestamp": "2026-03-20T12:00:00+00:00"},
            {"glucose_level": 95, "timestamp": "2026-03-20T18:00:00+00:00"},
        ]
        buf = generate_glucose_chart(logs)
        self.assertIsInstance(buf, io.BytesIO)
        # Verifica que o buffer contem dados PNG (header PNG)
        data = buf.read()
        self.assertTrue(len(data) > 0)
        self.assertTrue(data[:4] == b'\x89PNG')

    def test_chart_empty_glucose(self):
        logs = [
            {"glucose_level": None, "timestamp": "2026-03-20T08:00:00+00:00"},
        ]
        with self.assertRaises(ValueError):
            generate_glucose_chart(logs)

    def test_chart_empty_logs(self):
        with self.assertRaises(ValueError):
            generate_glucose_chart([])

    def test_chart_single_point(self):
        logs = [
            {"glucose_level": 150, "timestamp": "2026-03-20T10:00:00+00:00"},
        ]
        buf = generate_glucose_chart(logs)
        self.assertIsInstance(buf, io.BytesIO)


if __name__ == '__main__':
    unittest.main()
