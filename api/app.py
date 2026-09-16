import os
import secrets
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://escolhaom:escolhaom@db:5432/escolhaom")
ADMIN_PIN = os.getenv("ADMIN_PIN", "troque-este-pin")
EVENT_TITLE = os.getenv("EVENT_TITLE", "Escolha de Organização Militar")
EVENT_COURSE = os.getenv("EVENT_COURSE", "Curso de Cavalaria")

app = FastAPI(title="Escolha de OM - Cavalaria", docs_url=None, redoc_url=None)

# Exatamente as vagas informadas pelo usuário na última relação.
UNITS = [
    ("CMA", "18º RC Mec", "Boa Vista-RR", 2, 10, "right", "#178735"),
    ("CMNE", "16º RC Mec", "Bayeux-PB", 2, 20, "right", "#ef7f1a"),
    ("CML", "ESA", "Três Corações-MG", 1, 30, "right", "#ef2020"),
    ("CML", "2º RCG", "Rio de Janeiro-RJ", 3, 40, "right", "#ef2020"),
    ("CML", "15º RC Mec", "Rio de Janeiro-RJ", 2, 50, "right", "#ef2020"),
    ("CML", "EsAO", "Rio de Janeiro-RJ", 1, 60, "right", "#ef2020"),
    ("CML", "EsEqEx", "Rio de Janeiro-RJ", 1, 70, "right", "#ef2020"),
    ("CML", "AMAN", "Resende-RJ", 1, 80, "right", "#ef2020"),
    ("CMP", "1º RCG", "Brasília-DF", 2, 90, "right", "#2f5c95"),
    ("CMO", "20º RCB", "Campo Grande-MS", 2, 100, "right", "#63b63c"),
    ("CMO", "10º RC Mec", "Bela Vista-MS", 2, 110, "right", "#63b63c"),
    ("CMO", "11º RC Mec", "Ponta Porã-MS", 2, 120, "right", "#63b63c"),
    ("CMO", "17º RC Mec", "Amambai-MS", 2, 130, "right", "#63b63c"),
    ("CMSE", "13º RC Mec", "Pirassununga-SP", 2, 140, "right", "#ee4444"),
    ("CMSE", "3º RCC", "Ponta Grossa-PR", 2, 150, "right", "#ee4444"),
    ("CMS", "5º RCC", "Rio Negro-PR", 2, 160, "left", "#7fc3d3"),
    ("CMS", "14º RC Mec", "São Miguel d'Oeste-SC", 3, 170, "left", "#7fc3d3"),
    ("CMS", "3º RCG", "Porto Alegre-RS", 1, 180, "left", "#7fc3d3"),
    ("CMS", "1º RCC", "Santa Maria-RS", 2, 190, "left", "#7fc3d3"),
    ("CMS", "4º RCC", "Rosário do Sul-RS", 4, 200, "left", "#7fc3d3"),
    ("CMS", "1º RC Mec", "Itaqui-RS", 2, 210, "left", "#7fc3d3"),
    ("CMS", "2º RC Mec", "São Borja-RS", 1, 220, "left", "#7fc3d3"),
    ("CMS", "19º RC Mec", "Santa Rosa-RS", 1, 230, "left", "#7fc3d3"),
    ("CMS", "4º RCB", "São Luiz Gonzaga-RS", 1, 240, "left", "#7fc3d3"),
    ("CMS", "8º RC Mec", "Uruguaiana-RS", 1, 250, "left", "#7fc3d3"),
    ("CMS", "5º RC Mec", "Quaraí-RS", 3, 260, "left", "#7fc3d3"),
    ("CMS", "6º RCB", "Alegrete-RS", 1, 270, "left", "#7fc3d3"),
    ("CMS", "3º RC Mec", "Bagé-RS", 1, 280, "left", "#7fc3d3"),
    ("CMS", "7º RC Mec", "Santana do Livramento-RS", 3, 290, "left", "#7fc3d3"),
    ("CMS", "12º RC Mec", "Jaguarão-RS", 3, 300, "left", "#7fc3d3"),
    ("CMS", "9º RCB", "São Gabriel-RS", 4, 310, "left", "#7fc3d3"),
]

class ChoiceBody(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    unit_id: int

class QueueBody(BaseModel):
    names: list[str]

class OpenBody(BaseModel):
    open: bool


def connect():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, autocommit=False)


def wait_for_db():
    last = None
    for _ in range(60):
        try:
            with connect() as conn:
                conn.execute("select 1")
            return
        except Exception as exc:
            last = exc
            time.sleep(1)
    raise RuntimeError(f"Banco indisponível: {last}")


