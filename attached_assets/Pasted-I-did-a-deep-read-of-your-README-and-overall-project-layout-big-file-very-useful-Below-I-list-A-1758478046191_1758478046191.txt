I did a deep read of your README and overall project layout (big file; very useful). Below I list (A) concrete issues I found, (B) an implementation plan for each requested feature (with exact DB changes, API endpoints, frontend work, and example code snippets), and (C) a ready-to-run prompt you can give your AI agent so it can implement everything and test it automatically.

Where I quote or reference your project details I used your README as the source.&#x20;

-



# B. Implementation plan — concrete, exact changes & examples

Below are prioritized tasks with code-level guidance, DB migrations, endpoints, and sample snippets. Implement in this order (4 → 6) to minimize breakage.






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



---

# F. Final notes / risk & safety

* Implementing per-user bot instances increases resource use; monitor CPU/RAM and consider process-level isolation for production.
* Strongly consider adding 2FA and IP rotation for heavy usage to avoid Instagram blocks.
* Keep an operations runbook for handling Instagram challenges.


