# Checkpoint do Projeto

## Status geral

- Projeto: SGPD / DesligaFlow
- Fase atual: Fase 0 — Descoberta e fundação
- Estado: Não iniciado
- Banco: Oracle
- Backend: Django
- UI: Django Templates + HTMX + Alpine
- Integração principal: Senior HCM
- Autenticação prevista: Active Directory/LDAP

## Checkpoint 0 — Descoberta

### Ambiente

- [ ] Confirmar sistema operacional do servidor.
- [ ] Confirmar versão do Python.
- [ ] Confirmar versão do Oracle.
- [ ] Confirmar driver Oracle disponível.
- [ ] Confirmar acesso DEV/HML/PRD.
- [ ] Confirmar padrão de secrets.
- [ ] Confirmar SMTP.
- [ ] Confirmar Redis.
- [ ] Confirmar storage de evidências.
- [ ] Confirmar proxy/Nginx.
- [ ] Confirmar CI/CD.

### Senior HCM

- [ ] Confirmar versão.
- [ ] Confirmar owner.
- [ ] Confirmar views disponíveis.
- [ ] Mapear empresa.
- [ ] Mapear filial.
- [ ] Mapear tipo de colaborador.
- [ ] Mapear colaborador.
- [ ] Mapear cargo.
- [ ] Mapear local.
- [ ] Mapear centro de custo.
- [ ] Mapear gestor.
- [ ] Mapear e-mail.
- [ ] Confirmar data de atualização.
- [ ] Confirmar regras de colaborador ativo.
- [ ] Definir estratégia de homologação.

### Processo funcional

- [ ] Validar fluxo atual.
- [ ] Identificar setores.
- [ ] Identificar responsáveis.
- [ ] Levantar checklists atuais.
- [ ] Levantar prazos.
- [ ] Levantar regras de bloqueio.
- [ ] Levantar evidências.
- [ ] Levantar valores.
- [ ] Levantar aprovações.
- [ ] Levantar exceções.
- [ ] Validar cancelamento.
- [ ] Validar reabertura.
- [ ] Validar encerramento.

### Segurança

- [ ] Definir grupos AD.
- [ ] Definir papéis.
- [ ] Definir escopo por empresa/filial.
- [ ] Definir dados sensíveis.
- [ ] Definir retenção.
- [ ] Definir acesso a documentos médicos.
- [ ] Definir acesso a valores.
- [ ] Definir política de auditoria.

### Arquitetura

- [ ] Criar ADRs.
- [ ] Validar módulos Django.
- [ ] Definir estrutura de settings.
- [ ] Definir filas.
- [ ] Definir storage.
- [ ] Definir logging.
- [ ] Definir health checks.
- [ ] Definir backups.
- [ ] Definir observabilidade.

## Checkpoint 1 — Fundação técnica

- [ ] Repositório criado.
- [ ] `pyproject.toml` criado.
- [ ] Django iniciado.
- [ ] Settings por ambiente.
- [ ] `.env.example`.
- [ ] Oracle conectado.
- [ ] Redis conectado.
- [ ] Worker conectado.
- [ ] Health check.
- [ ] Logging estruturado.
- [ ] Testes executando.
- [ ] Lint e format.
- [ ] CI.

## Checkpoint 2 — Integração cadastral

- [ ] Models `REF_*`.
- [ ] Views Senior definidas.
- [ ] Carga inicial.
- [ ] Incremental.
- [ ] Reconciliação.
- [ ] Logs.
- [ ] Reprocessamento.
- [ ] Cascata funcionando.
- [ ] Snapshot validado.

## Checkpoint 3 — Configuração funcional

- [ ] Setores.
- [ ] Responsáveis.
- [ ] Grupos.
- [ ] Regras.
- [ ] Templates.
- [ ] Versionamento.
- [ ] Permissões.

## Checkpoint 4 — Workflow

- [ ] Abertura.
- [ ] Início.
- [ ] Tarefas.
- [ ] Estados.
- [ ] Prazos.
- [ ] Painéis.
- [ ] Auditoria.

## Checkpoint 5 — Pendências

- [ ] Cadastro.
- [ ] Ciclo de vida.
- [ ] Evidências.
- [ ] Hash.
- [ ] Bloqueios.
- [ ] Regularização.
- [ ] Decisões.

## Checkpoint 6 — Liberação

- [ ] Prontidão automática.
- [ ] Revisão do DP.
- [ ] Liberação.
- [ ] Registro de rescisão.
- [ ] Encerramento.
- [ ] Cancelamento.
- [ ] Reabertura.

## Registro de decisões

Use esta seção em cada execução:

```text
Data:
Responsável:
Fase:
O que foi concluído:
Decisões:
Riscos:
Pendências:
Próximo passo:
Comandos executados:
Arquivos alterados:
Testes:
```
