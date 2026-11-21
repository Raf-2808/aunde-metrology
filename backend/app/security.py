"""Sesje serwerowe, ograniczenie prób i oddzielna autoryzacja modułów."""

import os, secrets, hashlib, time
from datetime import timedelta
from fastapi import Request, HTTPException, Depends
from sqlalchemy import select, func
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from .models import Session, User, LoginSession, LoginAttempt, teraz

hasher = PasswordHasher()
GRANTS = {
    "admin": {
        "configure",
        "test",
        "order",
        "real",
        "simulated",
        "spc",
        "hold",
        "users",
    },
    "manager": {"configure", "test", "order", "real", "simulated", "spc", "hold"},
    "technician": {"test", "order"},
    "reporter": {"order"},
    "reader": {"real", "spc"},
}


def db_session():
    """Zamyka transakcję po żądaniu i wycofuje ją przy błędzie."""
    with Session() as db:
        try:
            yield db
        except Exception:
            db.rollback()
            raise


def verify(password, hashed):
    """Weryfikuje Argon2 bez ujawniania przyczyny odmowy."""
    try:
        return hasher.verify(hashed, password)
    except VerificationError:
        return False


def limit_attempts(db, key):
    """Ogranicza logowanie i ponowną autoryzację do 10 prób w 15 minut."""
    if (
        db.scalar(
            select(func.count())
            .select_from(LoginAttempt)
            .where(
                LoginAttempt.key == key,
                LoginAttempt.created > teraz() - timedelta(minutes=15),
            )
        )
        >= 10
    ):
        raise HTTPException(429, "Zbyt wiele prób. Odczekaj 15 minut.")
    db.add(LoginAttempt(key=key))
    db.commit()


def identity(request: Request, db=Depends(db_session)):
    """Sprawdza sesję, użytkownika oraz token CSRF dla każdej mutacji."""
    token = request.cookies.get("lims_session", "")
    session = db.get(LoginSession, hashlib.sha256(token.encode()).hexdigest())
    if not session or session.expires.replace(tzinfo=teraz().tzinfo) < teraz():
        raise HTTPException(401, "Zaloguj się")
    user = db.get(User, session.user_id)
    if not user or not user.active:
        raise HTTPException(401, "Konto nieaktywne")
    if request.method not in ("GET", "HEAD", "OPTIONS") and not secrets.compare_digest(
        request.headers.get("x-csrf-token", ""), session.csrf
    ):
        raise HTTPException(403, "Nieprawidłowy token CSRF")
    return user, session


def require(permission, protected=False):
    """Autoryzuje rolę i aktualne potwierdzenie hasła wybranego modułu."""

    def dependency(auth=Depends(identity)):
        user, session = auth
        if permission not in GRANTS.get(user.role, set()):
            raise HTTPException(403, "Brak uprawnień")
        if protected and session.scopes.get(permission, 0) < time.time():
            raise HTTPException(428, "Potwierdź hasło dla modułu " + permission)
        return user

    return dependency
