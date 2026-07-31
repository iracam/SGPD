# Decisões Arquiteturais

## Como ler este documento

Uma ADR sem estado explícito está vigente. ADRs substituídas permanecem apenas
como índice de rastreabilidade e não têm efeito normativo. O estado atual do
projeto está em `CHECKPOINT.md`.

## ADR-001 — Django como framework principal

### Decisão

Usar Django como backend, API, administração técnica e entrega da SPA.

### Motivos

- maturidade;
- ORM;
- autenticação;
- admin;
- segurança;
- velocidade de entrega;
- experiência existente da equipe;
- integração adequada com Oracle;
- boa aderência a sistemas corporativos.

## ADR-002 — Interface server-side

### Estado

Substituída pela ADR-025 em 2026-07-28.

A implementação correspondente foi removida na Fase G. A decisão vigente sobre
interface é exclusivamente a ADR-025.

## ADR-003 — Oracle como banco principal

### Estado

Vigente, com exceção da segregação de usuário no DEV definida pela ADR-022.

### Decisão

Usar Oracle Database 19c, conforme padrão definido.

### Restrições

- owner exclusivo;
- owner `SGPD` como conexão única de runtime e migrations somente no DEV;
- Oracle Instant Client 19.28 disponível em `/opt/oracle/instantclient_19_28`;
- migrations revisadas;
- nada de acesso direto de escrita ao Senior.

## ADR-004 — Sincronização local de referências

### Estado

Substituída pela ADR-020 em 2026-07-27.

A decisão vigente é a consulta direta e online da ADR-020. Não existe
sincronização cadastral nem tabela `REF_*`.

## ADR-005 — Snapshot imutável

### Decisão

Copiar os dados do colaborador ao abrir o processo.

### Motivos

- preservar contexto histórico;
- evitar alteração retroativa;
- sustentar auditoria.

## ADR-006 — Templates versionados

### Decisão

Checklist e grupos serão versionados.

### Motivos

- processos antigos não podem mudar;
- auditoria;
- evolução segura.

## ADR-007 — Services para regras

### Decisão

Regras de negócio críticas serão implementadas em services explícitos.

### Motivos

- testabilidade;
- menor dependência de views;
- evitar signals ocultos;
- clareza.

## ADR-008 — Pendência como entidade

### Decisão

Pendências não serão apenas observações textuais.

### Motivos

- ciclo de vida;
- evidências;
- valores;
- decisões;
- relatórios;
- auditoria.

## ADR-009 — Valor como pretensão

### Decisão

Valores lançados por setores serão solicitações de análise.

### Motivos

- reduzir risco;
- permitir contestação;
- exigir aprovação;
- evitar desconto automático.

## ADR-010 — Processamento assíncrono

### Decisão

Notificações e escaladas serão assíncronas. Consultas cadastrais ao Senior são online e não usam sincronização.

## ADR-011 — Evidências fora do Oracle

### Decisão

Armazenar arquivos em storage dedicado e manter metadados no Oracle.

### Exceção

Somente usar BLOB se houver exigência técnica ou corporativa formal.

## ADR-012 — Liberação pelo DP

### Decisão

A liberação para rescisão é ação explícita do DP.

### Motivos

- responsabilidade funcional;
- controle;
- revisão humana;
- exceções.

## ADR-013 — Ambiente único DEV

### Decisão

Manter somente o ambiente DEV no escopo atual.

### Consequências

- não haverá configuração de HML ou PRD nesta fase;
- settings e documentação devem refletir apenas DEV;
- a criação futura de outro ambiente exigirá revisão de segurança, dados e implantação.

## ADR-014 — WhiteNoise sem Nginx

### Decisão

Usar WhiteNoise para servir arquivos estáticos do Django e não utilizar Nginx.

### Restrições

- WhiteNoise atende somente arquivos estáticos;
- evidências e uploads permanecem em storage separado e protegido;
- qualquer necessidade futura de proxy, TLS ou balanceamento exigirá nova decisão.

## ADR-015 — Redis sob demanda

### Decisão

Não manter Redis ativo nesta etapa. Quando uma funcionalidade exigir cache, fila ou lock distribuído, subir Redis em container no DEV.

### Consequências

- a fundação inicial não depende de Redis;
- a introdução do container deverá incluir health check, volume quando necessário e configuração reproduzível;
- worker assíncrono permanece adiado.

## ADR-016 — Sem CI/CD no escopo atual

### Decisão

Não implementar pipeline de CI/CD no ambiente DEV atual.

### Consequências

- testes, lint e validações serão executados localmente;
- os comandos de validação deverão ser documentados e reproduzíveis;
- a adoção futura de CI/CD exigirá nova decisão.

## ADR-017 — Secrets no `.env` do DEV

### Decisão

Manter usuário, senha e e-mail de integrações no arquivo `.env` local, nunca no repositório.

### Convenções

- usuários individuais seguem `nome.sobrenome`;
- senhas não seguem padrão previsível e não devem ser documentadas;
- `.env.example` contém somente nomes de variáveis e valores não sensíveis;
- o arquivo `.env` deve ter acesso restrito ao usuário da aplicação.

## ADR-018 — SMTP Microsoft 365

### Decisão

Usar Microsoft 365 SMTP com remetente `noreply@bsabioenergia.com.br`.

### Configuração

- host `smtp.office365.com`;
- porta 587;
- TLS/STARTTLS habilitado;
- usuário, senha e endereço do remetente definidos no `.env`.

### Validação em 2026-07-28

O Microsoft 365 aceitou uma mensagem de prova enviada ao próprio remetente
configurado. SMTP AUTH e `Send As` estão homologados no DEV.

## ADR-019 — Evidências no filesystem local

### Decisão

Armazenar evidências no filesystem local privado do DEV.

### Restrições

- não servir evidências pelo WhiteNoise;
- não expor o diretório diretamente por URL;
- calcular SHA-256 e manter metadados no Oracle.

## ADR-020 — Consulta direta ao Senior sem models

### Decisão

Consultar os objetos homologados de `VETORH` diretamente no Oracle por SQL `SELECT` parametrizado.

Não criar:

- models Django para tabelas ou views do Senior;
- models não gerenciados;
- tabelas locais `REF_*`;
- carga inicial, incremental ou reconciliação cadastral;
- views Oracle locais nesta etapa.

O endpoint da API deverá delegar a consulta ao repository. Somente o snapshot
criado na abertura do processo será persistido no SGPD.

### Motivos

- decisão funcional de consultar a fonte oficial em tempo real;
- objetos `VETORH` estão no mesmo serviço Oracle;
- grants `SELECT` já foram concedidos ao schema SGPD para o contrato inicial;
- elimina defasagem e operação de sincronização.

### Consequências

- maior acoplamento ao contrato físico do Senior;
- indisponibilidade do Senior impede novas pesquisas e snapshots;
- consultas exigem bind variables, paginação, timeout e testes de contrato;
- a separação do owner `SGPD` foi posteriormente excepcionada pela ADR-022; `VETORH` continua proibido no runtime;
- o snapshot do processo continua obrigatório e imutável.

## ADR-021 — Cadastro local de usuários e vinculação futura ao AD

Complementada pela ADR-029 em 2026-07-28 quanto à implementação e ativação da
integração. Permanecem vigentes a propriedade local do cadastro funcional e a
separação entre identidade AD e autorização SGPD.

### Decisão

Cadastrar no SGPD todos os usuários, gestores, e-mails, papéis e escopos.

O Senior HCM não será fonte de identidades ou autorizações. O MVP terá autenticação local. Em fase posterior, cada conta SGPD poderá ser vinculada a uma identidade do Active Directory para autenticação corporativa com uma única senha.

### Regras

- o perfil funcional continua pertencendo ao SGPD após a vinculação;
- a vinculação usa identificador corporativo estável e único, não apenas e-mail;
- uma identidade AD não pode ser vinculada a mais de uma conta SGPD;
- papéis e permissões não serão importados automaticamente do Senior;
- a senha local comum será desabilitada após ativar AD, mantendo apenas contingência administrativa controlada;
- local de trabalho não faz parte do cadastro nem das regras do MVP.

### Consequências

- gestor deverá ser selecionado entre usuários SGPD na abertura do processo;
- nome e e-mail do gestor serão preservados historicamente no processo;
- a indisponibilidade futura do AD não altera os dados cadastrais e de autorização mantidos no SGPD.

## ADR-022 — Owner SGPD como usuário de runtime no DEV

### Decisão

Usar o owner `SGPD` como conexão única para runtime e migrations no ambiente DEV. Não criar `SGPD_APP` ou outro usuário Oracle para a aplicação.

### Limites

- a decisão vale para o único ambiente DEV atualmente em escopo;
- `VETORH` continua proibido como usuário da aplicação;
- o acesso ao Senior continua limitado a `SELECT` nos objetos homologados;
- nenhum DDL deve ser emitido pelo código de runtime;
- migrations continuam sendo operações explícitas e revisadas;
- uma futura criação de HML ou PRD exigirá nova avaliação desta exceção.

### Risco aceito

O processo da aplicação terá privilégios de owner sobre o schema SGPD. Um erro de aplicação ou comprometimento de credencial terá impacto maior do que teria com um usuário operacional restrito.

### Controles compensatórios

- `.env` com modo `600` e fora do Git;
- credencial exclusiva do SGPD, nunca compartilhada com `VETORH`;
- SQL do Senior centralizado, parametrizado e somente leitura;
- revisão de migrations e proibição de DDL dinâmico;
- logs e auditoria sem segredos;
- testes de contrato e revisão do escopo de grants.

## ADR-023 — Fundação Python, Django e conexão Oracle

### Decisão

Adotar Python 3.13, Django 5.2 LTS, Django REST Framework 3.17 e `uv` com
lockfile. Usar `python-oracledb` em modo Thick no DEV, carregando o Oracle
Instant Client 19.28 indicado por `ORACLE_CLIENT_LIB_DIR`.

### Motivos

- Django 5.2 é LTS e suporta Python 3.13;
- o lockfile torna a instalação local reproduzível;
- o modo Thin recusou o verificador de senha legado da conta `SGPD`
  (`DPY-3015`);
- o modo Thick conectou com sucesso usando a mesma conta, sem criar usuário
  adicional ou alterar a credencial no Oracle.

### Consequências

- o Oracle Instant Client passa a ser pré-requisito do ambiente DEV;
- uma falha ao carregar o client interrompe a inicialização com erro genérico,
  sem registrar credenciais;
- testes unitários usam SQLite em memória e testes de contrato separados
  validam o Oracle real;
- `SGPD` recebeu `CREATE TABLE` e `CREATE SEQUENCE`, ambos sem `ADMIN OPTION`,
  e quota finita de 500 MB em `PIMS_DATA`; migrations continuam sendo ações
  explícitas após revisão do SQL.

## ADR-024 — Papéis com escopo e vínculo administrativo com o AD

Complementada pela ADR-029 em 2026-07-28. O vínculo administrativo passou a ser
verificado no diretório quando a descoberta AD está habilitada.
O catálogo múltiplo e sua manutenção dinâmica foram substituídos pela ADR-034
em 2026-07-29; as regras de vínculo AD, escopo, validade, revogação e auditoria
permanecem vigentes.

### Decisão

Manter autorização funcional em papéis próprios do SGPD, com permissões
delegáveis e atribuições versionadas por escopo:

