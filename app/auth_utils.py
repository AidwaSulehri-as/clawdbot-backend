"""
=====================================================================
 auth_utils.py — password hashing and JWT (JSON Web Token) helpers.

 WHY A SEPARATE FILE: main.py defines API ROUTES (what URL does what).
 This file defines the actual SECURITY LOGIC those routes use -
 keeping them separate means main.py stays readable, and this logic
 can be tested/reused without touching route code.

 WHAT A JWT IS, IN PLAIN ENGLISH: after a user logs in successfully,
 we hand them back a signed "token" - a long string that proves who
 they are. The app saves this and sends it back on every future
 request (in the Authorization header). We can verify the token is
 genuine (not faked) because only OUR SECRET_KEY could have signed it.
=====================================================================
"""

from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# ---------------------------------------------------------------
# IMPORTANT (security note for your report/manual): in a real
# production system, SECRET_KEY would come from an environment
# variable, never hardcoded in source code. For this FYP, a fixed
# string is acceptable and simpler to demo/grade, but this is a
# documented, deliberate scope decision - the same kind of honest
# tradeoff you already made for ngrok deployment in Phase 1.
# ---------------------------------------------------------------
SECRET_KEY = "clawdbot-fyp-secret-key-change-if-this-were-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days - long-lived since
# this is a memory-assistance app; forcing frequent re-logins would
# work against the whole point of the app for its target users.

# ---------------------------------------------------------------
# Password hashing - we NEVER store plain-text passwords. bcrypt
# turns "mypassword123" into a long scrambled string that can be
# CHECKED against but never reversed back into the original.
# ---------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Turns a plain-text password into a bcrypt hash for storage."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Checks a login attempt's password against the stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------
# JWT creation - called once, right after a successful login.
# ---------------------------------------------------------------
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------------------------------------------
# JWT verification - called on every protected request.
# ---------------------------------------------------------------
def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# =====================================================================
# Sep 19 — Authentication middleware/dependency.
#
# HTTPBearer gives a simple "paste your token" box on the /docs
# Authorize popup, instead of a full OAuth2 username/password form -
# a better fit since our /auth/login endpoint takes JSON, not the
# OAuth2 standard form format.
#
# Any endpoint that adds
# `current_user_email: str = Depends(get_current_user_email)` to its
# parameters is now PROTECTED - FastAPI won't even call the endpoint
# function if the token is missing or invalid; it returns 401 first.
# =====================================================================

bearer_scheme = HTTPBearer()


def get_current_user_email(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """
    Extracts and validates the token from the Authorization header.
    Returns the logged-in user's email if valid. Raises 401 if the
    token is missing, malformed, expired, or otherwise invalid.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    email = payload.get("sub")
    if email is None:
        raise credentials_exception

    return email





# =====================================================================
# Sep 21 — Login rate-limiting (brute-force protection).
#
# WHY IN-MEMORY, NOT A DATABASE TABLE: this is a lightweight,
# documented scope decision appropriate for an FYP demo - a real
# production system would use Redis or a database table so the limit
# survives a server restart and works across multiple server
# instances. Here, a simple dictionary is sufficient to demonstrate
# the security concept and actually block real brute-force attempts
# during a single running session.
# =====================================================================

from collections import defaultdict

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

# Maps email -> list of datetimes when a failed login happened.
_failed_login_attempts: dict[str, list[datetime]] = defaultdict(list)


def is_locked_out(email: str) -> bool:
    """
    Checks whether this email has had too many failed login attempts
    recently. Old attempts (outside the lockout window) are cleaned
    up automatically each time this is called.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=LOCKOUT_MINUTES)
    recent_attempts = [t for t in _failed_login_attempts[email] if t > cutoff]
    _failed_login_attempts[email] = recent_attempts
    return len(recent_attempts) >= MAX_FAILED_ATTEMPTS


def record_failed_attempt(email: str) -> None:
    """Records one failed login attempt for this email, right now."""
    _failed_login_attempts[email].append(datetime.now(timezone.utc))


def clear_failed_attempts(email: str) -> None:
    """Called after a SUCCESSFUL login - resets the counter to zero."""
    _failed_login_attempts[email] = []