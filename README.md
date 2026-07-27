# SGPD / DesligaFlow

Sistema de Gestão do Processo Demissional.

O SGPD é um sistema corporativo para orquestrar o desligamento de colaboradores, desde a abertura pelo Departamento Pessoal até a liberação final para processamento da rescisão no Senior HCM.

O sistema não substitui o Senior HCM no cálculo ou processamento da rescisão. Seu papel é controlar, distribuir, registrar e auditar todas as validações necessárias entre DP, gestores e setores responsáveis.

## Objetivos principais

- Padronizar o processo demissional.
- Distribuir validações por setor.
- Controlar prazos e pendências.
- Registrar materiais, equipamentos, acessos, exames e documentos.
- Permitir evidências e rastreabilidade.
- Apoiar análise de valores sem executar descontos automaticamente.
- Integrar dados cadastrais do Senior HCM.
- Manter trilha de auditoria imutável.
- Liberar o processo ao DP somente quando os requisitos forem atendidos.

## Nome do projeto

- Nome institucional: `SGPD`
- Nome amigável: `DesligaFlow`

## Stack homologada na fundação

- Python 3.13
- Django 5.2 LTS
- Django REST Framework 3.17
- Django Templates
- HTMX
- Alpine.js
- Tailwind CSS ou daisyUI
- WhiteNoise para arquivos estáticos
- Oracle Database 19c
- Celery ou Django-Q2 para tarefas assíncronas
- Redis em container quando filas, cache ou locks forem necessários
- cadastro de usuários e papéis no SGPD, com autenticação local inicial e vinculação futura ao LDAP/Active Directory
- Microsoft 365 SMTP para notificações
- filesystem local privado para evidências

As versões exatas, inclusive dependências transitivas, estão registradas em
`uv.lock`.

## Execução local

Pré-requisitos: `uv`, Oracle Instant Client 19.28 e um `.env` criado a partir
de `.env.example`.

```bash
uv sync --dev
uv run manage.py check
uv run manage.py runserver
```

Endpoints operacionais:

- `GET /health/live/`: processo Django ativo;
- `GET /health/ready/`: conexão Oracle disponível por `SELECT 1 FROM DUAL`.

Validações locais:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy apps config tests manage.py
uv run manage.py makemigrations --check --dry-run --settings=config.settings.test
```

As migrations Oracle somente podem ser aplicadas após revisão do SQL e
liberação explícita de `CREATE TABLE` e quota para o próprio usuário `SGPD`.

## Escopo técnico atual

- somente ambiente DEV;
- sem Nginx;
- sem CI/CD;
- WhiteNoise não atende evidências ou uploads;
- Redis e worker serão introduzidos sob demanda.

## Estrutura da documentação (`./docs/SGPD/`)

- `VISION.md`: visão do produto.
- `ENVIRONMENT.md`: inventário e matriz dos ambientes.
- `REQUIREMENTS.md`: requisitos funcionais e não funcionais.
- `WORKFLOWS.md`: fluxo e estados do processo.
- `DATA_MODEL.md`: modelo conceitual inicial.
- `ARCHITECTURE.md`: arquitetura da solução.
- `INTEGRATION_SENIOR_ORACLE.md`: integração com Senior HCM e Oracle.
- `SECURITY.md`: segurança, LGPD e auditoria.
- `RISK_REGISTER.md`: registro e mitigação de riscos.
- `DECISIONS.md`: decisões arquiteturais iniciais.
- `ROADMAP.md`: fases de implementação.
- `CHECKPOINT.md`: controle de progresso do projeto.

## Na raiz do projeto
- `AGENTS.md`: instruções para agentes de IA.
- `PROMPT.md`: prompt principal para o Codex.


## Princípios do projeto

1. O Senior HCM permanece como sistema oficial do vínculo e da rescisão.
2. O SGPD é o orquestrador do processo.
3. Nenhuma escrita direta será feita em tabelas internas do Senior.
4. O banco Oracle do SGPD terá owner exclusivo.
5. No DEV, por decisão explícita, o owner `SGPD` será também o usuário da aplicação; não será criado `SGPD_APP`.
6. Referências do Senior serão consultadas em tempo real por SQL `SELECT` parametrizado, sem models ou cópias `REF_*` no SGPD.
7. Dados do colaborador serão copiados para um snapshot na abertura do processo.
8. Regras e checklists serão versionados.
9. Pendências serão entidades próprias e auditáveis.
10. Valores informados serão tratados como pretensões de cobrança.
11. A liberação final continuará sob responsabilidade do DP.

## Estado atual

A descoberta do ambiente e o contrato SQL do Senior estão concluídos. A
fundação Django está criada e validada localmente; a aplicação conecta ao
Oracle com `python-oracledb` em modo Thick. A aplicação das migrations no DEV
aguarda privilégios DDL e quota para `SGPD`.

Consulte `PROMPT.md` para o procedimento completo.
