# Ambiente

## 1. Escopo do levantamento

Levantamento executado em 2026-07-27 no ambiente DEV.

Desde 2026-08-05 existe um segundo ambiente: o host de produção da ADR-055, em
`/opt/sgpd` sob usuário de serviço, apontando para o mesmo schema `SGPD`. HML
continua fora do escopo.

Nenhum segredo foi exibido ou registrado. A inspeção documental considerou nomes de variáveis, executáveis, versões, estado de serviços e arquivos de configuração; as credenciais locais foram usadas somente pelo cliente Oracle durante o teste de conexão.

## 2. Ambiente local confirmado

| Componente | Estado observado | Situação para o projeto |
|---|---|---|
| Sistema operacional | Debian GNU/Linux 13.6 (trixie), kernel 6.12, x86_64 | Confirmado para DEV |
| Timezone | UTC-03:00 | Aplicação configurada com `America/Sao_Paulo` explicitamente |
| Locale | `C.UTF-8` | Validar regras de apresentação em português |
| Git | branch `main`, remoto `origin` configurado | Repositório confirmado |
| Python | CPython 3.13.5 | Python 3.13 homologado; ambiente virtual isolado pelo `uv` |
| `pip` | 25.1.1 | Disponível no Python do sistema |
| `uv` | 0.11.29 | Gerenciador adotado; dependências bloqueadas em `uv.lock` |
| Poetry / Pipenv / pyenv | Não instalados | Não necessários se `uv` for adotado |
| Django / DRF | Django 5.2.16 / DRF 3.17.1 | Instalados e bloqueados por `uv.lock` |
| Node.js | 24.18.0 | Homologado para o build da SPA (ADR-025) |
| npm | 11.16.0 | Homologado; instalação por `npm ci` com `package-lock.json` versionado |
| Angular / PrimeNG | 21.2.18 / 21.1.9 | Instalados e fixados pelo `package-lock.json` |
| Docker Engine | 26.1.5, daemon ativo, driver `overlay2` | Disponível; nenhum container em execução |
| Docker Compose | 2.26.1 | Disponível |
| Oracle Database | 19c | Versão confirmada para o projeto |
| Oracle Instant Client | 19.28 em `/opt/oracle/instantclient_19_28` | Cliente nativo confirmado |
| Driver Python Oracle | `python-oracledb` 4.0.2 | Modo Thick validado com o Instant Client 19.28 |
| SQLcl local | 26.1 em `/opt/sqlcl/bin/sql` | Conexões Oracle validadas |
| Redis | Somente `redis-cli` 8.0.2; servidor local ausente/inativo | Será iniciado em container quando necessário |
| Celery / Django-Q2 | Ausentes | Worker adiado até existir caso de uso |
| Gunicorn | 23.0.0, bloqueado em `uv.lock` | Servidor WSGI do host de produção, sob systemd com **um worker** (ADR-055). `runserver` volta a ser exclusivo de desenvolvimento |
| Nginx | Ausente, também no PRD | Estáticos e assets da SPA são servidos pelo WhiteNoise, no próprio processo (ADR-014, reafirmada pela ADR-055). O proxy em `192.168.1.6` só termina o TLS e encaminha; ele não tem o build da SPA e não serve arquivo (ADR-052) |
| WhiteNoise | 6.12.0 | Serve assets da SPA e estáticos do Django Admin; nunca evidências |
| LDAP nativo | OpenLDAP 2.6.10; `ldapsearch` e headers de desenvolvimento instalados | Pré-requisitos de build e diagnóstico confirmados |
| LDAP Python | `django-auth-ldap` 5.3.0 / `python-ldap` 3.4.7 | Instalados e bloqueados em `uv.lock`, sem regressão de Django ou DRF |
| Active Directory | `ad.bsa.local` → `192.168.1.20`; LDAP 389 e LDAPS 636 acessíveis; RootDSE `DC=bsa,DC=local` | Endpoint e domínio confirmados; CA `BSA-AD-CA`, bind e DNs de OU/grupo ainda pendentes de homologação |
| SMTP | Microsoft 365, `smtp.office365.com:587`, TLS/STARTTLS | SMTP AUTH e remetente configurado validados em 2026-07-28 |
| Evidências | Filesystem local privado | Caminho inicial `media/evidence`, fora do WhiteNoise |
| Configuração técnica | Filesystem local privado | Certificados em `media/system-configuration`, fora do WhiteNoise |
| Pytest | 9.1.1 no ambiente do projeto | Configurado com pytest-django |
| Ruff | 0.16.0 no ambiente do projeto | Lint e formatação configurados no `pyproject.toml` |
| Mypy | 1.20.2 no ambiente do projeto | Modo strict com django-stubs |
| CI/CD | Nenhum workflow ou arquivo de pipeline | Não será utilizado (ADR-016). O deploy do PRD é `scripts/deploy.sh`, executado à mão no host |

