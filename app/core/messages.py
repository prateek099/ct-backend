# Prateek: Single source of truth for all user-facing API response messages.
# All routes and services must import from here — never hardcode strings inline.


# ── Auth ──────────────────────────────────────────────────────────────────────

INVALID_CREDENTIALS = "Invalid username or password."
ACCOUNT_DISABLED = "Account is disabled."
EMAIL_ALREADY_REGISTERED = "Email is already registered."
TOKEN_INVALID_OR_EXPIRED = "Token is invalid or expired."
TOKEN_NOT_REFRESH = "Token is not a refresh token."
USER_NOT_FOUND_OR_INACTIVE = "User not found or inactive."

# ── General ───────────────────────────────────────────────────────────────────

INTERNAL_ERROR = "An unexpected error occurred."
