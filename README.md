# Escolha de OM — Cavalaria

Aplicação web multiusuário para escolha de Organização Militar, com fila **Em pista → Paddock → Aquece**, backend FastAPI, PostgreSQL e Nginx via Docker Compose.

## Versão atual

- escolha pública **sem código individual de acesso**;
- a escolha é sempre registrada para o militar que estiver **Em pista**;
- proteção contra clique em tela desatualizada por `expected_position`;
- atualização automática dos dados a cada **20 segundos**;
- painel administrativo protegido por PIN;
- PostgreSQL persistente em volume Docker;
- botão de atualização manual continua disponível.

## Subir na VPS

```bash
git clone https://github.com/IceBl4ack/escolha-om-cavalaria.git
cd escolha-om-cavalaria
cp .env.example .env
nano .env
docker compose up -d --build
```

Depois acesse `http://IP_DA_VPS/` e `http://IP_DA_VPS/admin.html`.

Consulte `README_DEPLOY.md` para o passo a passo completo.
