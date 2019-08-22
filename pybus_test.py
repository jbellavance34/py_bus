#!/usr/bin/env python
import unittest
from pybus import app


class Testcalltoapi(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_noargs(self):
        rv = self.app.get('/')
        self.assertEqual(rv.status_code, 200)

    def test_sjsr(self):
        rv = self.app.get('/?dest=sjsr')
        self.assertEqual(rv.status_code, 200)

    def test_mtrl(self):
        rv = self.app.get('/?dest=mtrl')
        self.assertEqual(rv.status_code, 200)

    def test_all(self):
        rv = self.app.get('/?dest=all')
        self.assertEqual(rv.status_code, 200)


if __name__ == '__main__':
    unittest.main()
