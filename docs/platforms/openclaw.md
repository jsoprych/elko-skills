# elko-skills on OpenClaw

OpenClaw agents use Python native modules. The elko-skill pattern — Python module + SQLite DB — is a natural fit.

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

### 2. Import in your Claw scripts

```python
import sys
sys.path.insert(0, os.path.expanduser('~/.elko-skills/contacts'))

import claws
from contacts import contacts as hs

# Use in your claw handlers
@claws.command('whois')
def whois(email: str):
    contact = hs.get_by_email(email)
    if contact:
        return f"{contact['name']} — {contact['circle']}, {contact['role']}"
    return "Not found"

@claws.command('add-contact')
def add_contact(name: str, email: str, requester: str):
    result = hs.add(name, email, requester_email=requester)
    return result.get('success', result.get('error'))
```

---

## Testing

```bash
cd ~/.elko-skills/contacts
python3 -m pytest tests/
```
