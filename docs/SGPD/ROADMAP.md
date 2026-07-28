# Roadmap

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
- matriz de papéis;
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
- cadastro local de usuários, gestores, e-mails e papéis;
- autenticação local;
- campos de vinculação futura ao AD;
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

A base de autenticação local, usuários, papéis, escopos, auditoria de contas,
troca obrigatória de senha temporária e vínculo administrativo com o AD está
implementada e aplicada no Oracle DEV. A primeira conta humana foi criada pelo
bootstrap auditado. SMTP AUTH e `Send As` foram validados em 2026-07-28 com
uma mensagem de prova aceita pelo Microsoft 365. Em 2026-07-28, a autorização
dos services, a imutabilidade da auditoria contra operações em lote e a
concorrência do último superusuário foram endurecidas antes do versionamento do
checkpoint.

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

### Estado em 2026-07-27

Concluída. Repository, contrato SQL, endpoints JSON, autorização por escopo e
seleção HTMX server-side estão implementados. O runtime HTMX 2.0.10 é servido
localmente, sem CDN. O snapshot permanece na Fase 4, dentro do caso de uso
transacional de abertura. Em 2026-07-28, o `LEFT JOIN` de centro de custo foi
homologado por contagem global e a consulta de colaboradores foi medida com até
dez conexões concorrentes, sem erros ou timeouts.

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
- API de administração de contas, papéis, escopos, vínculo AD e auditoria;
- envelope de erro padronizado e tradução única do `ValidationError`;
- SPA Angular com PrimeNG, mobile first;
- integração do build com o Django e o WhiteNoise;
- telas de contas e cascata cadastral do Senior na SPA;
- remoção da interface server-side, do HTMX e dos testes acoplados a ela.

### Saída esperada

Interface definitiva em operação, com o Django exposto apenas como API.

### Estado em 2026-07-28

Fases A a F concluídas. A SPA autentica, administra contas e papéis, consulta a
auditoria e executa a cascata Empresa → Filial → Tipo → Colaborador sobre os
quatro endpoints Senior homologados. A Fase G permanece pendente para remover
a interface server-side, o HTMX e os testes antigos.

O plano completo, com as sete fases e seus critérios de conclusão, está em
`MIGRATION_FRONTEND_SPA.md`.

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

- AD/LDAP para autenticação corporativa das contas já cadastradas no SGPD;
- controle de acesso;
- e-mail;
- VPN;
- patrimônio;
- ferramentaria;
- medicina ocupacional;
- frota;
- SAP;
- Senior HCM para retorno da rescisão.

O vínculo administrativo do lado SGPD não antecipa a autenticação AD desta
fase: ele apenas preserva a identidade externa única e sua trilha de
confirmação.

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