- global;
- empresa;
- filial.

Implementar o vínculo do lado SGPD com identificador AD opaco, único e
normalizado, usuário do diretório, data, administrador responsável,
justificativa e auditoria. Esse vínculo não ativa autenticação LDAP/AD.

### Regras

- atribuições possuem validade e são revogadas logicamente;
- escopo de filial exige empresa e filial;
- permissões diretas são globais;
- endpoints do Senior exigem permissão e respeitam empresa/filial;
- criação e manutenção passam por services transacionais;
- cada service administrativo valida a permissão do ator, sem depender
  exclusivamente do endpoint chamador;
- alterações concorrentes de usuário e papel são rejeitadas por versão;
- desativações bloqueiam os superusuários ativos em ordem determinística para
  preservar ao menos uma conta de contingência sob concorrência;
- login, logout, falha, senha, usuário, papel e vínculo AD geram auditoria;
- eventos de auditoria não aceitam `update` ou `delete`, inclusive por
  `QuerySet`;
- o Django Admin é somente leitura para esses registros;
- nenhuma senha ou credencial do AD é armazenada na auditoria.

### Papéis iniciais

`ADMIN_IDENTIDADE`, `DP`, `RESPONSAVEL_SETOR`, `COORDENADOR_SETOR`,
`GESTOR_IMEDIATO`, `FINANCEIRO`, `JURIDICO`, `AUDITOR` e
`ADMIN_FUNCIONAL`. Este catálogo é histórico e não está mais ativo.

### Consequências

- o SGPD possui autorização aplicável antes do workflow;
- a possibilidade de criar papéis e ampliar suas permissões foi substituída
  pelo catálogo fixo da ADR-034;
- autenticação LDAP/AD ainda exige atributo estável homologado, endpoint, TLS,
  base de busca, credencial técnica e política de contingência;
- a senha local não é desabilitada apenas pelo vínculo administrativo.

## ADR-025 — SPA Angular como interface do SGPD

### Estado

Aceita em 2026-07-28. Substitui a ADR-002.

### Decisão

Usar uma SPA Angular 21 como interface da aplicação, consumindo todos os
recursos funcionais do Django exclusivamente por API.

A substituição é total: administração de contas e cascata cadastral do Senior.
O Django Admin permanece, somente leitura, como ferramenta de diagnóstico,
conforme `SECURITY.md` §9.

### Motivos

- a administração funcional do processo demissional exige telas com estado
  local rico — checklists por setor, pendências com evidências, análise de
  valores — nas quais o custo de manter a coerência por fragmentos HTML cresce
  mais rápido do que o de manter um cliente com estado explícito;
- o requisito de mobile first, registrado na ADR-028, incide sobre interações
  que a renderização por fragmentos atende mal;
- os services de domínio já revalidam autorização no próprio limite, conforme
  a ADR-024, de modo que expor uma API não move a regra de negócio para o
  cliente;
- a cascata cadastral do Senior já possui endpoints JSON autenticados e
  autorizados por escopo, comprovando o padrão;
- existe um projeto corporativo de referência com a mesma arquitetura em
  operação, o que reduz o risco de decisões estruturais novas.

### Consequências

- o Django não renderiza telas de aplicação e expõe `/api/v1/` como única
  superfície funcional;
- toda a administração de contas foi exposta em API antes da remoção das views
  HTML;
- `npm` e o ecossistema Node passam a fazer parte do ciclo de build, com
  `package-lock.json` versionado e instalação por `npm ci`;
- a interface depende de JavaScript, o que não conflita com o
  RNF-008, que exige apenas os navegadores corporativos homologados;
- HTMX, Alpine.js, Tailwind e daisyUI não fazem parte da stack;
- a autorização não usa a renderização como barreira auxiliar: a API é a única
  superfície e cada endpoint possui teste de permissão negada;
- o plano de execução, com sete fases e critérios de conclusão, está preservado
  em `history/completed-plans/MIGRATION_FRONTEND_SPA.md`.

### Risco aceito

Uma SPA amplia a superfície de API e a quantidade de código de cliente frente à
opção server-side. O risco é aceito por decisão explícita do projeto, com a
mitigação de que nenhuma regra de negócio reside no cliente e de que os
services permanecem como limite de segurança.

## ADR-026 — Sessão Django com CSRF em origem única

### Decisão

Autenticar a SPA por sessão Django e proteção CSRF, servindo aplicação e API na
mesma origem. Não usar JWT.

### Regras

- o cookie de sessão permanece `HttpOnly`, com `SameSite` e `Secure` conforme
  a configuração do ambiente;
- requisições com efeito colateral enviam `X-CSRFToken` e credenciais;
- nenhum dado de sessão é gravado em `localStorage` ou `sessionStorage`; o
  armazenamento local guarda apenas preferências de interface, como tema e
  estado da navegação;
- `login`, `logout` e falha de autenticação continuam gerando os mesmos eventos
  de auditoria já implementados;
- o endpoint de login possui limitação de tentativas;
- a obrigatoriedade de troca da senha temporária é preservada: sob `/api/`, o
  middleware devolve `403` com código próprio; navegação direta é redirecionada
  para `/fe/senha`.

### Motivos

- preserva integralmente a auditoria de autenticação já homologada;
- mantém a revogação de sessão sob controle do servidor, o que um token de
  acesso autocontido não oferece;
- evita guardar credencial de longa duração em armazenamento acessível por
  JavaScript;
- dispensa CORS, refresh, rotação e blacklist de tokens;
- o projeto de referência usa JWT, mas naquele contexto a origem do cliente é
  separada; aqui não é.

### Consequências

- aplicação e API precisam permanecer na mesma origem;
- a criação futura de HML ou PRD, ou a introdução de proxy reverso, reabre esta
  decisão junto com a ADR-014;
- clientes não navegadores, se existirem no futuro, exigirão decisão própria de
  autenticação.

## ADR-027 — PrimeNG e build integrado ao WhiteNoise

### Decisão

Usar PrimeNG 21 com o preset Aura e primeicons como biblioteca de componentes.

Entregar a SPA pelo próprio Django: `ng build` gera os artefatos, os assets são
servidos pelo WhiteNoise e o `index.html` é servido por uma view Django
dedicada, registrada como catch-all depois de `/api/`, `/admin/`, `/health/` e
`/static/`.

### Motivos

- há um projeto corporativo de referência em PrimeNG, cuja estrutura, sistema
  de tokens e decisões podem ser reaproveitados;
- o conjunto de componentes cobre tabelas, filtros, diálogos e formulários
  administrativos sem construção própria;
- servir pelo Django preserva a ADR-014, que exclui Nginx, e sustenta a origem
  única exigida pela ADR-026.

### Restrições

- o `index.html` não pode ser servido pelo WhiteNoise:
  `CompressedManifestStaticFilesStorage` renomeia o arquivo incluindo hash e
  quebra a rota `/`;
- as versões de Angular e PrimeNG ficam fixadas no `package-lock.json`;
  atualização exige revisão técnica e de licenciamento explícita;
- nenhum código é carregado de CDN;
- fontes e ícones são empacotados localmente.

### Versão fixada em 21 por licenciamento

A versão 21 é a última publicada sob a licença MIT. A partir da 22, a PrimeTek
reclassificou o pacote como parte do PrimeUI, uma família comercial, e passou a
exigir chave de licença mesmo no nível Community, que continua gratuito para
organizações elegíveis. Sem chave válida, a biblioteca injeta um aviso
permanente em todas as telas.

A verificação foi feita empiricamente em 2026-07-28: a 22.0.0 traz
`primeng-license.mjs` no pacote, expõe `license?: string` na configuração e
exibiu o aviso em todas as capturas; a 21.1.9 não possui módulo de licença, não
expõe a opção e declara `The MIT License (MIT)` no `LICENSE.md`.

Decisão: permanecer na 21 sob MIT. O SGPD não fica dependente de cadastro,
emissão e renovação anual de chave para que a interface opere sem aviso.

### Consequências da fixação

- o Angular também fica fixado na 21, porque a `primeng@21` exige
  `@angular/core ^21.0.7`;
- atualizar o PrimeNG para 22 ou superior deixa de ser decisão técnica e passa a
  exigir decisão de licenciamento, com nova ADR;
- o par 21/21 é o mesmo em operação no projeto corporativo de referência.

### Nota de compatibilidade entre versões maiores

O PrimeNG altera contratos de componente entre versões maiores. Na passagem pela
22 observou-se que `p-message` deixou de aceitar a entrada `text`, passando a
projeção de conteúdo, e que a diretiva `pButton` deixou de aceitar `label` e
`icon`, que permaneceram apenas no componente `p-button`. Qualquer atualização
de versão maior exige revisão de template além de revisão de dependência.

## ADR-028 — Mobile first como requisito de interface

### Decisão

Projetar e implementar a interface a partir do menor viewport, ampliando-a por
pontos de quebra. Todo SCSS de layout usa exclusivamente
`@media (min-width: ...)`.

### Regras

- consultas `max-width` não são aceitas em código novo; sua presença indica que
  a regra base foi escrita para desktop;
- os pontos de quebra são declarados uma única vez, como tokens, e reutilizados
  por todas as features;
- a navegação tem como estado base uma barra superior com gaveta sobreposta, e
  só é promovida a barra lateral permanente a partir de 1024 px;
- listagens administrativas possuem representação em cartões no estado base e
  tabela a partir do ponto de quebra de tablet;
- elementos interativos têm no mínimo 44 × 44 px no estado base;
- campos de formulário nunca são renderizados abaixo de 16 px em telefone, para
  evitar o zoom automático do Safari no iOS;
- nenhuma tela produz rolagem horizontal no `body`.

### Motivos

- requisito explícito do projeto;
- o processo demissional envolve setores que operam fora da mesa — patrimônio,
  ferramentaria, medicina ocupacional e frota — para os quais a conferência de
  itens e o registro de evidências ocorrem em campo;
- responsividade tratada como adaptação posterior tende a produzir telas
  tecnicamente responsivas e operacionalmente inviáveis em telefone.

### Consequências

- o SCSS do projeto de referência serve como fonte de tokens, não de layout,
  pois ele é desktop first;
- cada listagem administrativa passa a ter duas representações a partir dos
  mesmos dados;
- a conclusão de cada fase de interface exige conferência visual em todos os
  pontos de quebra, começando pelo menor.

## ADR-029 — Active Directory com provisionamento explícito e ativação em estágios

### Estado

Aceita em 2026-07-28. A escolha de transporte da seção de segurança foi
substituída pela ADR-032.

### Decisão

Implementar a integração corporativa com `django-auth-ldap` 5.3.x e
`python-ldap` 3.4.x, preservando Django 5.2 LTS e Django REST Framework nas
versões mais recentes compatíveis resolvidas pelo projeto.

Separar a ativação em dois estágios:

1. `LDAP_ENABLED` para descoberta administrativa, importação explícita e
   vínculo verificado;
2. `LDAP_AUTHENTICATION_ENABLED` para autenticação corporativa de contas SGPD
   previamente vinculadas.

O SGPD suporta os dois fluxos necessários:

- cadastrar a conta local e vinculá-la posteriormente a uma identidade
  pesquisada no AD;
- pesquisar usuários/grupos e criar explicitamente uma conta local já
  vinculada, sem papel ou permissão automática.

