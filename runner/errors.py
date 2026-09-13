"""lastError codes the runner writes to a tenant document — codes, never messages.

The portal renders `portal_error_<code>` through t() in en/ur (landing/content/strings.json), so
the two-language rule is not smuggled around by putting English into a database.
tests/check_landing.py fails if a code listed here has no portal string. Dependency-free on purpose:
that check is stdlib-only.
"""
LAST_ERROR_CODES = ("auth",)   # the worker exited because WhatsApp rejected the token (401/190, 400/100)
