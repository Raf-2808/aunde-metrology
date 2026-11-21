"""HTTP API AUNDE LIMS. Uprawnienia obowiązują także eksport i Recover."""

import hashlib, io, os, secrets, time, zipfile
from datetime import timedelta, date
from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Request,
    Response,
    UploadFile,
    File,
    Query,
)
from fastapi.responses import StreamingResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from .models import *
from .schemas import *
from .security import *
from .services import *

app = FastAPI(title="AUNDE Laboratory Management", version="1.0.0")
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(
        ","
    ),
)


@app.middleware("http")
async def headers(request, call_next):
    """Wymusza ten sam origin dla mutacji i blokuje buforowanie danych prywatnych."""
    origin = request.headers.get("origin")
    if (
        request.method not in ("GET", "HEAD", "OPTIONS")
        and origin
        and origin != os.getenv("PUBLIC_URL", "http://localhost:8080").rstrip("/")
    ):
        return Response("Niedozwolone źródło żądania", status_code=403)
    response = await call_next(request)
    response.headers.update(
        {
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "same-origin",
        }
    )
    return response


@app.exception_handler(IntegrityError)
async def conflicts(request, exc):
    """Zwraca kontrolowany konflikt bez ujawniania zapytań SQL."""
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=409,
        content={"detail": "Konflikt danych lub równoległego zapisu. Odśwież widok."},
    )


@app.get("/api/health")
def health(db=Depends(db_session)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.post("/api/login")
def login(
    data: Credentials, request: Request, response: Response, db=Depends(db_session)
):
    """Tworzy losową sesję HTTP-only, nigdy nie przechowuje hasła w przeglądarce."""
    limit_attempts(db, "ip:" + request.client.host)
    limit_attempts(db, "user:" + data.login.lower())
    user = db.scalar(select(User).where(User.login == data.login, User.active == True))
    if not user or not verify(data.password, user.password):
        raise HTTPException(401, "Nieprawidłowe dane logowania")
    token = secrets.token_urlsafe(48)
    csrf = secrets.token_urlsafe(32)
    db.add(
        LoginSession(
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            user_id=user.id,
            expires=teraz() + timedelta(hours=8),
            csrf=csrf,
            scopes={},
        )
    )
    audit(db, user, "LOGIN", user.id, {})
    db.commit()
    response.set_cookie(
        "lims_session",
        token,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "true").lower() == "true",
        samesite="strict",
        max_age=28800,
        path="/",
    )
    return {
        "login": user.login,
        "role": user.role,
        "csrf": csrf,
        "permissions": sorted(GRANTS[user.role]),
    }


@app.get("/api/me")
def me(auth=Depends(identity)):
    u, s = auth
    return {
        "login": u.login,
        "role": u.role,
        "csrf": s.csrf,
        "permissions": sorted(GRANTS[u.role]),
        "scopes": s.scopes,
    }


@app.post("/api/logout")
def logout(response: Response, auth=Depends(identity), db=Depends(db_session)):
    db.delete(auth[1])
    db.commit()
    response.delete_cookie("lims_session", path="/")
    return {"ok": True}


@app.post("/api/reauth")
def reauth(data: Reauth, auth=Depends(identity), db=Depends(db_session)):
    """Przyznaje 15 minut dostępu tylko do wskazanego chronionego modułu."""
    u, s = auth
    if data.scope not in GRANTS[u.role]:
        raise HTTPException(403, "Brak uprawnień")
    limit_attempts(db, "reauth:" + str(u.id))
    if not verify(data.password, u.password):
        raise HTTPException(403, "Nieprawidłowe hasło")
    s.scopes = {**s.scopes, data.scope: time.time() + 900}
    audit(db, u, "REAUTH", data.scope, {})
    db.commit()
    return {"expires": s.scopes[data.scope]}


@app.get("/api/users")
def users(u=Depends(require("users")), db=Depends(db_session)):
    return [
        {"id": x.id, "login": x.login, "role": x.role, "active": x.active}
        for x in db.scalars(select(User))
    ]


