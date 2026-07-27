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

## Stack recomendada

- Python
- Django
- Django REST Framework
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
5. O usuário da aplicação não será o owner do schema.
6. Referências do Senior serão consultadas em tempo real por SQL `SELECT` parametrizado, sem models ou cópias `REF_*` no SGPD.
7. Dados do colaborador serão copiados para um snapshot na abertura do processo.
8. Regras e checklists serão versionados.
9. Pendências serão entidades próprias e auditáveis.
10. Valores informados serão tratados como pretensões de cobrança.
11. A liberação final continuará sob responsabilidade do DP.

## Estado inicial

Este repositório deverá começar pela fase de descoberta e fundação. O Codex deve primeiro levantar o ambiente, documentar lacunas, propor o plano detalhado e somente depois implementar.

Consulte `PROMPT.md` para o procedimento completo.
