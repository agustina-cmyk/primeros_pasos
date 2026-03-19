---
description: Generate Docker-based test runner scripts adapted to the project's tech stack. Use when the user says "generate test scripts", "create test runner", "setup Docker tests", or needs run-tests.sh and clean-test-cache.sh.
---

# SDD Utility: Generate Test Runner Scripts
A skill that analyzes the project's tech stack and generates `run-tests.sh` and `clean-test-cache.sh` scripts that run
tests inside Docker containers with volume caching for fast repeated runs.

# When to Use This Skill
## Ideal scenarios:
- When the project needs Docker-based test runner scripts and does not have them yet.
- When the existing test runner scripts are outdated or based on a different tech stack.


# How to generate the scripts

1. **Read and validate the project settings.** Read `.sdd.json` to resolve the paths `paths.run_tests` and
   `paths.clean_test_cache`. These are the file paths where the generated scripts will be saved.

   **If `.sdd.json` does not exist or is missing `paths.run_tests` / `paths.clean_test_cache`**: stop and
   inform the user:
   *"No `.sdd.json` found (or missing required paths). Run `sdd init` first to initialize this project."*
   Do NOT proceed without valid paths.

2. **Read the project documentation.** Read the following folders to understand the project:
    - @{paths.docs}/code/
    - @{paths.docs}/architecture/
    - @{paths.docs}/testing/ (if it exists)

3. **Detect the project's tech stack.** Scan the project root for stack-identifying files. Check for the presence of
   these files (in order of priority — stop at the first match):

   | File found            | Stack        | Docker image (example)         | Test command (example)          | Cache path inside container         |
   |-----------------------|--------------|--------------------------------|---------------------------------|-------------------------------------|
   | `build.gradle`        | Gradle/JVM   | `gradle:8.5-jdk17`            | `gradle test --no-daemon`       | `/home/gradle/.gradle`              |
   | `build.gradle.kts`    | Gradle/JVM   | `gradle:8.5-jdk17`            | `gradle test --no-daemon`       | `/home/gradle/.gradle`              |
   | `pom.xml`             | Maven/JVM    | `maven:3.9-eclipse-temurin-17`| `mvn test`                      | `/root/.m2`                         |
   | `package.json`        | Node.js      | `node:20-alpine`              | `npm test`                      | `/root/.npm`                        |
   | `requirements.txt`    | Python       | `python:3.12-slim`            | `pytest`                        | `/root/.cache/pip`                  |
   | `pyproject.toml`      | Python       | `python:3.12-slim`            | `pytest`                        | `/root/.cache/pip`                  |
   | `go.mod`              | Go           | `golang:1.22-alpine`          | `go test ./...`                 | `/go/pkg/mod`                       |
   | `Cargo.toml`          | Rust         | `rust:1.77`                   | `cargo test`                    | `/usr/local/cargo/registry`         |
   | `composer.json`       | PHP          | `php:8.3-cli`                 | `vendor/bin/phpunit`            | `/root/.composer`                   |

   The table above is a **starting point**. Read the actual project files (e.g., `package.json` scripts, `build.gradle`
   plugins, `pyproject.toml` tool sections) to determine the **exact** Docker image version, test command, and any
   additional setup required (dependency install step, env vars, etc.).

   If the stack cannot be determined automatically, ask the user using AskUserQuestion:
   - "I could not detect your project's tech stack automatically. What language/framework does this project use, and
     what command runs the tests?"

