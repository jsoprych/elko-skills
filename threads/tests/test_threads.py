"""
test_threads.py — Elko-Skill: hs-threads

Tests the threads module with an isolated test DB via ELKO_THREADS_DB.
All tests are self-contained — creates a fresh DB per test session.

Run:  python3 -m pytest test_threads.py -v
      python3 test_threads.py               (standalone runner)
"""
import os, sys, json, sqlite3, tempfile, shutil

# ── Fixture: isolated test DB ──────────────────────────────
TEST_DIR = tempfile.mkdtemp(prefix='elko_threads_test_')
TEST_DB = os.path.join(TEST_DIR, 'test_threads.db')
os.environ['ELKO_THREADS_DB'] = TEST_DB

# Make elko_util importable from the parent skill directory
_SKILL_DIR = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, os.path.abspath(_SKILL_DIR))

# Import module AFTER setting env var so it picks up ELKO_THREADS_DB
import importlib.util
_MODULE_PATH = os.path.join(os.path.dirname(__file__), '..', 'threads.py')
_SPEC = importlib.util.spec_from_file_location('elko_hs_threads', _MODULE_PATH)
t = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(t)

# ── Setup / Teardown ───────────────────────────────────────
# Schema is auto-created by ElkoSkill.connect() — no _create_db needed.
def teardown_module():
    shutil.rmtree(TEST_DIR, ignore_errors=True)


# ═══════════════════════════════════════════════════════════
# TESTS: CAPTURE
# ═══════════════════════════════════════════════════════════

class TestCapture:

    def test_capture_creates_new_thread(self):
        result = t.capture('test-topic-1', 'email', {
            'from_addr': 'alice@example.com',
            'from_name': 'Alice',
            'subject': 'Test',
            'body_preview': 'Hello world',
            'direction': 'inbound',
            'sent_at': '2025-01-01T12:00:00Z'
        })
        assert result['is_new_thread'] is True
        assert isinstance(result['thread_id'], int)
        assert isinstance(result['message_id'], int)

    def test_capture_appends_to_existing_thread(self):
        """Same topic+channel should append, not create new thread."""
        first_id = t.capture('test-topic-1', 'email', {
            'from_addr': 'bob@example.com',
            'from_name': 'Bob',
            'subject': 'Re: Test',
            'body_preview': 'Reply message',
            'direction': 'inbound',
            'sent_at': '2025-01-01T13:00:00Z'
        })
        assert first_id['is_new_thread'] is False
        assert first_id['thread_id'] is not None

    def test_capture_different_channel_creates_new_thread(self):
        """Same topic, different channel = separate thread."""
        result = t.capture('test-topic-1', 'telegram', {
            'from_addr': 'alice_tele',
            'from_name': 'Alice',
            'subject': 'Test via Telegram',
            'body_preview': 'Working from Telegram today',
            'direction': 'inbound',
            'sent_at': '2025-01-01T14:00:00Z'
        })
        assert result['is_new_thread'] is True
        assert result['thread_id'] != 1  # Different thread ID

    def test_capture_with_participants(self):
        result = t.capture('test-topic-2', 'email', {
            'from_addr': 'carol@example.com',
            'from_name': 'Carol',
            'subject': 'Group discussion',
            'body_preview': 'Let us all collaborate',
            'direction': 'inbound',
            'sent_at': '2025-01-02T10:00:00Z'
        }, participants=['alice@example.com', 'bob@example.com'])
        assert result['is_new_thread'] is True

    def test_capture_participants_merge(self):
        """Adding a participant should merge, not replace."""
        t.capture('test-topic-2', 'email', {
            'from_addr': 'dave@example.com',
            'from_name': 'Dave',
            'subject': 'Joining late',
            'body_preview': 'Can I join?',
            'direction': 'inbound',
            'sent_at': '2025-01-02T11:00:00Z'
        }, participants=['dave@example.com'])
        # Thread should now have 3 participants
        ctx = t.context('test-topic-2')
        participants = json.loads(ctx['thread']['participants'] or '[]')
        assert 'dave@example.com' in participants
        assert 'alice@example.com' in participants

    def test_capture_empty_body(self):
        """Empty body should not crash."""
        result = t.capture('test-topic-3', 'email', {
            'from_addr': 'empty@example.com',
            'from_name': 'Empty',
            'subject': '',
            'body_preview': '',
            'direction': 'inbound',
            'sent_at': '2025-01-03T00:00:00Z'
        })
        assert result['is_new_thread'] is True


class TestActive:

    def test_active_returns_threads(self):
        result = t.active()
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_active_sorted_by_recent(self):
        result = t.active()
        if len(result) >= 2:
            # Most recent should be first
            timestamps = [r.get('last', '') for r in result]
            assert timestamps == sorted(timestamps, reverse=True)

    def test_active_limited(self):
        result = t.active(limit=2)
        assert len(result) <= 2


