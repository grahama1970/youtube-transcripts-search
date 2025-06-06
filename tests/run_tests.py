import subprocess
import sys
import os

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

# Run pytest with correct environment
result = subprocess.run([
    sys.executable, '-m', 'pytest',
    'tests/level_0/test_youtube_transcripts_standardized.py',
    '-v', '--tb=short',
    '--json-report',
    '--json-report-file=test_reports/youtube_transcripts_test.json'
], env={**os.environ, 'PYTHONPATH': src_path})

sys.exit(result.returncode)
