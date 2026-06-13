import unittest

from bom_service import BOMCircularReferenceError, BOMService, BOMItem, build_sample_bom


class TestBOMService(unittest.TestCase):
    def test_single_level_explosion(self):
        svc = BOMService()
        svc.load_relations([("A", "B", 2), ("A", "C", 3)])
        items = svc.explode("A")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0], BOMItem(material="B", quantity=2, level=1))
        self.assertEqual(items[1], BOMItem(material="C", quantity=3, level=1))

    def test_multi_level_explosion(self):
        svc = BOMService()
        svc.load_relations([
            ("A", "B", 2),
            ("B", "C", 3),
        ])
        items = svc.explode("A")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0], BOMItem(material="B", quantity=2, level=1))
        self.assertEqual(items[1], BOMItem(material="C", quantity=6, level=2))

    def test_quantity_multiplication(self):
        svc = BOMService()
        svc.load_relations([
            ("A", "B", 2),
            ("B", "C", 3),
            ("C", "D", 4),
        ])
        items = svc.explode("A")
        d_item = [i for i in items if i.material == "D"][0]
        self.assertAlmostEqual(d_item.quantity, 24.0)

    def test_flatten_aggregation(self):
        svc = BOMService()
        svc.load_relations([
            ("A", "B", 2),
            ("A", "C", 1),
            ("B", "C", 3),
        ])
        flat = svc.flatten("A")
        flat_dict = dict(flat)
        self.assertAlmostEqual(flat_dict["C"], 1.0 + 2.0 * 3.0)

    def test_leaf_material_no_children(self):
        svc = BOMService()
        svc.load_relations([("A", "B", 1)])
        items = svc.explode("B")
        self.assertEqual(len(items), 0)

    def test_unknown_material(self):
        svc = BOMService()
        items = svc.explode("UNKNOWN")
        self.assertEqual(len(items), 0)

    def test_sample_bom(self):
        svc = build_sample_bom()
        flat = svc.flatten("自行车")
        flat_dict = dict(flat)
        self.assertAlmostEqual(flat_dict["辐条"], 24.0)
        self.assertAlmostEqual(flat_dict["轮胎"], 2.0)
        self.assertAlmostEqual(flat_dict["车架"], 1.0)
        self.assertAlmostEqual(flat_dict["车轮"], 2.0)
        self.assertAlmostEqual(flat_dict["把手"], 1.0)
        self.assertAlmostEqual(flat_dict["前叉"], 1.0)
        self.assertAlmostEqual(flat_dict["轮毂"], 2.0)

    def test_circular_reference_ab_a_raises(self):
        svc = BOMService()
        svc.load_relations([
            ("A", "B", 1),
            ("B", "A", 1),
        ])
        with self.assertRaises(BOMCircularReferenceError) as ctx:
            svc.explode("A")
        self.assertEqual(ctx.exception.path, ["A", "B", "A"])
        self.assertIn("A → B → A", str(ctx.exception))

    def test_circular_reference_abc_a_raises(self):
        svc = BOMService()
        svc.load_relations([
            ("A", "B", 1),
            ("B", "C", 1),
            ("C", "A", 1),
        ])
        with self.assertRaises(BOMCircularReferenceError) as ctx:
            svc.explode("A")
        self.assertEqual(ctx.exception.path, ["A", "B", "C", "A"])

    def test_circular_reference_error_is_custom_exception(self):
        svc = BOMService()
        svc.load_relations([("A", "B", 1), ("B", "A", 1)])
        try:
            svc.explode("A")
            self.fail("预期抛出 BOMCircularReferenceError")
        except BOMCircularReferenceError as e:
            self.assertTrue(hasattr(e, "path"))
            self.assertIsInstance(e.path, list)

    def test_multiple_paths_to_same_leaf(self):
        svc = BOMService()
        svc.load_relations([
            ("X", "Y", 2),
            ("X", "Z", 3),
            ("Y", "W", 4),
            ("Z", "W", 5),
        ])
        flat = svc.flatten("X")
        flat_dict = dict(flat)
        self.assertAlmostEqual(flat_dict["W"], 2 * 4 + 3 * 5)

    def test_decimal_quantities(self):
        svc = BOMService()
        svc.load_relations([
            ("A", "B", 0.5),
            ("B", "C", 1.5),
        ])
        flat = svc.flatten("A")
        flat_dict = dict(flat)
        self.assertAlmostEqual(flat_dict["C"], 0.75)


if __name__ == "__main__":
    unittest.main()
