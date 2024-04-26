import unittest
import psycopg2
from server import conn

class TestDatabaseConnection(unittest.TestCase):
    def test_database_connection(self):
        try:
            cur = conn.cursor()
            cur.execute("SELECT version();")
            db_version = cur.fetchone()
            self.assertIsNotNone(db_version)
        except psycopg2.Error as e:
            self.fail("Error connecting to database: " + str(e))

if __name__ == '__main__':
    unittest.main()