### Identidade e autorização

- `objectGUID`, convertido do formato binário little-endian para UUID canônico,
  é a chave estável do vínculo;
- login e e-mail servem para apresentação e detecção de conflitos, não como
  chave;
- credenciais AD válidas nunca criam usuário durante o login;
- grupos e OUs podem restringir o público elegível, mas não concedem papéis,
  permissões ou escopos;
- perfil, situação, papéis, permissões e escopos continuam exclusivamente no
  SGPD;
- a conta importada recebe senha local inutilizável;
- a importação não solicita justificativa manual; ator, origem, identidade e
  motivo operacional padronizado compõem a auditoria;
- conta comum vinculada não faz fallback para senha local quando o AD está
  ativo;
- definição, redefinição e troca de senha local são igualmente bloqueadas
  quando a política de autenticação não permite usar essa credencial;
- um superusuário local de contingência pode ser mantido por configuração
  explícita.

### Segurança e operação

- usar LDAPS ou StartTLS com validação obrigatória da cadeia de certificados;
- usar conta técnica AD somente leitura;
- excluir usuários desabilitados pelo `userAccountControl`;
- permitir base por OU, grupo direto ou aninhado e filtro fixo revisado;
- escapar toda entrada de busca, paginar e limitar resultados;
- não registrar senha, filtro preenchido, DN pesquisado ou atributos pessoais;
- validar configuração pelo system check e conectividade pelo comando
  `check_active_directory`;
- ativar autenticação somente após validar descoberta, importação, vínculo,
  contingência e comportamento de falha.

### Consequências

- `django-auth-ldap` e `python-ldap` passam a ser dependências diretas
  documentadas e bloqueadas em `uv.lock`;
- os headers e bibliotecas nativas OpenLDAP/SASL/OpenSSL tornam-se
  pré-requisitos de build;
- indisponibilidade do AD bloqueia login de contas comuns vinculadas, sem
  fallback silencioso que enfraqueça a política corporativa;
- a operação no AD real só é considerada homologada depois de preencher URI,
  bind, CA, bases e grupo/filtro no `.env` e executar o runbook
  `INTEGRATION_ACTIVE_DIRECTORY.md`;
- nenhuma migration de banco é necessária, pois os campos de identidade
  existentes atendem ao contrato.

## ADR-030 — Descoberta LDAP sem TLS como exceção temporária no DEV

### Estado

Substituída pela ADR-032 em 2026-07-28. O texto abaixo preserva a exceção
histórica que permitiu a primeira homologação.

### Decisão

Permitir LDAP simples exclusivamente para descoberta administrativa no ambiente
DEV, mediante todas as condições:

- `DJANGO_DEBUG=true`;
- `LDAP_ENABLED=true`;
- `LDAP_ALLOW_INSECURE_DISCOVERY=true`;
- `LDAP_AUTHENTICATION_ENABLED=false`;
- conta técnica de leitura;
- warning permanente no system check e na SPA.

A autenticação AD continua exigindo LDAPS ou StartTLS. O backend revalida o
contrato no momento do login e recusa LDAP simples, independentemente do modo
como o processo Django foi iniciado.

### Risco aceito

O bind simples transmite o usuário e a senha da conta técnica sem criptografia
na rede. A exceção não torna o transporte seguro e não é autorizada para senha
de usuário final, HML ou PRD.

### Saída da exceção

Obter a CA `BSA-AD-CA` por canal confiável, instalá-la no trust store ou
configurar `LDAP_TLS_CA_CERT_FILE`, retornar para
`ldaps://ad.bsa.local:636`, definir
`LDAP_ALLOW_INSECURE_DISCOVERY=false`, repetir o probe e somente então avaliar
`LDAP_AUTHENTICATION_ENABLED=true`.

## ADR-031 — Configuração LDAP dinâmica e exclusiva de SuperAdmin

### Estado

Aceita em 2026-07-28. As condições de transporte dos itens 2 e 3 da ativação
foram substituídas pela ADR-032.

### Decisão

Criar uma central técnica em `/fe/configuracoes`, começando por LDAP e
autenticação, cuja autoridade é diretamente `User.is_superuser`. Essa
capacidade vale para contas criadas por `createsuperuser` ou pelo bootstrap
administrativo e não será incluída no catálogo de permissões delegáveis.

Persistir a configuração efetiva no singleton `SGPD_LDAP_CONFIG`, com versão
otimista e o `.env` como baseline enquanto o registro não existir. O backend
LDAP monta sua configuração por instância de autenticação, para que a mudança
validada entre em vigor sem mutação de settings globais ou reinício.

### Segredos e certificados

- a senha de bind informada pela SPA é cifrada com Fernet usando uma chave
  derivada do `DJANGO_SECRET_KEY`;
- a API retorna apenas se existe segredo configurado, nunca seu valor ou
  ciphertext;
- a rotação do `DJANGO_SECRET_KEY` exige regravação coordenada da senha LDAP;
- o certificado ou bundle é validado como X.509 de CA vigente, normalizado para
  PEM e limitado a 512 KiB;
- o arquivo fica em `SYSTEM_CONFIGURATION_STORAGE_PATH`, com permissões
  privadas e fora do WhiteNoise; Oracle recebe somente nome, hash e metadados.

### Ativação e auditoria

O login AD só pode ser habilitado quando:

1. a descoberta estiver habilitada;
2. o transporte for LDAPS ou StartTLS com validação obrigatória;
3. a CA estiver válida e corresponder ao hash registrado;
4. o bind e o RootDSE tiverem passado para o mesmo fingerprint de configuração;
5. existir SuperAdmin ativo com senha local utilizável e fallback preservado.

A rotação do certificado desabilita a autenticação AD e invalida o probe
anterior; um novo teste é obrigatório antes da reativação.
O componente secreto do fingerprint é um HMAC com chave derivada do segredo da
aplicação, não um hash simples da senha de bind.

Atualização, upload e teste geram eventos append-only com correlation ID e
motivos operacionais padronizados no servidor, sem depender de justificativa
digitada e sem senha, caminho privado ou filtro preenchido.

### Consequências

- `cryptography`, já transitiva de `python-oracledb`, torna-se dependência
  direta pelo uso de Fernet e X.509;
- a tabela nova é pequena e singleton; a migration é somente aditiva;
- indisponibilidade do Oracle antes da migration mantém o baseline do ambiente
  para comandos de implantação, sem autorizar login fora das validações
  existentes;
- o risco R49 passa a representar a manutenção contínua desses controles.

## ADR-032 — Transporte LDAP único e simplificado

### Estado

Aceita em 2026-07-28 por decisão explícita do projeto.

### Decisão

Descoberta, busca de grupos e usuários, importação, vínculo e autenticação usam
uma única escolha de transporte administrada pelo SuperAdmin:

- `Negociar TLS` marcado monta `ldaps://` automaticamente; o campo recebe
  somente host ou host e porta, e a CA válida é obrigatória para ativar o
  login;
- `Negociar TLS` desmarcado monta `ldap://` automaticamente e permite os mesmos
  fluxos, inclusive login, sem uma segunda chave de exceção.

LDAP simples deve exibir warning permanente de que a credencial técnica e as
senhas dos usuários trafegam sem criptografia. O aviso torna o risco explícito,
mas não bloqueia a escolha administrativa. StartTLS permanece aceito somente
para compatibilidade de baselines antigos do ambiente e não é apresentado na
central.

A importação de usuários não recebe grupo adicional. Ela aplica exatamente a
base, o grupo obrigatório e o filtro salvos. A pesquisa de grupos passa para a
central de configurações, onde preenche o grupo obrigatório.

### Controles preservados

- senha de bind cifrada e nunca projetada;
- conta técnica somente leitura;
- probe da mesma configuração antes de ativar o login;
- contingência local de SuperAdmin;
- filtro de contas ativas, limites, paginação e escape LDAP;
- CA validada quando TLS estiver selecionado;
- warning `sgpd.AD900` e aviso na SPA enquanto LDAP simples estiver ativo.

### Consequências

- a ADR-030 deixa de ser regra vigente;
- `LDAP_ALLOW_INSECURE_DISCOVERY` e o campo equivalente são removidos;
- o risco R48 passa a incluir também a senha do usuário quando o login operar
  sem TLS;
- o transporte deixa de variar entre descoberta e autenticação.

## ADR-033 — Escopo explícito e inativação dos setores

### Estado

Aceita em 2026-07-28 como primeiro incremento da Fase 3.

### Decisão

Modelar a cobertura de cada setor por registros relacionais explícitos com
escopo `GLOBAL`, `COMPANY` ou `BRANCH`, reutilizando a semântica organizacional
já adotada para papéis sem criar tabelas de referência do Senior.

- todo setor possui ao menos um escopo;
- global não pode coexistir com empresa ou filial;
- empresa cobre suas filiais e impede filial redundante da mesma empresa;
- os códigos externos são positivos, mas não recebem foreign key local;
- código do setor é imutável;
- setor é inativado, nunca excluído;
- alterações usam versão otimista e service transacional;
- mutações bloqueiam as linhas do pequeno catálogo em ordem determinística para
  serializar a validação da cadeia de escalada;
- escalada exige setor ativo e não pode formar ciclo;
- auditoria append-only registra antes/depois, justificativa e correlation ID.

### Consequências

- três tabelas aditivas pertencem ao schema SGPD: setor, escopo e auditoria;
- indisponibilidade do Senior não impede consultar configurações existentes;
- a confirmação operacional dos códigos continua responsabilidade da
  configuração funcional, sem cache ou réplica cadastral;
- a permissão `sectors.manage_sectors` exige concessão global neste incremento,
  pois um único setor pode atender múltiplas empresas;
- responsáveis, grupos, templates e workflow permanecem fora deste
  incremento.

## ADR-034 — Papel funcional único e responsabilidade compartilhada

### Estado

Parcialmente substituída em 2026-07-29 pela ADR-036. Permanecem vigentes a
igualdade entre responsáveis de setor, a ausência de coordenador/substituto e
a proibição de catálogo dinâmico. Deixam de vigorar o papel funcional único e
a derivação das capacidades de DP pela associação ao setor.

### Decisão

Manter somente `RESPONSAVEL_SETOR` como papel funcional ativo.

- não existe papel de coordenador, DP, Financeiro, Jurídico, gestor, auditor ou
  administrador funcional;
- SuperAdmin é autoridade técnica por `User.is_superuser` e não pertence ao
  catálogo funcional;
- ações especiais decorrem do setor associado e do caso de uso: por exemplo,
  responsáveis do Departamento Pessoal liberam o processo;
- um setor pode possuir um ou mais responsáveis com a mesma autoridade;
- todos os responsáveis ativos do setor recebem as mesmas notificações e
  e-mails;
- qualquer responsável pode movimentar a tarefa;
- a primeira transação válida confirma a ação; concorrentes recebem o estado
  atualizado, sem duplicar auditoria, e-mail ou efeito externo;
- o grupo AD `BSA_SGPD` serve apenas para elegibilidade e descoberta de
  identidades, nunca para conceder papel ou associar setor.

### Controles

- criação e edição dinâmica de papéis são indisponíveis na API e na SPA;
- `AssignRoleService` aceita somente `RESPONSAVEL_SETOR`;
- `SGPD_CK_ROLE_ACTIVE_CODE` impede outro código ativo no Oracle;
- papéis legados são inativados e atribuições legadas revogadas, sem exclusão
  física;
