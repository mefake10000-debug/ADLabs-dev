import unittest
from src.analytics import shelf_gap_geometry

class ShelfProductWiringTests(unittest.TestCase):
    def test_actual_product_boxes_feed_gap_candidates(self):
        products = [{'bbox': [10, 10, 30, 40]}, {'bbox': [70, 10, 90, 40]}]
        result = shelf_gap_geometry.snapshot_from_products(products)
        self.assertEqual(len(result['active']), 1)
        self.assertEqual(result['active'][0]['width'], 40)
        self.assertEqual(result['status'], 'PARTIAL')

    def test_empty_products_do_not_invent_gaps(self):
        self.assertEqual(shelf_gap_geometry.snapshot_from_products([])['active'], [])