@app.post("/api/users")
def create_user(data: UserInput, u=Depends(require("users")), db=Depends(db_session)):
    if len(data.password) < 12:
        raise HTTPException(422, "Hasło musi mieć co najmniej 12 znaków")
    x = User(login=data.login, role=data.role, password=hasher.hash(data.password))
    db.add(x)
    db.flush()
    audit(db, u, "CREATE_USER", x.id, {"login": x.login, "role": x.role})
    db.commit()
    return {"id": x.id}


@app.patch("/api/users/{user_id}")
def update_user(
    user_id: int, data: UserUpdate, u=Depends(require("users")), db=Depends(db_session)
):
    """Zmienia rolę lub aktywność i unieważnia sesje zmienianego konta."""
    from sqlalchemy import delete

    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "Nieznane konto")
    if target.id == u.id and (not data.active or data.role != "admin"):
        raise HTTPException(422, "Nie można zablokować własnego konta administratora")
    before = {"role": target.role, "active": target.active}
    target.role = data.role
    target.active = data.active
    if data.password:
        target.password = hasher.hash(data.password)
    db.execute(delete(LoginSession).where(LoginSession.user_id == target.id))
    audit(
        db,
        u,
        "UPDATE_USER",
        target.id,
        {
            "before": before,
            "after": {"role": data.role, "active": data.active},
            "password_reset": bool(data.password),
        },
    )
    db.commit()
    return {"id": target.id}


@app.get("/api/methods")
def methods(auth=Depends(identity), db=Depends(db_session)):
    return [
        {"id": m.id, "code": m.code, "name": m.name}
        for m in db.scalars(select(Method).order_by(Method.code))
    ]


@app.post("/api/methods")
def add_method(
    data: MethodInput, u=Depends(require("configure")), db=Depends(db_session)
):
    m = Method(**data.model_dump())
    db.add(m)
    db.flush()
    audit(db, u, "CREATE_METHOD", m.id, data.model_dump())
    db.commit()
    return {"id": m.id}


@app.get("/api/articles")
def articles(auth=Depends(identity), db=Depends(db_session)):
    return [
        {"id": a.id, "code": a.code, "name": a.name, "cycle": a.cycle}
        for a in db.scalars(select(Article).order_by(Article.code))
    ]


@app.get("/api/articles/{article_id}/config")
def article_config(article_id: int, auth=Depends(identity), db=Depends(db_session)):
    c = current_config(db, article_id)
    return {"id": c.id, "version": c.version, "specs": specs_for(db, c.id)}


@app.post("/api/articles")
def add_article(
    data: ArticleInput, u=Depends(require("configure")), db=Depends(db_session)
):
    a = Article(code=data.code, name=data.name)
    db.add(a)
    db.flush()
    c = save_config(db, u, a, data)
    db.commit()
    return {"id": a.id, "config_id": c.id}


@app.post("/api/articles/{article_id}/config")
def update_config(
    article_id: int,
    data: ArticleInput,
    u=Depends(require("configure")),
    db=Depends(db_session),
):
    a = db.scalar(select(Article).where(Article.id == article_id).with_for_update())
    if not a:
        raise HTTPException(404, "Artykuł nie istnieje")
    if data.code != a.code or data.name != a.name:
        raise HTTPException(422, "Kod i nazwa artykułu są niezmienne")
    c = save_config(db, u, a, data)
    db.commit()
    return {"id": c.id, "version": c.version}


@app.get("/api/orders")
def orders(
    status: str | None = None,
    search: str = "",
    auth=Depends(identity),
    db=Depends(db_session),
):
    query = select(Order).order_by(Order.created.desc()).limit(500)
    if status:
        query = query.where(Order.status == status)
    if search:
        query = query.where(Order.lot.contains(search, autoescape=True))
    out = []
    for o in db.scalars(query):
        a = db.get(Article, o.article_id)
        events = [
            {
                "held": d.held,
                "reason": d.reason,
                "author": db.get(User, d.author).login,
                "date": d.created,
            }
            for d in db.scalars(
                select(Disposition)
                .where(Disposition.order_id == o.id)
                .order_by(Disposition.id)
            )
        ]
        out.append(
            {
                "id": o.id,
                "article_id": a.id,
                "article": a.name,
                "code": a.code,
                "lot": o.lot,
                "roll": o.roll,
                "quantity": o.quantity,
                "status": o.status,
                "created": o.created,
                "completed": o.completed,
                "reporter": db.get(User, o.reporter).login,
                "required_sessions": o.required_sessions,
                "extra": o.extra,
                "history": events,
            }
        )
    return out


