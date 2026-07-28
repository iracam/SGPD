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
- Angular 21 com PrimeNG 21, interface mobile first
- WhiteNoise para arquivos estáticos e para os assets da SPA
- Oracle Database 19c
- Celery ou Django-Q2 para tarefas assíncronas
- Redis em container quando filas, cache ou locks forem necessários
- cadastro de usuários e papéis no SGPD, com autenticação local inicial e vinculação futura ao LDAP/Active Directory
- Microsoft 365 SMTP para notificações
- filesystem local privado para evidências

As versões exatas do backend, inclusive dependências transitivas, estão
registradas em `uv.lock`; as do frontend, em `frontend/package-lock.json`.

A interface não depende de CDN: componentes, ícones e fontes são empacotados no
build.

Em 2026-07-28 o projeto decidiu substituir a interface Django Templates + HTMX
+ Alpine por uma SPA Angular, conforme as ADRs 025 a 028. O plano de execução
está em `docs/SGPD/MIGRATION_FRONTEND_SPA.md`. Enquanto a migração não conclui,
a interface server-side permanece em operação e não recebe telas novas.

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

As migrations Oracle somente podem ser aplicadas após revisão do SQL. O
próprio usuário `SGPD` possui `CREATE TABLE` e `CREATE SEQUENCE`, ambos sem
`ADMIN OPTION`, e quota finita de 500 MB em `PIMS_DATA`. As 23 migrations
iniciais foram aplicadas e validadas no DEV.

Não executar rollback para `zero` após existirem usuários ou auditoria: isso
removeria fisicamente o histórico. Correções de schema devem usar migration
adiante; recuperação operacional deve usar backup restaurado e procedimento
revisado.

Administração funcional de contas:

- `/accounts/login/`: autenticação local;
- `/accounts/users/`: criação e manutenção auditada de usuários;
- `/accounts/roles/`: papéis, permissões e escopos;
- `/accounts/audit/`: auditoria de contas;
- `uv run manage.py bootstrap_roles`: catálogo inicial idempotente de papéis;
- `uv run manage.py bootstrap_identity_admin`: bootstrap interativo, único e
  auditado da primeira conta humana.

Consulta cadastral Senior:

- `/references/senior/`: seleção Empresa → Filial → Tipo de colaborador
  → Colaborador, server-side até a Fase F da migração;
- exige autenticação, permissão `query_senior_references` e escopo compatível;
- consulta o Senior somente por `SELECT` e não cria snapshot nesta etapa.

## Escopo técnico atual

- somente ambiente DEV;
- sem Nginx;
- sem CI/CD;
- WhiteNoise não atende evidências ou uploads;
- Redis e worker serão introduzidos sob demanda;
- aplicação e API permanecem na mesma origem, exigência da ADR-026.

O diretório `frontend/` passa a existir na Fase D da migração. A partir dela, o
ciclo local inclui `npm ci`, `ng build` para gerar os artefatos servidos pelo
Django e `ng serve --proxy-config proxy.conf.json` durante o desenvolvimento.

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
- `MIGRATION_FRONTEND_SPA.md`: plano de migração da interface para a SPA.
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
Oracle com `python-oracledb` em modo Thick. A base de autenticação, usuários,
papéis, escopos, vínculo administrativo com o AD e auditoria foi aplicada no
Oracle DEV. O catálogo inicial contém nove papéis e cinco permissões
delegáveis; a autenticação LDAP/AD real continua dependente de contrato com a
Infraestrutura. A primeira conta humana foi criada explicitamente pelo
bootstrap auditado; nenhuma conta é criada automaticamente.

A seleção cadastral da Fase 2 está concluída e usa o mesmo repository e a
mesma autorização por escopo dos endpoints JSON. O `LEFT JOIN` de centro de
custo foi homologado no Oracle DEV e a consulta de colaboradores concluiu a
medição controlada com até dez conexões concorrentes sem erros ou timeouts.

SMTP AUTH e o uso do remetente configurado foram validados no Microsoft 365
via TLS/STARTTLS em 2026-07-28. Uma mensagem de prova foi aceita pelo serviço.

O checkpoint das Fases 1 e 2 foi estabilizado e versionado localmente em
2026-07-28. Os services administrativos validam a permissão do ator, a
auditoria rejeita mutação e exclusão em lote, e a desativação concorrente
preserva ao menos um superusuário ativo. A configuração funcional da Fase 3
ainda não foi iniciada.

Na mesma data, a Fase A da migração de frontend foi concluída: as decisões
foram registradas nas ADRs 025 a 028 e a documentação foi atualizada. Nenhum
código foi alterado por essa fase.

Consulte `PROMPT.md` para o procedimento completo.
