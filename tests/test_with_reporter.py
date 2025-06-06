import subprocess
import sys
import os

# Create a simple test that will work
test_content = '''
import pytest

class TestSimple:
    def test_always_passes(self):
        assert True
        
    def test_also_passes(self):
        assert 1 + 1 == 2
'''

# Write the test file
with open('test_simple.py', 'w') as f:
    f.write(test_content)

# Run pytest with claude reporter
result = subprocess.run([
    sys.executable, '-m', 'pytest',
    'test_simple.py',
    '-v',
    '--claude-reporter',
    '--claude-output-dir=test_reports'
], capture_output=True, text=True)

print(result.stdout)
print(result.stderr)

# Clean up
os.remove('test_simple.py')
