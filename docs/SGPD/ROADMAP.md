# Roadmap

## Como ler este documento

As entregas de fases concluídas preservam o plano e podem mencionar
componentes intermediários que já foram substituídos. Os blocos `Estado`
registram o resultado de cada fase; o status geral e o próximo incremento
autorizado estão em `CHECKPOINT.md`.

## Fase 0 — Descoberta e fundação

### Objetivos

- levantar ambiente;
- confirmar arquitetura;
- validar integração;
- mapear processo real;
- identificar responsáveis;
- fechar vocabulário;
- preparar repositório.

### Entregas

- inventário do ambiente;
- dicionário de termos;
- mapa AS-IS;
- mapa TO-BE;
- matriz de setores e responsáveis;
- contrato preliminar das consultas SQL ao Senior;
- arquitetura validada;
- backlog;
- riscos;
- plano de testes;
- ambiente Django inicial.

### Saída esperada

Checkpoint 0 aprovado.

## Fase 1 — Base técnica

### Entregas

- projeto Django;
- configuração do ambiente DEV;
- conexão Oracle;
- cadastro local de usuários, e-mails e papel funcional;
- autenticação local;
- descoberta de usuários/grupos, importação explícita, vínculo e autenticação
  AD em estágios;
- auditoria base;
- layout;
- WhiteNoise para arquivos estáticos;
- filesystem privado para evidências;
- SMTP Microsoft 365;
- health check;
- logging;
- comandos locais de validação, sem CI/CD;
- testes iniciais.

### Saída esperada

Aplicação acessível e autenticada.

### Estado em 2026-07-27

A base de autenticação local, usuários, papel funcional, escopos, auditoria de
contas, troca obrigatória de senha temporária e vínculo administrativo com o
AD está implementada e aplicada no Oracle DEV. A primeira conta humana foi criada pelo
bootstrap auditado. SMTP AUTH e `Send As` foram validados em 2026-07-28 com
uma mensagem de prova aceita pelo Microsoft 365. Em 2026-07-28, a autorização
dos services, a imutabilidade da auditoria contra operações em lote e a
concorrência do último superusuário foram endurecidas antes do versionamento do
checkpoint.

Em 2026-07-29, o catálogo funcional foi inicialmente simplificado para
`RESPONSAVEL_SETOR`; a decisão posterior ADR-036 o fixou em `DP` e
`RESPONSAVEL_SETOR`, cumulativos e independentes. SuperAdmin permaneceu como
atributo técnico fora do catálogo, e os demais papéis legados foram preservados
apenas como histórico inativo. A ADR-038 então eliminou a atribuição redundante:
`RESPONSAVEL_SETOR` tornou-se derivado do vínculo de setor e somente `DP`
permaneceu atribuível.

Em 2026-07-30, a ADR-044 estabeleceu `is_superuser` como autoridade global:
SuperAdmin acessa todos os processos, tarefas, menus e casos de uso sem receber
papel ou vínculo artificial, preservando integralmente as regras de negócio e
auditoria.

Em 2026-07-28, a integração AD foi antecipada da Fase 10 e implementada com
`django-auth-ldap` e `python-ldap`: pesquisa por OU/grupo, criação local
explícita já vinculada, vínculo posterior, autenticação somente de contas
previamente vinculadas e contingência administrativa. A ativação no AD real
permanece pendente de homologação do `.env`, TLS, bases e filtros.

## Fase 2 — Referências Senior

### Entregas

- repository de consultas SQL sem models;
- contrato homologado dos objetos `VETORH`;
- grants `SELECT` do owner `SGPD` nos objetos `VETORH` homologados;
- consultas parametrizadas e paginadas;
- tratamento de timeout e indisponibilidade;
- logs e métricas de consulta;
- testes de contrato;
- seleção em cascata.

### Saída esperada

Empresa → Filial → Tipo → Colaborador funcionando.

### Estado em 2026-07-28

Concluída. Repository, contrato SQL, endpoints JSON e autorização por escopo
estão implementados, e a seleção definitiva está na SPA. O snapshot permanece
na Fase 4, dentro do caso de uso transacional de abertura. O `LEFT JOIN` de
centro de custo foi homologado por contagem global e a consulta de colaboradores
foi medida com até dez conexões concorrentes, sem erros ou timeouts.

### Fechamento em 2026-07-28

As Fases 1 e 2 estão estabilizadas e versionadas localmente. A Fase 3 ainda não
foi iniciada.

## Fase 2.5 — Migração da interface para SPA Angular

Inserida em 2026-07-28 por decisão explícita, antes da configuração funcional,
para que os módulos das Fases 3 a 6 já sejam construídos sobre a interface
definitiva e não precisem ser escritos duas vezes.

### Entregas

