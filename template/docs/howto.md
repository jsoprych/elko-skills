# hs-template — Elko-Skill HOWTO

<!-- Fill this in after you implement your elko-skill. -->

## Quick install

```bash
git clone https://github.com/jsoprych/elko-skills.git
cd elko-skills
cp -r template/ my-skill-name/
# Then follow docs/howto-create-a-skill.md
```

## Version

```python
from my_skill import my_skill as s
s.get_skill().version()
```

## Parallel install (dev/test)

```bash
./install.sh my-skill --profile dev
export ELKO_PROFILE=dev
python3 -c "from my_skill import my_skill as s; s.list_all()"
unset ELKO_PROFILE
```

## Database

- **Path:** `/opt/data/elko-skills/my-skill/my-skill.db`
- **Env override:** `ELKO_MYSKILL_DB`
- **Schema:** `schema.sql`

## Key functions

### Lookup

```python
get(id)              # Get by ID
search("term")      # Search by name
list_all()          # Paginated listing
```

### Write

```python
add(name="Example", value="something", requester_email="admin@elko.ai")
update_record(id, requester_email="admin@elko.ai", name="New Name")
delete(id, requester_email="admin@elko.ai")
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
