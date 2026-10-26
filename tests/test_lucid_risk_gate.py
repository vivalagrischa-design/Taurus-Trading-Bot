import sqlite3
import unittest
from lucid_risk import allowed_quantity

class RiskGateTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.execute("CREATE TABLE trades (id TEXT, market TEXT, side TEXT, status TEXT, qty INTEGER)")
    def add(self, id, market, side, status, qty):
        self.db.execute("INSERT INTO trades VALUES (?,?,?,?,?)", (id, market, side, status, qty))
    def test_maximum(self):
        self.assertEqual(allowed_quantity(self.db, "nq", "LONG", 75), 20)
    def test_aggregate(self):
        self.add("a", "mes", "LONG", "OPEN", 17)
        self.assertEqual(allowed_quantity(self.db, "nq", "LONG", 10), 3)
    def test_opposite_same_instrument(self):
        self.add("a", "nq", "SHORT", "OPEN", 1)
        self.assertEqual(allowed_quantity(self.db, "nq", "LONG", 5), 0)
    def test_pending_reservation(self):
        self.add("a", "nq", "LONG", "PENDING", None)
        self.assertEqual(allowed_quantity(self.db, "mes", "LONG", 20), 19)
        self.assertEqual(allowed_quantity(self.db, "nq", "LONG", 20, exclude_trade_id="a"), 20)
    def test_invalid_market(self):
        self.assertEqual(allowed_quantity(self.db, "btc", "LONG", 10), 0)

if __name__ == "__main__":
    unittest.main()
