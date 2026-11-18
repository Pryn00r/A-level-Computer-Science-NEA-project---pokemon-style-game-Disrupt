# run_tests.py
# Runs every automated test file one after another and prints a short summary at the end.
# Run with:  python run_tests.py   (from any folder)

import subprocess
import sys
from os import listdir
from os.path import abspath, dirname, join

CODE_DIR = dirname(abspath(__file__))
TEST_FILES = sorted(name for name in listdir(CODE_DIR) if name.startswith('test_') and name.endswith('.py'))

summary = []   # (file name, last line of its output, passed?)
for name in TEST_FILES:
	result = subprocess.run([sys.executable, join(CODE_DIR, name)], cwd = CODE_DIR, capture_output = True, text = True)
	# (unittest files print their result to stderr; the pygame welcome line is skipped)
	lines = [line for line in (result.stdout + result.stderr).splitlines() if line.strip() and not line.strip().startswith(('pygame-ce', 'ALSA', 'Hello from', 'self.display_surface')) and 'Warning:' not in line]
	failures = [line for line in lines if line.startswith('FAIL')]
	last = lines[-1] if lines else '(no output)'
	passed = result.returncode == 0 and not failures
	summary.append((name, last, passed))
	for line in failures:
		print(f'{name}: {line}')
	if result.returncode != 0:
		print(f'{name} crashed:\n{result.stderr[-1500:]}')

print()
for name, last, passed in summary:
	print(f"{'OK  ' if passed else 'FAIL'} {name:<26} {last}")
print(f'\n{sum(passed for _, _, passed in summary)}/{len(summary)} test files passed')
sys.exit(0 if all(passed for _, _, passed in summary) else 1)
