# hs-contacts — Elko-Skill HOWTO

**contacts.db** — the canonical record of people: names, emails, phone numbers, platform IDs, permission levels, and circle tags.

---

## Database

- **Path:** `/opt/data/elko-skills/contacts/contacts.db`
- **Env override:** `ELKO_CONTACTS_DB`
- **Tables:** `contacts`, `contact_phones`, `contact_platforms`, `contact_auth`
- **Schema:** `elko-skills/contacts/schema.sql`

## Key functions (contacts.py)

### Lookup

```python
get_by_email("john@elko.ai")
get_by_id(1)
search("pat")               # partial match on name or email
list_by_circle("family")
list_all()                  # paginated with offset/limit
list_admins()
```

### Write (requires `requester_email` — permission check)

```python
# Add a new contact (super-admin only)
add("Pat Smith", "pat@example.com",
    requester_email="john@elko.ai",
    circle="family", role="contact",
    phone="+15551234567",
    platforms=[{"platform": "telegram", "id": "12345"}])

# Update (super-admin or yourself)
update(42, {"circle": "friends"}, requester_email="john@elko.ai")

# Change circle (contact-manager or yourself)
update_circle(42, "work", requester_email="john@elko.ai")
```

### Stats

```python
summary()     # Returns dict: total contacts, by circle, by role
```

## Common queries

```sql
-- All contacts with phone numbers
SELECT c.name, c.email, cp.phone
FROM contacts c
JOIN contact_phones cp ON c.id = cp.contact_id;

-- All super-admins
SELECT * FROM contacts c
JOIN contact_auth ca ON c.id = ca.contact_id
WHERE ca.user_role = 'super-admin';
```

## Permission levels

| Role | Can add | Can edit | Can delete | Can grant |
|---|---|---|---|---|
| super-admin | ✅ | ✅ | ✅ | ✅ |
| contact-manager | ✅ | ✅ | ✅ | — |
| viewer | — | — | — | — |
| contact | — | self only | — | — |

## Errors

| Error | Cause |
|---|---|
| `Permission denied: only super-admin can add contacts` | `requester_email` not in auth table with sufficient role |
| `Contact already exists` | Email already in DB |
| `Contact not found` | ID or email doesn't match any record |
