# GitHub Connector Diagnostic Guide

## Purpose

Use this guide before declaring that GitHub is unavailable. A failure in one repository, endpoint, tool, permission scope, or tool invocation does not establish a global GitHub outage.

## Known-good test repository

`SachinKumarChaudhary/sentinellayer-growth-systems`

The connected GitHub account has been directly verified against this repository.

Current reported permissions:

- pull: true
- push: true
- maintain: true
- admin: true
- triage: true

## Diagnostic sequence

### 1. Test authentication

Call the authenticated-user/login tool.

Expected login:

`SachinKumarChaudhary`

If this succeeds, GitHub authentication is working.

### 2. Test repository discovery

Call the repository-listing tool.

Expected to see:

`SachinKumarChaudhary/sentinellayer-growth-systems`

If this succeeds, the connector can communicate with GitHub and see repositories.

### 3. Test repository metadata

Fetch:

`SachinKumarChaudhary/sentinellayer-growth-systems`

Confirm the reported permissions include pull, push, maintain, and admin.

### 4. Test actual content access

Fetch a known file such as:

`.github/workflows/test.yml`

or `README.md`.

If this succeeds, repository read access is working.

### 5. Test GitHub Actions

Query the repository's workflow runs.

The repository has returned real workflow execution data, including a `total_count` and individual run records.

### 6. Distinguish failure types

Do not treat all errors as GitHub outages.

- Missing tool → connector/tool capability limitation.
- 404 from a particular API request → resource, path, repository-scope, or permission issue.
- Validation error → incorrect tool arguments.
- Repository not visible → repository scope/permission issue.
- Authentication error → connector authentication issue.
- Reproducible GitHub API 5xx/service-unavailable responses across independent operations → possible GitHub/service outage.

### 7. Do not infer global outage from one failed operation

A failed repository lookup, workflow query, branch query, file operation, or malformed request does not prove GitHub is unavailable.

Retry with the known-good SentinelLayer repository and a basic operation such as:

- get_user_login
- list_repositories
- get_repo
- fetch_file

### 8. Report precisely

Prefer:

> "GitHub connector is operational, but this particular repository/tool/endpoint is inaccessible."

Do not report:

> "GitHub is unavailable."

unless the connector/service itself has been tested and is actually failing.

## Current verification

The GitHub connector has been directly verified as operational. The SentinelLayer repository is accessible with repository-level admin and push permissions.

The repository currently exposed to the connector should be used as the baseline when diagnosing future GitHub problems.