- associação de responsável será explícita, versionada, auditada e delimitada
  por setor e escopo;
- mutações de tarefa usarão transação, lock ou versão e idempotência.

### Consequências

- o menu `/fe/papeis` e o catálogo de permissões deixam de existir;
- cadastro e detalhe de usuário podem atribuir somente o papel fixo;
- os dez responsáveis já importados permanecem com sua atribuição;
- regras futuras não devem testar códigos de papel para distinguir DP,
  Financeiro ou Medicina; devem verificar o setor da responsabilidade;
- o modelo de responsáveis fica menor, sem coordenador, principal, substituto
  ou flags individuais de capacidade.

## ADR-035 — Associação de responsável contida pelo setor e pelo papel

### Estado

Aceita em 2026-07-29 no incremento vertical de responsáveis da Fase 3.
Parcialmente substituída em 2026-07-30 pela ADR-044: o vínculo continua sendo
necessário para usuários funcionais, mas SuperAdmin possui autoridade global
sem vínculo artificial.

### Decisão

Modelar cada responsabilidade como uma associação única de usuário, setor e
chave de escopo, com:

- escopo `GLOBAL`, `COMPANY` ou `BRANCH`;
- validade iniciada em instante explícito e término opcional exclusivo;
- versão otimista;
- atribuição, atualização e revogação com ator e data;
- revogação lógica, sem `DELETE`;
- auditoria antes/depois no log append-only do setor.

Uma associação somente pode ser criada, atualizada ou reativada quando:

1. usuário e setor estão ativos;
2. o escopo cabe na cobertura configurada do setor;
3. existe uma atribuição ativa e não revogada de `RESPONSAVEL_SETOR`;
4. uma única atribuição do papel cobre todo o escopo e período da
   responsabilidade.

O service bloqueia setor, usuário, atribuições do papel e associação em ordem
determinística. A identidade usuário + setor + escopo não muda: ajuste de
setor ou escopo exige revogar e associar novamente. Repetir uma associação
idêntica é idempotente; reativar reutiliza a mesma linha e incrementa a versão.

### Autorização

Para usuários funcionais, a autoridade operacional exige uma responsabilidade
vigente para o setor e contexto organizacional. A revogação ou expiração retira
essa autoridade. SuperAdmin não se torna responsável funcional, mas satisfaz o
limite por autoridade global conforme a ADR-044.

### Consequências

- `SGPD_SECTOR_RESPONSIBLE` é a única tabela aditiva deste incremento;
- candidatos da SPA são contas ativas com o papel fixo vigente;
- o mesmo `manage_sectors` global administra setores e responsáveis;
- nenhuma referência do Senior é replicada e nenhum objeto `VETORH` é
  alterado;
- fan-out de notificações e first-writer-wins permanecem nos incrementos
  próprios de workflow e notificações.

## ADR-036 — Papel DP cumulativo e separado da responsabilidade de setor

### Estado

Aceita em 2026-07-29 por decisão explícita do responsável funcional.
Parcialmente substituída em 2026-07-30 pela ADR-044: `DP` continua sendo o
papel explícito dos usuários funcionais, mas SuperAdmin passa a satisfazer o
limite de autorização por autoridade global.

### Contexto

`RESPONSAVEL_SETOR` identifica quem executa as tarefas de um ou mais setores.
O ciclo demissional também precisa identificar quem coordena o processo como
um todo: abertura, acompanhamento, análise, liberação, cancelamento e
encerramento. Essa autoridade não é equivalente a executar a validação do
setor Departamento Pessoal.

Uma mesma pessoa poderá exercer as duas funções. Portanto, derivar `DP` da
associação ao setor impediria representar de modo explícito tanto a acumulação
quanto a separação dessas responsabilidades.

### Decisão

Manter um catálogo funcional fixo com dois códigos acumuláveis:

- `RESPONSAVEL_SETOR`: pré-requisito para associação e atuação nas tarefas do
  setor;
- `DP`: coordenação do ciclo demissional no escopo organizacional atribuído.

O papel `DP`:

- possui escopo `GLOBAL`, `COMPANY` ou `BRANCH`, validade e revogação lógica;
- concede `accounts.query_senior_references` para a seleção cadastral que
  antecede a abertura;
- será exigido pelos services de abertura, acompanhamento, análise final,
  liberação, cancelamento e encerramento;
- não concede `manage_users`, `manage_roles` ou `manage_sectors`;
- não associa o usuário ao setor Departamento Pessoal;
- não é concedido por grupo AD, associação de setor ou `is_superuser`.

`has_effective_role()` centraliza a verificação explícita de código, vigência e
escopo para os futuros services do workflow. A verificação do papel não
substitui validações de estado, prontidão, segregação, concorrência e auditoria
de cada transição.

### Controles

- `SGPD_CK_ROLE_ACTIVE_CODE` aceita somente `DP` e
  `RESPONSAVEL_SETOR` ativos;
- `AssignRoleService` rejeita códigos fora desse catálogo;
- criação e edição dinâmica de papéis continuam indisponíveis;
- atribuição e revogação reutilizam transação e auditoria existentes;
- a mesma conta pode possuir os dois papéis no mesmo ou em diferentes escopos;
- os endpoints de workflow ainda não são criados nesta decisão.

### Consequências

- a parte de papel único da ADR-034 é substituída;
- a igualdade entre responsáveis de um mesmo setor continua inalterada;
- o registro histórico `DP` pode ser reativado sem criar papel duplicado;
- responsável pelo setor Departamento Pessoal e `DP` são conceitos
  independentes;
- a implementação concreta das transições permanece no Checkpoint 4.

## ADR-037 — Abertura transacional do processo em rascunho

### Estado

Aceita em 2026-07-29 no primeiro incremento vertical da Fase 4. Complementada
pela ADR-039 quanto à configuração do workflow e à transição de início. A
identificação do gestor imediato foi substituída pela ADR-045.

### Contexto

A abertura precisa autorizar o coordenador funcional no escopo exato do
colaborador, consultar o Senior somente para leitura, congelar os dados
cadastrais usados pelo processo e registrar a ação de forma atômica. Grupos,
templates, tarefas e as demais transições ainda não estão homologados e não
devem ser antecipados por este incremento.

A consulta ao Senior não deve permanecer dentro de uma transação Oracle do
SGPD. Ao mesmo tempo, uma revogação concorrente do papel `DP` não pode ser
ignorada entre a leitura cadastral e a gravação do processo.

### Decisão

Implementar a abertura exclusivamente pelo
`OpenOffboardingProcessService.execute()`:

- exigir `has_effective_role(actor, "DP", company_code, branch_code)` antes de
  consultar dados pessoais no Senior;
- consultar o colaborador pela chave completa empresa, filial, tipo e
  matrícula e rejeitar chave divergente ou contrato inelegível;
- abrir a transação SGPD somente depois da consulta externa;
- bloquear o ator, o gestor e as atribuições `DP` relevantes em ordem
  determinística e repetir `has_effective_role()` dentro da transação;
- criar processo `RASCUNHO`, snapshot imutável e evento
  `PROCESS_OPENED` na mesma transação;
- aceitar somente gestor local ativo e congelar nome e e-mail do gestor no
  processo;
- impedir dois processos não encerrados para a mesma chave cadastral com a
  coluna técnica única e anulável `active_employee_key`;
- não incluir CPF, nome, e-mail ou outros dados pessoais no payload da
  auditoria;
- usar UUID como identificador público enquanto a numeração funcional não
  estiver homologada;
- manter prioridade como texto controlado pelo tamanho neste incremento,
  adiando um catálogo para a homologação funcional;
- não expor listagem, detalhe, alteração ou exclusão de processo enquanto suas
  regras de acesso e transição não estiverem implementadas.

O endpoint `POST /api/v1/processes/` autentica a sessão, mas a autorização
funcional permanece no service. A SPA pode ocultar a entrada de menu para quem
não possui `DP`; isso não substitui a verificação do backend.

### Consequências

- o primeiro estado persistido é somente `RASCUNHO`;
- grupos, versões de template, tarefas, prazos derivados e início foram
  definidos posteriormente pela ADR-039; cancelamento, reabertura e
  encerramento permanecem em incrementos futuros;
- a leitura do Senior continua sem DML e sem tabela local de referência;
- falha ao criar snapshot ou auditoria desfaz toda a abertura;
- o snapshot não acompanha futuras alterações do Senior;
- a chave ativa deverá ser liberada somente por uma futura transição auditada
  de cancelamento ou encerramento;
- a janela entre consulta cadastral e persistência não permite que a revogação
  concorrente de `DP` autorize uma abertura nova.

## ADR-038 — Responsabilidade derivada e contida no agregado Setor

### Estado

Aceita em 2026-07-29 por decisão explícita do responsável funcional.
Complementada pela ADR-039 quanto ao bloqueio efetivo no início.

### Contexto

A primeira implementação exigia duas designações para a mesma capacidade:
atribuição do papel `RESPONSAVEL_SETOR` e associação do usuário ao setor. O
vínculo também copiava escopo organizacional já existente no setor e possuía
uma tela/API separada. Isso criava estados divergentes possíveis, operação
duplicada e justificativas livres que não acrescentavam evidência à auditoria.

### Decisão

- manter `DP` como único papel funcional atribuível;
- derivar `RESPONSAVEL_SETOR` de ao menos um vínculo efetivo entre usuário e
  setor, sem torná-lo permissão administrativa nem autoridade implícita de
  SuperAdmin;
- incluir zero ou mais responsáveis no payload de criação/alteração do setor e
  sincronizar setor, escopos e vínculos na mesma transação;
- identificar o vínculo por `(setor, usuário)`, persistindo início inclusivo,
  fim exclusivo, estado e trilha de atribuição/revogação;
- remover do vínculo as colunas de tipo, empresa, filial e chave de escopo; a
  autoridade herda integralmente os escopos atuais do setor;
- considerar “sem responsável” quando não houver vínculo efetivo no instante
  consultado; vínculos futuros continuam visíveis como agendados;
- permitir qualquer usuário ativo como candidato, sem papel prévio;
- remover a manutenção independente `/fe/responsaveis` e
  `/api/v1/sector-responsibilities/`;
- listar no detalhe do usuário os setores vinculados e indicar vínculos nas
  listas de usuários e de setores;
- retirar justificativa digitada de inclusões e alterações cadastrais,
  inclusive ativação/inativação, redefinição administrativa de senha,
  atribuição/revogação de `DP` e vínculo/desvínculo AD;
- preservar motivos próprios do domínio, como o motivo da abertura/cancelamento
  do processo demissional;
- manter as colunas de motivo da auditoria e preenchê-las com descrição
  operacional padronizada, ator, alvo, antes/depois e correlation ID.

As migrations revogam atribuições ativas redundantes de
`RESPONSAVEL_SETOR`, inativam o papel e validam previamente se cada escopo
copiado é exatamente igual ao escopo do setor antes de remover as colunas.

### Consequências

- esta ADR substitui a composição setor + papel da ADR-035 e as partes das
  ADR-034 e ADR-036 que tratavam `RESPONSAVEL_SETOR` como atribuível;
- `DP` continua separado e explícito; ser responsável pelo setor Departamento
  Pessoal não concede coordenação do processo;
