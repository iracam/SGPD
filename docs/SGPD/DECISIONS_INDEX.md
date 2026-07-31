# Índice de Decisões Arquiteturais

Use este índice para localizar decisões; o texto normativo completo permanece
em `DECISIONS.md`. “Parcial” exige consultar também a ADR substituta.

## Fundação e infraestrutura

| ADR | Estado | Assunto |
| --- | --- | --- |
| 001 | Vigente | Django como framework principal |
| 002 | Substituída por 025 | Interface server-side |
| 003 | Vigente com exceção 022 | Oracle principal |
| 004 | Substituída por 020 | Sincronização local de referências |
| 013–019 | Vigentes | DEV único, WhiteNoise, Redis sob demanda, validação local, secrets, SMTP e storage |
| 049 | Vigente | Outbox no Oracle em vez de broker para notificações |
| 050 | Vigente | Configuração de e-mail na central, com `.env` como baseline |
| 022 | Vigente no DEV | Owner `SGPD` também como runtime |
| 023 | Vigente | Fundação Python, Django e conexão Oracle |

## Domínio e workflow

| ADR | Estado | Assunto |
| --- | --- | --- |
| 005–012 | Vigentes | Snapshot, versionamento, services, pendências, valores, async, evidências e liberação |
| 033 | Vigente | Escopo explícito e inativação de setores |
| 034–035 | Parcial | Papéis e responsabilidade; ler 036, 038 e 044 |
| 036 | Parcial por 044 | DP cumulativo e separado do setor |
| 037 | Vigente | Abertura transacional em rascunho |
| 038 | Parcial por 044 | Responsabilidade derivada do setor |
| 039–043 | Vigentes | Configuração versionada, templates, códigos e execução concorrente |
| 044 | Parcial por 048 | SuperAdmin como autoridade global explícita |
| 045 | Vigente | Abertura sem gestor imediato |
| 046 | Vigente | Regra de aplicabilidade como sugestão não vinculante |
| 048 | Vigente | Segregação nos valores e SuperAdmin sem barreira |
| 051 | Vigente | Estado formal persistido e situação funcional calculada |

## Integrações, identidade e frontend

| ADR | Estado | Assunto |
| --- | --- | --- |
| 020 | Vigente | Consulta direta e somente leitura ao Senior |
| 021 | Vigente | Cadastro local e vínculo posterior ao AD |
| 024 | Parcial | Papéis com escopo; ler 036, 038 e 044 |
| 025–028 | Vigentes | SPA Angular, mesma origem, PrimeNG e mobile first |
| 029 | Vigente | AD com provisionamento explícito |
| 030 | Exceção DEV | LDAP sem TLS, com aviso explícito |
| 031–032 | Vigentes | Configuração dinâmica e transporte LDAP único; ler 050 |
| 047 | Vigente | Protocolo de conferência como linguagem visual de execução |

## Regras de consulta

- Leia a ADR completa antes de mudar o comportamento que ela governa.
- ADR substituída serve apenas para rastreabilidade.
- Mudança que contradiga decisão vigente exige nova ADR, impactos, riscos e
  indicação explícita das decisões substituídas.

