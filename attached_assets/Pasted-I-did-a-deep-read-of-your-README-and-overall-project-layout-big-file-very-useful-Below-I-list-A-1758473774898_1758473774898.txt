I did a deep read of your README and overall project layout (big file; very useful). Below I list (A) concrete issues I found, (B) an implementation plan for each requested feature (with exact DB changes, API endpoints, frontend work, and example code snippets), and (C) a ready-to-run prompt you can give your AI agent so it can implement everything and test it automatically.

Where I quote or reference your project details I used your README as the source.&#x20;

---

# A. Problems & gaps (what’s wrong now / what to fix first)



5. **No structured error-code system**

   * README describes logs and stack traces but no machine-friendly error codes. You asked for advanced error code system that maps errors to file/module/line and gives action hints — not present in code.&#x20;

6. **Logging and observability gaps**

   * Logs are `tail -f` style, but missing: correlation IDs (per request / per task), structured JSON logs, error-code mapping to logs, and an errors table to query. No alerting hook defined (like webhook/Sentry).&#x20;

7. **Concurrency / scheduler race conditions**

   * Scheduler may start tasks even if another instance for same user is running. Need per-user locks and job status tracking. README implies state checking but must be enforced at runtime.&#x20;

8. **Missing user-level quotas / per-user rate-limits**

   * Limits appear global (daily\_limits table) but no per-user override, which is needed for multi-tenancy.&#x20;

9. **Missing UI features**

   * No user password change page, no password reset flows, no email verification, no per-user activity view, and no UI controls to enable/disable automation per account. README mentions settings but not concrete flows.&#x20;

10. **Security / defaults**

    * Default admin password insecure. There’s no forced password change on first login, and no RBAC (role-based access). Also missing row-level security for multi-tenant data.&#x20;

11. **Insufficient tests / CI for risky flows**

    * No E2E tests for login + start/stop automation + session restore flows. README lists tests but real coverage unclear.&#x20;

---

# B. Implementation plan — concrete, exact changes & examples

Below are prioritized tasks with code-level guidance, DB migrations, endpoints, and sample snippets. Implement in this order (2 → 6) to minimize breakage.



## Priority 2 — Per-user automation instance architecture {check if completed if yes skip this step}

**Goal:** Each user gets an isolated BotInstance object with its own `instagrapi.Client`, scheduler state, and local SQLite (or namespaced tables).

### Design

* `BotInstanceManager` (singleton) maintains dict `user_id -> BotInstance`.
* `BotInstance` encapsulates:

  * `client` (instagrapi client)
  * `auth` (InstagramAuth instance)
  * `scheduler` (thread / APScheduler per user)
  * `lock` (to avoid concurrent same-task for same user)
  * `task_queue` (async queue for operations)

### DB additions

```sql
CREATE TABLE bot_instances (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id VARCHAR REFERENCES users(id) UNIQUE,
  sqlite_db_path TEXT, -- e.g. bot_data_user_<id>.sqlite
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### Implementation notes

* When user logs in via `/api/bot/login` for that user, create BotInstance, restore session, validate connection, persist `session_data_encrypted` in `instagram_credentials`.
* Each bot instance should have isolated local SQLite to prevent data bleed.
* Option: run each bot instance as a separate process using `multiprocessing` or container per high-scale, but for start, threaded instance is fine.

### Example pseudo-code (Python):

```python
class BotInstance:
    def __init__(self, user_id):
        self.user_id = user_id
        self.client = instagrapi.Client()
        self.scheduler = BotScheduler(self)
        self.lock = threading.Lock()
        self.running = False

    def start(self):
        with self.lock:
            if not self.auth.is_logged_in():
                raise BotError("EAUTH0001", "Not logged in")
            self.scheduler.start()
            self.running = True

    def stop(self):
        self.scheduler.stop()
        self.running = False