- mudanças futuras no escopo do setor passam a valer para todos os seus
  responsáveis sem atualização redundante;
- a lista enviada no `PATCH` é o estado desejado completo: omitir vínculo ativo
  causa revogação lógica auditada;
- processos não iniciam quando um setor obrigatório estiver sem responsável
  efetivo; a validação foi implementada pelo service de início da ADR-039;
- a migração é deliberadamente bloqueante quando encontra duplicidade
  `(setor, usuário)` ou divergência entre escopo copiado e escopo do setor,
  evitando ampliação silenciosa de autoridade.

## ADR-039 — Configuração versionada e início idempotente do rascunho

### Estado

Aceita e implementada em 2026-07-29. As migrations
`templates_engine.0001` e `offboarding.0002` foram aplicadas posteriormente no
Oracle DEV. A cardinalidade entre template e setor foi substituída pela
ADR-040.

### Contexto

O processo em `RASCUNHO` precisa selecionar conjuntos funcionais revisáveis,
resolver os setores participantes e gerar tarefas sem depender de configuração
mutável. O início também precisa resistir a retry HTTP, dupla submissão,
alteração concorrente do rascunho e revogação concorrente da autoridade `DP`.

O Senior HCM já foi consultado na abertura e o snapshot resultante é a fonte
histórica do processo. Reconsultá-lo no início ampliaria a janela de falha e
poderia misturar versões cadastrais.

### Decisão

- separar cabeçalhos estáveis de template e grupo de suas versões;
- permitir correções auditadas enquanto a versão estiver em `DRAFT`; depois da
  publicação, qualquer mudança exige a criação de nova versão em `DRAFT`, e a
  versão vigente anterior não é alterada;
- associar cada setor de uma versão de grupo a uma versão exata e publicada de
  template; pela ADR-040, o template não pertence ao setor e pode ser
  reutilizado;
- permitir que `DP` vigente no escopo do processo selecione somente versões
  atualmente publicadas; o processo preserva as versões selecionadas;
- restringir a aplicabilidade automática deste incremento ao escopo
  organizacional do setor; regras por cargo, centro de custo ou outros campos
  do snapshot permanecem fora do recorte;
- aceitar inclusões e exclusões manuais de setor pela API, sempre com motivo;
- quando grupos se sobrepõem no mesmo setor, exigir a mesma versão de template,
  combinar obrigatoriedade e bloqueio por `OR` e usar o menor prazo;
- bloquear a resolução quando grupos aplicáveis apontarem versões de template
  diferentes para o mesmo setor;
- exigir no início ao menos um grupo selecionado e ao menos um setor
  obrigatório;
- exigir setor, grupo e template ativos e válidos, além de responsável vigente
  para cada setor obrigatório no escopo do processo;
- criar uma tarefa por setor, sem proprietário individual; autorização de
  execução será derivada do vínculo vigente com o setor e de seu escopo;
- congelar na tarefa o setor, a versão do template, seus itens e as origens de
  grupo, preservando perguntas e parâmetros históricos;
- calcular o prazo inicial por `override do rascunho > grupo > template >
  setor`, a partir do instante de início, limitado pela data final do processo;
- executar seleção e início exclusivamente por services transacionais, com
  versão otimista do processo, locks ordenados, revalidação de `DP`, auditoria
  append-only e rollback integral;
- exigir `Idempotency-Key` no início. A mesma chave, ator e payload devolvem o
  resultado anterior; reutilização divergente devolve conflito;
- não consultar nem escrever no Senior durante seleção ou início.

Os endpoints mínimos são:

- `GET /api/v1/processes/{uuid}/draft/`;
- `PUT /api/v1/processes/{uuid}/draft/selection/`;
- `POST /api/v1/processes/{uuid}/start/`;
- catálogo, criação, versionamento e publicação em
  `/api/v1/workflow-config/`.

A SPA oferece criação, correção do `DRAFT` e publicação da primeira versão de
templates e grupos, além da tela de rascunho para seleção, prévia e início. A
API já suporta versões posteriores e ajustes manuais do processo, mas esses
dois editores ficam para incremento posterior.

### Controles e compatibilidade

- constraints e nomes de objetos respeitam os limites do Oracle 19c;
- as migrations deste incremento não escrevem em objetos do Senior;
- o registro idempotente é persistido na mesma transação do processo, tarefas
  e auditoria;
- conflitos de versão, chave idempotente ou configuração são explícitos e não
  produzem mutação parcial;
- nenhum grupo, template ou pergunta funcional é semeado sem homologação.

### Consequências

- processos iniciados preservam sua configuração, mesmo após novas
  publicações;
- uma alteração de responsável posterior não troca o conteúdo da tarefa, mas
  afeta quem pode atuar conforme a responsabilidade vigente;
- o início depende somente do snapshot e da configuração SGPD já persistidos;
- regras automáticas além do escopo de setor, edição manual na SPA, editor de
  versões posteriores, execução/conclusão de tarefas e demais transições
  continuam pendentes;
- rollback de código antes de uso permite reverter as migrations aditivas;
  depois de dados reais, a correção deve ser evolutiva e precedida de backup,
  sem apagar histórico.

## ADR-040 — Template neutro quanto a setor

### Estado

Aceita e implementada em 2026-07-29 por homologação funcional. Substitui a
cardinalidade exclusiva `ChecklistTemplate → ValidationSector` da ADR-039.

### Contexto

Um template representa um questionário versionado e pode ser útil para um ou
mais setores. Vinculá-lo diretamente a um único setor obrigaria duplicar
perguntas, SLAs e histórico de versões para reutilizar o mesmo conteúdo.

A versão de grupo já contém a relação entre setor e versão de template. Manter
também o setor no cabeçalho do template duplicava a informação e permitia
divergência entre as duas relações.

### Decisão

- remover `SECTOR_ID` de `SGPD_CHECKLIST_TEMPLATE`;
- manter código, nome, descrição, situação e versão vigente no cabeçalho;
- manter perguntas e SLA padrão nas versões imutáveis do template;
- associar setor e versão publicada exclusivamente em
  `SGPD_VALIDATION_GROUP_SECTOR`;
- permitir que a mesma versão seja usada por múltiplos setores no mesmo grupo
  ou em grupos distintos;
- preservar uma tarefa e um conjunto independente de respostas por setor,
  mesmo quando as tarefas compartilham a mesma versão de template;
- selecionar setor e template separadamente na SPA de grupos;
- permitir que inclusão manual de setor escolha qualquer versão vigente
  publicada de template;
- manter o conflito explícito quando dois grupos aplicáveis usam versões
  diferentes para o mesmo setor.

Não será criada uma relação muitos-para-muitos de “setores permitidos” no
template. Ela repetiria a associação do grupo e precisaria de versionamento
próprio para não alterar historicamente a aplicabilidade.

### Migration e rollback

`templates_engine.0002_make_templates_sector_neutral` remove o índice
`SGPD_IX_TPL_SECTOR`, a FK e a coluna `SECTOR_ID`. Antes da aplicação no Oracle
DEV foram confirmados zero templates, versões, grupos e regras de setor.

O SQL foi revisado e a migration aplicada com plano final vazio. A tabela
resultante preserva todas as constraints e índices restantes habilitados,
validados e válidos.

O rollback automático só é seguro enquanto não houver templates genéricos.
Depois de cadastrar dados, não existe um único setor que possa preencher a
coluna antiga; eventual retorno exigiria uma nova modelagem e migração de dados,
sem apagar versões históricas.

### Consequências

- o catálogo de templates deixa de carregar contexto organizacional;
- composição, obrigatoriedade, bloqueio e SLA específico continuam pertencendo
  à regra setor/template do grupo;
- uma publicação nova permanece única e reaproveitável, reduzindo duplicação;
- auditoria de criação de template não registra mais `sector_id`;
- nenhuma tabela ou dado do Senior HCM é consultado ou alterado.

## ADR-041 — Identificador numérico e edição controlada do rascunho de template

### Estado

Aceita e implementada em 2026-07-29 por decisão explícita do responsável
funcional. Complementa as ADR-039 e ADR-040.

### Contexto

O primeiro editor exigia um código textual arbitrário e permitia apenas criar
e publicar a primeira versão. O operador localiza templates pelo nome; portanto
o código manual não acrescentava significado funcional. Além disso, um erro
antes da primeira publicação obrigava criar outro registro, embora a versão
ainda fosse um rascunho sem uso histórico.

Versões publicadas ou aposentadas já podem estar fixadas por grupos e processos
e precisam continuar imutáveis.

### Decisão

- usar o `ID` do cabeçalho como código público numérico, gerado pelo banco;
- retirar `code` dos payloads de criação e dos formulários de template;
- pesquisar o catálogo por `name` com correspondência parcial sem diferenciar
  maiúsculas e minúsculas;
- manter a coluna física `CODE` somente como compatibilidade técnica de
  rollback, preenchida com a representação decimal do `ID` e nunca exposta
  como identificador independente;
- permitir alterar nome, descrição, SLA e conjunto ordenado de perguntas
  somente enquanto a versão estiver em `DRAFT`;
- limitar cada template a um único rascunho por vez no service;
- criar uma nova versão a partir da versão publicada antes de qualquer mudança
  histórica; a SPA clona o conteúdo vigente para o novo rascunho;
- bloquear primeiro o cabeçalho e depois suas versões e itens, em ordem
  determinística, tanto na edição quanto na publicação;
- exigir a versão otimista do cabeçalho em edição, criação de versão e
  publicação;
- substituir os itens do rascunho na mesma transação e registrar
  `TPL_DRAFT_UPDATED`; falha de validação ou auditoria desfaz cabeçalho, SLA e
  perguntas;
- manter versões `PUBLISHED` e `RETIRED`, seus itens e todos os snapshots de
  processo imutáveis.

Os contratos mínimos ficam:

- `GET /api/v1/workflow-config/templates/?q={nome}`;
- `POST /api/v1/workflow-config/templates/`;
- `PUT /api/v1/workflow-config/template-versions/{id}/`;
- `POST /api/v1/workflow-config/templates/{id}/versions/`;
- `POST /api/v1/workflow-config/template-versions/{id}/publish/`.

### Migration e rollback

`templates_engine.0003_use_numeric_template_identifier_and_edit_drafts`
torna a coluna técnica anulável para permitir o primeiro `INSERT`, quando o
`ID` ainda não existe, e normaliza todos os valores existentes em duas etapas:
primeiro `NULL`, depois a representação decimal do `ID` pela camada de
migration. Isso evita colisão transitória com códigos manuais antigos e
preserva a unicidade.

O service preenche a coluna com o `ID` na mesma transação da criação. A
reversão mantém os valores numéricos não nulos, recompõe o campo obrigatório e
não precisa reconstruir códigos arbitrários. A migration altera somente
objetos do schema SGPD e não consulta nem escreve no Senior HCM.

A migration foi aplicada no Oracle DEV com um template existente em `DRAFT`.
Seu código técnico foi normalizado de `GEN_01` para `2`, igual ao `ID`, sem
alterar nome, versão, SLA ou pergunta. Constraint, índice único e plano final
foram validados; um smoke de edição com auditoria confirmou rollback integral.

### Consequências

- o usuário reconhece e busca o template pelo nome; o número serve somente
  como referência estável;
