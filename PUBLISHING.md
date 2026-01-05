# Publishing `osmsatlab`

This guide describes the process for publishing new versions of `osmsatlab` to PyPI using [Poetry](https://python-poetry.org/).

## Prerequisites

1.  **PyPI Account**: You must have an account on [PyPI](https://pypi.org/).
2.  **API Token**: Generate an API token on PyPI (Account Settings -> API Tokens).
3.  **Poetry**: Ensure you have Poetry installed.

## Workflow

### 1. Update Version

We use [Semantic Versioning](https://semver.org/).
Update the version number in `pyproject.toml` using the `poetry version` command.

```bash
# For a patch release (e.g., 0.1.0 -> 0.1.1)
poetry version patch

# For a minor release (e.g., 0.1.0 -> 0.2.0)
poetry version minor

# For a major release (e.g., 0.1.0 -> 1.0.0)
poetry version major
```

### 2. Build the Package

Create the distribution files (`.tar.gz` and `.whl`) in the `dist/` directory.

```bash
poetry build
```

**Verify the build:**
Check the `dist/` folder to ensure the files were created and look correct.

### 3. Publish to PyPI

**Configure your API Token:**
You only need to do this once per machine (or if you regenerate your token).

```bash
poetry config pypi-token.pypi <your-pypi-api-token>
```

**Publish:**
Upload the package to PyPI.

```bash
poetry publish
```

> **Note:** To quickly build and publish in one step, you use: `poetry publish --build`

### 4. Git Tagging

After successfully publishing, it's good practice to tag the commit in git.

```bash
git add pyproject.toml
git commit -m "Bump version to <new-version>"
git tag v<new-version>
git push && git push --tags
```

## Checklist Before Publishing

- [ ] All tests pass (`pytest`).
- [ ] `README.md` is up-to-date.
- [ ] `pyproject.toml` metadata (dependencies, description) is correct.
- [ ] Version number is updated.
