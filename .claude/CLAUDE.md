# Pipeline Whisperer - Development Guardrails

## Branch Strategy

**Always create feature branches before implementing:**
```bash
git checkout -b feat/phase<N>-<feature-name>
```

**Examples:**
- `feat/phase1-lead-ingestion`
- `feat/phase2-outreach-orchestration`
- `feat/phase3-feedback-loop`

## Implementation Workflow

### 1. **Plan** (Before Code)
- Review PLAN.md for phase requirements
- Create todo list with TodoWrite tool
- Break down into testable increments

### 2. **Implement** (During Code)
- Update todo list as you progress
- Mark tasks in_progress → completed
- Keep commits atomic (one logical change)

### 3. **Validate** (Before Commit)

**Always validate based on implementation type:**

#### Python Changes
```bash
# Syntax check
uv run --directory apps/agent-api python -m py_compile <file.py>

# Type hints (if added)
uv run --directory apps/agent-api mypy <file.py>

# Run affected tests
uv run --directory apps/agent-api pytest <test_file.py>
```

#### TypeScript/Next.js Changes
```bash
cd apps/web
pnpm build  # Catches TypeScript errors
pnpm lint   # ESLint validation
```

#### Database Changes
```bash
# Generate migration
cd apps/agent-api
uv run alembic revision --autogenerate -m "description"

# Apply migration
uv run alembic upgrade head

# Verify schema
sqlite3 pipeline.db ".schema"
```

#### API Changes
```bash
# Start server
cd apps/agent-api
uv run python main.py &
sleep 3

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/docs  # Check OpenAPI spec

# Kill server
pkill -f "python main.py"
```

#### Full Integration Test
```bash
# If adding new Kafka producer/consumer
./scripts/start-infra.sh  # Docker must be running

# Run end-to-end test
uv run --directory apps/agent-api python scripts/check_env.py
```

### 4. **Commit** (After Validation)

**Only commit after validation passes.**

**Commit Message Format:**
```
<Short Title> (max 72 chars)

<Detailed body explaining:>
- What changed
- Why it changed
- How to test it

Files changed:
- path/to/file.py (added feature X)
- path/to/file2.py (updated logic Y)

Phase <N> progress: <X>/<Y> tasks complete

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### 5. **Create PR** (After Commit)

**Use `gh` CLI for PRs:**

```bash
gh pr create \
  --title "Phase <N>: <Concise Feature Description>" \
  --body "$(cat <<'EOF'
## Summary
<1-3 sentence overview>

## Changes
- Feature A: <description>
- Feature B: <description>

## Files Changed
- `path/to/file.py` - <what changed>
- `path/to/file2.py` - <what changed>

## Phase <N> Progress
- [x] Task 1
- [x] Task 2
- [ ] Task 3 (next)

## Testing
<How to test this PR>

## Screenshots (if UI)
<Add if applicable>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

## Validation Rules

### Never Commit Without:
1. ✅ **Syntax validation** - No Python/TS errors
2. ✅ **Build check** - Code compiles/runs
3. ✅ **Schema validation** - DB migrations apply cleanly
4. ✅ **API validation** - Endpoints respond correctly (if changed)
5. ✅ **Dependency check** - `uv pip install -e .` succeeds

### Optional But Recommended:
- Run integration test with simulator
- Check Sentry for errors (if configured)
- Test with curl/API docs
- Verify Kafka messages flow (if streaming changed)

## Anti-Patterns to Avoid

❌ **Don't:**
- Commit directly to main
- Commit without validation
- Mix multiple features in one commit
- Use vague commit messages ("fix stuff")
- Push broken code

✅ **Do:**
- Create feature branches
- Validate before every commit
- Keep commits atomic and logical
- Write descriptive commit messages
- Test integration points

## Phase-Specific Validation

### Phase 1 (Lead Ingestion)
- Run simulator: `uv run --directory apps/agent-api python services/simulators/lightfield_simulator.py`
- Test worker: `uv run --directory apps/agent-api python services/workers/lead_scorer_worker.py`
- Check DB: `sqlite3 apps/agent-api/pipeline.db "SELECT COUNT(*) FROM leads;"`

### Phase 2 (Outreach)
- Test Truefoundry integration
- Verify outreach.events topic
- Check experiment assignment

### Phase 3 (Feedback)
- Test conversion tracking
- Verify A/B experiment updates
- Check Sentry metrics

## Emergency Rollback

If validation fails after commit:

```bash
# Revert last commit (keeps changes)
git reset HEAD~1

# Fix issues, re-validate, re-commit
<validate again>
git add -A
git commit -m "..."
```

## CI/CD Readiness

All validation steps mirror what CI would check:
1. Syntax errors
2. Build success
3. Test passage
4. Schema validity

Passing local validation = passing CI.

## Questions?

- Check PLAN.md for phase requirements
- Check docs/phase-N-testing.md for test procedures
- Check README.md for setup instructions

---

**Last Updated:** 2025-10-17
**For:** Pipeline Whisperer Hackathon Project
