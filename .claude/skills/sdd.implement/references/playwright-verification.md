# E2E Browser Verification with Playwright CLI

This procedure runs after unit tests pass in each phase. It opens a **visible** browser (headed mode)
and executes the feature's user flow so the user can watch it live and confirm the tests reflect
actual working behavior.

**Prerequisites:**

- `@playwright-cli` must be installed and available in PATH (see Installation below)
- The dev server must be running at the URL configured in `.sdd.json`

## 0. Installation

Install the official Playwright CLI package:

```bash
npm install -D @playwright/cli
```

This installs the `playwright-cli` binary into your project's `node_modules/.bin/`.

> **WARNING:** The old `playwright-cli` package on npm is **deprecated**. Always use `@playwright/cli`
> (scoped under `@playwright`). If you see `playwright-cli@0.x` in your dependencies, replace it
> with `@playwright/cli`.

---

## 1. Read Configuration

Read the `playwright` section from `.sdd.json`:

```json
{
  "playwright": {
    "baseUrl": "http://localhost:5173",
    "credentialsFile": "e2e/.env.local"
  }
}
```

- **`baseUrl`** (required): The URL of the running dev server.
- **`credentialsFile`** (optional): Path to a file containing login credentials as environment variables. If not present, assume the app does not require authentication.
  > **SECURITY:** The credentials file (e.g., `e2e/.env.local`) contains real login credentials.
  > **Never commit it to version control.** Add it to `.gitignore`:
  >
  > ```
  > # Playwright E2E credentials
  > e2e/.env.local
  > ```

---

## 2. Detect Availability

```bash
# Check playwright-cli is installed
which playwright-cli 2>/dev/null

# Check dev server is running
curl -s -o /dev/null -w "%{http_code}" <baseUrl>
```

If `playwright-cli` is not found or the dev server does not respond (non-2xx/3xx), skip the
entire verification and inform the user why.

---

## 3. Open the Browser (Headed)

**CRITICAL: Always use `--headed` so the user sees the browser.**

```bash
playwright-cli open --headed <baseUrl>
```

This opens a visible Chrome window navigated to the dev server URL.

---

## 4. Authentication (if configured)

If `.sdd.json` includes `playwright.credentialsFile`:

1. Read the credentials file to extract username and password values.
2. After opening the browser, the app may redirect to a login page.
3. Take a snapshot to identify the current page state and form element refs:
   ```bash
   playwright-cli snapshot
   ```
4. Fill in the credentials and submit:
   ```bash
   playwright-cli fill <username-field-ref> "<username>"
   playwright-cli fill <password-field-ref> "<password>"
   playwright-cli click <submit-button-ref>
   ```
5. Wait for the app to load after authentication:
   # Wait for the page to fully load (do NOT use a fixed sleep)
   ```bash
   playwright-cli eval "document.readyState === 'complete'"
   playwright-cli snapshot
   ```
   If the snapshot still shows a loading state (spinner, skeleton, etc.), retry once:
   ```bash
   playwright-cli eval "document.readyState === 'complete'"
   playwright-cli snapshot
   ```

**Important:** Element refs (e.g., `e13`, `e17`) change between sessions. Always take a fresh
snapshot to identify the correct refs for the current page state.

If no `credentialsFile` is configured, skip this step.

---

## 5. Execute the E2E Flow

Read the **source story** linked in the plan to extract the user flow steps. The story describes
what the user does (navigate, click, fill forms, verify results, etc.).

For each step in the flow:

1. **Navigate** if needed:

   ```bash
   playwright-cli goto <url>
   ```

2. **Take a snapshot** to identify element refs on the current page:

   ```bash
   playwright-cli snapshot
   ```

3. **Interact** with the page using the identified refs:

   ```bash
   playwright-cli click <ref>
   playwright-cli fill <ref> "value"
   playwright-cli select <ref> "option"
   playwright-cli hover <ref>
   ```

4. **Verify** the expected outcome:

   ```bash
   # Take a screenshot for visual verification
   playwright-cli screenshot --filename=step-N.png

   # Or take a snapshot to check element state (text, attributes, visibility)
   playwright-cli snapshot
   ```

Work through the story flow sequentially, verifying each step before moving to the next.

---

## 6. Verification Results

After completing the flow:

1. Take a final screenshot of the end state:

   ```bash
   playwright-cli screenshot --filename=e2e-final.png
   ```

2. Confirm to the user what was verified and whether the flow completed successfully.

3. If any step failed or looked wrong, report it clearly with:
   - Which step failed
   - What was expected vs. what happened
   - A screenshot of the failure state

---

## 7. Cleanup

Always close the browser session when verification is complete:

```bash
playwright-cli close
```

If the session is unresponsive:

```bash
playwright-cli kill-all
```

---

## Troubleshooting

| Issue                          | Solution                                                                            |
| ------------------------------ | ----------------------------------------------------------------------------------- |
| Browser not visible (headless) | Make sure you used `playwright-cli open --headed` — the `--headed` flag is required |
| Browser already in use error   | Run `playwright-cli kill-all` then retry                                            |
| Element refs not found         | Take a fresh `playwright-cli snapshot` — refs change between page states            |
| Login redirect loop            | Check that the dev server is running and auth env vars are configured               |
| Dev server not responding      | Verify the server is running at the URL in `.sdd.json` `playwright.baseUrl`         |
