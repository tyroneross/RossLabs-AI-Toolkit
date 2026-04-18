# Autoresearch Profiles — Pre-Configured Targets

Reference document. Each profile is a ready-to-use autoresearch configuration. Pass the values directly to `--init` or let `detect_autoresearch_targets()` propose them.

---

## Profile Index

| Profile | Target | Direction | Default Budget |
|---------|--------|-----------|----------------|
| `optimize-build` | Build/CI time | lower | 20 |
| `optimize-tests` | Test coverage | higher | 15 |
| `optimize-prompt` | Prompt/skill quality | higher | 10 |
| `optimize-docs` | Doc quality | higher | 10 |
| `optimize-perf` | Runtime performance | lower | 20 |

---

## optimize-build

**When to use:** Build time is measurably slow (>30s), CI minutes are expensive, or bundle size is affecting load performance.

**Scope:** `*.config.*`, `webpack.*`, `vite.config.*`, `tsconfig.*`, `package.json`, `Makefile`, `Dockerfile`

**Metric commands by stack:**

```bash
# Node/Vite — wall-clock build time
time npm run build 2>&1 | grep real | awk '{print $2}'

# Node — bundle size (bytes)
npm run build --silent && du -sb dist/ | awk '{print $1}'

# Rust — compile time
cargo build --release 2>&1 | grep "Finished" | grep -oP '[0-9]+\.[0-9]+(?=s)'

# Swift/Xcode
xcodebuild -scheme MyApp -configuration Release build 2>&1 | grep "Build complete" -A1
```

**Guard commands:**

```bash
# Must pass all tests
npm test

# Must produce a valid build artifact
[ -f dist/index.js ] && node dist/index.js --help
```

**Typical iteration patterns:**
- Tree-shaking unused exports
- Code-splitting lazy routes
- Moving heavy deps to dynamic imports
- Tightening `tsconfig` include/exclude
- Removing redundant babel transforms
- Parallelizing independent build steps

**Overfitting risks:**
- Removing source maps (fast build, worse debugging)
- Disabling type checking (`transpileOnly`) — guard cmd must catch this
- Hard-coding environment assumptions that break in CI

---

## optimize-tests

**When to use:** Test suite is slow (impeding CI feedback loop), coverage is below a target threshold, or there are flaky tests.

**Scope:** `**/*.test.*`, `**/*.spec.*`, `**/__tests__/**`, `jest.config.*`, `vitest.config.*`, `pytest.ini`, `conftest.py`

**Metric commands by stack:**

```bash
# Jest — statement coverage percentage
npx jest --coverage 2>&1 | grep "Stmts" | awk '{print $4}'

# Jest — total test duration (seconds)
npx jest --forceExit 2>&1 | grep "Time:" | awk '{print $2}'

# Vitest — coverage
npx vitest run --coverage 2>&1 | grep "Stmts" | awk '{print $4}'

# Python/pytest — coverage
pytest --cov=src --cov-report=term 2>&1 | grep "TOTAL" | awk '{print $NF}' | tr -d '%'

# Python — test duration
pytest --tb=no -q 2>&1 | grep "passed" | grep -oP '[0-9]+\.[0-9]+(?=s)'
```

**Guard commands:**

```bash
# All tests must still pass
npx jest --passWithNoTests

# Pytest
pytest --tb=short -q
```

**Typical iteration patterns:**
- Adding missing branch tests
- Extracting shared fixtures to reduce duplication
- Parallelizing test suites with `--maxWorkers`
- Replacing slow integration tests with focused unit tests
- Fixing flaky async tests with proper awaits

**Overfitting risks:**
- Writing tests that test implementation details, not behavior
- Adding coverage for dead code paths just to raise the number
- Disabling slow-but-important integration tests

---

## optimize-prompt

**When to use:** A prompt, skill, or agent instruction set has measurable eval scores below target, or produces inconsistent output quality.

**Scope:** `prompts/**`, `skills/**/*.md`, `agents/**/*.md`, `*.prompt.md`, `*.prompt.txt`

**Metric commands:**

```bash
# Custom eval runner (outputs 0-100 score)
node evals/run-evals.mjs 2>&1 | grep "Total:" | awk '{print $2}'

# Python eval harness
python3 evals/run.py --suite default 2>&1 | grep "score:" | awk '{print $2}'

# Pass@K style (% of N runs that pass criteria)
python3 evals/pass_at_k.py --prompt skills/myprompt/SKILL.md --k 10 2>&1 | grep "pass_rate:" | awk '{print $2}'
```