4. **Read the reference scripts.** Read the example scripts in the current skill folder to understand the structural
   pattern you must follow:
    - `reference-run-tests.sh` (in this skill's folder)
    - `reference-clean-test-cache.sh` (in this skill's folder)

   These scripts are built for a Gradle/JDK project. You will use them as a **structural template** — keep the same
   overall flow but replace the stack-specific parts.

5. **Determine the project name.** Derive a short, kebab-case project identifier from the project root folder name or
   from the project manifest (e.g., `name` field in `package.json`). This will be used for:
   - The Docker cache volume name: `{project-name}-test-cache`
   - Banner text in the script output
   - Docker image grep patterns in the clean script

6. **Check for credentials or environment variables.** Look for files that suggest private registry access or
   environment-specific configuration:
   - `local.env`, `.env`, `.env.example`
   - `.npmrc`, `.yarnrc`, `pip.conf`, `settings.xml`
   - `docker-compose.yml` (env vars section)

   If the project requires credentials (e.g., private npm registry, GitHub Packages, private PyPI):
   - Include a prerequisites step in `run-tests.sh` that loads them from `local.env` (or the appropriate file)
   - Pass them as `-e` flags to the `docker run` command

   If no credentials are needed, omit the credentials section entirely.

7. **Generate `run-tests.sh`.** Create the script at the path defined by `paths.run_tests` in `settings.json`.
   The script MUST follow this structure:

   ```
   Section 1: Header comment — project name, strategy description
   Section 2: set -e, color definitions (RED, GREEN, YELLOW, BLUE, NC)
   Section 3: Configuration — Docker image, cache volume name, project name
   Section 4: Resolve PROJECT_ROOT from script location
   Section 5: Banner with project name
   Section 6: print_step() helper function
   Section 7: Prerequisites check
              - Load credentials from local.env (only if needed — see step 6)
              - Verify Docker is installed
              - Verify Docker daemon is running
              - Create cache volume if it doesn't exist
   Section 8: Run tests
              - Install dependencies if needed (e.g., npm install, pip install)
              - Execute test command in Docker container with:
                - Source code mounted as volume (-v PROJECT_ROOT:/app)
                - Cache volume mounted (-v CACHE_VOLUME:/path/to/cache)
                - Working directory set to /app (-w /app)
                - Environment variables passed (-e VAR=value)
              - Capture exit code
   Section 9: Results — print pass/fail with colors, execution time, exit with test exit code
   ```

   Make the script executable after creating it.

8. **Generate `clean-test-cache.sh`.** Create the script at the path defined by `paths.clean_test_cache` in
   `settings.json`. The script MUST follow this structure:

   ```
   Section 1: Header comment
   Section 2: set -e, color definitions
   Section 3: Banner
   Section 4: List what will be removed (specific to this project's stack)
   Section 5: Confirmation prompt (read -p)
   Section 6: Resolve PROJECT_ROOT
   Section 7: Remove cache volume (docker volume rm)
   Section 8: Remove test Docker images (if any)
   Section 9: Remove build/output directory (e.g., build/, dist/, node_modules/, __pycache__/, target/)
   Section 10: Summary and hint to re-run tests
   ```

   Make the script executable after creating it.

9. **Verify the generated scripts.** After creating both scripts:
   - Read them back to ensure they are syntactically valid bash
   - Verify the Docker image name is a real, existing image on Docker Hub
   - Verify the test command matches what the project actually uses
   - Ensure the cache volume path is correct for the chosen Docker image

10. **Report results to the user.** Show:
    - The detected tech stack and Docker image
    - The paths where the scripts were created
    - The test command that will be executed
    - Any credentials/env vars that need to be configured before first run


# Important Notes

- **Do NOT modify the reference scripts** in this skill's folder — those are read-only examples managed by the SDD framework.
- The generated scripts go to the paths defined in `.sdd.json`.
- Always resolve `PROJECT_ROOT` relative to the script's own location, not the current working directory.
- The `clean-test-cache.sh` script MUST prompt for confirmation before deleting anything.
- If the project uses a monorepo structure, ask the user which sub-project to target.

# Language

Write all script comments and banner text in **English**. Bash scripts are conventionally written in English regardless
of the user's language.

# Additional Resources

### Reference Scripts (read-only pattern templates)
- **`reference-run-tests.sh`** — Complete example of a Gradle/JDK test runner script. Use as structural template.
- **`reference-clean-test-cache.sh`** — Complete example of a cache cleanup script. Use as structural template.
