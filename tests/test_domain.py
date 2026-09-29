import sqlite3
import unittest

import domain


class StoreDomainTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        domain.init(self.db)

    def test_checkout_uses_server_prices_and_reduces_stock(self):
        product = self.db.execute("SELECT * FROM products WHERE sku='audit-kit'").fetchone()
        result = domain.handle("POST", "/api/orders", {
            "customer": "Demo Buyer",
            "email": "buyer@example.com",
            "items": [{"sku": "audit-kit", "quantity": 2, "price_cents": 1}],
        }, self.db)
        self.assertEqual(result["total_cents"], product["price_cents"] * 2)
        self.assertEqual(self.db.execute("SELECT stock FROM products WHERE sku='audit-kit'").fetchone()[0], product["stock"] - 2)

    def test_oversell_is_rejected(self):
        with self.assertRaises(ValueError):
            domain.handle("POST", "/api/orders", {
                "customer": "Demo Buyer",
                "email": "buyer@example.com",
                "items": [{"sku": "audit-kit", "quantity": 99}],
            }, self.db)


if __name__ == "__main__":
    unittest.main()
