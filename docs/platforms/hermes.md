# elko-skills on Hermes Agent

Hermes is the native platform. Integration is the deepest — direct Python import, auto-registered in the elko-registry, bootstrapped every session.

---

## One-liner

```bash
./install.sh contacts
```

That's it. The installer detects Hermes from `HERMES_DATA_DIR` or `$HOME/.hermes/config.yaml` and auto-registers in `elko-registry.db`.

---

## Manual setup

### 1. Clone

```bash
git clone https://github.com/jsoprych/elko-skills.git /opt/data/elko-skills
```

### 2. Configure env var (optional)

Add to your `.env` or `config.yaml`:

```yaml
# config.yaml
env:
  ELKO_CONTACTS_DB: /custom/path/contacts.db
```

Default path: `/opt/data/elko-skills/contacts/contacts.db`

### 3. Register in the registry

```bash
python3 -c "
import sqlite3
db = sqlite3.connect('/opt/data/elko-registry.db')
db.execute('''
  INSERT INTO services (name, kind, path, capability, summary_query, active)
  VALUES ('hs-contacts', 'elko-skill', '/opt/data/elko-skills/contacts',
          'people, permissions, platforms',
          'SELECT COUNT(*)||\" contacts\" FROM contacts', 1)
''')
db.commit()
"
```

### 4. Add to bootstrap

In your `startup.py` or bootstrap card, add:

```python
import sqlite3
reg = sqlite3.connect('/opt/data/elko-registry.db')
for r in reg.execute("SELECT name, path FROM services WHERE kind='elko-skill' AND active=1"):
    print(f"  elko-skill: {r[0]} → {r[1]}")
```

---

## Usage in Hermes

```python
from contacts import contacts as hs

# Reads (no auth)
hs.list_all()
hs.get_by_email('john@elko.ai')
hs.find('john')

# Writes (require super-admin email)
hs.add('Diana', 'diana@example.com', requester_email='john@elko.ai')
hs.update('diana@example.com', 'john@elko.ai', circle='friends')
hs.grant('diana@example.com', 'email.send', requester_email='john@elko.ai')

# Utility
hs.summary()
hs.check_is_super_admin('john@elko.ai')
```

---

## Bootstrap card output

Every session prints:

```
╔══════════════════════════════════════════════════════════╗
║                    ELKO-SKILLS                          ║
╠══════════════════════════════════════════════════════════╣
║  hs-contacts   → 5 contacts (1 admin, 2 family)        ║
║  hs-threads    → 8 threads (5 active), 34 messages     ║
╚══════════════════════════════════════════════════════════╝
```

---

## Testing

```bash
cd /opt/data/elko-skills
python3 -m pytest contacts/tests threads/tests
```
