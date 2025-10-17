# Migration to uv - Python Package Management

## Summary

Migrated from `pip + venv` to **`uv`** for faster, modern Python package management.

## Key Changes

1. **Added `pyproject.toml`** - Modern Python project standard (PEP 621)
2. **Updated setup scripts** - Auto-install uv, use `uv venv` and `uv pip`
3. **New convenience scripts** - `pnpm dev:api`, `pnpm test:api`, `pnpm lint:api`
4. **Virtual env location** - Changed from `venv/` to `.venv/`

## Benefits

- **10-100x faster** dependency installation
- **Parallel downloads** with global cache
- **No activation needed** - use `uv run python main.py`
- **Modern tooling** - pyproject.toml, ruff, black included

## Quick Reference

```bash
# Install dependencies
uv pip install -e .

# Run without activation
uv run python main.py

# Traditional activation still works
source .venv/bin/activate && python main.py
```

See SETUP.md for complete usage guide.