```

---

## Priority 3 — Advanced error codes & observability

**Goal:** Error codes that precisely indicate module, severity, error type, and a help message. Integrate into logs and DB.

### Error code schema (recommended)

Format: `E-{MOD}-{SEV}-{NNNN}`

* `MOD` = 3-letter module code (e.g., `AUTH`, `FLW`, `LIKE`, `STO`, `DM`, `SCH`, `DB`, `API`, `NET`)
* `SEV` = 1 letter: `I` (info), `W` (warning), `E` (error), `C` (critical)
* `NNNN` = 4-digit sequential or hash-based code

Examples:

* `E-AUTH-E-0001` = Auth module, error, invalid credentials
* `E-FLW-W-0002` = Follow module warning, rate limit near

### DB table for error codes

```sql
CREATE TABLE error_codes (
  code TEXT PRIMARY KEY,
  module TEXT,
  severity TEXT,
  description TEXT,
  file_path TEXT,  -- optional
  recommended_action TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Integrate into logger

* Use structured JSON logger (python `structlog` or `logging` with JSONFormatter).
* Every `Exception` raised in modules should be wrapped into `BotException(error_code, message, extra={})`, then logged with `error_code` and saved to `activity_logs` table.

Example Python helper:

```python
class BotException(Exception):
    def __init__(self, code, message, **meta):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.meta = meta

def log_and_record_exception(code, exc, user_id=None, action=None):
    logger.error("bot_error", error_code=code, exc_info=exc, user_id=user_id, action=action)
    db.execute("INSERT INTO activity_logs (action, status, error_message, metadata) VALUES (%s,%s,%s,%s)",
               (action or 'unknown','error', str(exc), json.dumps({'error_code':code, **getattr(exc,'meta',{})})))
```

### Auto-map file/line

* When catching an exception, capture `traceback.extract_tb()` and attach `file_path` + `lineno` to the DB record and recommended action.
* Optionally add a small `error_registry.json` that maps common exceptions to helpful remediation text.

---

## Priority 4 — User & Admin login + password change + defaults

**Goal:** Proper user login page, admin dashboard still present, default admin forced to reset on first login.

### DB / Auth

* Ensure `users.password` is `bcrypt` hashed (already in README). Implement `must_change_password` boolean for admin on first boot.

```sql
ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT FALSE;
```

* On first boot create admin and set `must_change_password = TRUE`.
* Login endpoint `/api/auth/login` returns `must_change_password` flag.

### Frontend flows

* Add `/login` page with username/password and support for:

  * “Forgot password” → email OTP or token-based reset.
  * Profile page where user can change password (`PUT /api/users/:id/change-password`).
* Add admin-only user management page to create users and reset passwords.

### Security

* Enforce password rules and rate-limit login attempts.
* Provide endpoint to change default admin password:

  * `POST /api/admin/initialize-password` that requires current admin credentials and forces change.

---

## Priority 5 — Per-user quotas, RBAC & row-level security

**Goal:** Per-user daily limits and role separation.

### DB changes

* Move daily limits to per-user:

```sql
ALTER TABLE daily_limits ADD COLUMN user_id VARCHAR REFERENCES users(id) NULL;
-- Add unique constraint for user-specific limits
CREATE UNIQUE INDEX idx_daily_limits_user ON daily_limits(user_id);
```

* If `user_id` is NULL, treat as global default.

### RBAC

* Add `roles` column to users: `role ENUM('admin','user')` and enforce route access.

---

## Priority 6 — Password resets, 2FA, session restore & tests

**Goal:** Full lifecycle for login: login → 2FA support → session blob stored encrypted → session test/revoke.

### Implementation

* `POST /api/bot/login` should:

  1. Validate creds
  2. If 2FA required return `requires_verification: true`.
  3. On success, encrypt session blob and store in `instagram_credentials.session_data_encrypted`.
  4. Mark `user_bot_status.session_valid = true`.

* Add `/api/bot/logout` to clear session and mark invalid.

### Tests

* Add E2E test: create user, login, start bot (should not start until logged in), run `test-session`, start scheduler, submit a follow-hashtag job, then stop bot; assert `activity_logs` entries with proper codes.

---

## Example code snippets (put these into relevant files)

### Error code generator (python)

```python
import hashlib, time, json

def generate_error_code(module:str, severity:str, desc:str):
    base = f"{module}-{severity}-{int(time.time()*1000)}"
    h = hashlib.sha1(base.encode()).hexdigest()[:4].upper()
    return f"E-{module}-{severity}-{h}"

# usage
code = generate_error_code('AUTH','E','Invalid credentials for user')
```

### API route (Flask) — login + create BotInstance

```python
@app.post("/api/bot/login")
def bot_login():
    body = request.json
    user_id = body['user_id']
    username = body['username']
    password = body['password']
    try:
        bot_inst = BotInstanceManager.create_for_user(user_id)
        result = bot_inst.auth.login(username, password)
        if result.get('success'):
            # persist encrypted session blob
            encrypted = encrypt_session(bot_inst.client.get_session())
            db.execute("UPDATE instagram_credentials SET session_data_encrypted=%s WHERE username=%s", (encrypted, username))
            db.execute("UPDATE user_bot_status SET session_valid=true, instagram_username=%s WHERE user_id=%s", (username, user_id))
            return jsonify(success=True, message="Login successful")
        else:
            return jsonify(success=False, error=result.get('error'), message=result.get('message')), 400
    except BotException as e:
        log_and_record_exception(e.code, e, user_id=user_id, action='login')
        return jsonify(success=False, error=e.code, message=str(e)), 500
```

---

## Frontend changes (high-level)

1. Add `/login` page; call `/api/auth/login`.
2. Add per-user `Automation` page that shows user-specific bot status, `Start/Stop` toggle, `Test Session` button.
3. Settings page: change password, change admin default on first login.
4. In Automation UI, show last error code and link to knowledge base entry for remediation.

---

## Migration & deployment commands (what to run)

1. Create DB migrations (SQL above).
2. Restart backend: `systemctl restart instagram-bot` or `python main.py`.
3. Run a script to create admin user with `must_change_password = true`.
4. Run E2E tests: `npm run test:e2e && pytest bot/tests/`.

---

# C. Prompt for your AI agent (copy-paste ready)

Use this prompt exactly (agent should have repo mounted and can run tests; it should commit changes and produce PRs):

```
You are an autonomous dev agent. Repo is mounted at /workspace/instagram-bot-dashboard. Implement the following changes and tests (commit each logical change in its own commit, produce a short changelog).



3) Add advanced error code system:
   - Create error_codes table and add helper generate_error_code() and BotException class.
   - Wrap all module exceptions so they log structured JSON (fields: timestamp, error_code, module, severity, user_id, action, stack) and insert a row into activity_logs with metadata including error_code and stack_trace.

4) Create full user auth flows:
   - Add /api/auth/login and /api/auth/logout endpoints (JWT or session cookie).
   - Ensure admin is created on first launch with must_change_password=true and force password change flow on first login.
   - Implement change-password endpoint and frontend forms (/login, /profile/change-password).

5) Per-user quotas & RBAC:
   - Move daily_limits to optionally accept user_id; implement server-side enforcement when performing actions.

6) Tests:
   - Add E2E test that creates a user, logs in, attempts to start bot (should fail), logs into Instagram via bot API (mock if necessary), tests session, starts bot (should succeed), runs a follow-hashtag action, asserts activity_logs entry and no errors.

7) Docs:
   - Update README with new endpoints and error-code mapping examples.

Make sure:
- Do not log plaintext passwords.
- Encrypt session_data with AES-256 and store in instagram_credentials.session_data_encrypted.
- Use structured JSON logging.
- Add migrations SQL into /migrations/0001_add_bot_instances.sql.

Run unit tests and E2E tests. If anything fails, fix until they pass. Commit each step and create a final PR with summary of changes, migration steps, and instructions to rollback.

When finished, output:
- list of commits,
- test results,
- instructions to manually verify (HTTP requests and expected responses),
- known limitations.

Do not ask for clarification; make reasonable defaults where unspecified.
```

---

# D. Testing & verification checklist (manual commands)

* `curl POST /api/auth/login` — returns token + flag `must_change_password`.
* `curl POST /api/users/:id/test-session` — returns `session_valid:false` for fresh user.
* After login via `/api/bot/login`, `/api/users/:id/test-session` -> `session_valid:true`.
* Try `POST /api/bot/actions/follow-hashtag` for user without valid session -> should return error `SESSION_INVALID`.
* Once valid and bot started, schedule a follow job and check `activity_logs` for status and error\_code fields.
* Check `error_codes` table for mapping entries.

---

# E. Quick priorities for you (what to do now)

1. Back up DB.
2. Create a branch `feature/multiuser-bot-instances`.
3. Give the AI agent repo access and run the prompt above.
4. After PR, run E2E tests and then merge to main.
5. Change default admin password immediately if deployed.

---

# F. Final notes / risk & safety

* Implementing per-user bot instances increases resource use; monitor CPU/RAM and consider process-level isolation for production.
* Strongly consider adding 2FA and IP rotation for heavy usage to avoid Instagram blocks.
* Keep an operations runbook for handling Instagram challenges.