## 3. Fundação instalada

O repositório possui:

- `pyproject.toml`, `uv.lock` e ambiente virtual reproduzível;
- projeto Django e settings separados para base, DEV e testes;
- conexão Oracle Thick com o mesmo owner `SGPD`;
- WhiteNoise para assets da SPA e estáticos do Django Admin;
- configuração de testes, lint, formatação e tipagem;
- configuração de SMTP;
- integração LDAP/Active Directory com descoberta e autenticação em estágios;
- definição de storage de evidências;
- health checks e logs JSON com correlation ID.

Redis e worker continuam adiados: a Fase 7 resolveu notificações com outbox no
Oracle e comandos agendados, sem broker (ADR-049).

### Configuração de e-mail

Desde a ADR-050, as variáveis `EMAIL_*`, `DEFAULT_FROM_EMAIL`, `SGPD_BASE_URL` e
`NOTIFICATION_*` do `.env` são apenas o baseline do primeiro boot. O que vale em
execução é o singleton `SGPD_EMAIL_CONFIG`, editado em
`/fe/configuracoes/email` por SuperAdmin. Enquanto ninguém salvar a primeira
vez, o `.env` continua governando — nada quebra por não haver registro.

### Agendamento das notificações

A fila só anda quando o sistema operacional chama os comandos, e a sonda
`sgpd_operations_check` é quem torna o agendamento parado visível (R63). No DEV
o `crontab` foi instalado em 2026-08-01; no PRD o mesmo par de comandos roda por
timers do systemd, que expõem a saída diferente de zero da sonda como unidade
`failed`. As entradas exatas, a verificação e o que fazer quando a fila empaca
estão no `RUNBOOK.md` §2 — fonte canônica do procedimento.

## 4. Ambientes

| Item | DEV | PRD (ADR-055) |
|---|---|---|
| Host/SO | Debian 13.6 confirmado | Debian 13, host próprio |
| Diretório | Árvore de trabalho do desenvolvedor | `/opt/sgpd`, usuário de serviço `sgpd` sem shell de login |
| Python | 3.13 homologado; dependências gerenciadas por `uv` | Mesmo `uv.lock`, instalado com `uv sync --frozen --no-dev` |
| Oracle | Database 19c e Instant Client 19.28 confirmados | Mesmos |
| Oracle SGPD | Owner `SGPD` como conexão única; `CREATE TABLE` e `CREATE SEQUENCE` sem `ADMIN OPTION`; quota de 500 MB em `PIMS_DATA`; migrations aplicadas | **O mesmo schema**, promovido a produtivo; ADR-022 estendida como risco aceito |
| Senior HCM | Schema `VETORH` no mesmo serviço; cinco grants `SELECT` confirmados para `SGPD` | Mesmo contrato |
| Servidor | `runserver` com `--settings=config.settings.development` | Gunicorn sob `sgpd-web.service`, **um worker** e oito threads, em `:8002` |
| Agendamento | `crontab` do usuário (`RUNBOOK.md` §2) | `sgpd-notifications.timer` e `sgpd-operations-check.timer` |
| Redis | Container sob demanda | Ausente; exigido apenas se a concorrência subir de um worker |
| Worker | Adiado até necessidade | Adiado |
| SMTP | Microsoft 365; SMTP AUTH e `Send As` validados com uma mensagem de prova aceita | Mesma conta; transporte efetivo vem da central (ADR-050) |
| Autenticação | Local operacional; descoberta e login AD compartilham o transporte definido pelo SuperAdmin; LDAP simples funciona com warning; login AD desligado até teste controlado | Mesma configuração, lida do mesmo schema |
| Estáticos | WhiteNoise configurado para assets da SPA e Django Admin | Mesmo, sem releitura de disco |
| Frontend | SPA Angular 21 + PrimeNG 21 em operação; Node 24.18.0 e npm 11.16.0 homologados | Mesmo build, gerado no host pelo `scripts/deploy.sh` |
| Evidências | Filesystem local privado em `media/evidence` | `/var/lib/sgpd/evidence`, fora da árvore da aplicação |
| Django Admin | Ligado | Desligado (`DJANGO_ADMIN_ENABLED=false`) |
| Publicação | Acesso local | `https://sgpd.bsabioenergia.com.br` por proxy em `192.168.1.6`, que termina o TLS e encaminha para `:8002` repassando `X-Forwarded-Proto` e `X-Forwarded-For`; settings `config.settings.production` (ADR-052) |
| Secrets | `.env` local; usuários individuais no formato `nome.sobrenome` | `.env` em modo `600`; **mesmo `DJANGO_SECRET_KEY` enquanto o schema for compartilhado** (R69) |
| CI/CD | Não utilizado | Não utilizado; `scripts/deploy.sh` à mão |

