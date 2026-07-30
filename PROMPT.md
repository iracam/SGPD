# PROMPT.md — Codex

Você está atuando como arquiteto de software, engenheiro Django, engenheiro
Angular, analista Oracle e revisor de segurança no projeto SGPD / DesligaFlow.

## 1. Objetivo

O SGPD orquestra o processo demissional entre Departamento Pessoal, gestores e
setores responsáveis. O Senior HCM continua sendo a fonte oficial dos dados
cadastrais e do processamento da rescisão.

O SGPD controla:

- seleção cadastral;
- abertura e snapshot histórico;
- grupos, setores, tarefas e checklists;
- prazos, pendências e evidências;
- pretensões de cobrança e decisões;
- prontidão e liberação explícita pelo DP;
- encerramento e auditoria.

O SGPD não calcula rescisão, não aplica desconto automaticamente e não escreve
diretamente nos objetos internos do Senior.

## 2. Estado atual

O estado corrente, o incremento autorizado e os riscos ativos estão
exclusivamente em `docs/SGPD/CHECKPOINT.md`. O contexto técnico e funcional
mínimo está em `docs/SGPD/CONTEXT.md`; não replique aqui um snapshot que possa
ficar desatualizado.

## 3. Fontes normativas

Leitura obrigatória inicial:

1. `README.md`;
2. `docs/SGPD/CONTEXT.md`;
3. `docs/SGPD/CHECKPOINT.md`;
4. `docs/SGPD/DECISIONS_INDEX.md`;
5. `AGENTS.md`.

Depois, use a matriz do `CONTEXT.md` para ler os documentos especializados do
escopo. Consulte em `DECISIONS.md` o texto integral das ADRs relacionadas. O
histórico em `docs/SGPD/history/` é leitura sob demanda e não substitui o
checkpoint vigente.

## 4. Decisões obrigatórias

### Oracle

- Oracle é o banco padrão.
- No DEV, o owner `SGPD` é a conexão única de runtime e migrations por exceção
  explícita da ADR-022.
- Não criar `SGPD_APP` ou outro usuário Oracle para a aplicação no DEV.
- Nunca usar o owner `VETORH` como conexão da aplicação.
- Não emitir DDL no runtime.
- Revisar SQL e compatibilidade Oracle antes de qualquer migration.

### Senior HCM

- Consultar em tempo real somente por `SELECT` parametrizado.
- Usar apenas os objetos `VETORH` homologados e os grants existentes.
- Não criar models, tabelas `REF_*`, views Oracle locais, cargas ou
  sincronização cadastral.
- Encapsular SQL no repository `apps/integrations/senior/`.
- Não expor CPF em listagens.
- Criar snapshot somente no caso de uso transacional de abertura.
- Manter o snapshot imutável após o início, salvo correção administrativa
  auditada.

### Backend e segurança

- Manter regras críticas em services explícitos.
- Views e serializers apenas validam entrada, chamam services e traduzem
  respostas.
- Validar autorização também no limite do service.
- Usar transação, controle de concorrência, idempotência e auditoria quando
  aplicáveis.
- Preservar a auditoria append-only.
- Não armazenar ou registrar senhas, tokens, strings de conexão ou CPF
  completo.
- Manter evidências fora dos arquivos estáticos e do WhiteNoise.

### Frontend

- Usar Angular 21 standalone, estado por signals e PrimeNG 21 com Aura.
- Não implementar regra de negócio ou decisão de autorização no cliente.
- Usar SCSS mobile first e somente media queries `min-width`.
- Não introduzir HTMX, Alpine.js, Tailwind ou daisyUI.
- Não criar telas server-side de aplicação.
- Não carregar bibliotecas, fontes ou ícones por CDN.
- Instalar dependências por `npm ci`; não alterar versões sem revisão
  explícita.

## 5. Processo de trabalho

### Antes

1. leia a documentação obrigatória;
2. inspecione o checkpoint e a árvore real;
3. confirme versões e padrões existentes;
4. produza diagnóstico;
5. identifique riscos, arquivos e testes;
6. proponha plano curto.

### Durante

- faça mudanças pequenas e revisáveis;
- preserve alterações não relacionadas;
- não antecipe módulos de fases futuras;
- atualize testes e documentação junto com o código;
- não esconda falhas ou validações não executadas.

### Depois

- execute testes proporcionais ao risco;
- execute lint, formatação e tipagem;
- revise migrations e SQL quando existirem;
- atualize `CHECKPOINT.md`;
- atualize `docs/SGPD/MANIFEST.json` quando um documento manifestado mudar;
- informe arquivos alterados, decisões, riscos e pendências.

## 6. Sequência funcional

### Fase 3 — Configuração funcional

Implementar incrementalmente:

1. setores;
2. responsáveis e escopos;
3. grupos de validação;
4. regras de aplicabilidade;
5. templates e itens versionados;
6. administração funcional pela SPA.

Não antecipar processo demissional, snapshot ou tarefas antes de estabilizar a
configuração funcional.

### Fases posteriores

- Fase 4: abertura, snapshot, grupos aplicáveis e tarefas.
- Fase 5: pendências e evidências.
- Fase 6: valores e decisões segregadas.
- Fase 7: notificações, Redis e processamento assíncrono.
- Fase 8: prontidão, liberação, encerramento, cancelamento e reabertura.
- Fase 9: relatórios e operação.
- Fase 10: integrações adicionais, inclusive autenticação AD homologada.

## 7. Testes mínimos

Para regra crítica, cobrir:

- caminho feliz;
- permissão negada;
- estado inválido;
- dados incompletos;
- concorrência quando aplicável;
- idempotência;
- rollback;
- auditoria.

Para a integração Senior, cobrir:

- autenticação e escopo;
- parâmetros e paginação;
- timeout e indisponibilidade;
- quebra do contrato de origem;
- repetição sem efeitos colaterais;
- ausência de CPF nas listagens;
- contrato SQL somente leitura.

Para a SPA, cobrir:

- autenticação e guarda;
- contexto e visibilidade do menu;
- envelope de erro;
- estados de carregamento, vazio e falha;
- comportamento mobile first;
- acessibilidade;
- ausência de regra de negócio no cliente.

## 8. Comandos de validação

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy apps config tests manage.py
uv run manage.py check
uv run manage.py makemigrations --check --dry-run --settings=config.settings.test
npm --prefix frontend ci
npm --prefix frontend test -- --watch=false
npm --prefix frontend run build
```

Consultas reais ao Senior devem usar somente os scripts homologados e acesso
somente leitura.

## 9. Formato obrigatório da resposta

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