**Guard commands:**

```bash
# Safety/validation language must still be present
grep -rq "safety\|guard\|validate\|verify" skills/

# No prompt must exceed token budget
python3 scripts/check_token_budget.py --max 2000 skills/
```

**Typical iteration patterns:**
- Tightening scope-check sections (fewer false triggers)
- Reordering instructions to front-load highest-signal rules
- Replacing vague language with concrete criteria
- Adding worked examples for ambiguous cases
- Removing redundant phrasing that adds tokens without signal

**Overfitting risks:**
- Optimizing for a narrow eval harness that doesn't represent real inputs
- Removing nuance that handles edge cases correctly
- Hardcoding expected outputs that make evals pass trivially

---

## optimize-docs

**When to use:** Documentation quality is measurably poor (eval rubric), onboarding time is high, or docs are known to be stale.

**Scope:** `docs/**/*.md`, `README.md`, `CONTRIBUTING.md`, `*.md` (configurable)

**Metric commands:**

```bash
# LLM-as-judge rubric (outputs 0-100)
node evals/doc-quality.mjs --file README.md 2>&1 | grep "score:" | awk '{print $2}'

# Python rubric runner
python3 evals/doc_rubric.py --path docs/ 2>&1 | grep "aggregate:" | awk '{print $2}'

# Word count proxy (for docs that are known to be too thin)
wc -w docs/getting-started.md | awk '{print $1}'
```

**Guard commands:**

```bash
# All internal links must resolve
node scripts/check-links.mjs docs/

# All code examples must be syntactically valid
python3 scripts/validate_code_blocks.py docs/
```

**Typical iteration patterns:**
- Expanding thin sections with concrete examples
- Replacing vague language ("it works") with specific behavior descriptions
- Adding prerequisite and next-steps sections
- Removing outdated version-specific instructions
- Fixing broken code examples

**Overfitting risks:**
- Adding content that scores well on the rubric but reads poorly to humans
- Inflating word count without adding information density
- Optimizing for a rubric that doesn't reflect real reader needs — the guard cmd factual check is critical here

---

## optimize-perf

**When to use:** A hot-path function, endpoint, or pipeline has a measurable latency or throughput problem.

**Scope:** Specific source files containing the hot path (avoid wide globs — scope tightly to prevent unintended side effects)

**Metric commands by stack:**

```bash
# Node — p95 latency via autocannon
npx autocannon -c 10 -d 5 http://localhost:3000/api/target 2>&1 | grep "99%" | awk '{print $2}'

# Node — benchmark script (outputs ms)
node benchmarks/hot-path.mjs 2>&1 | grep "mean:" | awk '{print $2}'

# Python — timeit
python3 -m timeit -n 100 -r 5 "import mymodule; mymodule.hot_path()" 2>&1 | grep "per loop" | awk '{print $1}'

# Rust — criterion benchmark
cargo bench 2>&1 | grep "time:" | awk '{print $3}'

# Swift — XCTest measure block output
xcodebuild test -scheme MyApp 2>&1 | grep "average:" | awk '{print $2}'
```

**Guard commands:**

```bash
# All tests still pass
npm test

# Pytest
pytest -q

# Output correctness check
node scripts/verify-output.mjs
```

**Typical iteration patterns:**
- Replacing O(n²) lookups with Map/Set
- Memoizing expensive pure computations
- Moving invariant work outside hot loops
- Batching sequential async calls
- Replacing synchronous I/O with streams
- Eliminating redundant serialization/deserialization

**Overfitting risks:**
- Removing correctness checks inside the hot path (faster but wrong)
- Hardcoding inputs that the benchmark happens to hit efficiently
- Micro-optimizing a path that is not actually the bottleneck (always profile first)
- Sacrificing readability for marginal gains in non-critical paths

---

## Choosing a Profile

1. Run the benchmark/test/build command manually first. Confirm it outputs a stable number.
2. Verify the guard command passes on the current codebase before starting the loop.
3. Set a conservative budget first (10 iterations). Increase only if progress is strong.
4. If you are unsure which profile fits, pass the goal to `detect_autoresearch_targets()` and let Phase 1 (Opus) decide.
