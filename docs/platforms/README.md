# Platform Setup Guides

How to integrate elko-skills into any agent framework. Each guide covers:

1. **What to install** (one `pip` or `python3` command)
2. **Where to configure** (config file, env vars, or init script)
3. **How to call it** (import, CLI, or skill binding)
4. **How to test it** (run the test suite)

## Available platforms

| Guide | Agent | Import Method |
|---|---|---|
| [Hermes](hermes.md) | Native Hermes Agent | Python import + registry |
| [Claude Code](claude-code.md) | Anthropic's Claude Code (ACP) | Python subprocess |
| [Codex CLI](codex.md) | OpenAI Codex CLI | Tool/config file |
| [OpenClaw](openclaw.md) | OpenClaw agent | Python import |
| [OpenCode](opencode.md) | OpenCode agent | Skill config file |

## Quick install (any platform)

```bash
curl -sS https://raw.githubusercontent.com/jsoprych/elko-skills/main/install.sh \
  | bash -s -- contacts
```

See `install.sh` for full options.