@app.post("/api/orders")
def add_order(data: OrderInput, u=Depends(require("order")), db=Depends(db_session)):
    c = current_config(db, data.article_id)
    keys = {s["key"] for s in specs_for(db, c.id)}
    if not set(data.extra) <= keys:
        raise HTTPException(422, "Nieznane badanie dodatkowe")
    if (data.extra or data.required_sessions > 1) and u.role not in (
        "manager",
        "admin",
    ):
        raise HTTPException(403, "Plan dodatkowy wymaga kierownika")
    o = Order(**data.model_dump(), reporter=u.id)
    db.add(o)
    db.flush()
    audit(db, u, "CREATE_ORDER", o.id, data.model_dump())
    db.commit()
    return {"id": o.id}


@app.post("/api/orders/{order_id}/start")
def start_order(order_id: int, u=Depends(require("test")), db=Depends(db_session)):
    o = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if not o:
        raise HTTPException(404, "Nieznane zlecenie")
    if o.status not in ("WAITING", "IN_PROGRESS"):
        raise HTTPException(409, "Partia niedostępna do badania")
    o.status = "IN_PROGRESS"
    audit(db, u, "START_ORDER", o.id, {})
    db.commit()
    return plan(db, o)


@app.get("/api/orders/{order_id}/plan")
def get_plan(order_id: int, u=Depends(require("test")), db=Depends(db_session)):
    o = db.get(Order, order_id)
    if not o:
        raise HTTPException(404, "Nieznane zlecenie")
    return plan(db, o)


@app.post("/api/orders/{order_id}/disposition")
def disposition(
    order_id: int,
    data: DispositionInput,
    u=Depends(require("hold")),
    db=Depends(db_session),
):
    """Zapisuje dyspozycję partii niezależnie od laboratoryjnej zgodności."""
    o = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if not o:
        raise HTTPException(404, "Nieznane zlecenie")
    if data.held and o.status != "TESTED":
        raise HTTPException(409, "Wstrzymanie dostępne dla zbadanej partii")
    if not data.held and o.status != "HELD":
        raise HTTPException(409, "Partia nie jest wstrzymana")
    o.status = "HELD" if data.held else "TESTED"
    db.add(Disposition(order_id=o.id, author=u.id, **data.model_dump()))
    audit(db, u, "DISPOSITION", o.id, data.model_dump())
    db.commit()
    return {"status": o.status}


@app.post("/api/sessions")
def save_session(data: SaveInput, u=Depends(require("test")), db=Depends(db_session)):
    return zapisz_wyniki(db, u, data)


def source_guard(source, auth):
    """Wspólna ochrona źródła dla tabel, Recover i każdego eksportu."""
    if source not in ("real", "simulated"):
        raise HTTPException(422, "Nieznane źródło")
    require(source, True)(auth)


def session_query(db, article_id, lot, start, end, offset, limit):
    q = select(LabSession).join(Order, LabSession.order_id == Order.id)
    if article_id:
        q = q.where(LabSession.article_id == article_id)
    if lot:
        q = q.where(Order.lot.contains(lot, autoescape=True))
    if start:
        q = q.where(LabSession.test_date >= str(start))
    if end:
        q = q.where(LabSession.test_date <= str(end))
    return list(
        db.scalars(q.order_by(LabSession.cycle.desc()).offset(offset).limit(limit))
    )


@app.get("/api/results/{source}")
def results(
    source: str,
    article_id: int | None = None,
    lot: str = "",
    start: date | None = None,
    end: date | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    auth=Depends(identity),
    db=Depends(db_session),
):
    source_guard(source, auth)
    return [
        serialize_session(db, s, source)
        for s in session_query(db, article_id, lot, start, end, offset, limit)
    ]


@app.get("/api/results/{source}/{session_id}")
def recover(
    source: str, session_id: int, auth=Depends(identity), db=Depends(db_session)
):
    source_guard(source, auth)
    s = db.get(LabSession, session_id)
    if not s:
        raise HTTPException(404, "Nieznana sesja")
    return serialize_session(db, s, source)


