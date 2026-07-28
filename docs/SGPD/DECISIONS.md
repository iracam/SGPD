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
`ADMIN_FUNCIONAL`.

### Consequências

- o SGPD possui autorização aplicável antes do workflow;
- papéis podem receber novas permissões quando módulos forem adicionados;
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
- o plano de execução, com sete fases e critérios de conclusão, está em
  `MIGRATION_FRONTEND_SPA.md`.

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
