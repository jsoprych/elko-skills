# hs-contacts — Elko-Skill HOWTO

**contacts.db** — the canonical record of people: names, emails, phone numbers, platform IDs, permission levels, and circle tags.

---

## Quick install

```bash
git clone https://github.com/jsoprych/elko-skills.git
cd elko-skills
./install.sh contacts                         # production
```

See [`docs/platforms/`](../docs/platforms/) for platform-specific setup.

### Parallel install (dev/test)

```bash
# Development — separate DB, separate registry name, no conflict with prod
./install.sh contacts --profile dev

# Activate dev profile
export ELKO_PROFILE=dev
python3 -c "from contacts import contacts as hs; hs.list_all()"
# → uses /tmp/elko-contacts-dev.db, registered as hs-contacts-dev

# Back to production
unset ELKO_PROFILE
```

Or with a custom suffix:

```bash
./install.sh contacts --suffix my-test
export ELKO_CONTACTS_DB=/tmp/my-test-contacts.db
```

### Uninstall

```bash
./uninstall.sh hs-contacts          # remove production
./uninstall.sh hs-contacts-dev       # remove dev profile
./uninstall.sh hs-contacts --keep-db # remove module, keep data
```

---

## Version

```bash
./install.sh --version
# → elko-skills v0.1.0
```

Or from Python:

```python
from contacts import contacts as hs
hs.get_skill().version()
# → {'elko_framework_version': '0.1.0', 'installed_at': '2026-04-29 04:17:23'}
```

---

## Database

- **Production:** `/opt/data/elko-skills/contacts/contacts.db`
- **Dev (profile):** `/tmp/elko-contacts-dev.db`
- **Env override:** `ELKO_CONTACTS_DB`
- **Tables:** `contacts`, `contact_phones`, `contact_platforms`, `auth_rules`, `meta`
- **Schema:** `schema.sql`

## Key functions

### Lookup

```python
get_by_email("john@elko.ai")           # single contact + phones + platforms
list_all()                              # all contacts
find("pat")                             # fuzzy search (name or email)
check_is_super_admin("john@elko.ai")    # True/False
has_permission("diana@example.com", "email.send")
get_permissions("diana@example.com")    # list of {permission, scope}
```

### Write (every function requires `requester_email` — permission check)

```python
# Add a new contact (super-admin only)
add("Pat Smith", "pat@example.com",
    requester_email="john@elko.ai",
    circle="family", role="contact",
    phone="+15551234567",
    platforms=[{"platform": "telegram", "id": "12345"}])

# Update fields (super-admin only)
update("pat@example.com", "john@elko.ai",
       circle="work", name="Pat Gibson")

# Grant permission (super-admin only)
grant("pat@example.com", "email.send",
      scope="*", requester_email="john@elko.ai")
```

### Stats

```python
summary()     # Returns string: "5 contacts (1 admin, 2 family)"
```

## Common queries

```sql
-- All contacts with phone numbers
SELECT c.name, c.email, cp.number
FROM contacts c
JOIN contact_phones cp ON c.id = cp.contact_id;

-- All super-admins
SELECT name, email FROM contacts WHERE role = 'super-admin';

-- Contacts in a specific circle
SELECT name, email FROM contacts WHERE circle = 'family';
```

## Permission levels

| Role | Can add | Can edit | Can delete | Can grant |
|---|---|---|---|---|
| super-admin | ✅ | ✅ | ✅ | ✅ |
| contact-manager | ✅ | ✅ | ✅ | — |
| viewer | — | — | — | — |
| contact | — | self only | — | — |

## Testing

```bash
cd elko-skills/contacts
python3 -m pytest tests/ -v
```

## Errors

| Error | Cause |
|---|---|
| `Permission denied. ... is not super-admin.` | `requester_email` not in contacts with `role='super-admin'` |
| `Contact {email} already exists.` | Email already in DB |
| `Contact {email} not found.` | Email doesn't match any record |
| `No valid columns to update. Allowed: ...` | kwargs contained only invalid column names |

## Security

- All queries use `?` parameterized placeholders — no SQL injection
- Column names validated against whitelist in `safe_update()`
- Every write checks `requester_email` is a super-admin first
- 5 dedicated injection-resistance tests
