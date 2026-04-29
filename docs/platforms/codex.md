# elko-skills on Codex CLI

Codex CLI can import Python modules directly. The elko-skill is a regular Python module — no special adapter needed.

---

## One-liner

```bash
./install.sh contacts
```

---

## Manual setup

### 1. Clone

```bash
git clone https://github.com/jsoprych/elko-skills.git ~/.elko-skills
```

### 2. Add to codex config

Edit `~/.codex/config.yaml`:

```yaml
tools:
  - name: contacts
    module: contacts.contacts
    path: ~/.elko-skills/contacts/contacts.py
    description: People database with permissions
```

### 3. Or use inline

```python
import sys
sys.path.insert(0, os.path.expanduser('~/.elko-skills/contacts'))

from contacts import contacts as hs

# Ready to use
alice = hs.get_by_email('alice@example.com')
print(alice['name'])
```

---

## Permissions

Codex runs as the current user. The elko-skill's internal permission model
(super-admin vs contact) applies regardless of the hosting agent — every
write function checks `requester_email` against the contacts table.
