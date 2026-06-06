# CI

`ci/ci.yml` is the GitHub Actions workflow for Milestone 1 (migrate + pytest
against a `pgvector/pgvector:pg16` service container).

It lives here rather than under `.github/workflows/` because the token used to
push this repo lacked the `workflow` scope. **To enable CI, move it into place:**

```bash
mkdir -p .github/workflows
git mv ci/ci.yml .github/workflows/ci.yml
git commit -m "Enable CI workflow"
git push
```

Do this with a token that has the `workflow` scope, or add the file through the
GitHub web UI (Actions → new workflow), which has the scope by default.