- correções de rascunho deixam trilha de auditoria sem criar versões
  descartáveis;
- qualquer conteúdo já publicado continua exigindo uma nova versão;
- chamadas fora dos services de domínio permanecem proibidas, inclusive para
  não persistir a coluna técnica no estado transitório;
- a busca atual respeita a paginação máxima da API, sem regra de negócio no
  cliente.

## ADR-042 — Código automático para cadastros configuráveis locais

### Estado

Aceita e implementada em 2026-07-29 por decisão explícita do responsável
funcional. Generaliza a convenção da ADR-041.

### Contexto

Setores, grupos e perguntas ainda exigiam códigos textuais arbitrários, embora
templates já usassem o identificador gerado pelo banco. Esses valores não
possuíam regra funcional, duplicavam o `ID`, aumentavam o risco de colisão e
obrigavam o operador a inventar uma chave técnica.

Nem todo campo chamado código é local: empresa, filial, tipo de colaborador e
demais chaves do Senior são referências externas; `DP` e outros códigos
declarados pelo domínio são contratos fixos.

### Decisão

- usar o `ID` como código público numérico de setor, template, grupo e pergunta;
- remover `code` dos comandos, serializers, payloads e formulários de criação;
- persistir a representação decimal do `ID` na coluna técnica `CODE`, na mesma
  transação que cria o agregado;
- não copiar o código de uma pergunta ao clonar ou substituir itens: cada novo
  registro recebe seu novo `ID`;
- manter versões publicadas/aposentadas e snapshots de processo imutáveis;
- ordenar catálogos por nome e/ou chave numérica, nunca pela representação
  textual do número;
- não aplicar a convenção a referências externas do Senior, papéis funcionais,
  tipos de evento, estados, chaves de escopo ou códigos de erro da API.

### Migration e rollback

`sectors.0004_use_automatic_sector_code` e
`templates_engine.0004_use_automatic_group_and_question_codes` tornam as
colunas técnicas anuláveis somente para o `INSERT` transitório. Cada migration
normaliza valores legados em duas etapas: primeiro `NULL`, depois o `ID`
decimal. Isso evita colisões temporárias sob as constraints únicas.

O rollback recompõe o schema anterior mantendo os valores numéricos válidos;
ele não tenta reconstruir códigos arbitrários antigos, porque eles deixam de
ter semântica funcional. As migrations alteram somente tabelas do owner `SGPD`
e não consultam nem escrevem no Senior HCM.

### Consequências

- o operador informa nomes, perguntas e regras, sem inventar chaves técnicas;
- APIs continuam devolvendo `code` como referência compatível, agora numérica;
- acesso de escrita direto ao ORM continua proibido, pois a coluna permanece
  nula durante o primeiro `INSERT` e deve ser completada pelo service;
- snapshots históricos preservam os códigos capturados no início do processo;
- os números são estáveis, mas não necessariamente contíguos, pois sequências
  Oracle não são revertidas junto com transações;
- qualquer novo cadastro configurável local que proponha código manual deve
  justificar a exceção em ADR.

## ADR-043 — Execução concorrente da tarefa e resposta JSON compatível com Oracle

### Estado

Aceita e implementada em 2026-07-29. A restrição que excluía SuperAdmin da
autoridade sobre tarefas foi substituída em 2026-07-30 pela ADR-044; os demais
controles permanecem vigentes.

### Contexto

As tarefas já eram geradas por setor, sem proprietário individual, mas não
possuíam ciclo operacional. O incremento precisava preservar a igualdade entre
responsáveis, limitar acesso pelo escopo vigente, validar snapshots históricos
e impedir duplicação sob retry ou concorrência.

No smoke do Oracle DEV, a primeira tentativa de gravar a resposta booleana
como escalar JSON acionou `ORA-02290` na constraint `IS JSON` de
`SGPD_PROCESS_CHECKLIST_ITEM.RESPONSE`. A transação externa foi revertida e
nenhum dado permaneceu. O comportamento difere do SQLite usado nos testes
unitários e exige um contrato explícito de persistência.

### Decisão

- manter a tarefa pertencente ao setor, sem campo de responsável individual;
- para usuários funcionais, autorizar consulta e mutação somente por vínculo
  vigente cujo escopo herdado cobre o processo; SuperAdmin satisfaz o limite
  por autoridade global, sem receber vínculo funcional implícito;
- implementar `PENDENTE → EM_ANALISE → CONCLUIDA` com locks ordenados, versão
  otimista, chave idempotente por tarefa/ação e auditoria atômica;
- exigir todas as respostas obrigatórias válidas na conclusão, sem persistir
  rascunho parcial neste incremento;
- validar tipos e opções no backend a partir do snapshot histórico;
- bloquear `FILE` e itens com evidência obrigatória até a Fase 5;
- armazenar cada resposta no documento `{"value": ...}`, compatível com a
  constraint Oracle, e remover o envelope na projeção da API;
- registrar na auditoria somente IDs e quantidade de itens respondidos, nunca
  valores ou observações;
- não promover automaticamente o estado do processo após a conclusão.

### Migration e rollback

`offboarding.0003_alter_processauditevent_event_type_and_more` altera somente
o estado conhecido pelo Django para incluir escolhas de tarefa e evento. O SQL
Oracle direto e reverso é no-op. A migration foi registrada no Oracle DEV e o
plano final ficou vazio.

O smoke integrado abriu e iniciou um processo, iniciou e concluiu uma tarefa e
repetiu as três ações com as mesmas chaves. O rollback obrigatório removeu
processo, snapshot, tarefas, respostas, auditoria e idempotência. Nenhuma
tabela do Senior foi escrita.

### Consequências

- responsáveis de um mesmo setor continuam com autoridade equivalente e a
  primeira transação válida vence;
- retries idênticos não duplicam mudança nem evento; chave divergente retorna
  conflito;
- a API mantém respostas simples e não expõe o detalhe físico do Oracle;
- templates com arquivo/evidência não podem ser concluídos até o módulo
  correspondente existir;
- prontidão, pendências, painel do DP e estados posteriores continuam fora
  deste incremento.

## ADR-044 — SuperAdmin como autoridade global explícita

### Estado

Aceita e implementada em 2026-07-30 por decisão explícita do responsável
funcional.

### Contexto

O atributo `is_superuser` já concedia todas as permissões administrativas, mas
os limites funcionais de `DP`, responsabilidade de setor e os filtros da SPA
o excluíam de abertura, leitura e execução de processos e tarefas. Isso
produzia uma conta tecnicamente administrativa que não conseguia inspecionar
ou operar toda a aplicação.

### Decisão

- definir SuperAdmin como toda conta ativa, autenticada e com
  `is_superuser=true`;
- centralizar essa premissa em `has_global_authority()`;
- permitir ao SuperAdmin acessar e executar todos os processos, tarefas,
  endpoints, services, menus e funções atuais ou futuras do SGPD;
- fazer `has_effective_role()` e `has_sector_responsibility()` aceitarem a
  autoridade global sem criar atribuição `DP` ou vínculo de setor artificiais;
- fazer consultas de tarefas devolverem todas as linhas ao SuperAdmin e manter
  os filtros por vínculo e escopo para os demais usuários;
- exibir todos os itens de navegação existentes ao SuperAdmin, ainda que o
  contexto não projete papéis funcionais artificiais;
- registrar o SuperAdmin real como ator de toda mutação e preservar a
  auditoria transacional.

### Limites

A autoridade global substitui somente verificações de permissão, papel, setor
e escopo. Ela não permite contornar:

- estado e transições do workflow;
- prontidão e decisões explícitas;
- validação de entrada e integridade;
- locks, versão otimista e idempotência;
- imutabilidade de snapshots, versões publicadas e auditoria;
- minimização de dados, restrições de evidência e logs seguros;
- a proibição de DML no Senior HCM.

A segregação de função constava desta lista até 2026-07-31, quando a ADR-048
a removeu: o SuperAdmin decide a pretensão de cobrança que ele mesmo informou,
e a auditoria registra o rompimento. Leia a ADR-048 antes de mudar qualquer
regra de segregação.

### Compatibilidade e migrations

A decisão não altera models, tabelas, constraints, grants ou dados. Não existe
migration. `DP` continua sendo o único papel atribuível e
`RESPONSAVEL_SETOR` continua sendo uma capacidade derivada para usuários
funcionais.

### Consequências

- uma conta SuperAdmin comprometida possui impacto máximo, registrado no risco
  R61;
- contas SuperAdmin devem ser poucas, ativas somente quando necessárias,
  protegidas e revisadas periodicamente;
- funcionalidades futuras devem reutilizar `has_global_authority()` no
  backend e projetar todos os seus menus para SuperAdmin;
- testes devem cobrir SuperAdmin sem papel ou vínculo, além dos casos de
  negação para usuários comuns.

## ADR-045 — Remoção do gestor imediato da abertura

### Estado

Aceita e implementada em 2026-07-30 por decisão explícita do responsável
funcional.

### Contexto

A abertura exigia selecionar uma conta SGPD como gestor imediato e copiava
identificador, nome e e-mail para o processo. O workflow vigente distribui as
validações por setores e responsáveis configurados, sem usar essa atribuição
nas tarefas, nos bloqueios ou nas transições posteriores. O campo adicionava
cadastro e validação obrigatórios sem produzir autoridade ou roteamento.

### Decisão

- remover gestor imediato do comando, serializer e payload da abertura;
- remover o endpoint e a consulta de candidatos a gestor;
- remover o seletor e todo o estado correspondente da SPA;
- retirar do processo a referência de usuário, o nome histórico e o e-mail
  histórico;
- remover `manager_user_id` do evento `PROCESS_OPENED`;
- manter inalterados o snapshot do colaborador, a autorização `DP` ou
  SuperAdmin, a releitura somente leitura do Senior, a unicidade do processo e
  a auditoria transacional;
- distribuir as validações exclusivamente pelas tarefas dos setores e seus
  responsáveis vigentes.

### Compatibilidade e migration

A migration `offboarding.0004` remove as colunas `MANAGER_ID`,
`MANAGER_NAME_SNAPSHOT` e `MANAGER_EMAIL_SNAPSHOT` e recria
`SGPD_CK_PROCESS_REQUIRED` sem essas colunas. A operação é destrutiva para os
três valores removidos e deve ser aplicada somente após confirmar que não há
processos cujo histórico precise preservá-los, além de revisar o SQL Oracle e
o plano de rollback operacional.

### Consequências

- a abertura não depende de outra conta SGPD além do ator autorizado;
- processos e respostas da API deixam de expor um bloco `manager`;
- a remoção reduz dados pessoais persistidos sem alterar a integração Senior;
- necessidades relacionadas à gestão imediata devem ser modeladas por setor,
  checklist ou responsável de setor, e não reintroduzidas como campo do
  processo sem nova decisão.

## ADR-046 — Regra de aplicabilidade como sugestão não vinculante

### Estado

Aceita e implementada em 2026-07-30. Conclui o RF-012 e a Fase 3. Complementa
a ADR-039 sem substituí-la: a seleção explícita do `DP` permanece a única
forma de fixar grupos no processo.

### Contexto

A ADR-039 restringiu a aplicabilidade automática ao escopo organizacional do
setor e deixou fora os demais atributos do snapshot. Na prática, o `DP`
precisava reconhecer manualmente, a cada processo, quais grupos publicados se
aplicavam ao colaborador — conhecimento tácito, não auditável e sujeito a
esquecimento.

