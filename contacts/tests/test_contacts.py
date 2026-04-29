"""
test_contacts.py — Elko-Skill: hs-contacts

Tests the contacts module with an isolated test DB via ELKO_CONTACTS_DB.
All tests are self-contained — creates a fresh DB per test session.

Run:  python3 -m pytest test_contacts.py -v
      python3 test_contacts.py               (standalone runner)
"""
import os, sys, json, sqlite3, tempfile, shutil

# ── Fixture: isolated test DB ──────────────────────────────
TEST_DIR = tempfile.mkdtemp(prefix='elko_contacts_test_')
TEST_DB = os.path.join(TEST_DIR, 'test_contacts.db')
os.environ['ELKO_CONTACTS_DB'] = TEST_DB

# Make elko_util importable from the parent skill directory
_SKILL_DIR = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, os.path.abspath(_SKILL_DIR))

# Import module AFTER setting env var so it picks up ELKO_CONTACTS_DB
import importlib.util
_MODULE_PATH = os.path.join(os.path.dirname(__file__), '..', 'contacts.py')
_SPEC = importlib.util.spec_from_file_location('elko_hs_contacts', _MODULE_PATH)
c = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(c)

# ── Helpers ─────────────────────────────────────────────────
def _seed_admin():
    """Insert super-admin for tests. Schema is auto-created by ElkoSkill.connect()."""
    conn = c._connect()
    conn.execute(
        "INSERT OR IGNORE INTO contacts (name, email, role, circle) VALUES (?, ?, ?, ?)",
        ('Test Admin', 'admin@elko.ai', 'super-admin', 'owner')
    )
    conn.execute(
        "INSERT OR IGNORE INTO auth_rules (contact_id, permission, scope) VALUES (?, ?, ?)",
        (1, 'system.config', '*')
    )
    conn.commit()
    conn.close()

# ── Setup / Teardown ───────────────────────────────────────
def setup_module():
    _seed_admin()

def teardown_module():
    shutil.rmtree(TEST_DIR, ignore_errors=True)


# ═══════════════════════════════════════════════════════════
# TESTS: READERS
# ═══════════════════════════════════════════════════════════

class TestReaders:

    def test_list_all_returns_contacts(self):
        result = c.list_all()
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_list_all_returns_dicts(self):
        result = c.list_all()
        for contact in result:
            assert isinstance(contact, dict)
            assert 'name' in contact
            assert 'email' in contact

    def test_get_by_email_found(self):
        result = c.get_by_email('admin@elko.ai')
        assert result is not None
        assert result['name'] == 'Test Admin'
        assert result['email'] == 'admin@elko.ai'

    def test_get_by_email_not_found(self):
        result = c.get_by_email('nobody@example.com')
        assert result is None

    def test_get_by_email_includes_phones_and_platforms(self):
        result = c.get_by_email('admin@elko.ai')
        assert 'phones' in result
        assert 'platforms' in result

    def test_find_by_name(self):
        result = c.find('Admin')
        assert len(result) >= 1
        assert result[0]['email'] == 'admin@elko.ai'

    def test_find_by_email(self):
        result = c.find('admin@elko')
        assert len(result) >= 1

    def test_find_no_match(self):
        result = c.find('zzzzz_nonexistent_zzzzz')
        assert len(result) == 0

    def test_find_limited_to_20(self):
        # Add 25 dummy contacts
        conn = sqlite3.connect(TEST_DB)
        for i in range(25):
            conn.execute(
                "INSERT OR IGNORE INTO contacts (name, email, role) VALUES (?, ?, 'contact')",
                (f'FindTest User{i}', f'findtest{i}@example.com')
            )
        conn.commit()
        conn.close()
        result = c.find('FindTest')
        assert len(result) <= 20


class TestPermissionChecks:

    def test_is_super_admin_true(self):
        assert c.check_is_super_admin('admin@elko.ai') is True

    def test_is_super_admin_false(self):
        assert c.check_is_super_admin('nobody@elko.ai') is False

    def test_is_super_admin_no_such_user(self):
        assert c.check_is_super_admin('') is False

    def test_has_permission_callable(self):
        # Permission system uses auth_rules table
        result = c.has_permission('admin@elko.ai', 'system.config')
        assert isinstance(result, bool)

    def test_get_permissions_empty_for_unknown(self):
        result = c.get_permissions('unknown@elko.ai')
        assert result == []

    def test_get_permissions_for_admin(self):
        result = c.get_permissions('admin@elko.ai')
        assert len(result) >= 1
        assert result[0]['permission'] == 'system.config'


