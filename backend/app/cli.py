"""Polecenia administratora uruchamiane lokalnie lub wewnątrz kontenera."""

import argparse, getpass, os, json
from sqlalchemy import select
from .models import *
from .security import hasher


def main():
    """Tworzy administratora bez hasła w argumentach i ładuje katalog z JSON."""
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["create-admin", "load-catalog"])
    p.add_argument("--login", default="admin")
    p.add_argument("--file")
    a = p.parse_args()
    with Session() as db:
        if a.command == "create-admin":
            if db.scalar(select(User).where(User.login == a.login)):
                raise SystemExit("Konto już istnieje")
            password = getpass.getpass("Hasło administratora (minimum 12 znaków): ")
            if len(password) < 12:
                raise SystemExit("Hasło zbyt krótkie")
            db.add(User(login=a.login, password=hasher.hash(password), role="admin"))
            db.commit()
            print("Utworzono administratora")
        else:
            from .schemas import ArticleInput
            from .services import save_config

            u = db.scalar(
                select(User).where(User.login == a.login, User.role == "admin")
            )
            if not u:
                raise SystemExit("Brak administratora")
            data = json.load(open(a.file, encoding="utf-8"))
            specs = []
            for sp in data["specs"]:
                code = sp.pop("method")
                method = db.scalar(select(Method).where(Method.code == code))
                if not method:
                    method = Method(code=code, name=code)
                    db.add(method)
                    db.flush()
                specs.append({**sp, "method_id": method.id})
            payload = ArticleInput(code=data["code"], name=data["name"], specs=specs)
            article = Article(code=payload.code, name=payload.name)
            db.add(article)
            db.flush()
            save_config(db, u, article, payload)
            db.commit()
            print("Wczytano katalog")


if __name__ == "__main__":
    main()
