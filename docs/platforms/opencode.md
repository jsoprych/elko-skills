# elko-skills on OpenCode

OpenCode integrates Python modules via its skill config system.

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

### 2. Add to OpenCode config

Edit `~/.opencode/skills.yaml`:

```yaml
skills:
  - name: contacts
    module: contacts.contacts
    path: ~/.elko-skills/contacts
    description: People database with permissions
    functions:
      - list_all
      - get_by_email
      - find
      - add
      - summary

  - name: threads
    module: threads.threads
    path: ~/.elko-skills/threads
    description: Cross-channel conversation tracking
    functions:
      - active
      - capture
      - context
      - summary
```

### 3. Use in OpenCode

```
opencode> contacts.list_all()
opencode> contacts.find('john')
opencode> threads.active()
```

---

## Env var configuration

Set per-skill DB paths in your shell profile:

```bash
export ELKO_CONTACTS_DB=/custom/path/contacts.db
export ELKO_THREADS_DB=/custom/path/threads.db
```