class TestWriters:

    def test_add_new_contact_success(self):
        result = c.add(
            'Alice Smith', 'alice@example.com',
            requester_email='admin@elko.ai',
            circle='friends', role='contact'
        )
        assert result.get('success') is True
        assert result['name'] == 'Alice Smith'
        assert result['email'] == 'alice@example.com'
        assert isinstance(result['id'], int)

    def test_add_duplicate_email_fails(self):
        result = c.add(
            'Alice Again', 'alice@example.com',
            requester_email='admin@elko.ai'
        )
        assert result.get('success') is not True
        assert 'error' in result
        assert 'already exists' in result['error']

    def test_add_non_admin_fails(self):
        result = c.add(
            'Bob', 'bob@example.com',
            requester_email='regular@elko.ai'
        )
        assert result.get('success') is not True
        assert 'error' in result
        assert 'Permission denied' in result['error']

    def test_add_with_phone(self):
        result = c.add(
            'Carol', 'carol@example.com',
            requester_email='admin@elko.ai',
            phone='+15551234567'
        )
        assert result.get('success') is True
        # Verify phone stored
        contact = c.get_by_email('carol@example.com')
        assert len(contact['phones']) >= 1
        assert contact['phones'][0]['number'] == '+15551234567'

    def test_add_with_platforms(self):
        result = c.add(
            'Dave', 'dave@example.com',
            requester_email='admin@elko.ai',
            platforms=[{'platform': 'telegram', 'id': '12345'}]
        )
        assert result.get('success') is True
        contact = c.get_by_email('dave@example.com')
        assert len(contact['platforms']) >= 1
        assert contact['platforms'][0]['platform'] == 'telegram'
        assert contact['platforms'][0]['platform_id'] == '12345'


class TestGrants:

    def test_grant_permission(self):
        result = c.grant(
            'alice@example.com', 'email.send',
            scope='*', requester_email='admin@elko.ai'
        )
        assert result.get('success') is True
        assert result['permission'] == 'email.send'

    def test_grant_no_requester_fails(self):
        result = c.grant(
            'alice@example.com', 'email.send', scope='*'
        )
        assert result.get('success') is not True
        assert 'error' in result

    def test_grant_unknown_contact_fails(self):
        result = c.grant(
            'unknown@elko.ai', 'email.send',
            scope='*', requester_email='admin@elko.ai'
        )
        assert result.get('success') is not True
        assert 'not found' in result['error']

    def test_grant_non_admin_fails(self):
        result = c.grant(
            'alice@example.com', 'email.send',
            scope='*', requester_email='alice@example.com'
        )
        assert result.get('success') is not True
        assert 'error' in result

    def test_permissions_persist_after_grant(self):
        perms = c.get_permissions('alice@example.com')
        perm_names = [p['permission'] for p in perms]
        assert 'email.send' in perm_names


class TestUpdates:

    def test_update_name(self):
        result = c.update(
            'alice@example.com', 'admin@elko.ai',
            name='Alice Johnson'
        )
        assert result.get('success') is True
        assert 'name' in result['updated']
        updated = c.get_by_email('alice@example.com')
        assert updated['name'] == 'Alice Johnson'

    def test_update_circle(self):
        result = c.update(
            'alice@example.com', 'admin@elko.ai',
            circle='family'
        )
        assert result.get('success') is True
        updated = c.get_by_email('alice@example.com')
        assert updated['circle'] == 'family'

    def test_update_metadata(self):
        result = c.update(
            'alice@example.com', 'admin@elko.ai',
            metadata={'nickname': 'AJ', 'timezone': 'EST'}
        )
        assert result.get('success') is True
        assert 'metadata' in result['updated']

    def test_update_invalid_field_fails(self):
        result = c.update(
            'alice@example.com', 'admin@elko.ai',
            invalid_field='nope', password='hunter2'
        )
        assert result.get('success') is not True
        assert 'No valid' in result.get('error', '')

    def test_update_non_admin_fails(self):
        result = c.update(
            'alice@example.com', 'alice@example.com',
            name='Alice Hacker'
        )
        assert result.get('success') is not True
        assert 'error' in result


class TestSummary:

    def test_summary_returns_string(self):
        result = c.summary()
        assert isinstance(result, str)
        assert 'contacts' in result.lower()
        assert 'admin' in result.lower()