- decisões registradas nas ADR-025 a ADR-028;
- API de autenticação e contexto de autorização;
- API de administração de contas, atribuição dos papéis fixos, escopos, vínculo AD
  e auditoria;
- envelope de erro padronizado e tradução única do `ValidationError`;
- SPA Angular com PrimeNG, mobile first;
- integração do build com o Django e o WhiteNoise;
- telas de contas e cascata cadastral do Senior na SPA;
- remoção da interface server-side, do HTMX e dos testes acoplados a ela.

### Saída esperada

Interface definitiva em operação, com API como única superfície funcional e
Django Admin somente leitura preservado.

### Estado em 2026-07-28

Fases A a G concluídas. A SPA autentica, administra contas e a atribuição dos
papéis fixos, consulta a auditoria e executa a cascata Empresa → Filial → Tipo →
Colaborador sobre os quatro endpoints Senior homologados. O Django Admin
somente leitura foi
preservado. A rota de catálogo editável de papéis foi removida em 2026-07-29.

O plano completo, com as sete fases e seus critérios de conclusão, está em
`MIGRATION_FRONTEND_SPA.md`.

## Fase 2.7 — Configuração técnica de autenticação

Inserida antes da configuração funcional por solicitação explícita, sem
antecipar setores, grupos de validação, templates ou workflow.

### Entregas

- central de Configurações com cards de módulos atuais e futuros;
- visibilidade, rotas e API exclusivas de `is_superuser`;
- singleton LDAP versionado no schema SGPD, com baseline do `.env`;
- senha de bind cifrada e nunca projetada;
- upload privado e validação X.509 do bundle de CA;
- validação do contrato, teste de bind/RootDSE e auditoria;
- transporte único para descoberta e login, com LDAPS automático quando TLS
  estiver selecionado e warning permanente quando não estiver;
- ativação do login condicionada a probe correspondente e contingência local;
  com TLS, também a CA válida.

### Estado em 2026-07-28

Implementação e testes concluídos. A ADR-032 simplificou o transporte em uma
única escolha administrativa: com TLS usa LDAPS e CA; sem TLS funciona para
descoberta e login com aviso explícito. A migration de remoção do campo legado
foi aplicada no Oracle DEV. O login AD permanece desligado até o teste
controlado da configuração escolhida.

## Fase 3 — Configuração funcional

### Entregas

- setores;
- responsáveis;
- grupos;
- regras de aplicabilidade;
- templates;
- itens;
- versionamento;
- administração funcional.

### Saída esperada

Administrador consegue configurar o processo sem alteração de código.

### Estado em 2026-07-29

Iniciada. O primeiro incremento vertical entrega setores de validação, escopos
globais/empresa/filial, prazos, indicadores de bloqueio/valor/evidência,
escalada sem ciclos, autorização, auditoria, API e SPA mobile first. O catálogo
de nove setores informado pelo responsável funcional está cadastrado no Oracle
DEV; seus prazos, escopos e regras permanecem provisórios até homologação.
O desenho de responsáveis foi consolidado no agregado Setor: um ou mais
usuários, todos com a mesma autoridade, validade própria e escopo herdado do
setor. `RESPONSAVEL_SETOR` deixou de ser atribuível e passa a ser derivado do
vínculo vigente. A SPA e a API independentes de responsáveis foram removidas;
o setor sincroniza seus vínculos atomicamente e as listas de setores/usuários
exibem indicadores. `DP` permanece como único papel atribuível, cumulativo e
independente da responsabilidade de setor. Templates e grupos versionados
também estão implementados com publicação auditada e SPA; nenhuma pergunta ou
composição funcional é carregada automaticamente. O Oracle DEV contém o
template piloto `Demissional Geral` e o grupo piloto `Todos` publicados
manualmente, ainda sujeitos à homologação funcional. Templates são neutros
quanto a setor e podem ser reutilizados por diferentes regras de grupo. Regras
automáticas de aplicabilidade continuam pendentes.

O editor de templates usa o `ID` numérico gerado pelo banco, busca pelo nome e
permite corrigir o único rascunho do cabeçalho. Para conteúdo publicado, a SPA
cria uma nova versão clonada antes da edição; versões históricas permanecem
imutáveis e auditadas.

O editor de grupos também permite corrigir nome, descrição, setores, templates,
SLA, obrigatoriedade e bloqueio enquanto a versão estiver em `DRAFT`, com
concorrência otimista e auditoria. A publicação mantém a versão imutável.

A convenção foi uniformizada para os cadastros configuráveis locais: setor,
template, grupo e pergunta recebem código numérico automático igual ao `ID`;
API e SPA não solicitam código manual. Referências do Senior e códigos
funcionais fixos permanecem fora dessa regra.

## Fase 4 — Processo demissional

### Entregas

- abertura;
- snapshot;
- sugestão de grupos;
- ajuste pelo DP;
- início;
- tarefas;
- estados;
- prazos;
- painel do DP;
- painel dos setores.

