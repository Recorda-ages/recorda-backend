# Deploy na AWS (demo para stakeholders)

Arquitetura: EC2 `t4g.small` (Caddy + API em Docker) + RDS PostgreSQL `db.t4g.micro` + S3 para fotos e vídeos (com CloudFront depois), em **us-east-2 (Ohio)**. Custo estimado: ~US$ 32/mês + domínio.

A branch publicada é a **`dev`**. As migrações do banco (Alembic) rodam sozinhas a cada vez que a API sobe (`docker-entrypoint.sh`).

> **Mídias hoje:** o código da `dev` ainda guarda fotos e vídeos no PostgreSQL (tabela `media`). O bucket S3 já fica criado aqui. Quando o código passar a usar o S3, basta preencher as variáveis de S3 no `.env.prod` e configurar o CloudFront (etapa 9). Até lá, o disco do RDS tem autoscaling ligado.

Siga as etapas na ordem. Cada etapa diz o que anotar para as próximas.

---

## 0. Repositório (uma vez)

1. Faça o merge desta branch na `dev`. O workflow **Docker image** (`.github/workflows/docker-image.yml`) roda sozinho e publica `ghcr.io/recorda-ages/recorda-backend:latest`.
2. Confira em **Actions** se o job terminou verde.
3. Torne a imagem pública, para a EC2 baixar sem senha: no GitHub, abra a organização → **Packages** → `recorda-backend` → **Package settings** → **Change visibility** → **Public**.

## 1. Conta AWS

1. No canto superior direito do console, selecione a região **US East (Ohio) us-east-2**. Use essa região em todas as etapas.
2. Em **Billing → Budgets**, crie um orçamento mensal de **US$ 35** com alertas em US$ 25 e US$ 30.

## 2. Security groups (EC2 → Security Groups → Create)

Use a **VPC padrão** nos dois.

| Nome | Regras de entrada |
| --- | --- |
| `recorda-api-sg` | HTTP 80 de `0.0.0.0/0` · HTTPS 443 de `0.0.0.0/0` · **sem porta 22** |
| `recorda-db-sg` | PostgreSQL 5432 com origem **`recorda-api-sg`** (o security group, não um IP) |

A porta 80 fica aberta só para o Caddy emitir o certificado e redirecionar para HTTPS.

## 3. Bucket S3 (S3 → Create bucket)

1. Nome: `recorda-midias-550348326941` (precisa ser único no mundo; o sufixo é o ID da conta). Região: us-east-2.
2. **Block all public access: ligado.** Demais opções no padrão.
3. Depois de criado: **Permissions → Cross-origin resource sharing (CORS) → Edit** e cole o conteúdo de `deploy/aws/s3-cors.json`. Isso permite o upload direto do app por URL pré-assinada.

Anote o **nome do bucket**.

## 4. IAM role da EC2 (IAM → Roles → Create role)

1. Trusted entity: **AWS service → EC2**.
2. Permissões: marque **`AmazonSSMManagedInstanceCore`** (acesso ao terminal pelo Session Manager).
3. Nome: `recorda-ec2-role` → Create.
4. Abra a role → **Add permissions → Create inline policy → JSON**, cole `deploy/aws/iam-ec2-s3-policy.json` → nome `recorda-s3-midias`.

Com a role, a API acessa o S3 sem chave de acesso no `.env.prod` (o SDK pega as credenciais da instância).

## 5. Banco (RDS → Create database)

| Campo | Valor |
| --- | --- |
| Creation method | Standard create |
| Engine | PostgreSQL 16 (16.15) |
| Template | Dev/Test (troque a disponibilidade para Single-AZ) |
| DB instance identifier | `recorda-db` |
| Master username | `postgres` |
| Credentials management | **Self managed** (o Secrets Manager cobra à parte) |
| Master password | senha só com **letras e números** (`@ / :` quebram a URL) |
| Instance class | `db.t4g.micro` |
| Storage | gp3, 20 GB · **Storage autoscaling ligado, máximo 30 GB** (enquanto as mídias ficam no banco) |
| Availability | Single-AZ |
| VPC | VPC padrão (o subnet group padrão já cobre 2+ zonas) |
| Public access | **No** |
| Security group | `recorda-db-sg` (remova o `default`) |
| Availability Zone | `us-east-2a` |
| Database Insights | Standard · **Enhanced Monitoring desligado** |
| Additional configuration → Initial database name | **`recorda`** |

Leva 5–10 min. Anote o **Endpoint** (aba *Connectivity & security*).

## 6. Servidor (EC2 → Launch instance)

