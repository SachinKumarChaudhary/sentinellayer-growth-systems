# SentinelLayer Laptop Test Guide

## Quick start

Linux/macOS:
1. Install Git, Python 3.11+, and Docker.
2. Clone the repository.
3. Run ./scripts/setup-test.sh
4. Run ./scripts/doctor.sh
5. Run ./scripts/test-system.sh

Windows PowerShell:
1. Install Git, Python 3.11+, and Docker Desktop.
2. Clone the repository.
3. Run .\scripts\setup-test.ps1
4. Run .\scripts\doctor.ps1
5. Run .\scripts\test-system.ps1

## Database

Integration tests require SL_DATABASE_URL for the designated non-production Supabase/PostgreSQL environment. Never use production database credentials for routine laptop testing.

## Email safety

Normal laptop testing forces development mode and real email disabled. A real SMTP test is a separate controlled procedure using a dedicated test mailbox. Never commit SMTP credentials.

## Expected result

The automated gate runs Ruff, MyPy, unit tests, contract tests, integration tests, and a Docker build. A successful run produces test-results/test-report.txt.

## If something fails

Send the complete terminal output and test report to the developer. Do not disable safety checks or paste secrets. Include the commit SHA being tested.