### Saída esperada

Processo completo sem pendências avançadas.

### Estado em 2026-07-29

Iniciada pelos incrementos de abertura, início e execução inicial das tarefas.
A SPA reaproveita a cascata
Senior e cria `RASCUNHO` sem exigir gestor imediato; o service relê o colaborador,
usa `has_effective_role()` antes da consulta e após lock transacional, impede
duplicidade e grava processo, snapshot e `PROCESS_OPENED` atomicamente. A
migration `offboarding.0001` está aplicada no Oracle DEV. O rascunho fixa
grupos publicados, resolve setores pelo escopo e inicia de forma idempotente,
gerando uma tarefa por setor e snapshots de perguntas. Ausência de responsável
vigente em setor obrigatório bloqueia e desfaz a transição. A SPA cobre
confirmação de grupos e início; ajustes manuais existem na API e ainda não
possuem editor visual. Regras automáticas de sugestão, estados posteriores e
painel do DP permanecem pendentes. A SPA `/fe/tarefas` já funciona como painel
inicial dos setores: filtra usuários funcionais pelo vínculo e escopo vigentes,
enquanto SuperAdmin visualiza todas as tarefas; ambos iniciam a análise,
validam respostas simples e concluem a tarefa com concorrência, idempotência e
auditoria. Itens de arquivo ou com evidência obrigatória aguardam a Fase 5; a
conclusão ainda não promove automaticamente o estado do processo. As migrations
`templates_engine.0001`, `templates_engine.0002` e `offboarding.0002` estão
aplicadas e validadas no Oracle DEV.
`templates_engine.0003`, que normaliza o identificador automático e habilita o
editor de rascunho, também está aplicada e validada.
`offboarding.0003`, state-only para os novos estados/eventos, também está
aplicada e deixou o plano Oracle DEV vazio.

Um smoke transacional com rollback obrigatório validou no Oracle DEV o fluxo
abrir → selecionar → iniciar sobre a configuração piloto publicada. Foram
geradas nove tarefas, nove snapshots de checklist e três eventos de auditoria;
o retry com a mesma chave foi reconhecido como replay sem duplicação. Nenhuma
linha do teste permaneceu persistida e o Senior foi consultado somente por
`SELECT`.

Um segundo smoke, também com rollback obrigatório, iniciou e concluiu uma das
tarefas, validou os dois replays idempotentes e cinco eventos totais. A
resposta booleana foi persistida no envelope JSON compatível com Oracle e
nenhuma linha permaneceu após o rollback.

## Fase 5 — Pendências e evidências

### Entregas

- pendências;
- itens;
- evidências;
- hash;
- bloqueios;
- regularização;
- comentários;
- histórico.

### Saída esperada

Setores conseguem documentar e resolver pendências.

## Fase 6 — Valores e decisões

### Entregas

- pretensão de cobrança;
- análise;
- contestação;
- aprovação;
- parecer;
- segregação de função;
- consolidação de valores.

### Saída esperada

Valores controlados sem desconto automático.

## Fase 7 — Notificações e escaladas

### Entregas

- Redis em container;
- fila de e-mail;
- templates;
- lembretes;
- atrasos;
- escaladas;
- painel de falhas;
- reprocessamento.

### Saída esperada

O sistema conduz o processo proativamente.

## Fase 8 — Liberação e encerramento

### Entregas

- avaliação automática de prontidão;
- revisão do DP;
- liberação;
- registro de processamento;
- encerramento;
- cancelamento;
- reabertura controlada.

### Saída esperada

Fluxo ponta a ponta concluído.

## Fase 9 — Relatórios e operação

### Entregas

- indicadores;
- exportações;
- performance;
- monitoramento;
- backup validado;
- runbook;
- documentação operacional;
- treinamento.

## Fase 10 — Integrações adicionais

Possíveis integrações:

- homologação operacional e evolução da integração AD/LDAP já implementada;
- controle de acesso;
- e-mail;
- VPN;
- patrimônio;
- ferramentaria;
- medicina ocupacional;
- frota;
- SAP;
- Senior HCM para retorno da rescisão.

A capacidade AD foi antecipada para a fundação por necessidade operacional. A
Fase 10 preserva apenas evoluções futuras, como MFA coordenado pela
infraestrutura, reconciliação periódica ou integrações adicionais; papéis e
escopos continuam exclusivamente no SGPD.

## Critério de MVP

O MVP estará pronto quando for possível:

1. autenticar;
2. selecionar colaborador integrado;
3. abrir processo;
4. gerar tarefas;
5. responder checklists;
6. registrar pendências;
7. anexar evidências;
8. concluir setores;
9. revisar no DP;
10. liberar;
11. encerrar;
12. auditar tudo.
