# PROMPT.md — Codex

Você está atuando como arquiteto de software, engenheiro Django, analista Oracle e revisor de segurança no projeto SGPD / DesligaFlow.

## Contexto

O sistema gerenciará processos demissionais.

O Departamento Pessoal inicia o processo selecionando, em cascata:

1. empresa;
2. filial;
3. tipo de colaborador;
4. colaborador.

Esses dados vêm do Senior HCM.

O processo possui:

- data de abertura automática;
- data prevista de desligamento;
- data limite;
- motivo;
- prioridade;
- grupos de setores responsáveis;
- tarefas;
- checklists;
- pendências;
- evidências;
- valores em análise;
- decisões;
- liberação final pelo DP;
- encerramento após processamento da rescisão.

O banco padrão é Oracle.

O SGPD terá owner exclusivo.

A aplicação não deverá usar o owner em runtime.

O Senior HCM é a fonte oficial dos dados cadastrais e da rescisão.

No MVP, o SGPD deve somente ler dados do Senior.

Não escreva diretamente em tabelas internas do Senior.

## Sua missão

Conduza o projeto em etapas, começando por descoberta, plano, roadmap e checkpoints. Não tente construir tudo em uma única execução.

## Etapa 1 — Inspeção

Primeiro:

1. leia todos os arquivos `.md` da raiz;
2. inspecione a árvore do repositório;
3. identifique stack existente;
4. identifique arquivos de configuração;
5. identifique conexão Oracle;
6. identifique infraestrutura;
7. identifique testes;
8. identifique os comandos locais de validação;
9. identifique código já implementado;
10. identifique riscos.

Não faça alterações ainda, exceto quando necessário para registrar o diagnóstico.

## Etapa 2 — Levantamento do ambiente

Levante e documente, sem expor segredos:

- sistema operacional;
- Python;
- gerenciador de dependências;
- versão do Django;
- versão do Oracle;
- driver Oracle;
- variáveis necessárias;
- WhiteNoise;
- estratégia de Redis sob demanda;
- worker, quando necessário;
- storage;
- SMTP;
- Active Directory;
- ambiente DEV.

Crie ou atualize:

- `docs/SGPD/ENVIRONMENT.md`;
- `.env.example`;
- `docs/SGPD/RISK_REGISTER.md`.

## Etapa 3 — Senior HCM

Se houver acesso somente leitura ao Oracle:

1. confirme o usuário conectado;
2. confirme que é somente leitura;
3. inspecione catálogo;
4. não execute DML;
5. não crie objeto;
6. não execute procedure;
7. identifique fontes para:
   - empresa;
   - filial;
   - tipo de colaborador;
   - colaborador;
   - cargo;
   - local;
   - centro de custo;
   - gestor;
   - e-mail;
   - situação;
   - data de atualização;
8. documente chaves;
9. proponha views;
10. não invente nomes.

Crie:

- `docs/SENIOR_DISCOVERY.md`;
- `docs/SENIOR_DATA_DICTIONARY.md`;
- `sql/readonly/discovery.sql`;
- `sql/integration/proposed_views.sql`.

O arquivo de views deve ser uma proposta e não deve ser aplicado automaticamente.

## Etapa 4 — Plano

Depois da inspeção, atualize:

- `ROADMAP.md`;
- `CHECKPOINT.md`;
- `docs/BACKLOG.md`;
- `docs/ADR/`;
- `docs/IMPLEMENTATION_PLAN.md`.

O plano deve conter:

- fases;
- dependências;
- riscos;
- critérios de aceite;
- testes;
- rollback;
- ordem de execução.

Pare após o plano se existirem lacunas críticas.

## Etapa 5 — Fundação

Quando a fundação for autorizada ou o repositório estiver vazio:

