# Publishing elko-skills to PyPI

## Prerequisites

```bash
pip install build twine hatchling
# For uvx distribution:
pip install uv
```

## Build

Each skill is a separate PyPI package. Build from its directory:

```bash
# elko-util (build first — it's a dependency)
python3 -m build --outdir dist/elko-util/

# elko-contacts
cd contacts
python3 -m build
cd ..

# elko-threads
cd threads
python3 -m build
cd ..
```

## Test on TestPyPI first

```bash
twine upload --repository testpypi contacts/dist/*
twine upload --repository testpypi threads/dist/*

# Verify install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ elko-contacts
uvx --index-url https://test.pypi.org/simple/ elko-contacts
```

## Publish to PyPI

```bash
twine upload contacts/dist/*
twine upload threads/dist/*
twine upload dist/elko-util/*
```

Or use `uv publish` (faster):

```bash
cd contacts && uv publish
cd ../threads && uv publish
```

## After publishing

Test `uvx` install:

```bash
uvx elko-contacts   # should start MCP server
uvx elko-threads
```

Update `smithery.yaml` version to match `pyproject.toml` version, then submit to Smithery.

---

## Documentation hosting

PyPI shows the `README.md` from each package as its description page. That's automatic.

For full searchable docs, two free options:

### Option A — Read the Docs (recommended)

1. Push to GitHub
2. Go to [readthedocs.org](https://readthedocs.org) → Import a Project → connect GitHub
3. Add `.readthedocs.yaml` to repo root:

```yaml
version: 2
build:
  os: ubuntu-22.04
  tools:
    python: "3.12"
mkdocs:
  configuration: mkdocs.yml
```

4. Add `mkdocs.yml` to repo root:

```yaml
site_name: elko-skills
site_url: https://elko-skills.readthedocs.io
repo_url: https://github.com/jsoprych/elko-skills
theme:
  name: material
nav:
  - Home: README.md
  - elko-contacts:
    - Overview: contacts/README.md
    - How-to: contacts/docs/howto.md
  - elko-threads:
    - Overview: threads/README.md
    - How-to: threads/docs/howto.md
  - Platforms:
    - Claude Code: docs/platforms/claude-code.md
    - Cursor: docs/platforms/cursor.md
    - Windsurf: docs/platforms/windsurf.md
    - Hermes: docs/platforms/hermes.md
    - OpenCode: docs/platforms/opencode.md
    - Codex CLI: docs/platforms/codex.md
  - Create a skill: docs/howto-create-a-skill.md
```

5. Docs auto-build on every push. URL: `https://elko-skills.readthedocs.io`

6. Update `[project.urls]` in each `pyproject.toml`:

```toml
Documentation = "https://elko-skills.readthedocs.io"
```

### Option B — GitHub Pages (simpler, no extra service)

Enable GitHub Pages on the repo (Settings → Pages → source: `main` branch, `/docs` folder).
Markdown files in `docs/` are served at `https://jsoprych.github.io/elko-skills/`.

---

## Smithery marketplace submission

Once on PyPI, submit each skill:

1. Go to [smithery.ai](https://smithery.ai/submit)
2. Point to the GitHub repo
3. Smithery reads `smithery.yaml` from each skill directory
4. Each skill gets its own listing: `smithery.ai/server/elko-contacts`

`contacts/smithery.yaml` and `threads/smithery.yaml` are already in the repo.

## PulseMCP submission

Go to [pulsemcp.com](https://pulsemcp.com) → Submit → provide GitHub URL and PyPI package name.

---

## Version bump checklist

1. Update `version` in `pyproject.toml`
2. Update `version` in `smithery.yaml`
3. `git tag v0.x.0 && git push --tags`
4. `python3 -m build && twine upload dist/*`
