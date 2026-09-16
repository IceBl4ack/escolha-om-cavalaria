# Escolha de OM — Docker / Ubuntu Minimal

Aplicação web multiusuário para escolha de Organização Militar, com fila `Em pista → Paddock → Aquece`, backend FastAPI, PostgreSQL e Nginx via Docker Compose.

Esta versão é autônoma e roda integralmente na VPS. O arquivo `.env` não deve ser commitado; use `.env.example` como modelo.

## Subir na VPS

```bash
git clone https://github.com/IceBl4ack/escolha-om-cavalaria.git
cd escolha-om-cavalaria
cp .env.example .env
nano .env
docker compose up -d --build
```

Consulte `README_DEPLOY.md` para o passo a passo completo.
