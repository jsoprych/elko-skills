# elko-skills on Claude Code (ACP)

Claude Code connects via the Agent Communication Protocol (ACP) bridge. The elko-skill runs as a Python subprocess with a stdio transport.

---

## One-liner

```bash
./install.sh contacts
```

The installer detects `claude` in PATH and prints the right CLAUDE.md entry.

---

## Manual setup

### 1. Clone

```bash
git clone https://github.com/jsoprych/elko-skills.git ~/.elko-skills
```

### 2. Add to CLAUDE.md

```markdown
## elko-skill: contacts

People database with permissions. Import in Python:

```python
import sys
sys.path.insert(0, '~/.elko-skills/contacts')
from contacts import contacts as hs

# List all contacts
hs.list_all()
# → [{'name': 'John', 'email': 'john@elko.ai', ...}]

# Find someone
hs.find('john')
# → [{'name': 'John Soprych', 'email': 'john@elko.ai', ...}]

# Add a contact (requires super-admin)
hs.add('Alice', 'alice@example.com', requester_email='john@elko.ai')
# → {'success': True, 'id': 42, ...}
```

## ACP bridge

For direct actor-to-actor communication:

```bash
claude --acp --stdio --skill ~/.elko-skills/contacts/contacts.py
```

This exposes every function as an ACP tool:
- `list_all()` → tool
- `find(query)` → tool with string parameter
- `add(name, email, requester_email)` → tool with 3 string parameters
