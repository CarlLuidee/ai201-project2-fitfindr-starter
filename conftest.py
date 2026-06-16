# conftest.py  (place this file in the project ROOT, next to tools.py)
#
# pytest automatically loads conftest.py before collecting tests.
# Adding the repo root to sys.path here lets every test file do
#   from tools import search_listings
# regardless of where pytest is invoked from.

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
