# docs/

Per-skill HOWTO documentation for every elko-skill in the repo.

```
docs/
├── README.md                           ← You are here
├── howto-create-a-skill.md             ← Walkthrough: building a new elko-skill from scratch
├── hs-contacts.md → (link)            ← contacts/docs/howto.md
└── hs-threads.md → (link)             ← threads/docs/howto.md
```

## Quick reference

| Skill | DB | Purpose | Permissions |
|---|---|---|---|
| [hs-contacts](hs-contacts.md) | contacts.db | People, names, emails, phones, platforms, roles | Role-based hierarchy |
| [hs-threads](hs-threads.md) | threads.db | Cross-channel conversation tracking | None (capture-only) |

## Creating a new elko-skill

See [howto-create-a-skill.md](howto-create-a-skill.md) for a complete walkthrough, or use the template at `template/` to bootstrap.
