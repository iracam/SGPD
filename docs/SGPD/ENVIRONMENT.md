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
| Python | CPython 3.13.5, sem ambiente virtual do projeto | Versão do projeto ainda precisa ser homologada |
| `pip` | 25.1.1 | Disponível no Python do sistema |
| `uv` | 0.11.29 | Disponível e candidato a gerenciador do projeto |
| Poetry / Pipenv / pyenv | Não instalados | Não necessários se `uv` for adotado |
| Django / DRF | Não instalados | Fundação ainda não iniciada |
| Node.js | 24.18.0 | Disponível; versão do projeto ainda não definida |
| npm | 11.16.0 | Disponível |
| Docker Engine | 26.1.5, daemon ativo, driver `overlay2` | Disponível; nenhum container em execução |
| Docker Compose | 2.26.1 | Disponível |
| Oracle Database | 19c | Versão confirmada para o projeto |
| Oracle Instant Client | 19.28 em `/opt/oracle/instantclient_19_28` | Cliente nativo confirmado |
| Driver Python Oracle | `oracledb` e `cx_Oracle` ausentes | `python-oracledb` será instalado na fundação |
| SQLcl local | 26.1 em `/opt/sqlcl/bin/sql` | Conexões Oracle validadas |
| MCP Oracle | Ativo, com conexão `DEV@VETORH` salva | Definição aponta para serviço não registrado; não usada na validação final |
| Redis | Somente `redis-cli` 8.0.2; servidor local ausente/inativo | Será iniciado em container quando necessário |
| Celery / Django-Q2 | Ausentes | Worker adiado até existir caso de uso |
| Gunicorn | Ausente | Fora da execução DEV atual |
| Nginx | Ausente/inativo | Não será utilizado; estáticos serão servidos por WhiteNoise |
| WhiteNoise | Ainda não instalado | Será configurado com a fundação Django |
| LDAP tools | `ldapsearch` ausente | Não bloqueia o MVP local; necessário na integração futura com AD |
| SMTP | Microsoft 365, `smtp.office365.com:587`, TLS/STARTTLS | Remetente definido; credenciais ficarão no `.env` |
| Evidências | Filesystem local privado | Caminho inicial `media/evidence`, fora do WhiteNoise |
| Pytest | executável global 9.0.3 e módulo do Python 8.3.5 | Conflito será eliminado pelo ambiente virtual do projeto |
| Ruff | 0.15.11 | Disponível globalmente, sem configuração do projeto |
| Mypy | 1.15.0 no Python do sistema | Disponível globalmente, sem configuração do projeto |
| CI/CD | Nenhum workflow ou arquivo de pipeline | Não será utilizado no escopo atual |

## 3. Stack e configurações ausentes

O repositório ainda não possui:

- `pyproject.toml`, lockfile ou requirements;
- ambiente virtual;
- projeto Django ou `manage.py`;
- settings do DEV;
- configuração Oracle;
- configuração WhiteNoise;
- definição do container Redis e do worker, ambos adiados;
- configuração de testes, lint ou tipagem;
- configuração de SMTP;
- configuração futura de LDAP/Active Directory;
- definição de storage de evidências;
- health checks e observabilidade.

## 4. Ambientes

| Item | DEV |
|---|---|
| Host/SO | Debian 13.6 confirmado |
| Python | 3.13.5 do sistema; versão do projeto pendente de homologação |
| Oracle | Database 19c e Instant Client 19.28 confirmados |
| Oracle SGPD | Owner `SGPD` configurado e validado como conexão única de runtime e migrations no DEV |
| Senior HCM | Schema `VETORH` no mesmo serviço; cinco grants `SELECT` confirmados para `SGPD` |
| Redis | Container sob demanda |
| Worker | Adiado até necessidade |
| SMTP | Microsoft 365; remetente `noreply@bsabioenergia.com.br`; credenciais no `.env` |
| Autenticação | Local no MVP; LDAP/AD não configurado e previsto para fase futura |
| Estáticos | WhiteNoise definido; instalação pendente |
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

1. Homologar Python 3.12 ou 3.13 para Django e `python-oracledb`.
2. Adotar formalmente `uv` e definir estratégia de lock.
3. Definir modo Thin ou Thick do `python-oracledb`.
4. Confirmar TLS/wallet da conexão única `SGPD`.
5. Escolher Celery ou Django-Q2.
6. Confirmar SMTP AUTH e a permissão `Send As` da conta de envio.
7. Definir identificador, endpoints, TLS e processo de vinculação ao AD na fase futura.
8. Definir backup, retenção e antivírus das evidências.
9. Definir o Compose do Redis quando surgir a primeira dependência.
10. Liberar espaço no filesystem local antes de baixar imagens e dependências.

## 8. Estado do bloco de ambiente

O inventário e as decisões do bloco Ambiente estão concluídos.

As instalações, conexões e validações restantes pertencem à fundação técnica:

- homologar Python e o gerenciador;
- instalar `python-oracledb` e confirmar o contrato da conexão única `SGPD`;
- configurar WhiteNoise;
- testar SMTP AUTH;
- configurar permissões e proteção do filesystem de evidências;
- liberar espaço no filesystem antes de baixar imagens e dependências.

Referência do SMTP Microsoft 365: [Microsoft Learn — configurar envio por aplicativo](https://learn.microsoft.com/pt-br/exchange/mail-flow-best-practices/how-to-set-up-a-multifunction-device-or-application-to-send-email-using-microsoft-365-or-office-365).
