# AGENTS.md

## 1. Objetivo

Este repositório contém o SGPD / DesligaFlow, sistema corporativo de gestão do processo demissional.

Todo agente deve preservar:

- segurança;
- rastreabilidade;
- separação entre SGPD e Senior HCM;
- compatibilidade com Oracle;
- regras de negócio explícitas;
- documentação;
- testes;
- mudanças pequenas e revisáveis.

## 2. Regra principal

Antes de implementar:

1. leia `README.md`;
2. leia `VISION.md`;
3. leia `REQUIREMENTS.md`;
4. leia `ARCHITECTURE.md`;
5. leia `DATA_MODEL.md`;
6. leia `INTEGRATION_SENIOR_ORACLE.md`;
7. leia `SECURITY.md`;
8. leia `ROADMAP.md`;
9. leia `CHECKPOINT.md`;
10. produza diagnóstico do estado atual.

Não implemente grandes blocos sem verificar o checkpoint atual.

## 3. Proibições

O agente não deve:

- escrever diretamente em tabelas internas do Senior;
- usar o owner Oracle como usuário da aplicação;
- armazenar senha no código;
- inventar nomes de tabelas do Senior;
- criar integração destrutiva;
- aplicar descontos automaticamente;
- apagar auditoria;
- apagar processos encerrados;
- alterar snapshots históricos;
- usar signals para regras centrais sem justificativa;
- criar SPA sem decisão explícita;
- introduzir dependência sem explicar;
- executar migration destrutiva sem revisão;
- fazer refatoração ampla fora do escopo;
- esconder falhas;
- concluir tarefa sem testes ou justificativa.

## 4. Stack padrão

- Python 3.12 ou versão homologada.
- Django 5.x ou versão LTS/estável homologada.
- Django REST Framework.
- Oracle.
- HTMX.
- Alpine.js.
- Tailwind CSS/daisyUI.
- Redis.
- Celery ou Django-Q2.
- Pytest.
- Ruff.
- Mypy quando viável.
- Docker Compose para ambiente local.

O agente deve confirmar versões existentes antes de alterar.

## 5. Estrutura esperada

```text
project/
├── apps/
│   ├── accounts/
│   ├── core/
│   ├── references/
│   ├── sectors/
│   ├── templates_engine/
│   ├── offboarding/
│   ├── pending_items/
│   ├── evidence/
│   ├── approvals/
│   ├── notifications/
│   ├── integrations/
│   ├── audit/
│   └── reporting/
├── config/
├── docs/
├── tests/
├── scripts/
├── docker/
├── manage.py
├── pyproject.toml
├── AGENTS.md
├── PROMPT.md
├── ROADMAP.md
└── CHECKPOINT.md
```

Não force essa estrutura se o repositório já possuir padrão consolidado. Nesse caso, documente a adaptação.

## 6. Agentes ou papéis sugeridos

### `solution-architect`

Responsável por:

- arquitetura;
- ADRs;
- limites;
- módulos;
- dependências;
- integração.

### `django-backend`

Responsável por:

- models;
- services;
- forms;
- views;
- APIs;
- permissões;
- testes.

### `oracle-db-readonly`

Responsável por:

- inspecionar catálogo;
- mapear views;
- levantar chaves;
- produzir SQL somente leitura;
- documentar origem.

Nunca executar DML no Senior.

### `oracle-schema`

Responsável por:

- schema SGPD;
- grants;
- índices;
- constraints;
- migrations;
- performance.

### `security-reviewer`

Responsável por:

- autenticação;
- autorização;
- LGPD;
- uploads;
- secrets;
- auditoria;
- logs.

### `workflow-reviewer`

Responsável por:

- estados;
- transições;
- prazos;
- bloqueios;
- reabertura;
- cancelamento;
- idempotência.

### `qa-engineer`

Responsável por:

- testes;
- cenários;
- regressão;
- autorização;
- workflow;
- integração.

## 7. Regras de domínio

### Senior HCM

- fonte oficial;
- somente leitura no MVP;
- integração por views ou contrato homologado;
- nunca assumir estrutura sem inspeção.

### Snapshot

- criado na abertura;
- não atualizado automaticamente;
- imutável após início, salvo correção administrativa auditada.

### Templates

- sempre versionados;
- processos antigos mantêm perguntas históricas.

### Pendências

- entidade própria;
- pode possuir itens, evidências, valores e decisões;
- deve possuir estado;
- pode bloquear processo.

### Valores

- são pretensões;
- precisam de análise;
- aprovação segregada;
- valor processado é registrado posteriormente.

### Liberação

- somente DP;
- ação explícita;
- exige verificação de prontidão;
- deve ser auditada.

## 8. Padrão de implementação

### Services

Use services para casos de uso:

```python
service.execute(command)
```

Evite regras críticas em:

- templates;
- signals;
- serializers;
- views;
- properties com efeitos colaterais.

### Transações

Use `transaction.atomic()` em operações de negócio compostas.

### Concorrência

Use controle otimista ou locks nos pontos críticos.

### Idempotência

Tarefas assíncronas e integrações devem ser idempotentes.

### Auditoria

Toda mudança relevante deve gerar evento.

### Logs

Use correlation ID.

## 9. Banco e migrations

Antes de migration:

1. revisar SQL gerado;
2. verificar compatibilidade Oracle;
3. avaliar lock;
4. avaliar índice;
5. avaliar volume;
6. prever rollback.

Não renomear ou remover coluna em produção sem plano.

## 10. Integração

Toda integração deve definir:

- origem;
- destino;
- chave;
- payload;
- frequência;
- idempotência;
- retry;
- timeout;
- log;
- reconciliação;
- segurança;
- ownership.

## 11. Testes obrigatórios

Para regra crítica:

- caminho feliz;
- permissão negada;
- estado inválido;
- concorrência quando aplicável;
- idempotência;
- rollback;
- auditoria;
- dados incompletos.

Fluxos mínimos:

- abertura;
- geração de tarefas;
- pendência;
- conclusão de setor;
- prontidão;
- liberação;
- cancelamento;
- reabertura;
- sincronização.

## 12. Processo de trabalho

### Antes

- identificar checkpoint;
- inspecionar repositório;
- listar riscos;
- propor plano curto;
- identificar arquivos.

### Durante

- alterações pequenas;
- commits lógicos;
- testes frequentes;
- atualizar documentação;
- não quebrar compatibilidade.

### Depois

- executar testes;
- executar lint;
- revisar migrations;
- atualizar `CHECKPOINT.md`;
- registrar decisões;
- listar arquivos alterados;
- listar riscos restantes;
- informar próximos passos.

## 13. Definition of Done

Uma tarefa só está concluída quando:

- implementação existe;
- testes passam;
- autorização foi considerada;
- auditoria foi considerada;
- Oracle foi considerado;
- documentação foi atualizada;
- checkpoint foi atualizado;
- riscos foram informados.

## 14. Formato de resposta do agente

```text
Resumo
Diagnóstico
Plano executado
Arquivos alterados
Decisões
Testes
Riscos
Pendências
Próximo passo
```
