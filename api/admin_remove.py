from typing import Optional
from fastapi import Header, HTTPException
from pydantic import BaseModel
from app import app, connect, get_state, verify_admin

class RemoveParticipantBody(BaseModel):
    position: int

@app.post('/api/admin/remove-participant')
def admin_remove_participant(body: RemoveParticipantBody, x_admin_pin: Optional[str] = Header(default=None)):
    verify_admin(x_admin_pin)
    with connect() as conn:
        try:
            with conn.cursor() as cur:
                event = cur.execute('select * from event_state where id=1 for update').fetchone()
                participant = cur.execute('select * from participants where position=%s for update', (body.position,)).fetchone()
                if not participant:
                    raise HTTPException(404, 'Nome não encontrado na fila')
                if cur.execute('select 1 from choices where participant_id=%s', (participant['id'],)).fetchone():
                    raise HTTPException(409, 'Este militar já realizou a escolha e não pode ser removido por esta função.')
                cur.execute('delete from participants where id=%s', (participant['id'],))
                if body.position == event['current_position']:
                    nxt = cur.execute("select min(p.position) as pos from participants p where p.position>%s and not exists(select 1 from choices c where c.participant_id=p.id)", (body.position,)).fetchone()['pos']
                    if nxt is None:
                        maxpos = cur.execute('select coalesce(max(position),%s) as pos from participants', (body.position,)).fetchone()['pos']
                        nxt = maxpos + 1
                    cur.execute('update event_state set current_position=%s,version=version+1,updated_at=now() where id=1', (nxt,))
                else:
                    cur.execute('update event_state set version=version+1,updated_at=now() where id=1')
            conn.commit()
            return get_state(conn)
        except HTTPException:
            conn.rollback()
            raise