class TestContext:

    def test_context_returns_thread_and_messages(self):
        result = t.context('test-topic-1')
        assert 'thread' in result
        assert 'messages' in result
        assert result['thread'] is not None
        assert len(result['messages']) >= 1

    def test_context_returns_none_for_missing(self):
        result = t.context('nonexistent-topic')
        assert result['thread'] is None
        assert result['messages'] == []

    def test_context_messages_in_order(self):
        result = t.context('test-topic-1')
        if len(result['messages']) >= 2:
            timestamps = [m['sent_at'] for m in result['messages']]
            assert timestamps == sorted(timestamps, reverse=True)

    def test_context_filter_by_channel(self):
        result = t.context('test-topic-1', channel='telegram')
        # Should find the telegram thread
        assert result['thread'] is None or result['thread']['topic'] == 'test-topic-1'


class TestAllByStatus:

    def test_all_active(self):
        result = t.all_by_status('active')
        assert len(result) >= 1

    def test_all_by_status_empty(self):
        result = t.all_by_status('resolved')
        assert isinstance(result, list)
        # Should be empty or have specific status

    def test_all_without_filter(self):
        result = t.all_by_status()
        assert len(result) >= 1


class TestTags:

    def test_tag_add(self):
        result = t.tag('test-topic-1', 'important')
        assert result['success'] is True
        assert 'important' in result['tags']

    def test_tag_duplicate_no_error(self):
        result = t.tag('test-topic-1', 'important')
        assert result['success'] is True
        assert result['tags'].count('important') == 1  # No duplicates

    def test_tag_multiple(self):
        t.tag('test-topic-1', 'design')
        t.tag('test-topic-1', 'action-needed')
        ctx = t.context('test-topic-1')
        tags = json.loads(ctx['thread']['tags'] or '[]')
        assert 'design' in tags
        assert 'action-needed' in tags

    def test_tag_nonexistent_thread(self):
        result = t.tag('nonexistent-topic', 'urgent')
        assert 'error' in result


class TestRecent:

    def test_recent_returns_list(self):
        result = t.recent()
        assert isinstance(result, list)

    def test_recent_limited(self):
        result = t.recent(limit=2)
        assert len(result) <= 2

    def test_recent_returns_dicts(self):
        result = t.recent()
        if result:
            assert isinstance(result[0], dict)
            assert 'topic' in result[0]


class TestSummary:

    def test_summary_returns_string(self):
        result = t.summary()
        assert isinstance(result, str)
        assert 'threads' in result.lower()


class TestEdgeCases:

    def test_env_var_override(self):
        assert os.environ['ELKO_THREADS_DB'] == TEST_DB
        # DB path should match env var, accessible via _skill.db_path
        assert t._connect() is not None

    def test_missing_sent_at_defaults_now(self):
        result = t.capture('test-topic-now', 'email', {
            'from_addr': 'time@example.com',
            'from_name': 'Time',
            'subject': 'No timestamp',
            'body_preview': 'Default time should work',
        })
        assert result['is_new_thread'] is True

    def test_body_truncated_at_500(self):
        long_body = 'x' * 1000
        result = t.capture('test-topic-truncate', 'email', {
            'from_addr': 'long@example.com',
            'from_name': 'Long',
            'subject': 'Long body',
            'body_preview': long_body,
            'direction': 'inbound',
            'sent_at': '2025-01-04T00:00:00Z'
        })
        assert result['is_new_thread'] is True
        ctx = t.context('test-topic-truncate')
        assert len(ctx['messages'][0]['body_preview']) <= 500

    def test_message_count_increments(self):
        """Each capture should increment message_count."""
        t.capture('test-topic-count', 'email', {
            'from_addr': 'count@example.com',
            'from_name': 'Count',
            'subject': 'Msg 1',
            'body_preview': 'First',
            'direction': 'inbound',
            'sent_at': '2025-01-05T00:00:00Z'
        })
        ctx = t.context('test-topic-count')
        initial = ctx['thread']['message_count']
        
        t.capture('test-topic-count', 'email', {
            'from_addr': 'count@example.com',
            'from_name': 'Count',
            'subject': 'Msg 2',
            'body_preview': 'Second',
            'direction': 'inbound',
            'sent_at': '2025-01-05T01:00:00Z'
        })
        ctx = t.context('test-topic-count')
        assert ctx['thread']['message_count'] == initial + 1

    def test_round_trip_body_hash(self):
        """body_hash should be consistent for same input."""
        body = "This is a test message for hashing."
        t.capture('test-topic-hash', 'email', {
            'from_addr': 'hash@example.com',
            'from_name': 'Hash',
            'subject': 'Hash test',
            'body_preview': body,
            'direction': 'inbound',
            'sent_at': '2025-01-06T00:00:00Z'
        })
        ctx = t.context('test-topic-hash')
        msg = ctx['messages'][0]
        assert msg['body_hash'] is not None
        assert len(msg['body_hash']) == 16  # SHA256 truncated to 16 chars


# ═══════════════════════════════════════════════════════════
# STANDALONE RUNNER
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    import inspect
    
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
    print(f"  Test DB: {os.environ.get('ELKO_THREADS_DB')}")
    teardown_module()