HML continua fora do escopo. O procedimento de corte, o checklist de go-live e o
rollback estão no `RUNBOOK.md` §11.

## 5. Contrato de variáveis

O arquivo `.env.example` define, sem valores sensíveis:

- variáveis ativas de aplicação, settings, cookies e logging;
- conexão Oracle única do runtime e migrations com `SGPD`;
- leitura direta dos objetos `VETORH` autorizados pela mesma conexão;
- Oracle Instant Client e TNS;
- WhiteNoise;
- SMTP;
- caminho do storage local de evidências;
- caminho do storage privado de configuração técnica;
- limitação de tentativas de login;
- configuração AD completa: chaves independentes de descoberta e autenticação,
  URI, TLS/CA, bind, bases, grupo/filtro, timeouts, paginação e contingência.

As variáveis de LDAP/AD são o baseline de primeiro boot. Depois do primeiro
salvamento por SuperAdmin, o singleton versionado do schema SGPD passa a ser a
fonte dinâmica dos backends e consultas, sempre sujeito às chaves explícitas
de descoberta e autenticação. Redis/Celery e S3 continuam como reservas para
fases futuras.

O `.env` local contém o owner `SGPD`, que será reutilizado no runtime DEV por decisão explícita. A conexão separada com o owner `VETORH` não faz parte do contrato da aplicação.

## 6. Segredos

- arquivos `.env` reais são ignorados pelo Git;
- `.env.example` não contém credenciais;
- wallets, arquivos TNS locais e keystores são ignorados;
- usuário, senha e e-mail das integrações partem do `.env` local; a senha de
  bind informada pela central é persistida cifrada e nunca projetada;
- usuários individuais seguem a convenção `nome.sobrenome`;
- senhas não podem seguir padrão previsível;
- o `.env` deve ter permissões restritas ao usuário da aplicação;
- credenciais de SGPD, SMTP, LDAP e storage devem ser distintas e rotacionáveis;
- nenhuma string de conexão deve ser registrada em logs.

Nenhum valor real de usuário, senha ou token deve ser incluído no repositório.

## 7. Pendências operacionais

1. Confirmar TLS/wallet da conexão única `SGPD`.
2. ~~Instalar o agendamento das notificações no DEV~~ — feito em 2026-08-01:
   varredura com despacho a cada dez minutos e sonda a cada trinta, ambas no
   `crontab` do usuário da aplicação (`RUNBOOK.md` §2). Celery e Django-Q2
   continuam sem caso de uso.
3. Decidir operacionalmente entre TLS e LDAP simples. Para TLS, instalar a CA
   `BSA-AD-CA`; sem TLS, aceitar explicitamente o warning de credenciais e
   senhas sem criptografia. Bind, bases, grupo `BSA_SGPD` e descoberta já foram
   validados no DEV.
4. Definir o Compose do Redis quando surgir a primeira dependência de cache,
   lock distribuído ou limitação de taxa; notificações não exigem Redis.
5. Validar o backup com o DBA: cobertura do schema `SGPD`, do storage privado
   de evidências e prova de restauração. O procedimento está no `RUNBOOK.md`
   §6 e ainda não foi executado.

Pendências abertas com o PRD, aceitas por decisão em 2026-08-05 (ADR-055) e
registradas no `RISK_REGISTER.md` com prazo, sem bloquear o go-live:

6. Rotacionar as senhas do Oracle e do SMTP, hoje previsíveis (R66).
7. Trocar o bind do AD por conta de serviço somente leitura com TLS (R67).
8. Criar usuário Oracle de aplicação com privilégio mínimo, separado do owner
   `SGPD`, encerrando a extensão da ADR-022 ao ambiente produtivo.
9. Substituir a chave de cifra da central por chave dedicada e rotacionável,
   independente do `DJANGO_SECRET_KEY` (R69) — hoje ela é o que obriga os dois
   hosts a compartilharem a mesma chave enquanto o schema for o mesmo.

O procedimento de descoberta de domínio, OUs e grupos, os filtros LDAP e a
sequência de ativação estão em `INTEGRATION_ACTIVE_DIRECTORY.md`.

## 8. Estado do bloco de ambiente

O inventário e as decisões do bloco Ambiente estão concluídos.

SMTP AUTH e `Send As` foram validados em 2026-07-28. O Microsoft 365 aceitou
uma mensagem de prova enviada ao próprio remetente configurado.

Referência do SMTP Microsoft 365: [Microsoft Learn — configurar envio por aplicativo](https://learn.microsoft.com/pt-br/exchange/mail-flow-best-practices/how-to-set-up-a-multifunction-device-or-application-to-send-email-using-microsoft-365-or-office-365).
