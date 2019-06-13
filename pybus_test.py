#!/usr/bin/env python
import unittest
from pybus import app

class TestHello(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_hello(self):
        rv = self.app.get('/')
        self.assertEqual(rv.status_code, 200)

if __name__ == '__main__':
    unittest.main()