| Campo | Valor |
| --- | --- |
| Name | `recorda-api` |
| AMI | **Ubuntu Server 24.04 LTS**, arquitetura **64-bit (Arm)** |
| Instance type | `t4g.small` |
| Key pair | **Proceed without a key pair** (o acesso é pelo Session Manager) |
| Network → Subnet | a da zona **us-east-2a** (mesma do banco) |
| Auto-assign public IP | Enable |
| Security group | `recorda-api-sg` |
| Storage | 20 GB gp3 |
| Advanced → IAM instance profile | `recorda-ec2-role` |
| Advanced → User data | conteúdo de `deploy/ec2-user-data.sh` |

Depois de criada:

1. **EC2 → Elastic IPs → Allocate** → selecione o IP → **Associate** → instância `recorda-api`. Anote o **Elastic IP**.
2. Aguarde ~3 min para o user data terminar.

## 7. Domínio

Crie um registro **A** `api.<seu domínio>` apontando para o **Elastic IP**: no Route 53 (Hosted zone → Create record) ou no painel de DNS de onde o domínio foi comprado.

Sem domínio ainda? Use provisoriamente `<ip-com-hifens>.sslip.io` (ex.: Elastic IP `3.140.12.34` → `3-140-12-34.sslip.io`). Não precisa criar registro. É só para testes: a emissão do certificado pode falhar por limite do Let's Encrypt nesse domínio compartilhado.

## 8. Subir a API

1. **EC2 → recorda-api → Connect → Session Manager → Connect.** Abre um terminal no navegador.
2. Rode:

```bash
sudo -i
cd /opt/recorda-backend
openssl rand -hex 32          # copie o valor para ACCESS_TOKEN_SECRET_KEY
nano deploy/.env.prod         # preencha API_DOMAIN, DATABASE_URL, ACCESS_TOKEN_SECRET_KEY e as senhas do seed
docker compose -f deploy/compose.prod.yaml pull
docker compose -f deploy/compose.prod.yaml up -d
docker compose -f deploy/compose.prod.yaml logs -f   # migrações + certificado; Ctrl+C para sair
```

3. Teste: `https://<API_DOMAIN>/api/v1/health` deve responder `{"status":"ok", ...}`. A documentação fica em `/docs`.

### Dados de demonstração (opcional, uma vez)

O seed é bloqueado com `ENVIRONMENT=production`. Para carregar os usuários e Recordas de demo:

```bash
sed -i 's/^ENVIRONMENT=production/ENVIRONMENT=staging/' deploy/.env.prod
docker compose -f deploy/compose.prod.yaml up -d
docker compose -f deploy/compose.prod.yaml exec api python scripts/seed.py
sed -i 's/^ENVIRONMENT=staging/ENVIRONMENT=production/' deploy/.env.prod
docker compose -f deploy/compose.prod.yaml up -d
```

## 9. CloudFront (quando o código usar o S3)

1. **CloudFront → Create distribution** → plano **Free**.
2. Origin: o bucket `recorda-midias-550348326941` → **Origin access: Origin access control (OAC)** → crie um OAC.
3. Ao final, o console mostra uma **bucket policy**: copie e cole em S3 → bucket → Permissions → Bucket policy.
4. Anote o domínio `xxxx.cloudfront.net` e preencha `CLOUDFRONT_DOMAIN` no `.env.prod`. A API usa esse endereço para montar os links das mídias.

## Atualizar a versão no ar

Cada push na `dev` gera uma imagem nova. Para colocar no ar:

```bash
sudo -i
cd /opt/recorda-backend && git pull
docker compose -f deploy/compose.prod.yaml pull
docker compose -f deploy/compose.prod.yaml up -d
```

## Problemas comuns

| Sintoma | Causa provável |
| --- | --- |
| `pull` pede login / `denied` | Imagem do ghcr.io ainda privada (etapa 0.3) |
| Upload pelo app falha com erro de CORS | Regra de CORS do bucket ausente (etapa 3.3) |
| Caddy não emite certificado | Registro DNS ainda não aponta para o Elastic IP, ou porta 80 fechada |
| API reinicia com `ACCESS_TOKEN_SECRET_KEY must be configured` | Variável vazia no `.env.prod` |
| API reinicia com erro de conexão ao banco | `DATABASE_URL` errada, `recorda-db-sg` sem origem `recorda-api-sg`, ou banco `recorda` não criado |
| Session Manager não conecta | Role `recorda-ec2-role` não anexada à instância; anexe em Actions → Security → Modify IAM role e reinicie |

## Migração das mídias para o S3 (código)

A troca do armazenamento é no código: `app/repositories/media_storage_repository.py` passa a gravar e ler no bucket (via `boto3`), e a tabela `media` guarda só a chave do arquivo. Mídias enviadas antes dessa troca continuam no banco; para a demo, o mais simples é recarregar o seed depois da migração.
