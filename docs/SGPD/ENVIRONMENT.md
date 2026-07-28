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
| LDAP tools | `ldapsearch` ausente | Não bloqueia o MVP local; necessário na integração futura com AD |
| SMTP | Microsoft 365, `smtp.office365.com:587`, TLS/STARTTLS | SMTP AUTH e remetente configurado validados em 2026-07-28 |
| Evidências | Filesystem local privado | Caminho inicial `media/evidence`, fora do WhiteNoise |
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
- configuração futura de LDAP/Active Directory;
- definição de storage de evidências;
- health checks e logs JSON com correlation ID.

Redis e worker continuam adiados até surgir um caso de uso.

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
| Autenticação | Local; usuários, papéis e escopos aplicados; vínculo AD administrativo disponível; LDAP/AD real não configurado |
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
- limitação de tentativas de login.

As variáveis de Redis/Celery, LDAP/AD e S3 são reservas explícitas para fases
futuras e ainda não são consumidas pelos settings atuais. Sua presença não
significa que essas integrações estejam implantadas.

O `.env` local contém o owner `SGPD`, que será reutilizado no runtime DEV por decisão explícita. A conexão separada com o owner `VETORH` não faz parte do contrato da aplicação.

## 6. Segredos

- arquivos `.env` reais são ignorados pelo Git;
- `.env.example` não contém credenciais;
- wallets, arquivos TNS locais e keystores são ignorados;
- usuário, senha e e-mail das integrações ficarão no `.env` local;
- usuários individuais seguem a convenção `nome.sobrenome`;
- senhas não podem seguir padrão previsível;
- o `.env` deve ter permissões restritas ao usuário da aplicação;
- credenciais de SGPD, SMTP, LDAP e storage devem ser distintas e rotacionáveis;
- nenhuma string de conexão deve ser registrada em logs.

Nenhum valor real de usuário, senha ou token deve ser incluído no repositório.

## 7. Pendências operacionais

1. Confirmar TLS/wallet da conexão única `SGPD`.
2. Escolher Celery ou Django-Q2 quando houver processamento assíncrono.
3. Homologar atributo identificador, endpoints, TLS e backend de autenticação
   LDAP/AD. O vínculo administrativo do lado SGPD já está implementado.
4. Definir o Compose do Redis quando surgir a primeira dependência.

## 8. Estado do bloco de ambiente

O inventário e as decisões do bloco Ambiente estão concluídos.

SMTP AUTH e `Send As` foram validados em 2026-07-28. O Microsoft 365 aceitou
uma mensagem de prova enviada ao próprio remetente configurado.

Referência do SMTP Microsoft 365: [Microsoft Learn — configurar envio por aplicativo](https://learn.microsoft.com/pt-br/exchange/mail-flow-best-practices/how-to-set-up-a-multifunction-device-or-application-to-send-email-using-microsoft-365-or-office-365).
