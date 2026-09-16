# Deploy na VPS Ubuntu Minimal

## 1. Instalar Docker

```bash
apt update
apt install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${UBUNTU_CODENAME:-$VERSION_CODENAME} stable" > /etc/apt/sources.list.d/docker.list
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
```

Teste:

```bash
docker --version
docker compose version
```

## 2. Clonar e configurar

```bash
cd /root
git clone https://github.com/IceBl4ack/escolha-om-cavalaria.git
cd escolha-om-cavalaria
cp .env.example .env
nano .env
```

Defina pelo menos:

```text
POSTGRES_PASSWORD=UMA_SENHA_FORTE
ADMIN_PIN=UM_PIN_FORTE
HTTP_PORT=80
```

## 3. Subir

```bash
docker compose up -d --build
docker compose ps
curl http://127.0.0.1/api/health
```

Acesso público: `http://IP_DA_VPS/`

Administração: `http://IP_DA_VPS/admin.html`

## 4. Funcionamento atual

A página pública não exige código individual. A OM confirmada é registrada para o militar que estiver em **Em pista**. O backend recebe também a posição que a tela espera (`expected_position`) e rejeita a requisição se a fila já tiver avançado, evitando uma escolha acidental para o próximo militar.

A página pública e o painel administrativo consultam os dados novamente a cada **20 segundos**. O botão **Atualizar agora** permite sincronização imediata.

## 5. Atualizar uma VPS já instalada

```bash
cd /root/escolha-om-cavalaria
git pull
docker compose up -d --build
```

Confira:

```bash
docker compose ps
docker compose logs --tail=100 api
curl http://127.0.0.1/api/health
```

Se o navegador ainda mostrar a versão anterior, faça uma atualização forçada ou feche e abra novamente o PWA. O service worker desta versão usa um novo cache.

## 6. Dados

O PostgreSQL usa volume persistente. Para parar sem apagar os dados:

```bash
docker compose down
```

Não use `docker compose down -v` em produção, pois `-v` remove o volume do banco.
