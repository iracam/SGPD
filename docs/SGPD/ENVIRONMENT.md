# Ambiente

## 1. Escopo do levantamento

Levantamento executado em 2026-07-27 no ambiente DEV.

Este é o único ambiente no escopo atual. HML e PRD não serão configurados nesta etapa.

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
| Gunicorn | Ausente | Fora da execução DEV atual |
| Nginx | Ausente/inativo | Não será utilizado; estáticos serão servidos por WhiteNoise |
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
| CI/CD | Nenhum workflow ou arquivo de pipeline | Não será utilizado no escopo atual |

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

### Agendamento das notificações no DEV

A fila só anda quando o sistema operacional chama os comandos, e a sonda
`sgpd_operations_check` é quem torna o agendamento parado visível (R63). As
entradas sugeridas de `crontab`, a verificação e o que fazer quando a fila
empaca estão no `RUNBOOK.md` §2 — fonte canônica do procedimento.

## 4. Ambientes

| Item | DEV |
|---|---|
| Host/SO | Debian 13.6 confirmado |
| Python | 3.13 homologado; dependências gerenciadas por `uv` |
| Oracle | Database 19c e Instant Client 19.28 confirmados |
| Oracle SGPD | Owner `SGPD` como conexão única; `CREATE TABLE` e `CREATE SEQUENCE` sem `ADMIN OPTION`; quota de 500 MB em `PIMS_DATA`; migrations aplicadas |
| Senior HCM | Schema `VETORH` no mesmo serviço; cinco grants `SELECT` confirmados para `SGPD` |
| Redis | Container sob demanda |
| Worker | Adiado até necessidade |
| SMTP | Microsoft 365; SMTP AUTH e `Send As` validados com uma mensagem de prova aceita |
| Autenticação | Local operacional; descoberta e login AD compartilham o transporte definido pelo SuperAdmin; LDAP simples funciona com warning; login AD desligado até teste controlado |
| Estáticos | WhiteNoise configurado para assets da SPA e Django Admin |
| Frontend | SPA Angular 21 + PrimeNG 21 em operação; Node 24.18.0 e npm 11.16.0 homologados |
| Evidências | Filesystem local privado em `media/evidence` |
| Nginx / proxy | Não utilizado |
| Secrets | `.env` local; usuários individuais no formato `nome.sobrenome` |
| CI/CD | Não utilizado |

HML e PRD estão explicitamente fora do escopo atual.

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
2. Instalar o agendamento das notificações no DEV e confirmar a primeira
   execução (R63). Celery e Django-Q2 continuam sem caso de uso. O
   procedimento e a sonda estão no `RUNBOOK.md` §2.
3. Decidir operacionalmente entre TLS e LDAP simples. Para TLS, instalar a CA
   `BSA-AD-CA`; sem TLS, aceitar explicitamente o warning de credenciais e
   senhas sem criptografia. Bind, bases, grupo `BSA_SGPD` e descoberta já foram
   validados no DEV.
4. Definir o Compose do Redis quando surgir a primeira dependência de cache,
   lock distribuído ou limitação de taxa; notificações não exigem Redis.
5. Validar o backup com o DBA: cobertura do schema `SGPD`, do storage privado
   de evidências e prova de restauração. O procedimento está no `RUNBOOK.md`
   §6 e ainda não foi executado.

O procedimento de descoberta de domínio, OUs e grupos, os filtros LDAP e a
sequência de ativação estão em `INTEGRATION_ACTIVE_DIRECTORY.md`.

## 8. Estado do bloco de ambiente

O inventário e as decisões do bloco Ambiente estão concluídos.

SMTP AUTH e `Send As` foram validados em 2026-07-28. O Microsoft 365 aceitou
uma mensagem de prova enviada ao próprio remetente configurado.

Referência do SMTP Microsoft 365: [Microsoft Learn — configurar envio por aplicativo](https://learn.microsoft.com/pt-br/exchange/mail-flow-best-practices/how-to-set-up-a-multifunction-device-or-application-to-send-email-using-microsoft-365-or-office-365).
