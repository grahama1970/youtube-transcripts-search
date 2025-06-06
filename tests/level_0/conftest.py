import sys
import os

# Add src to Python path for test imports
test_dir = os.path.dirname(__file__)
tests_dir = os.path.dirname(test_dir)
project_dir = os.path.dirname(tests_dir)
src_dir = os.path.join(project_dir, 'src')

if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
