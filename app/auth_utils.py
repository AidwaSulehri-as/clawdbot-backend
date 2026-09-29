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
# JWT verification - called on every protected request (this is
# what Sep 19's auth middleware will use).
# ---------------------------------------------------------------
def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None