@app.get("/api/export/{source}")
def export(
    source: str,
    session_id: int | None = None,
    article_id: int | None = None,
    lot: str = "",
    start: date | None = None,
    end: date | None = None,
    auth=Depends(identity),
    db=Depends(db_session),
):
    """Eksportuje wartości i historyczne tolerancje z niezależną ochroną API."""
    from .export import eksportuj_raport_excel

    source_guard(source, auth)
    rows = (
        [db.get(LabSession, session_id)]
        if session_id
        else session_query(db, article_id, lot, start, end, 0, 5000)
    )
    if any(x is None for x in rows):
        raise HTTPException(404, "Nieznana sesja")
    blob = eksportuj_raport_excel(
        [serialize_session(db, s, source) for s in rows], source, bool(session_id)
    )
    audit(db, auth[0], "EXPORT", source, {"sessions": [s.id for s in rows]})
    db.commit()
    return StreamingResponse(
        io.BytesIO(blob),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="lims-{source}.xlsx"'},
    )


@app.get("/api/spc/configs")
def spc_configs(u=Depends(require("spc", True)), db=Depends(db_session)):
    return [
        {
            "id": c.id,
            "characteristic_id": c.characteristic_id,
            "name": db.get(Characteristic, c.characteristic_id).spec["name"],
            "limits": c.limits,
            "sampling_plan": c.sampling_plan,
            "author": c.author,
            "created": c.created,
        }
        for c in db.scalars(select(SpcConfig).order_by(SpcConfig.id.desc()))
    ]


@app.post("/api/spc/configs")
def add_spc(
    data: SpcInput,
    u=Depends(require("configure")),
    auth=Depends(identity),
    db=Depends(db_session),
):
    require("spc", True)(auth)
    c = db.get(Characteristic, data.characteristic_id)
    if not c or c.spec["kind"] != "numeric" or c.spec["count"] != data.n:
        raise HTTPException(422, "Plan nie odpowiada charakterystyce liczbowej")
    cfg = SpcConfig(
        characteristic_id=c.id,
        limits={
            k: v
            for k, v in data.model_dump().items()
            if k not in ("characteristic_id", "sampling_plan")
        },
        sampling_plan=data.sampling_plan,
        author=u.id,
    )
    db.add(cfg)
    db.flush()
    audit(db, u, "APPROVE_SPC", cfg.id, data.model_dump())
    db.commit()
    return {"id": cfg.id}


@app.get("/api/spc/chart/{config_id}")
def chart(
    config_id: int,
    start: date | None = None,
    end: date | None = None,
    u=Depends(require("spc", True)),
    db=Depends(db_session),
):
    cfg = db.get(SpcConfig, config_id)
    if not cfg:
        raise HTTPException(404, "Brak konfiguracji SPC")
    groups, labels = groups_for(db, cfg.characteristic_id, start=start, end=end)
    spec = db.get(Characteristic, cfg.characteristic_id).spec
    means = [sum(g) / len(g) for g in groups]
    ranges = (
        [max(g) - min(g) for g in groups]
        if cfg.limits["n"] > 1
        else (
            [None] + [abs(means[i] - means[i - 1]) for i in range(1, len(means))]
            if means
            else []
        )
    )
    return {
        "limits": cfg.limits,
        "spec": spec,
        "labels": labels,
        "means": means,
        "ranges": ranges,
        "alarms": wykryj_przekroczenia_spc(groups, cfg.limits, spec),
        "source": "real",
        "sampling_plan": cfg.sampling_plan,
    }


@app.get("/api/spc/proposal/{characteristic_id}")
def spc_proposal(
    characteristic_id: int,
    start: date | None = None,
    end: date | None = None,
    u=Depends(require("configure")),
    auth=Depends(identity),
    db=Depends(db_session),
):
    """Przelicza propozycję granic z próby bazowej bez automatycznego zatwierdzenia."""
    require("spc", True)(auth)
    c = db.get(Characteristic, characteristic_id)
    if not c or c.spec["kind"] != "numeric":
        raise HTTPException(422, "Wymagana charakterystyka numeryczna")
    groups, labels = groups_for(db, characteristic_id, start=start, end=end)
    try:
        limits = oblicz_granice_kontrolne(groups)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return {
        "limits": limits,
        "subgroups": len(groups),
        "first": labels[0],
        "last": labels[-1],
        "approved": False,
    }


