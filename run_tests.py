#!/usr/bin/env python3
"""
run_tests.py — Run all elko-skill tests.

Usage:
    python3 run_tests.py                        # Run all test suites
    python3 run_tests.py contacts               # Run specific skill tests
    python3 run_tests.py contacts threads       # Run multiple
    python3 run_tests.py -v                     # Verbose
"""
import os, sys, glob, importlib.util, traceback

SKILLS_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_PATHS = {
    'contacts': os.path.join(SKILLS_DIR, 'contacts', 'tests', 'test_contacts.py'),
    'threads':  os.path.join(SKILLS_DIR, 'threads', 'tests', 'test_threads.py'),
    'template': os.path.join(SKILLS_DIR, 'template', 'tests', 'test_template.py'),
}

def run_test(test_path, verbose=False):
    """Run a test file and return (passed, failed, errors)."""
    if not os.path.exists(test_path):
        return 0, 0, [f"Test file not found: {test_path}"]
    
    # Clean pycache to prevent stale imports
    test_dir = os.path.dirname(test_path)
    for root, dirs, files in os.walk(test_dir):
        if '__pycache__' in dirs:
            import shutil
            shutil.rmtree(os.path.join(root, '__pycache__'), ignore_errors=True)
    
    # Run the test file as a subprocess for isolation
    import subprocess
    result = subprocess.run(
        [sys.executable, test_path],
        capture_output=True, text=True, timeout=60
    )
    
    # Count results from output
    passed = failed = 0
    errors = []
    
    for line in result.stdout.split('\n'):
        if 'passed' in line and 'failed' in line and 'RESULTS' in line:
            parts = line.split(',')
            for p in parts:
                p = p.strip()
                if 'passed' in p:
                    try:
                        passed = int(p.split()[0])
                    except ValueError:
                        pass
                if 'failed' in p:
                    try:
                        failed = int(p.split()[0])
                    except ValueError:
                        pass
    
    if verbose or failed > 0 or result.returncode != 0:
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr, file=sys.stderr)
    
    if result.returncode != 0 and passed == 0 and failed == 0:
        errors.append(result.stderr or "Unknown error (returncode={})".format(result.returncode))
    
    return passed, failed, errors


def main():
    verbose = '-v' in sys.argv or '--verbose' in sys.argv
    skills = sys.argv[1:]
    skills = [s for s in skills if s in TEST_PATHS]
    
    if not skills:
        # Run all
        skills = list(TEST_PATHS.keys())
    
    total_passed = 0
    total_failed = 0
    all_errors = []
    
    print(f"{'='*60}")
    print(f"  elko-skills Test Runner")
    print(f"{'='*60}")
    
    for skill in skills:
        print(f"\n{'─'*60}")
        print(f"  [{skill}]")
        print(f"{'─'*60}")
        
        passed, failed, errors = run_test(TEST_PATHS[skill], verbose=verbose)
        total_passed += passed
        total_failed += failed
        all_errors.extend(errors)
        
        status = "✅" if failed == 0 else "❌"
        print(f"  {status} {passed} passed, {failed} failed")
    
    # Summary
    print(f"\n{'='*60}")
    if total_failed == 0 and not all_errors:
        print(f"  ✅ ALL PASSED — {total_passed} tests across {len(skills)} skills")
    else:
        print(f"  {'✅' if total_failed == 0 else '❌'} {total_passed} passed, {total_failed} failed")
        for err in all_errors:
            print(f"  Error: {err}")
    print(f"{'='*60}")
    
    return 1 if total_failed > 0 else 0


if __name__ == '__main__':
    sys.exit(main())