O `DATA_MODEL.md` já previa `REGRA_APLICABILIDADE` com seis campos de match,
prioridade e janela de validade, mas a entidade não existia no código.

### Decisão

- criar `SGPD_GROUP_APPLICAB_RULE`, associando filtros do snapshot a um
  cabeçalho de grupo;
- comparar empresa, filial, tipo de colaborador, estrutura de cargos, cargo e
  centro de custo; campo nulo é curinga e campo preenchido exige igualdade;
- a regra **sugere**, não aplica: o rascunho pré-marca os grupos sugeridos e o
  `DP` confirma, inclui ou remove antes de salvar. Nada é persistido no
  processo sem a seleção explícita da ADR-039;
- usar união quando várias regras vigentes casam: toda regra contribui seu
  grupo e nenhuma suprime outra. `PRIORIDADE` apenas ordena a exibição;
- resolver o grupo para sua versão publicada vigente no momento da consulta; a
  regra não é versionada porque o processo já preserva a versão selecionada;
- limitar a sugestão aos grupos que também estão disponíveis pelo escopo
  organizacional do setor, evitando sugerir o que o início não resolveria;
- exigir `templates_engine.manage_workflow_configuration` para manter regras,
  com versão otimista, auditoria append-only e inativação em vez de exclusão;
- exigir que o grupo esteja ativo e publicado quando a regra estiver ativa;
- exigir a empresa quando a filial for informada, pela mesma semântica de
  `SectorScope`.

Os endpoints são `GET POST /api/v1/workflow-config/applicability-rules/` e
`PUT /api/v1/workflow-config/applicability-rules/{id}/`. O rascunho passa a
devolver `applicability_suggestion` com os grupos sugeridos e a regra de
origem de cada um.

### Alternativa descartada

“Maior prioridade vence”, em que a regra específica substituiria a geral, foi
descartada neste incremento. Como a sugestão não é vinculante, o único dano
possível é esconder do `DP` um grupo que deveria aparecer — exatamente o que a
supressão por prioridade produziria, e de forma silenciosa. A semântica de
sobreposição também exigiria decidir empates e escopo da substituição sem
nenhuma regra de exceção real cadastrada.

A troca posterior é barata: `PRIORIDADE` já existe na tabela e a mudança fica
contida no resolvedor, sem migration nem correção de dados.

### Migration e rollback

`templates_engine.0006_add_group_applicability_rules` é aditiva: cria a tabela,
a FK `PROTECT` para `SGPD_VALIDATION_GROUP`, o índice de recorte e três check
constraints (`REQ`, `WIN`, `BRA`). Também reescreve as opções de
`SGPD_WORKFLOW_CONFIG_AUDIT.EVENT_TYPE`, que no Oracle é no-op. Todos os
identificadores respeitam o limite de 30 caracteres. O rollback automático é
seguro enquanto não houver regras cadastradas.

### Consequências

- a configuração funcional deixa de depender de conhecimento tácito do `DP`;
- a sugestão é rastreável: o rascunho mostra qual regra propôs cada grupo;
- regras sem filtro algum são válidas e sugerem sempre, cobrindo o caso do
  grupo piloto único;
- nenhuma regra bloqueia, obriga ou remove grupo: bloqueio continua sendo
  atributo do setor no grupo, e o ajuste manual permanece no RF-013;
- expressões declarativas, regras por categoria ou vínculo e supressão por
  prioridade continuam fora do recorte.

## ADR-047 — Protocolo de conferência como linguagem visual de execução

### Estado

Aceita e implementada em 2026-07-30 nas telas Minhas tarefas e Processos;
estendida na mesma data a todas as telas da SPA (rascunho do processo,
abertura de processo, catálogo de workflow, auditoria, usuários,
configurações). Complementa a ADR-027 (PrimeNG e tokens) e a ADR-028
(mobile first) sem substituí-las.

### Contexto

A identidade do SGPD — grafite e verdigris, "a cor do item conferido", os
tokens `--status-*` e as fontes Kanit/DM Sans/JetBrains Mono — existia em
`styles.scss`, mas as telas de execução não a exerciam: tudo era caixa cinza
dentro de caixa cinza, o status chegava ao usuário como enum cru
(`EM_ANALISE`, `NAO_BLOQUEANTE`), a fonte mono nunca era usada e o checklist,
artefato central do domínio, parecia um formulário genérico. Tarefa concluída
exibia controles desabilitados vazios em vez da resposta registrada.

### Decisão

O vocabulário visual das telas de execução é o protocolo de conferência,
compartilhado em `frontend/src/styles/_conferencia.scss` e consumido por
`@use` em cada folha de componente (mesma convenção de `_listagem.scss`):

- **grupos são seções, não caixas**: cabeçalho com ícone, título display,
  régua inferior em verdigris translúcido e total em mono (`.grupo__*`);
- **estado sai em chip sobre os tokens `--status-*`** (`.chip--pending`,
  `--review`, `--released`, `--blocked`, `--canceled`), sempre com rótulo
  legível; enum cru nunca chega ao usuário;
- **dado de registro em mono** (`.registro`): matrícula, códigos de empresa e
  filial, template, versões, datas de trilha;
- **trilho de conferência**: itens verificáveis correm sobre um fio com um nó
  quadrado por item; o nó preenche em verdigris com ✓ quando o item está
  conferido — resposta dada na sessão ou registrada na conclusão. No
  checklist da tarefa, o nó acompanha `respostas()`/`answered_at`; no
  processo expandido, a tarefa de setor concluída;
- **registro em vez de formulário morto**: tela concluída mostra a resposta
  registrada em texto (mono), não controles desabilitados;
- **fato mais grave na estrutura**: o nível de bloqueio da pendência colore a
  borda esquerda do cartão (bloqueante em `--status-blocked-color`).

`p-tag` deixa de ser usado para status de domínio nessas telas; o chip do
parcial é o único desenho de status.

### Alternativa descartada

Estilos globais em `styles.scss` foram descartados: o parcial por `@use`
segue a convenção de `_listagem.scss`, mantém o custo no chunk de quem usa e
não vaza desenho para telas administrativas que têm padrão próprio.

### Consequências

- tela de execução nova deve consumir `_conferencia.scss` em vez de redesenhar
  grupo, chip ou registro; desvio do vocabulário exige nova ADR;
- os mapas de rótulo (status, categoria, nível de bloqueio) vivem no
  componente; enum novo exige rótulo novo no mesmo incremento;
- o CSS do parcial duplica por chunk lazy que o usa — aceito pelo tamanho
  (~2 kB) e pela ausência de estado global;
- o cabeçalho de página (`.pagina-cabecalho`, `.pagina-acoes` e o selo de
  domínio `.pagina-selo`) é vocabulário global em `styles.scss`, ao lado de
  `.page-title`/`.page-lead`: toda tela abre com selo, título e lead;
- `p-tag` saiu de todas as telas; o chip do parcial é o único desenho de
  status de domínio na SPA.

## ADR-048 — Segregação de função nos valores, com SuperAdmin sem barreira

### Estado

Aceita em 2026-07-31 por decisão explícita do responsável funcional.
Implementada nos services de valor da Fase 6; API e SPA seguem nas fatias
seguintes.

### Contexto

A Fase 6 introduz a pretensão de cobrança. Diferente das demais mutações do
SGPD, um valor aprovado vira desconto na rescisão de uma pessoa — o efeito
recai sobre quem não opera o sistema e não pode conferir o registro. A ADR-009
já reduzia esse risco tratando valor como solicitação de análise, mas não dizia
quem analisa nem quem aprova.

Duas normas vigentes afirmavam que a autoridade global não dispensa
segregação: `CONTEXT.md`, entre os invariantes, e a ADR-044, entre os Limites.
Nenhuma das duas foi escrita diante de um caso concreto de segregação — não
havia nenhum no sistema até aqui.

### Decisão

Analisar e decidir valor exigem `DP` vigente no escopo do processo ou
autoridade global. Responsabilidade de setor autoriza informar e contestar,
não apurar nem decidir.

Quem informou o valor não decide a própria pretensão. Para usuário funcional
essa barra é absoluta e não há caminho de exceção.

**O SuperAdmin não encontra barreira**: ele decide a pretensão que ele mesmo
informou, sem confirmação adicional, sem etapa extra e sem depender de um
segundo usuário. Quando isso acontece, `segregation_override` fica gravado na
decisão append-only e no evento de auditoria, distinguindo permanentemente a
decisão sobre valor de terceiro da decisão sobre o próprio lançamento.

### Decisões substituídas

- ADR-044 §Limites deixa de valer integralmente: a autoridade global continua
  sem contornar estado, prontidão, validação, locks, idempotência,
  imutabilidade e auditoria, mas passa a contornar a segregação de função;
- o invariante correspondente de `CONTEXT.md` foi reescrito para remeter a esta
  ADR.

### Alternativas descartadas

Exigir dois usuários sempre, inclusive SuperAdmin, foi a recomendação técnica e
foi descartada por decisão do responsável funcional: no DEV único ela travaria
a homologação da fase com o operador existente.

Uma confirmação explícita no request (`confirm_self_approval`) foi desenhada
como rede contra autoaprovação por distração e também descartada, por
contrariar a orientação de que o SuperAdmin não deve encontrar etapa extra.

Um gate por settings, ligado só em DEV, foi descartado porque o ambiente é DEV
único e sem CI/CD: o gate estaria sempre ligado e daria falsa impressão de
controle.

### Consequências

- uma conta SuperAdmin comprometida passa a poder lançar e aprovar cobrança
  contra o colaborador sem segundo par de olhos; é extensão do risco R61 e tem
  registro próprio no `RISK_REGISTER.md`;
- a trilha é a única evidência do rompimento, o que torna a imutabilidade da
  auditoria e das decisões condição da própria decisão — nenhuma delas pode ser
  relaxada sem revisar esta ADR;
- a consolidação de valores deve poder separar decisões com
  `segregation_override` para conferência posterior;
- se a operação sair do DEV único para um ambiente com segregação exigida por
  Jurídico ou Segurança da Informação, esta ADR precisa ser revista antes, não
  depois.

## ADR-049 — Outbox no Oracle em vez de broker para notificações

### Estado

Aceita em 2026-07-31 por decisão explícita do responsável funcional, ao abrir a
Fase 7. Implementada a partir da fatia 1 da fase.

### Contexto

A Fase 7 precisa enviar lembretes, avisos de atraso e escaladas por e-mail, com
painel de falhas e reprocessamento (RF-027, RF-028, R07). O roadmap previa
Redis em container com fila de e-mail, e a ADR-015 autoriza subir Redis quando
uma funcionalidade exigir cache, fila ou lock distribuído.

Ao desenhar a fase, três exigências apareceram antes do transporte:

1. o painel de falhas e o reprocessamento exigem registro **durável** por
   mensagem, com tentativa, erro e resultado — um broker não guarda esse
   histórico;
2. a varredura de prazos é periódica e precisa ser idempotente: varrer o mesmo
   marco duas vezes não pode gerar dois e-mails, e a garantia natural disso é
   uma chave única no banco;
