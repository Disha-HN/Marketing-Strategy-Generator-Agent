import sqlite3
import hashlib
import os
import re
from datetime import datetime

# On Streamlit Cloud the working directory resets on redeploy.
# Store DB in /tmp for persistence within a session, or use the
# working directory locally. For production, replace with a
# hosted DB (e.g. Supabase, PlanetScale, or st.secrets + psycopg2).
DB_PATH = os.path.join(os.getenv("TMPDIR", os.getcwd()), "users.db")


def _get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT    UNIQUE NOT NULL,
                email       TEXT    UNIQUE NOT NULL,
                password    TEXT    NOT NULL,
                created_at  TEXT    NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_strategies (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                product     TEXT    NOT NULL,
                result      TEXT    NOT NULL,
                tone        TEXT,
                language    TEXT,
                created_at  TEXT    NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.commit()


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def validate_email(email: str) -> bool:
    return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w{2,}$", email))


def validate_password(password: str) -> str | None:
    if len(password) < 6:
        return "Password must be at least 6 characters."
    return None


def register_user(username: str, email: str, password: str) -> tuple[bool, str]:
    username = username.strip()
    email    = email.strip().lower()

    if not username or len(username) < 3:
        return False, "Username must be at least 3 characters."
    if not validate_email(email):
        return False, "Please enter a valid email address."
    err = validate_password(password)
    if err:
        return False, err

    try:
        with _get_conn() as conn:
            conn.execute(
                "INSERT INTO users (username, email, password, created_at) VALUES (?,?,?,?)",
                (username, email, _hash(password), datetime.now().isoformat())
            )
            conn.commit()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            return False, "Username already taken."
        if "email" in str(e):
            return False, "Email already registered."
        return False, "Registration failed. Please try again."


def login_user(username_or_email: str, password: str) -> tuple[bool, str, dict | None]:
    val = username_or_email.strip().lower()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE LOWER(username)=? OR email=?", (val, val)
        ).fetchone()

    if not row:
        return False, "No account found with that username or email.", None
    if row["password"] != _hash(password):
        return False, "Incorrect password.", None

    return True, "Login successful!", dict(row)


def get_user_strategies(user_id: int) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM user_strategies WHERE user_id=? ORDER BY created_at DESC LIMIT 20",
            (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def save_strategy(user_id: int, product: str, result: dict, tone: str, language: str):
    import json
    # Remove meta keys before saving
    clean = {k: v for k, v in result.items() if not k.startswith("_meta")}
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO user_strategies (user_id, product, result, tone, language, created_at) VALUES (?,?,?,?,?,?)",
            (user_id, product, json.dumps(clean), tone, language, datetime.now().isoformat())
        )
        conn.commit()


def delete_strategy(strategy_id: int, user_id: int):
    with _get_conn() as conn:
        conn.execute(
            "DELETE FROM user_strategies WHERE id=? AND user_id=?",
            (strategy_id, user_id)
        )
        conn.commit()


# Initialize DB on import
init_db()
