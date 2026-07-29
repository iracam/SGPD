# Visão do Produto

## Estado do documento

Esta visão descreve o produto alvo. O que já está implementado e o próximo
incremento autorizado são definidos em `CHECKPOINT.md`.

## 1. Problema

O desligamento de um colaborador exige validações distribuídas entre diversas áreas da organização. Essas validações podem envolver:

- devolução de materiais;
- devolução de ferramentas;
- devolução de equipamentos;
- encerramento de acessos;
- exame demissional;
- pendências financeiras;
- documentos;
- atividades em andamento;
- passagem de conhecimento;
- contratos;
- veículos;
- patrimônio;
- segurança patrimonial;
- obrigações específicas da função.

Quando esse processo é conduzido por e-mail, planilhas ou comunicação informal, surgem problemas como:

- ausência de rastreabilidade;
- desconhecimento sobre quem deve agir;
- perda de prazos;
- pendências não verificadas;
- descontos sem documentação adequada;
- falta de evidências;
- ausência de visão consolidada;
- dificuldade de auditoria;
- liberação prematura da rescisão;
- dependência excessiva de pessoas específicas.

## 2. Solução

O SGPD será uma aplicação web corporativa para:

- iniciar processos demissionais;
- selecionar o colaborador com base nos dados do Senior HCM;
- aplicar grupos de validação;
- criar tarefas por setor;
- gerar checklists específicos;
- registrar pendências;
- anexar evidências;
- controlar prazos;
- escalar atrasos;
- analisar valores;
- consolidar o resultado;
- liberar o processo para rescisão;
- encerrar o processo após confirmação do Senior HCM.

## 3. Usuários

Todos os participantes abaixo pertencem ao SGPD. O catálogo funcional fixo
possui `DP` e `RESPONSAVEL_SETOR`; os demais títulos abaixo descrevem setor ou
contexto de atuação, não novos papéis. Os dois papéis podem coexistir na mesma
conta. Gestores, e-mails, papéis, associações e escopos não virão do Senior HCM
nem de grupos AD. A conta poderá ser cadastrada
localmente e vinculada depois, ou criada explicitamente a partir de uma
identidade pesquisada no Active Directory. A autenticação AD somente aceitará
contas previamente vinculadas e nunca provisionará usuário durante o login.

### Departamento Pessoal

- possui o papel `DP` vigente no escopo do processo;
- inicia o processo;
- informa datas;
- seleciona ou confirma grupos;
- acompanha o andamento;
- solicita correções;
- analisa pendências;
- libera o processo;
- registra encerramento.

O papel `DP` coordena o ciclo do processo e não associa o usuário
automaticamente ao setor de validação Departamento Pessoal. Quando a mesma
pessoa também executar tarefas desse setor, receberá separadamente
`RESPONSAVEL_SETOR` e a associação explícita ao setor.

### Responsável de setor

- compartilha a mesma autoridade com os demais responsáveis do setor;
- recebe tarefas;
- recebe todas as notificações destinadas ao setor;
- responde checklist;
- registra pendências;
- anexa evidências;
- informa valores estimados;
- conclui a validação.

### Gestor imediato

- valida entregas;
- registra transferência de atividades;
- informa pendências;
- confirma passagem de conhecimento.

### Financeiro

- valida valores;
- aprova ou rejeita cobranças;
- registra valor final aprovado.

### Jurídico

- analisa casos excepcionais;
- emite parecer;
- valida situações de maior risco.

### Auditor

- consulta processos;
- visualiza histórico;
- acessa evidências permitidas;
- não modifica registros.

### Administrador funcional

- configura setores;
- configura responsáveis;
- configura grupos;
- configura templates;
- configura regras de aplicabilidade;
- mantém parâmetros.

## 4. Fronteiras do sistema

### O SGPD fará

- workflow;
- checklist;
- tarefas;
- prazos;
- pendências;
- evidências;
- valores em análise;
- auditoria;
- integração cadastral;
- notificações;
- dashboards;
- relatórios;
- liberação final.

### O SGPD não fará no MVP

- cálculo da rescisão;
- folha de pagamento;
- movimentação funcional;
- desligamento oficial no Senior;
- bloqueio técnico automático em todos os sistemas;
- desconto automático;
- assinatura eletrônica avançada;
- integração com todos os sistemas corporativos desde a primeira versão.

## 5. Resultado esperado

Ao final, o DP deverá conseguir responder rapidamente:

- qual processo está em andamento;
- quais setores ainda não validaram;
- quais pendências existem;
- quais pendências são bloqueantes;
- quais valores foram informados;
- quais valores foram aprovados;
- quais documentos estão anexados;
- quem executou cada ação;
- se o processo pode ser liberado;
- quando o processo foi encerrado.