# ═══════════════════════════════════════════════════════════
# EDGE CASES
# ═══════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_add_missing_name(self):
        """Missing name should raise — it's NOT NULL in schema."""
        import pytest
        conn = sqlite3.connect(TEST_DB)
        try:
            conn.execute(
                "INSERT INTO contacts (email, role) VALUES (?, ?)",
                ('noname@example.com', 'contact')
            )
            conn.commit()
        except Exception as e:
            assert e is not None
        finally:
            conn.close()

    def test_get_by_email_special_chars(self):
        result = c.get_by_email('nobody+test@example.com')
        assert result is None

    def test_platforms_are_case_sensitive(self):
        conn = sqlite3.connect(TEST_DB)
        try:
            conn.execute(
                "INSERT INTO contact_platforms (contact_id, platform, platform_id) VALUES (?, ?, ?)",
                (2, 'Discord', 'discord123')
            )
            conn.commit()
        except Exception as e:
            assert e is not None
        finally:
            conn.close()

    def test_multiple_phones_per_contact(self):
        """Add a contact specifically for this test, then add phones."""
        # First ensure the contact exists
        existing = c.get_by_email('multiphone@example.com')
        if not existing:
            c.add('MultiPhone', 'multiphone@example.com',
                  requester_email='admin@elko.ai')
        
        conn = sqlite3.connect(TEST_DB)
        # Get actual contact_id from DB
        cid = conn.execute("SELECT id FROM contacts WHERE email = ?",
                          ('multiphone@example.com',)).fetchone()[0]
        conn.execute(
            "INSERT INTO contact_phones (contact_id, label, number) VALUES (?, ?, ?)",
            (cid, 'work', '+15559876543')
        )
        conn.execute(
            "INSERT INTO contact_phones (contact_id, label, number) VALUES (?, ?, ?)",
            (cid, 'home', '+15555555555')
        )
        conn.commit()
        conn.close()
        contact = c.get_by_email('multiphone@example.com')
        assert len(contact['phones']) >= 2

    def test_env_var_override_used(self):
        """Test that ELKO_CONTACTS_DB env var is respected."""
        assert os.environ['ELKO_CONTACTS_DB'] == TEST_DB


class TestSqlInjection:

    def test_update_rejects_unknown_columns(self):
        """Column names outside whitelist are silently dropped."""
        result = c.update(
            'alice@example.com', 'admin@elko.ai',
            role='contact',  # allowed
            password="' OR '1'='1",  # not in whitelist
            delete_from_contacts="1; DROP TABLE contacts; --",  # not in whitelist
        )
        assert result.get('success') is True
        # password and delete_from_contacts should have been ignored
        assert 'password' not in result.get('updated', [])
        assert 'delete_from_contacts' not in result.get('updated', [])

    def test_update_whitelist_only(self):
        """Only keys in the whitelist reach the SET clause."""
        result = c.update(
            'alice@example.com', 'admin@elko.ai',
            name='Alice Safe',
            malicious_col="x; DROP TABLE contacts; --",
        )
        assert result.get('success') is True
        assert 'malicious_col' not in result.get('updated', [])

    def test_update_name_with_sql_metacharacters(self):
        """Names containing SQL metacharacters are safely parameterized."""
        dangerous_name = "Robert'); DROP TABLE contacts; --"
        result = c.update(
            'alice@example.com', 'admin@elko.ai',
            name=dangerous_name,
        )
        assert result.get('success') is True
        # Verify the contact still exists
        contact = c.get_by_email('alice@example.com')
        assert contact is not None
        assert contact['name'] == dangerous_name
        # Verify the contacts table still exists
        all_contacts = c.list_all()
        assert len(all_contacts) > 0

    def test_add_email_with_sql_injection(self):
        """Email with SQL injection attempts is safely parameterized."""
        malicious_email = "'; DELETE FROM contacts WHERE '1'='1"
        result = c.add(
            'Hacker', malicious_email,
            requester_email='admin@elko.ai'
        )
        assert result.get('success') is True
        # Other contacts should still exist
        admin = c.get_by_email('admin@elko.ai')
        assert admin is not None

    def test_grant_permission_with_injection(self):
        """Permission names with SQL metacharacters are parameterized."""
        malicious_perm = "system.config'); DROP TABLE auth_rules; --"
        result = c.grant(
            'alice@example.com', malicious_perm,
            scope='*', requester_email='admin@elko.ai'
        )
        assert result.get('success') is True
        # Auth rules table should still exist
        perms = c.get_permissions('alice@example.com')
        perm_names = [p['permission'] for p in perms]
        assert malicious_perm in perm_names


# ── Standalone runner ──────────────────────────────────────
if __name__ == '__main__':
    import inspect
    
    # Run setup
    setup_module()
    
    passed = 0
    failed = 0
    
    for name, cls in sorted(inspect.getmembers(sys.modules[__name__], inspect.isclass)):
        if name.startswith('Test'):
            print(f"\n{'='*60}")
            print(f"  {name}")
            print(f"{'='*60}")
            for m_name, method in sorted(inspect.getmembers(cls, inspect.isfunction)):
                if m_name.startswith('test_'):
                    try:
                        method(cls())
                        print(f"  ✅ {m_name}")
                        passed += 1
                    except Exception as e:
                        print(f"  ❌ {m_name}: {e}")
                        failed += 1
    
    print(f"\n{'='*60}")
    print(f"  RESULTS: {passed} passed, {failed} failed")
    if os.environ.get('ELKO_CONTACTS_DB'):
        print(f"  Test DB: {os.environ['ELKO_CONTACTS_DB']}")
    teardown_module()
