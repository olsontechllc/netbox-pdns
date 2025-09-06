# GitLab CI to GitHub Actions Migration

This document outlines the conversion from GitLab CI to GitHub Actions workflows.

## GitLab CI vs GitHub Actions Mapping

| GitLab CI Job | GitHub Actions Workflow | Purpose |
|---------------|--------------------------|---------|
| `mypy` | `ci.yml` (lint job, mypy matrix) | Type checking with mypy |
| `ruff-check` | `ci.yml` (lint job, ruff-check matrix) | Code linting |
| `ruff-format` | `ci.yml` (lint job, ruff-format matrix) | Code formatting check |
| `pytest-python-3.11` | `ci.yml` (test job, Python 3.11 matrix) | Testing on Python 3.11 |
| `pytest-python-3.12` | `ci.yml` (test job, Python 3.12 matrix) | Testing on Python 3.12 |
| `pytest-python-3.13` | `ci.yml` (test job, Python 3.13 matrix) | Testing on Python 3.13 |
| `all-checks-python-3.11` | `ci.yml` (all-checks job) | Combined validation |
| `build-docker` | `docker.yml` (build job) | Docker image building |
| N/A | `docs.yml` | Documentation deployment (new) |
| N/A | `release.yml` | Automated releases (new) |

## Key Improvements in GitHub Actions

### Enhanced Features

1. **Multi-platform Docker builds**: Now builds for both `linux/amd64` and `linux/arm64`
2. **Automated releases**: Creates GitHub releases with changelogs on version tags
3. **Documentation deployment**: Automatic GitHub Pages deployment
4. **Coverage reporting**: Integrated Codecov reporting
5. **Caching**: Improved caching strategy for uv dependencies

### Trigger Improvements

- **GitLab CI**: Runs on all pushes and merges
- **GitHub Actions**: 
  - CI: Runs on push/PR to `main`/`develop` branches
  - Docker: Runs on push to `main`/`develop`, tags, and PRs to `main`
  - Docs: Runs on documentation changes only
  - Release: Runs only on version tags

### Registry Changes

- **GitLab CI**: Uses GitLab Container Registry (`$CI_REGISTRY_IMAGE`)
- **GitHub Actions**: Uses GitHub Container Registry (`ghcr.io`)

## Migration Benefits

### Performance
- **Parallel execution**: Lint jobs run in parallel using matrix strategy
- **Efficient caching**: Better cache key strategies for uv dependencies
- **Multi-platform builds**: Single job builds for multiple architectures

### Security
- **GITHUB_TOKEN**: Built-in token for container registry access
- **Secrets management**: Centralized secret management for external services
- **Permissions**: Explicit permission declarations for each workflow

### Observability
- **Coverage reporting**: Automatic Codecov integration
- **Release automation**: Automated changelog generation
- **Status checks**: Clear status reporting on PRs

## Required Secrets

To use all features, configure these repository secrets:

| Secret Name | Purpose | Required For |
|-------------|---------|--------------|
| `CODECOV_TOKEN` | Coverage reporting | `ci.yml` |
| `DOCKERHUB_USERNAME` | Docker Hub description updates | `docker.yml` |
| `DOCKERHUB_TOKEN` | Docker Hub description updates | `docker.yml` |

## Workflow Files

1. **`.github/workflows/ci.yml`**: Main CI pipeline (lint, test, coverage)
2. **`.github/workflows/docker.yml`**: Docker image building and publishing
3. **`.github/workflows/docs.yml`**: Documentation building and deployment
4. **`.github/workflows/release.yml`**: Automated release creation

## Migration Checklist

- [x] Convert lint jobs to GitHub Actions matrix strategy
- [x] Convert test jobs with Python version matrix
- [x] Convert Docker build job with multi-platform support  
- [x] Add coverage reporting integration
- [x] Add documentation deployment workflow
- [x] Add automated release workflow
- [x] Update container registry from GitLab to GitHub
- [x] Configure proper workflow triggers
- [x] Document required repository secrets