3. a mensagem nasce de uma mudança de domínio que já está numa transação
   Oracle; publicá-la num broker fora dessa transação abre a janela clássica em
   que o domínio confirma e a mensagem se perde, ou a mensagem sai e o domínio
   é revertido.

Um broker satisfaz nenhuma das três sozinho: em todos os desenhos avaliados a
tabela de outbox continuava necessária.

### Decisão

A fila de notificações é uma tabela do schema SGPD — `SGPD_NOTIFICATION` —
gravada na **mesma transação** do fato que a origina. O envio acontece depois,
fora da requisição, por comando `manage.py` acionado pelo agendador do sistema
operacional no DEV. Cada tentativa de entrega é uma linha append-only em
`SGPD_NOTIFICATION_ATTEMPT`.

Redis, broker, worker e scheduler dedicados **não** entram na Fase 7. Nenhuma
dependência nova é adicionada ao projeto.

### Decisões substituídas

- o item “Redis em container” e “fila de e-mail” da Fase 7 do `ROADMAP.md` deixa
  de valer como entrega desta fase;
- a ADR-015 permanece vigente e não é contrariada: ela condiciona o Redis a uma
  funcionalidade que o exija, e esta não exige. A ADR-010 também permanece — o
  processamento continua assíncrono em relação à requisição, apenas sem broker.

### Alternativas descartadas

Redis com Celery e Celery Beat: dois processos de runtime a mais, duas
dependências novas e um Compose a manter, num DEV único, sem CI/CD e sem
supervisor — e ainda assim com o outbox no Oracle para o painel de falhas. O
custo operacional não se pagava no volume desta fase.

Django-Q2 com broker ORM: entrega worker e scheduler sem Redis, mas traz
dependência, tabelas próprias fora do padrão de services e auditoria do projeto
e comportamento não homologado sobre `python-oracledb` Thick.

### Consequências

- a periodicidade do envio passa a depender do agendador do sistema
  operacional: um agendamento ausente ou parado significa silêncio, não erro
  visível. O painel de falhas mostra a fila parada, mas alguém precisa olhar —
  o runbook da fase precisa registrar a verificação;
- a entrega é **ao menos uma vez**: se o processo morrer entre o envio SMTP e a
  confirmação no banco, a mensagem fica em `ENVIANDO` e uma reabertura pode
  duplicar o e-mail. Duplicar aviso é aceitável; perder aviso não é;
- a latência é a do intervalo de varredura, não a de um broker. Para lembrete,
  atraso e escalada isso é irrelevante — nenhum desses marcos é sensível a
  minutos;
- volume alto de notificações passa a ser carga no Oracle. Enquanto a fila for
  medida em dezenas por dia, o custo é desprezível; se a operação crescer, a
  troca do transporte é local ao despachante e não toca o domínio;
- a condição de qualquer check constraint sobre coluna anulável do outbox
  precisa decidir o caso ausente explicitamente, pelo motivo registrado na
  homologação da Fase 6: no Oracle `full_clean()` não envolve a condição em
  `Coalesce(..., True)`.

## ADR-050 — Configuração de e-mail na central, com o `.env` como baseline

### Estado

Aceita em 2026-07-31 por decisão explícita do responsável funcional, entre a
Fase 7 e a Fase 8. Implementada no módulo `E-mail e notificações` da central.

### Contexto

A ADR-031 criou a central técnica em `/fe/configuracoes` e a aplicou ao LDAP:
singleton no schema SGPD, versão otimista, segredo cifrado, `.env` como baseline
e configuração montada por uso, sem reinício. O card `E-mail e notificações`
existia desde então marcado como “Em breve”.

A Fase 7 tornou o e-mail operacional e expôs o custo de a configuração viver só
no `.env`: mudar remetente, servidor, ritmo da fila ou os marcos de lembrete
exigia acesso ao host e reinício do processo. A homologação terminou com uma
pendência exatamente desse tipo — `SGPD_BASE_URL` vazio fez os links das
mensagens saírem relativos.

### Decisão

Aplicar ao e-mail a mesma arquitetura da ADR-031. O singleton
`SGPD_EMAIL_CONFIG` passa a ser a fonte efetiva de:

- transporte SMTP: servidor, porta, TLS, usuário, senha e timeout;
- identidade das mensagens: remetente padrão e URL base dos links;
- ritmo da fila: tentativas, tamanho do lote e janela de reabertura;
- marcos de lembrete e escalada de `WORKFLOWS.md` §7.

O `EMAIL_BACKEND` do Django passa a ser `ConfiguredEmailBackend`, que lê a
configuração vigente a cada envio. As variáveis do `.env` permanecem como
baseline do primeiro boot e como contingência enquanto o registro não existir;
elas não são apagadas e continuam válidas.

### Chave de envio

A central ganha um interruptor de envio. Desligado, a fila continua acumulando
em `PENDENTE` e nada é entregue: nenhuma mensagem se perde e religar despacha o
acumulado. É a forma de silenciar o sistema sem mexer no agendador do sistema
operacional nem editar arquivo no host.

### Segredos e prova

- a senha SMTP é cifrada com Fernet pela mesma derivação do `DJANGO_SECRET_KEY`
  usada no LDAP, e a rotação da chave exige regravá-la;
- a API responde apenas se existe segredo configurado, nunca o valor nem o
  ciphertext; campo em branco preserva a senha vigente;
- a mensagem de prova vai obrigatoriamente para o endereço da própria conta que
  pediu o teste — a central não é ferramenta de envio para terceiros — e o
  resultado fica registrado no singleton e na auditoria;
- servidor, porta, TLS e remetente entram na trilha de auditoria, porque
  redirecionar o e-mail do sistema é ato relevante; a senha nunca entra.

### Consequências

- um SuperAdmin comprometido passa a poder redirecionar todo o e-mail do sistema
  para outro servidor sem tocar no host. É extensão do risco R61 e tem registro
  próprio como R64; a auditoria é a evidência;
- a validação separa o que bloqueia do que apenas avisa: habilitar sem servidor
  ou sem remetente é recusado, enquanto ausência de URL base, ausência de TLS e
  porta fora do usual são avisos que não impedem salvar;
- o `EMAIL_BACKEND` deixa de ser o backend SMTP direto. Código que precise do
  transporte real deve continuar usando `get_connection()` sem fixar backend,
  para que testes sigam usando o backend de memória — fixar o SMTP faria a suíte
  abrir conexão viva com o servidor gravado na central;
- a configuração de arquivos e evidências continua no `.env` e permanece como o
  próximo módulo previsto da central.

## ADR-051 — Estado formal persistido e situação funcional calculada

### Estado

Aceita em 2026-07-31, na abertura da Fase 8. Governa prontidão, liberação,
registro de processamento, encerramento, cancelamento e reabertura.

### Contexto

O `WORKFLOWS.md` §2 descreve nove estados do processo. Cinco deles —
`EM_VALIDACAO`, `COM_PENDENCIAS`, `AGUARDANDO_REGULARIZACAO`,
`AGUARDANDO_DECISAO` e `PRONTO_PARA_ANALISE_DP` — não são atos de ninguém: são
consequências do que as tarefas, as pendências e as pretensões já registram. Só
os quatro restantes nascem de uma decisão humana explícita e datada
(`LIBERADO_PARA_RESCISAO`, `RESCISAO_PROCESSADA`, `ENCERRADO`, `CANCELADO`),
somados aos dois já implementados (`RASCUNHO`, `INICIADO`).

Persistir os cinco derivados obrigaria todo service de pendência, valor e tarefa
a travar o processo e reescrever seu `STATUS` na mesma transação — acoplamento
amplo, corrida entre setores que trabalham em paralelo (R51) e a possibilidade
permanente de o estado gravado divergir do fato que ele afirma.

### Decisão

`SGPD_OFFBOARDING_PROCESS.STATUS` guarda **somente estado formal**:

```text
RASCUNHO → INICIADO → LIBERADO_PARA_RESCISAO → RESCISAO_PROCESSADA → ENCERRADO
(RASCUNHO | INICIADO) → CANCELADO
```

A situação funcional é **calculada a cada leitura** por
`evaluate_process_readiness()`, sobre tarefas, pendências e pretensões. Ela não
é gravada, não é transição e não bloqueia nada por si: quem bloqueia é a
verificação de prontidão dentro do service de liberação, refeita sob lock no
instante do ato.

Toda transição da fase é service transacional com lock do processo, versão
otimista, `Idempotency-Key`, auditoria append-only e revalidação de autoridade
depois do lock — o mesmo desenho do início e da conclusão de tarefa.

### Autoridade

| Transição | Quem pode |
| --- | --- |
| liberar | `DP` vigente no escopo ou SuperAdmin |
| registrar processamento | `DP` vigente no escopo ou SuperAdmin |
| encerrar | `DP` vigente no escopo ou SuperAdmin |
| cancelar | `DP` vigente no escopo ou SuperAdmin |
| reabrir | **somente SuperAdmin** |

A reabertura desfaz um ato formal já concluído. A “permissão especial” do RF-032
é a autoridade global da ADR-044 — o SGPD não cria papel novo para isso, o que
contrariaria a ADR-034 e a ADR-036. O `DP` que liberou não desfaz o próprio ato
sozinho.

### Rescisão processada é declaração, não integração

O Senior HCM continua sendo a fonte oficial e o SGPD não lê nem escreve a
rescisão (ADR-020, RF-037). `RESCISAO_PROCESSADA` registra o que o `DP`
**declara** ter processado no Senior: número, data e observação. O campo é
prova de conferência humana, não espelho do Senior, e a API o identifica como
tal. Quando a integração de retorno existir, ela passa a preencher os mesmos
campos e esta ADR precisa ser revista.

### Cancelamento é terminal

Cancelar libera a chave do colaborador e cancela as tarefas ainda abertas. Não
há reabertura de cancelado: ressuscitar tarefas canceladas e disputar a chave
com um processo aberto depois seria ambiguidade sem ganho. Quem cancelou por
engano abre outro processo — a auditoria preserva os dois e nada é apagado.

### Chave do colaborador

`ACTIVE_EMPLOYEE_KEY` é liberada — passa a `NULL` — no encerramento e no
cancelamento, e só neles. É o que permite abrir um processo novo para o mesmo
colaborador. A reabertura precisa retomá-la e é recusada quando outro processo
já a tomou: a unicidade do banco é a árbitra, não a leitura prévia.

### Consequências

- a SPA e os relatórios passam a exibir duas coisas diferentes com nomes
  diferentes: o estado formal (o que foi decidido) e a situação funcional (onde
  o trabalho está). Confundi-las na interface anula a decisão;
- a prontidão é sempre recalculada: nenhuma tela pode liberar com base no que
  leu antes, porque o service refaz a verificação sob lock e pode recusar;
- consultas por situação funcional não são filtros de coluna. Enquanto o volume
  for de dezenas de processos, calcular na leitura é barato; se crescer, a saída
  é materializar a leitura, nunca gravar o estado no domínio;
- o encerramento passa a ser o marco confiável de contagem da retenção de
  evidências (`SECURITY.md` §14), que até aqui não existia;
- `SGPD_PROCESS_IDEMPOTENCY.ACTION` guarda ações curtas (`RELEASE`, `PROCESS`,
  `CLOSE`, `CANCEL`, `REOPEN`) no mesmo espaço de 30 caracteres já usado por
  `START` e pelas ações de tarefa.
