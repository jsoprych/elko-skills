"""
test_template.py — Elko-Skill: hs-template (example/test scaffold)

Demonstrates the test pattern for a new elko-skill. Every elko-skill
should have a tests/ directory with this structure:

    elko-skills/my-skill/
    ├── tests/
    │   ├── __init__.py
    │   ├── test_my_skill.py    ← Your actual tests
    │   └── conftest.py         ← optional shared fixtures
    └── ...

Pattern to follow:
1. Set ELKO_{NAME}_DB env var to temp path BEFORE import
2. Add elko-skills/ root to sys.path for elko_util import
3. Import the module
4. Insert known test data (schema is auto-created)
5. Test reads return expected values
6. Test writes check permissions
7. Test edge cases (empty, missing, duplicates, long input)
8. Clean up

Run:  python3 test_template.py            (standalone)
      cd tests && python3 -m pytest -v    (pytest)
"""
import os, sys, json, sqlite3, tempfile, shutil

# ── 1. Set env var before import ───────────────────────────
TEST_DIR = tempfile.mkdtemp(prefix='elko_template_test_')
TEST_DB = os.path.join(TEST_DIR, 'test_template.db')
os.environ['ELKO_TEMPLATE_DB'] = TEST_DB

# ── 2. Add elko_util to path ────────────────────────────────
_SKILL_DIR = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, os.path.abspath(_SKILL_DIR))

# ── 3. Import ──────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
# from module import * as s     # ← Uncomment when module exists

# ── 4. Setup/Teardown ──────────────────────────────────────
def setup_module():
    """Schema is auto-created by ElkoSkill.connect().
    Seed any test data here if needed."""
    pass

def teardown_module():
    shutil.rmtree(TEST_DIR, ignore_errors=True)


# ── 5-8. Tests (example) ──────────────────────────────────

# from elko_util import ElkoSkill
# 
# class TestReads:
#     def test_list_all(self):
#         result = s.list_all()
#         assert len(result) >= 2
#         assert isinstance(result[0], dict)


if __name__ == '__main__':
    import inspect
    print(f"\n{'='*60}")
    print("  TEMPLATE TEST — No module loaded yet.")
    print("  Copy this pattern when you build your skill.")
    print(f"\n  Test DB: {TEST_DB}")
    teardown_module()
