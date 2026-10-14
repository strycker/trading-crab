# Releasing to PyPI

Both packages, `trading-crab` (the app, root `pyproject.toml`) and `trading-crab-lib` (the library,
`src/trading_crab_lib/pyproject.toml`), publish from this repository through `.github/workflows/publish-pypi.yml`
with PyPI **Trusted Publishing**: GitHub mints a short-lived upload token for the publish job, so no API token is
stored anywhere (DECISIONS G-24). If this page and the workflow disagree, the workflow wins. Nothing was published in
Phase 9.1.

## 1. What starts a release

Only a tag push or a manual run. **A GitHub Release publishes nothing**, and no branch push publishes anything.

| Tag | Publishes |
|---|---|
| `v0.2.0` | `trading-crab` (the app) only |
| `lib-v0.2.0` | `trading-crab-lib` (the library) only |
| `both-v0.2.0` | both packages, in one run |

**The `v*` trap:** a `v*` tag skips the library leg, and a skipped leg shows **green** in the Actions UI. Read the
gate line of each leg ("Decide whether to publish this leg") on every run. Each prints exactly one of:

- `PUBLISH: <leg> ...`: this leg builds, is checked and uploads;
- `SKIP: <leg> reason=...`: this leg does nothing this run.

Wanted both packages but see one `PUBLISH:`? You meant `both-v*`. Other tags, such as `legacy/quarterly-final`, match
no prefix and never start the workflow.

## 2. Before you tag

1. Bump **both** `pyproject.toml` versions (and the app's `trading-crab-lib>=` floor if the library changed).
2. Run the checks locally: `pytest tests -q -p no:cacheprovider`, both `python -m build` commands and
   `bash scripts/check_wheels.sh dist-lib dist-app`.
3. Merge to `main`, then tag `main`: `git tag -a both-v0.2.0 -m "Release 0.2.0" && git push origin both-v0.2.0`.

On a tag push the build job refuses any file of the selected leg whose version differs from the tag ("bump both
pyproject versions or retag"), before anything uploads.

## 3. Burned versions are permanent

A version once uploaded to PyPI (or TestPyPI) can never be uploaded again, even after deleting it in the web UI.
**0.1.3 and 0.1.4 are burned** (0.1.3 by a failed attempt; 0.1.4 shipped an empty library wheel), **0.1.5 is live**,
and **0.2.0 is unpublished** (Phase 9.1 bumped the versions and published nothing). Treat every version as one shot:
verify before you tag.

## 4. The TestPyPI rehearsal

Actions → **Publish to PyPI** → **Run workflow**: choose the branch and `package`, leave `target` at `testpypi` (the
default). The run builds, checks and uploads to `https://test.pypi.org/legacy/` through the `testpypi` environment.
It burns that version **on TestPyPI only**. A manual run with `target: pypi` reaches real PyPI only from a release
tag, and only after Glenn approves it (§7.3).

## 5. The checks every selected leg passes before any upload

- `twine check --strict`: metadata (a missing README once gave a blank PyPI page).
- `scripts/check_wheels.sh dist-lib dist-app`: installs both freshly built wheels in a new venv, imports them from
  site-packages and runs `tradingcrab --help`. **Releases 0.1.0 to 0.1.4 of the library shipped zero Python
  modules**: build, twine and the version guard all passed, because none of them looks inside the wheel. Only
  install-and-import catches an empty wheel. Keep the library's explicit `package-dir` and `packages` list; never
  reintroduce a discovery glob there.
- The publish job runs only if every selected leg passed (`needs: build`); it checks out no code and only uploads.

## 6. Never couple the two legs

The legs run in parallel. On `both-v0.1.5` the app leg's smoke test resolved `trading-crab-lib>=0.1.5` from PyPI six
seconds before the library leg published it, and the release half-shipped. Here each leg builds **both** packages
and installs the two local wheels together, so no leg waits on PyPI. No step in one leg may depend on the other.

To finish a half-shipped release, publish only the missing half with its own prefix (for example `v0.2.0` when the
library is already up); never burn a new version for it.

## 7. One-time setup (Glenn, before the first release from this repo)

1. **PyPI publishers.** On pypi.org → Your projects → `trading-crab` → Manage → Publishing → "Add a new publisher"
   (GitHub): owner `strycker`, repository `trading-crab`, workflow `publish-pypi.yml`, environment `pypi`. Repeat for
   `trading-crab-lib`.
2. **TestPyPI publishers.** The same on test.pypi.org with environment `testpypi`, for both projects (a "pending
   publisher" where the TestPyPI project does not exist yet).
3. **GitHub environments.** strycker/trading-crab → Settings → Environments: create `pypi` and `testpypi`. Both
   `pypi` settings are **required**: Glenn as required reviewer, so every real publish waits for his click; and under
   "Deployment branches and tags", "Selected branches and tags" with the tag rules `v*`, `lib-v*` and `both-v*`, so no
   manual or branch run can reach real PyPI. Leave `testpypi` open for rehearsals.
4. **Retire the old tokens.** Revoke `PYPI_APP_TOKEN` and `PYPI_LIB_TOKEN` on pypi.org and `TEST_PYPI_API_TOKEN` on
   test.pypi.org, then delete those three secrets in claude-scratch-work → Settings → Secrets and variables → Actions
   (and in its `pypi` environment, if stored there). The scratch repo no longer publishes.

## 8. The legacy tree

The last legacy quarterly tree (before the Phase 9.1 skeleton) is the tag `legacy/quarterly-final`, on `b3e80b3`:
https://github.com/strycker/trading-crab/tree/legacy/quarterly-final. Glenn pushed it; it publishes nothing.
