# tests/test_prediction_service.py
import unittest
from datetime import datetime, timezone, timedelta
from ml_engine.prediction_service import (
    predict_glucose_trend,
    calculate_metabolic_score,
    simulate_meal_impact,
)


class TestPredictGlucoseTrend(unittest.TestCase):
    """Testes para predicao de tendencia glicemica."""

    def _make_readings(self, values, interval_minutes=5):
        """Helper: gera leituras com timestamps espaçados."""
        base = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)
        return [
            {
                "glucose_value": v,
                "timestamp": (base + timedelta(minutes=i * interval_minutes)).isoformat(),
            }
            for i, v in enumerate(values)
        ]

    def test_insufficient_data(self):
        readings = self._make_readings([100, 110])
        result = predict_glucose_trend(readings)
        self.assertIsNone(result)

    def test_stable_trend(self):
        readings = self._make_readings([100, 101, 100, 99, 100])
        result = predict_glucose_trend(readings)
        self.assertIsNotNone(result)
        self.assertEqual(result['trend'], 'STABLE')
        self.assertIn('→', result['trend_arrow'])

    def test_rising_trend(self):
        readings = self._make_readings([100, 110, 120, 130, 140])
        result = predict_glucose_trend(readings)
        self.assertIsNotNone(result)
        self.assertIn(result['trend'], ['RISING', 'RISING_FAST'])
        self.assertGreater(result['rate_of_change'], 0)
        self.assertGreater(result['predicted_glucose_60m'], 140)

    def test_falling_trend(self):
        readings = self._make_readings([200, 180, 160, 140, 120])
        result = predict_glucose_trend(readings)
        self.assertIsNotNone(result)
        self.assertIn(result['trend'], ['FALLING', 'FALLING_FAST'])
        self.assertLess(result['rate_of_change'], 0)
        self.assertLess(result['predicted_glucose_60m'], 120)

    def test_proactive_hypo_alert(self):
        readings = self._make_readings([120, 105, 90, 80, 75])
        result = predict_glucose_trend(readings)
        self.assertIsNotNone(result)
        alerts = result.get('alerts', [])
        proactive = [a for a in alerts if a['level'] == 'PROACTIVE']
        self.assertGreater(len(proactive), 0)

    def test_proactive_hyper_alert(self):
        readings = self._make_readings([120, 140, 155, 165, 175])
        result = predict_glucose_trend(readings)
        self.assertIsNotNone(result)
        alerts = result.get('alerts', [])
        proactive = [a for a in alerts if a['level'] == 'PROACTIVE']
        self.assertGreater(len(proactive), 0)

    def test_urgent_low_alert(self):
        readings = self._make_readings([60, 55, 50])
        result = predict_glucose_trend(readings)
        alerts = result.get('alerts', [])
        urgent = [a for a in alerts if a['level'] == 'URGENT']
        self.assertGreater(len(urgent), 0)

    def test_confidence_score(self):
        readings = self._make_readings([100, 110, 120, 130, 140])
        result = predict_glucose_trend(readings)
        self.assertIn('confidence', result)
        self.assertGreaterEqual(result['confidence'], 0)
        self.assertLessEqual(result['confidence'], 1)

    def test_predicted_value_clamped(self):
        # Valores extremos nao devem ultrapassar limites fisiologicos
        readings = self._make_readings([400, 420, 440, 460, 480])
        result = predict_glucose_trend(readings)
        self.assertLessEqual(result['predicted_glucose_60m'], 500)

    def test_time_to_hypo(self):
        readings = self._make_readings([120, 110, 100, 90, 80])
        result = predict_glucose_trend(readings)
        self.assertIsNotNone(result.get('time_to_hypo_minutes'))


class TestCalculateMetabolicScore(unittest.TestCase):
    """Testes para score metabolico."""

    def test_empty_data(self):
        result = calculate_metabolic_score([])
        self.assertIsNone(result['score'])

    def test_insufficient_data(self):
        result = calculate_metabolic_score([{"glucose_value": 100}] * 3)
        self.assertIsNone(result['score'])

    def test_perfect_control(self):
        readings = [{"glucose_value": 100}] * 50
        result = calculate_metabolic_score(readings)
        self.assertIsNotNone(result['score'])
        self.assertGreaterEqual(result['score'], 80)

    def test_poor_control(self):
        # Glicemias altas e variaveis
        readings = [{"glucose_value": v} for v in [50, 300, 60, 280, 55, 350] * 5]
        result = calculate_metabolic_score(readings)
        self.assertIsNotNone(result['score'])
        self.assertLess(result['score'], 50)

    def test_score_range(self):
        readings = [{"glucose_value": 120 + (i % 30)} for i in range(50)]
        result = calculate_metabolic_score(readings)
        self.assertGreaterEqual(result['score'], 0)
        self.assertLessEqual(result['score'], 100)

    def test_stats_present(self):
        readings = [{"glucose_value": 100 + i} for i in range(20)]
        result = calculate_metabolic_score(readings)
        stats = result.get('stats', {})
        self.assertIn('mean_glucose', stats)
        self.assertIn('time_in_range', stats)
        self.assertIn('cv_percent', stats)

    def test_empathic_message(self):
        readings = [{"glucose_value": 110}] * 50
        result = calculate_metabolic_score(readings)
        self.assertTrue(len(result['message']) > 0)


class TestSimulateMealImpact(unittest.TestCase):
    """Testes para simulacao do gemeo digital."""

    def test_basic_simulation(self):
        curve = simulate_meal_impact(
            current_glucose=120,
            carbs=50,
            icr=10,
            correction_factor=50,
            target_glucose=120,
            insulin_dose=5,
        )
        self.assertGreater(len(curve), 0)
        self.assertEqual(curve[0]['minutes'], 0)
        self.assertEqual(curve[-1]['minutes'], 240)

    def test_no_food_no_spike(self):
        curve = simulate_meal_impact(
            current_glucose=120,
            carbs=0,
            icr=10,
            correction_factor=50,
            target_glucose=120,
            insulin_dose=0,
        )
        for point in curve:
            self.assertAlmostEqual(point['predicted_glucose'], 120, delta=5)

    def test_high_carbs_spike(self):
        curve = simulate_meal_impact(
            current_glucose=100,
            carbs=100,
            icr=10,
            correction_factor=50,
            target_glucose=100,
            insulin_dose=10,
        )
        peak = max(p['predicted_glucose'] for p in curve)
        self.assertGreater(peak, 100)

    def test_curve_has_15min_intervals(self):
        curve = simulate_meal_impact(
            current_glucose=120,
            carbs=50,
            icr=10,
            correction_factor=50,
            target_glucose=120,
            insulin_dose=5,
        )
        minutes = [p['minutes'] for p in curve]
        for i in range(1, len(minutes)):
            self.assertEqual(minutes[i] - minutes[i - 1], 15)

    def test_glucose_clamped(self):
        curve = simulate_meal_impact(
            current_glucose=40,
            carbs=0,
            icr=10,
            correction_factor=50,
            target_glucose=120,
            insulin_dose=20,
        )
        for point in curve:
            self.assertGreaterEqual(point['predicted_glucose'], 40)
            self.assertLessEqual(point['predicted_glucose'], 400)


if __name__ == '__main__':
    unittest.main()