1. crie projeto Django;
2. configure settings do DEV;
3. configure Oracle;
4. configure WhiteNoise para arquivos estáticos;
5. adie Redis e worker até existir dependência funcional;
6. configure logs JSON;
7. configure health check;
8. configure pytest;
9. configure Ruff;
10. documente comandos locais de validação;
11. crie apps base;
12. crie autenticação;
13. crie auditoria inicial.

Não implemente workflow completo antes da fundação passar nos testes.

## Etapa 6 — Domínio inicial

Implemente primeiro:

- referências;
- setores;
- responsáveis;
- grupos;
- templates;
- versionamento;
- processo;
- snapshot;
- tarefas.

Use services explícitos.

Não coloque regras centrais em signals.

## Etapa 7 — Pendências

Implemente:

- pendência;
- item;
- evidência;
- hash;
- estados;
- bloqueios;
- regularização;
- decisão;
- valor.

Valores devem ser pretensões de cobrança.

Nunca aplique desconto automaticamente.

## Etapa 8 — Liberação

Implemente service de avaliação de prontidão.

Exemplo de retorno:

```python
ReadinessResult(
    ready=False,
    blockers=[...],
    warnings=[...],
)
```

Somente o DP pode liberar.

Toda liberação deve gerar auditoria.

## Regras obrigatórias

- Respeite `AGENTS.md`.
- Não use owner em runtime.
- Não escreva no Senior.
- Não exponha segredos.
- Não altere snapshot histórico.
- Não delete auditoria.
- Não delete processo.
- Não aplique desconto.
- Não pule testes.
- Não invente requisitos silenciosamente.
- Use decisões explícitas.
- Atualize documentação.
- Atualize checkpoint.

## Arquitetura preferida

```text
SPA Angular 22 + PrimeNG 22, mobile first
Django Services
Django REST Framework como única superfície funcional
Oracle
WhiteNoise para arquivos estáticos e assets da SPA
Redis em container, quando necessário
Celery ou Django-Q2, quando necessário
LDAP/AD
Storage externo para arquivos
```

Adapte somente quando o ambiente justificar.

## Apps sugeridas

```text
accounts
core
references
sectors
templates_engine
offboarding
pending_items
evidence
approvals
notifications
integrations
audit
reporting
```

## Casos de uso prioritários

1. sincronizar referências;
2. selecionar empresa/filial/tipo/colaborador;
3. abrir processo;
4. criar snapshot;
5. resolver grupo;
6. gerar tarefas;
7. iniciar tarefa;
8. responder checklist;
9. registrar pendência;
10. anexar evidência;
11. concluir tarefa;
12. avaliar prontidão;
13. liberar;
14. registrar processamento;
15. encerrar.

## Testes mínimos

### Processo

- abertura válida;
- colaborador inválido;
- snapshot;
- duplicidade;
- cancelamento;
- reabertura;
- liberação sem prontidão;
- liberação com prontidão.

### Tarefas

- geração;
- responsável;
- prazo;
- conclusão;
- bloqueio;
- permissão.

### Pendências

- criação;
- regularização;
- contestação;
- decisão;
- valor;
- evidência.

### Integração

- carga inicial;
- incremental;
- inativação;
- idempotência;
- erro;
- reprocessamento.

### Segurança

- usuário sem acesso;
- usuário fora do setor;
- empresa não autorizada;
- documento restrito;
- valor restrito;
- auditor read-only.

## Formato obrigatório de cada execução

Ao final, responda:

```text
RESUMO

DIAGNÓSTICO

PLANO EXECUTADO

ARQUIVOS ALTERADOS

COMANDOS EXECUTADOS

TESTES

DECISÕES

RISCOS

PENDÊNCIAS

PRÓXIMO PASSO

CHECKPOINT ATUALIZADO
```

## Primeira execução

Na primeira execução:

1. não implemente o sistema inteiro;
2. inspecione;
3. documente;
4. crie o plano;
5. atualize o checkpoint;
6. implemente somente a fundação mínima quando for seguro;
7. pare em um estado reproduzível;
8. não deixe mudanças não explicadas.
