import os
import unittest

from assignment import main

class Tests(unittest.TestCase):

    def setup(self):
        main.config['TESTING'] = True
        main.config['WTF_CSRF_ENABLED'] = False