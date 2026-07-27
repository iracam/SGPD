# Ambiente

## 1. Escopo do levantamento

Levantamento executado em 2026-07-27 no ambiente DEV.

Este é o único ambiente no escopo atual. HML e PRD não serão configurados nesta etapa.

Nenhum segredo foi exibido ou registrado. A inspeção documental considerou nomes de variáveis, executáveis, versões, estado de serviços e arquivos de configuração; as credenciais locais foram usadas somente pelo cliente Oracle durante o teste de conexão.

## 2. Ambiente local confirmado

| Componente | Estado observado | Situação para o projeto |
|---|---|---|
| Sistema operacional | Debian GNU/Linux 13.6 (trixie), kernel 6.12, x86_64 | Confirmado para DEV |
| Timezone | UTC-03:00 | A aplicação deverá usar `America/Sao_Paulo` explicitamente |
| Locale | `C.UTF-8` | Validar regras de apresentação em português |
| Filesystem | ext4, 96% utilizado, aproximadamente 1,9 GiB livres | Espaço insuficiente para crescimento seguro de imagens, caches e evidências |
| Git | branch `main`, remoto `origin` configurado | Repositório confirmado |
| Python | CPython 3.13.5 | Python 3.13 homologado; ambiente virtual isolado pelo `uv` |
| `pip` | 25.1.1 | Disponível no Python do sistema |
| `uv` | 0.11.29 | Disponível e candidato a gerenciador do projeto |
| Poetry / Pipenv / pyenv | Não instalados | Não necessários se `uv` for adotado |
| Django / DRF | Django 5.2.16 / DRF 3.17.1 | Instalados e bloqueados por `uv.lock` |
| Node.js | 24.18.0 | Disponível; versão do projeto ainda não definida |
| npm | 11.16.0 | Disponível |
| Docker Engine | 26.1.5, daemon ativo, driver `overlay2` | Disponível; nenhum container em execução |
| Docker Compose | 2.26.1 | Disponível |
| Oracle Database | 19c | Versão confirmada para o projeto |
| Oracle Instant Client | 19.28 em `/opt/oracle/instantclient_19_28` | Cliente nativo confirmado |
| Driver Python Oracle | `python-oracledb` 4.0.2 | Modo Thick validado com o Instant Client 19.28 |
| SQLcl local | 26.1 em `/opt/sqlcl/bin/sql` | Conexões Oracle validadas |
| MCP Oracle | Ativo, com conexão `DEV@VETORH` salva | Definição aponta para serviço não registrado; não usada na validação final |
| Redis | Somente `redis-cli` 8.0.2; servidor local ausente/inativo | Será iniciado em container quando necessário |
| Celery / Django-Q2 | Ausentes | Worker adiado até existir caso de uso |
| Gunicorn | Ausente | Fora da execução DEV atual |
| Nginx | Ausente/inativo | Não será utilizado; estáticos serão servidos por WhiteNoise |
| WhiteNoise | 6.12.0 | Configurado somente para arquivos estáticos |
| LDAP tools | `ldapsearch` ausente | Não bloqueia o MVP local; necessário na integração futura com AD |
| SMTP | Microsoft 365, `smtp.office365.com:587`, TLS/STARTTLS | Remetente definido; credenciais ficarão no `.env` |
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
- WhiteNoise para estáticos;
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
| Oracle SGPD | Owner `SGPD` configurado e validado como conexão única de runtime e migrations no DEV |
| Senior HCM | Schema `VETORH` no mesmo serviço; cinco grants `SELECT` confirmados para `SGPD` |
| Redis | Container sob demanda |
| Worker | Adiado até necessidade |
| SMTP | Microsoft 365; remetente `noreply@bsabioenergia.com.br`; credenciais no `.env` |
| Autenticação | Local no MVP; LDAP/AD não configurado e previsto para fase futura |
| Estáticos | WhiteNoise instalado e configurado |
| Evidências | Filesystem local privado em `media/evidence` |
| Nginx / proxy | Não utilizado |
| Secrets | `.env` local; usuários individuais no formato `nome.sobrenome` |
| CI/CD | Não utilizado |

HML e PRD estão explicitamente fora do escopo atual.

## 5. Contrato preliminar de variáveis

O arquivo `.env.example` define, sem valores sensíveis:

- aplicação e settings Django;
- conexão Oracle única do runtime e migrations com `SGPD`;
- leitura direta dos objetos `VETORH` autorizados pela mesma conexão;
- Oracle Instant Client e wallet/TNS;
- WhiteNoise;
- Redis e Celery opcionais;
- SMTP;
- LDAP/Active Directory;
- storage local ou S3 compatível;
- cookies seguros.

O nome `SGPD_DB_NAME` foi alinhado à configuração local validada. Os demais nomes devem ser confirmados durante a criação dos settings.

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

## 7. Decisões pendentes

1. Confirmar TLS/wallet da conexão única `SGPD`.
2. Escolher Celery ou Django-Q2 quando houver processamento assíncrono.
3. Confirmar SMTP AUTH e a permissão `Send As` da conta de envio.
4. Definir identificador, endpoints, TLS e processo de vinculação ao AD na fase futura.
5. Definir backup, retenção e antivírus das evidências.
6. Definir o Compose do Redis quando surgir a primeira dependência.
7. Liberar espaço no filesystem local antes de armazenar evidências.
8. Obter `CREATE TABLE` e quota no tablespace designado para o próprio `SGPD`
   antes de aplicar migrations.

## 8. Estado do bloco de ambiente

O inventário e as decisões do bloco Ambiente estão concluídos.

As validações restantes da fundação técnica são:

- liberar e aplicar as migrations no schema `SGPD`;
- testar SMTP AUTH;
- configurar permissões e proteção do filesystem de evidências;
- liberar espaço no filesystem antes de armazenar evidências.

Referência do SMTP Microsoft 365: [Microsoft Learn — configurar envio por aplicativo](https://learn.microsoft.com/pt-br/exchange/mail-flow-best-practices/how-to-set-up-a-multifunction-device-or-application-to-send-email-using-microsoft-365-or-office-365).
