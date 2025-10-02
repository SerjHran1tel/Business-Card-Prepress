# -*- coding: utf-8 -*-
# tests/test_layout_calculator.py
import unittest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from layout_calculator import LayoutCalculator


class TestLayoutCalculator(unittest.TestCase):

    def setUp(self):
        self.calc = LayoutCalculator(210, 297, 90, 50, 5, 3, 2)

    def test_basic_layout(self):
        layout = self.calc.calculate_layout()
        self.assertGreater(layout.cards_total, 0)
        self.assertGreater(layout.efficiency, 0)

    def test_rotated_layout(self):
        calc = LayoutCalculator(210, 297, 90, 50, 5, 3, 2, rotate=True)
        layout = calc.calculate_layout()
        self.assertGreater(layout.cards_total, 0)

    def test_no_fit(self):
        calc = LayoutCalculator(100, 100, 200, 200, 5, 3, 2)
        layout = calc.calculate_layout()
        self.assertEqual(layout.cards_total, 0)

    def test_sheets_calculation(self):
        sheets = self.calc.calculate_sheets_needed(100)
        self.assertGreaterEqual(sheets, 1)


if __name__ == '__main__':
    unittest.main()