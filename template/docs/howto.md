# hs-template — Elko-Skill HOWTO

<!-- 
Fill this in after you implement your elko-skill.
Remove these instructions and write real documentation.
-->

## Database

- **Path:** `/opt/data/elko-skills/template/template.db`
- **Env override:** `ELKO_TEMPLATE_DB`
- **Tables:** `records`
- **Schema:** `schema.sql`

## Key functions

### Lookup

```python
get(1)              # Get by ID
search("term")      # Search by name
list_all()          # Paginated listing
```

### Write

```python
add(name="Example", value="something", requester_email="admin@elko.ai")
update(1, requester_email="admin@elko.ai", name="New Name")
delete(1, requester_email="admin@elko.ai")
```

## Common queries

```sql
SELECT * FROM records WHERE name LIKE '%term%';
```

## Permission levels

| Role | Can add | Can edit | Can delete |
|---|---|---|---|
| super-admin | ✅ | ✅ | ✅ |
| contact-manager | ✅ | ✅ | — |
| viewer | — | — | — |
| contact | — | — | — |
