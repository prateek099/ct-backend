"""Single source of truth for user-facing API response messages."""
# Prateek: Single source of truth for all user-facing API response messages.
# All routes and services must import from here — never hardcode strings inline.


# ── Auth ──────────────────────────────────────────────────────────────────────

INVALID_CREDENTIALS = "Invalid username or password."
ACCOUNT_DISABLED = "Account is disabled."
EMAIL_ALREADY_REGISTERED = "Email is already registered."
TOKEN_INVALID_OR_EXPIRED = "Token is invalid or expired."
TOKEN_NOT_REFRESH = "Token is not a refresh token."
USER_NOT_FOUND_OR_INACTIVE = "User not found or inactive."
PASSWORD_RESET_SENT = "If an account exists with this email, a reset link has been sent."
PASSWORD_RESET_SUCCESS = "Password has been successfully updated."
PASSWORD_RESET_TOKEN_INVALID = "Reset link is invalid or has expired."
USER_NOT_FOUND = "User not found."
EMAIL_NOT_FOUND = "This email is not registered. Please sign up first."

# ── General ───────────────────────────────────────────────────────────────────

INTERNAL_ERROR = "An unexpected error occurred."