@app.get("/api/spc/export/{config_id}")
def export_spc(
    config_id: int,
    start: date | None = None,
    end: date | None = None,
    u=Depends(require("spc", True)),
    db=Depends(db_session),
):
    from .export import eksportuj_spc

    data = chart(config_id, start, end, u, db)
    return StreamingResponse(
        io.BytesIO(eksportuj_spc(data)),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="spc.xlsx"'},
    )


@app.get("/api/notifications")
def notifications(u=Depends(require("configure")), db=Depends(db_session)):
    return {
        "rules": [
            {
                "id": x.id,
                "characteristic_id": x.characteristic_id,
                "email": x.email,
                "events": x.events,
                "enabled": x.enabled,
            }
            for x in db.scalars(select(NotificationRule))
        ],
        "outbox": [
            {
                "id": x.id,
                "alert_id": x.alert_id,
                "recipient": x.recipient,
                "status": x.status,
                "sent_at": x.sent_at,
                "error": x.error,
            }
            for x in db.scalars(select(Outbox).order_by(Outbox.id.desc()).limit(200))
        ],
    }


@app.post("/api/notifications")
def add_notification(
    data: RuleInput, u=Depends(require("configure")), db=Depends(db_session)
):
    if not db.get(Characteristic, data.characteristic_id):
        raise HTTPException(422, "Nieznana charakterystyka")
    rule = NotificationRule(**data.model_dump())
    db.add(rule)
    db.flush()
    audit(db, u, "NOTIFICATION_RULE", rule.id, data.model_dump())
    db.commit()
    return {"id": rule.id}


@app.put("/api/notifications/{rule_id}")
def edit_notification(
    rule_id: int,
    data: RuleInput,
    u=Depends(require("configure")),
    db=Depends(db_session),
):
    rule = db.get(NotificationRule, rule_id)
    if not rule or not db.get(Characteristic, data.characteristic_id):
        raise HTTPException(404, "Nieznana reguła lub charakterystyka")
    before = {"email": rule.email, "events": rule.events, "enabled": rule.enabled}
    for k, v in data.model_dump().items():
        setattr(rule, k, v)
    audit(
        db,
        u,
        "EDIT_NOTIFICATION",
        rule.id,
        {"before": before, "after": data.model_dump()},
    )
    db.commit()
    return {"id": rule.id}


@app.get("/api/audit")
def audit_log(u=Depends(require("configure")), db=Depends(db_session)):
    return [
        {
            "id": x.id,
            "author": x.author,
            "action": x.action,
            "entity": x.entity,
            "payload": x.payload,
            "created": x.created,
        }
        for x in db.scalars(select(Audit).order_by(Audit.id.desc()).limit(500))
    ]


@app.post("/api/import/history")
async def import_history(
    file: UploadFile = File(...),
    u=Depends(require("configure")),
    db=Depends(db_session),
):
    """Importuje do kwarantanny historycznej, nigdy do zatwierdzonych wyników."""
    from .importer import importuj_historie

    content = await file.read(20 * 1024 * 1024 + 1)
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(413, "Limit pliku 20 MB")
    try:
        result = importuj_historie(db, u, content)
    except (ValueError, zipfile.BadZipFile, KeyError) as exc:
        raise HTTPException(422, "Nieprawidłowy skoroszyt: " + str(exc))
    audit(db, u, "IMPORT_HISTORY", file.filename, result)
    db.commit()
    return result


@app.get("/api/history")
def historical(
    lot: str = "", source: str = "real", auth=Depends(identity), db=Depends(db_session)
):
    source_guard(source, auth)
    if source != "real":
        raise HTTPException(422, "Historia źródłowa nie ma zatwierdzonej symulacji")
    return [
        {
            "id": x.id,
            "lot": x.lot,
            "row": x.row_number,
            "values": x.values,
            "issues": x.issues,
            "label": "HISTORIA DO WERYFIKACJI",
        }
        for x in db.scalars(
            select(HistoricalRow)
            .where(HistoricalRow.lot.contains(lot, autoescape=True))
            .limit(500)
        )
    ]