def init_db():
    wait_for_db()
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                create table if not exists event_state (
                    id integer primary key check (id=1),
                    title text not null,
                    course text not null,
                    current_position integer not null default 1,
                    is_open boolean not null default false,
                    version bigint not null default 0,
                    updated_at timestamptz not null default now()
                );
                create table if not exists units (
                    id bigserial primary key,
                    region_code text not null,
                    unit_name text not null,
                    city text not null,
                    capacity integer not null check (capacity >= 0),
                    display_order integer not null,
                    side text not null check (side in ('left','right')),
                    color text not null,
                    unique(unit_name, city)
                );
                create table if not exists participants (
                    id bigserial primary key,
                    position integer not null unique,
                    name text not null,
                    access_code text not null unique
                );
                create table if not exists choices (
                    id bigserial primary key,
                    participant_id bigint not null unique references participants(id) on delete cascade,
                    unit_id bigint not null references units(id),
                    participant_position integer not null unique,
                    created_at timestamptz not null default now()
                );
                create index if not exists idx_choices_unit on choices(unit_id);
                create index if not exists idx_participants_code on participants(access_code);
            """)
            cur.execute("""
                insert into event_state(id,title,course,current_position,is_open,version)
                values(1,%s,%s,1,false,0)
                on conflict(id) do update set title=excluded.title, course=excluded.course
            """, (EVENT_TITLE, EVENT_COURSE))

            keep = []
            for region, name, city, capacity, order, side, color in UNITS:
                cur.execute("""
                    insert into units(region_code,unit_name,city,capacity,display_order,side,color)
                    values(%s,%s,%s,%s,%s,%s,%s)
                    on conflict(unit_name,city) do update set
                      region_code=excluded.region_code,
                      capacity=excluded.capacity,
                      display_order=excluded.display_order,
                      side=excluded.side,
                      color=excluded.color
                    returning id
                """, (region, name, city, capacity, order, side, color))
                keep.append(cur.fetchone()["id"])
            # Só remove OMs antigas sem escolhas. Mantém integridade se houver histórico.
            cur.execute("delete from units where not (id = any(%s)) and not exists (select 1 from choices c where c.unit_id=units.id)", (keep,))
        conn.commit()


@app.on_event("startup")
def startup_event():
    init_db()


def verify_admin(pin: Optional[str]):
    if not pin or not secrets.compare_digest(pin, ADMIN_PIN):
        raise HTTPException(status_code=401, detail="PIN administrativo inválido")


def get_state(conn, access_code: Optional[str] = None):
    event = conn.execute("select * from event_state where id=1").fetchone()
    units = conn.execute("""
        select u.*,
               count(c.id)::int as used,
               (u.capacity-count(c.id))::int as remaining
        from units u
        left join choices c on c.unit_id=u.id
        group by u.id
        order by u.display_order
    """).fetchall()
    queue = conn.execute("""
        select p.position,p.name,exists(select 1 from choices c where c.participant_id=p.id) as chosen
        from participants p order by p.position
    """).fetchall()
    choices = conn.execute("""
        select c.participant_position as position,p.name,u.id as unit_id,u.region_code as region,
               u.unit_name as unit,u.city,c.created_at
        from choices c
        join participants p on p.id=c.participant_id
        join units u on u.id=c.unit_id
        order by c.participant_position
    """).fetchall()
    me = None
    if access_code:
        p = conn.execute("select id,position,name from participants where upper(access_code)=upper(%s) limit 1", (access_code.strip(),)).fetchone()
        if p:
            chosen = conn.execute("select 1 from choices where participant_id=%s", (p["id"],)).fetchone() is not None
            me = {
                "id": p["id"], "position": p["position"], "name": p["name"], "chosen": chosen,
                "can_choose": bool(event["is_open"] and not chosen and p["position"] == event["current_position"]),
            }
    return {
        "event": {
            "title": event["title"], "course": event["course"],
            "current_position": event["current_position"], "is_open": event["is_open"],
            "version": event["version"], "updated_at": event["updated_at"].isoformat(),
        },
        "me": me,
        "units": [dict(x) for x in units],
        "queue": [dict(x) for x in queue],
        "choices": [{**dict(x), "created_at": x["created_at"].isoformat()} for x in choices],
    }


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/state")
def state(code: Optional[str] = None):
    with connect() as conn:
        return get_state(conn, code)


@app.post("/api/choose")
def choose(body: ChoiceBody):
    with connect() as conn:
        try:
            with conn.cursor() as cur:
                event = cur.execute("select * from event_state where id=1 for update").fetchone()
                if not event["is_open"]:
                    raise HTTPException(409, "As escolhas estão fechadas")
                participant = cur.execute(
                    "select * from participants where upper(access_code)=upper(%s) limit 1", (body.code.strip(),)
                ).fetchone()
                if not participant:
                    raise HTTPException(401, "Código de acesso inválido")
                if cur.execute("select 1 from choices where participant_id=%s", (participant["id"],)).fetchone():
                    raise HTTPException(409, "Você já realizou sua escolha")
                if participant["position"] != event["current_position"]:
                    raise HTTPException(409, "Ainda não é sua vez de escolher")
                unit = cur.execute("select * from units where id=%s for update", (body.unit_id,)).fetchone()
                if not unit:
                    raise HTTPException(404, "OM inválida")
                used = cur.execute("select count(*) as n from choices where unit_id=%s", (body.unit_id,)).fetchone()["n"]
                if used >= unit["capacity"]:
                    raise HTTPException(409, "Essa OM não possui mais vagas")
                cur.execute(
                    "insert into choices(participant_id,unit_id,participant_position) values(%s,%s,%s)",
                    (participant["id"], body.unit_id, participant["position"]),
                )
                nxt = cur.execute("""
                    select min(p.position) as pos from participants p
                    where p.position > %s and not exists(select 1 from choices c where c.participant_id=p.id)
                """, (participant["position"],)).fetchone()["pos"]
                new_pos = nxt if nxt is not None else participant["position"] + 1
                cur.execute("update event_state set current_position=%s,version=version+1,updated_at=now() where id=1", (new_pos,))
            conn.commit()
            return get_state(conn, body.code)
        except HTTPException:
            conn.rollback()
            raise
        except psycopg.errors.UniqueViolation:
            conn.rollback()
            raise HTTPException(409, "A escolha já foi registrada. Atualize a tela.")


@app.get("/api/admin/state")
def admin_state(x_admin_pin: Optional[str] = Header(default=None)):
    verify_admin(x_admin_pin)
    with connect() as conn:
        s = get_state(conn)
        codes = conn.execute("select position,name,access_code as code from participants order by position").fetchall()
        s["codes"] = [dict(x) for x in codes]
        return s


@app.post("/api/admin/queue")
def admin_queue(body: QueueBody, x_admin_pin: Optional[str] = Header(default=None)):
    verify_admin(x_admin_pin)
    names = [n.strip() for n in body.names if n and n.strip()]
    if not names:
        raise HTTPException(400, "A lista de nomes está vazia")
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("select * from event_state where id=1 for update")
            cur.execute("delete from choices")
            cur.execute("delete from participants")
            for pos, name in enumerate(names, start=1):
                code = secrets.token_hex(6).upper()
                cur.execute("insert into participants(position,name,access_code) values(%s,%s,%s)", (pos, name, code))
            cur.execute("update event_state set current_position=1,is_open=false,version=version+1,updated_at=now() where id=1")
        conn.commit()
        s = get_state(conn)
        codes = conn.execute("select position,name,access_code as code from participants order by position").fetchall()
        s["codes"] = [dict(x) for x in codes]
        return s


@app.post("/api/admin/open")
def admin_open(body: OpenBody, x_admin_pin: Optional[str] = Header(default=None)):
    verify_admin(x_admin_pin)
    with connect() as conn:
        conn.execute("update event_state set is_open=%s,version=version+1,updated_at=now() where id=1", (body.open,))
        conn.commit()
        s = get_state(conn)
        s["codes"] = [dict(x) for x in conn.execute("select position,name,access_code as code from participants order by position").fetchall()]
        return s


@app.post("/api/admin/undo")
def admin_undo(x_admin_pin: Optional[str] = Header(default=None)):
    verify_admin(x_admin_pin)
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("select * from event_state where id=1 for update")
            last = cur.execute("select * from choices order by participant_position desc limit 1 for update").fetchone()
            if not last:
                raise HTTPException(409, "Não há escolha para desfazer")
            cur.execute("delete from choices where id=%s", (last["id"],))
            cur.execute("update event_state set current_position=%s,version=version+1,updated_at=now() where id=1", (last["participant_position"],))
        conn.commit()
        s = get_state(conn)
        s["codes"] = [dict(x) for x in conn.execute("select position,name,access_code as code from participants order by position").fetchall()]
        return s


@app.post("/api/admin/reset")
def admin_reset(x_admin_pin: Optional[str] = Header(default=None)):
    verify_admin(x_admin_pin)
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("select * from event_state where id=1 for update")
            cur.execute("delete from choices")
            cur.execute("update event_state set current_position=1,is_open=false,version=version+1,updated_at=now() where id=1")
        conn.commit()
        s = get_state(conn)
        s["codes"] = [dict(x) for x in conn.execute("select position,name,access_code as code from participants order by position").fetchall()]
        return s


@app.exception_handler(HTTPException)
def http_error(_, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
