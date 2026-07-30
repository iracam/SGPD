# Segurança, LGPD e Auditoria

## 1. Princípios

- menor privilégio;
- segregação de funções;
- rastreabilidade;
- necessidade de conhecimento;
- defesa em profundidade;
- proteção de dados pessoais;
- ausência de exclusão destrutiva de histórico;
- decisões sensíveis com dupla validação quando aplicável.

## 2. Autenticação

Estratégia:

- cadastrar todos os usuários e seus e-mails no SGPD;
- manter autenticação local enquanto o AD estiver desabilitado e para a
  contingência administrativa controlada;
- usar o model customizado `accounts.User` desde a primeira migration;
- manter e-mail único e identificador AD único e anulável;
- permitir vínculo auditado de uma conta SGPD existente ou criação local
  explícita a partir de uma identidade pesquisada no Active Directory;
- não exigir justificativa digitada na criação manual de conta local, mantendo
  o ator e um motivo operacional padronizado no evento append-only;
- usar `objectGUID`, convertido para UUID canônico, como identificador
  corporativo estável e único para a vinculação;
- exigir confirmação humana para vínculo e desvínculo, registrando identidade,
  ator e motivo operacional padronizado sem texto livre;
- exigir troca da senha temporária no próximo acesso quando configurado;
- não criar perfis ou permissões automaticamente a partir do Senior;
- não criar conta implicitamente quando credenciais AD válidas forem
  apresentadas no login;
- manter o papel funcional e escopos no SGPD mesmo após a vinculação ao AD;
- bloquear o fallback para senha local de contas comuns vinculadas quando a
  autenticação AD estiver ativa;
- aplicar o mesmo bloqueio à definição, redefinição e troca de senha, tanto no
  service quanto na interface, evitando armazenar uma credencial que a política
  de login recusaria;
- preservar somente contingência administrativa de superusuário, controlada
  por configuração e testada antes da ativação;
- aplicar a mesma escolha de transporte a descoberta e autenticação;
- usar LDAPS montado automaticamente, validação do certificado e cadeia
  corporativa confiável quando TLS estiver selecionado;
- permitir LDAP simples por escolha explícita do SuperAdmin, mantendo warning
  permanente de que a credencial técnica e a senha do usuário trafegam sem
  criptografia;
- usar conta técnica AD somente leitura e nunca registrar senha, DN consultado,
  filtro preenchido ou atributos pessoais retornados;
- excluir contas desabilitadas no AD e, quando configurado, restringir
  elegibilidade por OU e grupo direto ou aninhado;
- tratar grupos AD exclusivamente como filtro de elegibilidade, nunca como
  fonte do papel, associação a setor ou permissão;
- MFA quando a infraestrutura permitir.

Descoberta e autenticação possuem chaves de ativação independentes. Isso
permite homologar transporte, bind, filtros, importação e vínculo antes de
habilitar o backend de login. Falha do AD produz erro genérico, sem enumeração
de usuário e sem fallback silencioso para senha local de conta comum
vinculada. O runbook está em `INTEGRATION_ACTIVE_DIRECTORY.md`.

Quando `LDAP_AUTHENTICATION_ENABLED=false`, uma conta vinculada pode receber
senha local para homologação controlada. Ao ativar o login AD, a API passa a
recusar novas definições e redefinições para contas comuns vinculadas; somente
o superusuário coberto por `LDAP_LOCAL_SUPERUSER_FALLBACK=true` conserva essa
capacidade.

Sem TLS, a credencial técnica e as senhas de login trafegam sem criptografia.
O system check, a central de configurações e a importação exibem alerta
permanente. Esse aviso não altera a opção administrativa nem apresenta LDAP
simples como transporte seguro.

### Administração técnica de autenticação

A central `/fe/configuracoes` e os endpoints `/api/v1/settings/` exigem
diretamente uma conta ativa com `is_superuser=true`. Essa autoridade não é uma
permissão do papel funcional: uma conta comum com permissões administrativas
diretas continua recebendo `403`.

Na configuração LDAP:

- a senha de bind nunca é devolvida pela API, auditoria ou logs;
- quando informada pela tela, é cifrada com Fernet usando chave derivada do
  `DJANGO_SECRET_KEY`; a troca dessa chave exige regravação coordenada do
  segredo;
- o certificado ou bundle de CA é limitado a 512 KiB, validado como X.509,
  exige `Basic Constraints: CA`, validade vigente e recebe hash SHA-256;
- o PEM normalizado fica em storage privado com arquivo `0600` e diretório
  `0700`, fora do WhiteNoise;
- a ativação de login AD exige probe de bind e RootDSE da mesma configuração e
  ao menos um SuperAdmin ativo com senha local utilizável; quando TLS estiver
  selecionado, exige também CA válida;
- com TLS ativo, a substituição da CA desabilita o login AD e invalida o probe
  anterior até que a nova cadeia seja testada; sem TLS, a CA não interfere no
  login nem no probe;
- o fingerprint do probe usa HMAC com chave derivada do segredo da aplicação;
  não persiste hash simples que funcione como verificador offline da senha;
- alterações usam versão otimista; atualização, upload e teste geram eventos
  append-only com motivos operacionais padronizados no servidor, sem
  justificativa digitada, segredo, filtro preenchido ou caminho privado.

A SPA autentica por sessão Django com proteção CSRF em origem única, conforme a
ADR-026:

- não há JWT, token de acesso ou credencial de longa duração no navegador;
- `localStorage` guarda apenas preferências de interface, como tema e estado da
  navegação, e nunca dados de sessão ou identidade;
- requisições com efeito colateral enviam `X-CSRFToken`;
- o endpoint de login valida CSRF explicitamente: o DRF só o exige quando já
  existe sessão, de modo que um `POST` anônimo ficaria exposto a login CSRF;
- a revogação de sessão permanece sob controle do servidor;
- o endpoint de login tem limitação de tentativas por origem anônima,
  configurável por `LOGIN_THROTTLE_RATE`, complementando o registro de falha já
  auditado;
- a resposta de login não distingue usuário inexistente, senha incorreta e conta
  inativa: todas retornam `invalid_credentials`;
- a obrigatoriedade de troca da senha temporária é preservada na API: o
  middleware devolve `403` com código próprio, a SPA conduz o usuário à tela de
  troca e a navegação direta é redirecionada para `/fe/senha`.

## 3. Autorização

Autorização deve considerar:

- papel;
- setor;
- empresa;
- filial;
- atribuição ao processo;
- sensibilidade do dado;
- estado do processo.

Os endpoints cadastrais do Senior exigem autenticação e a permissão
`query_senior_references`. A autorização considera atribuição ativa e válida
com escopo global, de empresa ou de filial. Empresas fora do escopo não são
retornadas e filtros fora do escopo recebem `403`.

Com a adoção da SPA pela ADR-025, a API é a única superfície funcional da
aplicação. A renderização não funciona como barreira auxiliar de autorização,
e disso decorrem duas obrigações:

- cada endpoint valida permissão e escopo por conta própria, sem depender do
  que o cliente exibe ou deixa de exibir;
- cada endpoint possui teste de permissão negada.

O contexto de autorização devolvido por `GET /api/v1/auth/context/` serve
apenas para orientar a navegação da SPA. Ele não concede acesso: um cliente
adulterado que exiba um item de menu indevido continua recebendo `403` do
endpoint correspondente.

Nenhum código é carregado de CDN. Componentes, ícones e fontes são empacotados
no build.

A SPA não é uma barreira de autorização: toda requisição continua sendo
validada pela API, e nenhuma listagem cadastral projeta CPF.

As permissões administrativas existentes são:

- `manage_users`;
- `manage_roles`;
- `link_ad_identity`;
- `view_account_audit`;
- `query_senior_references`;
- `manage_sectors`;
- `manage_workflow_configuration`.

O único papel funcional atribuível ativo é `DP`. `RESPONSAVEL_SETOR` é
derivado de vínculo efetivo com o setor e não concede administração técnica.
`DP` recebe apenas `query_senior_references` neste
incremento para selecionar o colaborador dentro do seu escopo; permissões
diretas são globais e permanecem disponíveis para evolução controlada.
SuperAdmin é a autoridade global explícita do SGPD. Uma conta ativa com
`is_superuser=true` acessa todos os processos, tarefas, menus, endpoints e
services, sem precisar de atribuição `DP`, vínculo de setor ou escopo. Papéis e
atribuições legados permanecem inativos ou revogados com auditoria, nunca
excluídos.

O bypass de SuperAdmin limita-se à decisão de autorização. Ele não remove:

- pré-condições e estados do workflow;
- validações de entrada e de prontidão;
- segregação e decisões explícitas exigidas pelo domínio;
- locks, versão otimista e idempotência;
- imutabilidade de snapshots e auditoria;
- minimização de dados, logs seguros e acesso somente leitura ao Senior.

`manage_sectors` exige concessão global na configuração funcional, pois um
setor e suas responsabilidades podem cobrir múltiplas empresas e filiais. A
API, o service e a visibilidade da SPA usam o mesmo identificador, mas somente
API e service autorizam a operação.

`manage_workflow_configuration` é segregada de `DP`: permite criar/publicar
templates e grupos, mas não iniciar nem liberar processo. A SPA usa a permissão
somente para visibilidade; services e endpoints repetem a autorização.

Os códigos técnicos de setor, template, grupo e pergunta não são campos de
entrada. O backend os deriva do `ID` na transação de criação, evitando
mass assignment e colisões escolhidas pelo cliente. Essa regra não transforma
nem substitui códigos oficiais recebidos do Senior.

Uma responsabilidade pode ser cadastrada para qualquer usuário ativo e herda
integralmente o escopo organizacional do setor. A autoridade operacional exige,
no instante do caso de uso, usuário, setor e vínculo ativos e dentro da
validade para usuários funcionais. SuperAdmin não recebe vínculo funcional
artificial, mas sua autoridade global satisfaz a verificação de autorização.
Escopo e validade são reavaliados no backend; ocultar controles na SPA não
substitui essa decisão.

O papel `DP` é cumulativo e independente da responsabilidade de setor. A
abertura já exige uma atribuição `DP` ativa, vigente e compatível com a
empresa/filial; acompanhamento, análise final, liberação, cancelamento e
encerramento deverão repetir o mesmo limite para usuários funcionais.
SuperAdmin não se torna `DP`, mas a autoridade global explícita satisfaz o
limite; responsável pelo setor Departamento Pessoal continua sem receber `DP`
implicitamente.

Na abertura, a API exige sessão, mas a decisão funcional permanece no service.
O service chama `has_effective_role()` antes da consulta ao Senior e novamente
dentro da transação, após lock da conta e das atribuições `DP`. Assim,
revogação e abertura concorrentes não produzem autoridade implícita para
usuários funcionais; SuperAdmin ativo é reconhecido pela mesma função. A SPA
oculta o item de menu sem o papel `DP`, exceto para SuperAdmin, mas isso é
somente orientação de navegação.

Na seleção e no início, o service revalida `DP` no escopo do processo. O início
bloqueia configuração, setores, responsabilidades e usuários em ordem
determinística, repete a autoridade sob lock e exige responsável efetivo para
cada setor obrigatório. Tarefas não copiam proprietário individual: a futura
atuação continua derivada do setor, vigência e escopo.

Em 2026-07-29, a atribuição `DP` de `victor.delgado` foi preservada no escopo
global e sem validade final. A capacidade `RESPONSAVEL_SETOR` da conta passa a
ser derivada dos vínculos vigentes, sem atribuição redundante.

Os endpoints e os services administrativos validam autorização. A checagem no
service preserva o limite de segurança quando o caso de uso for chamado por
outro endpoint ou comando. A desativação de contas bloqueia os
superusuários ativos em ordem determinística e impede transacionalmente a
remoção do último superusuário ativo.

No cadastro manual, a designação inicial de `DP` é opcional.
Quando solicitada, o mesmo caso de uso exige `manage_users` e `manage_roles`,
cria a conta e a atribuição na mesma transação e registra separadamente
`USER_CREATED` e `ROLE_ASSIGNED`. Falha de autorização, papel, escopo ou
auditoria desfaz toda a criação; a SPA não exibe os campos de papel a quem não
possui `manage_roles`.

Criação e edição de outros papéis não possuem API nem interface, e o model
impede outro código ativo. Criação, reativação, atualização e revogação de
atribuições de `DP` não recebem justificativa livre do cliente. Os eventos
registram ator, usuário, papel, escopo, validade e motivo operacional
padronizado pelo servidor.

Além da auditoria de sucesso, a borda HTTP registra o recebimento e a conclusão
da designação em log JSON. Somente IDs técnicos, escopo, resultado e correlation
ID são permitidos; corpo da requisição, nomes, logins, e-mails e credenciais
permanecem fora do log.

Exemplos:

- responsável vê somente tarefas dos setores e escopos aos quais foi
  explicitamente associado;
- usuário com `DP` vigente executa as ações de coordenação do processo dentro
  do escopo, independentemente de associação ao setor Departamento Pessoal;
- responsável pelo setor Departamento Pessoal executa as tarefas desse setor,
  mas só coordena o processo quando também possui `DP`;
- responsáveis do Financeiro tratam valores conforme o caso de uso;
- responsáveis de Medicina do Trabalho veem somente os dados clínicos
  estritamente necessários;
- múltiplos responsáveis de um setor têm a mesma autoridade; a primeira ação
  válida vence e as demais não duplicam efeitos.

Na API de tarefas, listagem e detalhe devolvem `404` para tarefa fora da
responsabilidade vigente e do escopo herdado do usuário funcional. SuperAdmin
lista e acessa todas as tarefas. A mutação repete sob locks a responsabilidade
ou a autoridade global; os eventos registram o SuperAdmin como ator e mantêm
apenas IDs dos itens respondidos e quantidade, nunca o conteúdo das respostas
ou observações.

## 4. Segregação

- quem informa um valor não deve necessariamente aprová-lo;
- quem administra templates não deve liberar processos;
- no DEV, o owner `SGPD` é o usuário da aplicação por exceção registrada; o owner `VETORH` permanece proibido;
- operadores não devem apagar auditoria;
- evidências sensíveis devem ter acesso restrito.

## 5. Dados pessoais

Classificação preliminar, ainda não homologada. A definição formal de dados
sensíveis foi postergada por decisão do projeto em 2026-07-28.

### Dados cadastrais

- nome;
- matrícula;
- empresa;
- filial;
- cargo;
- centro de custo;
- e-mail.

### Dados sensíveis ou restritos

- documentos médicos;
- justificativas disciplinares;
- parecer jurídico;
- dados financeiros;
- CPF completo;
- evidências pessoais.

## 6. LGPD

O sistema deverá:

- limitar coleta;
- registrar finalidade;
- restringir acesso;
- definir retenção;
- permitir auditoria de acesso;
- evitar exposição desnecessária;
- mascarar dados;
- controlar download de evidências;
- registrar base operacional definida pela organização.

## 7. Evidências

Cada arquivo deverá possuir:

- UUID;
- nome original;
- nome armazenado;
- MIME type;
- tamanho;
- hash SHA-256;
- usuário;
- data e hora;
- classificação;
- vínculo com processo;
- storage seguro.

Recomendações:

- bloqueio de extensões perigosas;
- limite de tamanho;
- nome aleatório;
- diretório não público;
- download autorizado;
- logs de acesso.

### Storage no DEV

- filesystem local privado em caminho configurado por `EVIDENCE_STORAGE_PATH`;
- diretório inicial `media/evidence`;
- nunca servir pelo WhiteNoise;
- acesso somente por endpoint autenticado e autorizado.

Controles implementados na Fase 5:

- limite padrão de 10 MiB, configurável por `EVIDENCE_MAX_UPLOAD_BYTES`;
- somente PDF, PNG e JPEG, com validação coerente de extensão, MIME type e
  assinatura inicial;
- SHA-256 calculado em streaming, nome armazenado aleatório e permissões
  `0600/0700`;
- nenhuma projeção do caminho ou nome privado pela API;
- upload somente em tarefa `EM_ANALISE`, com versão, lock, chave idempotente,
  auditoria e remoção compensatória do arquivo se a transação falhar;
- download somente por endpoint autenticado, autorizado por responsabilidade
  setorial, `DP` no escopo ou SuperAdmin, com evento de auditoria por acesso;
- item `FILE` ou com evidência obrigatória só permite concluir a tarefa quando
  possui evidência ativa.

Certificados de integração não usam o storage de evidências. Eles ficam em
`SYSTEM_CONFIGURATION_STORAGE_PATH`, também privado e não servido pelo
WhiteNoise.

## 8. Auditoria

A política ampla de auditoria foi postergada por decisão do projeto em
2026-07-28. A trilha técnica já implementada para autenticação e administração
de contas permanece obrigatória.

Eventos mínimos:

- login;
- logout;
- falha de autenticação;
- abertura;
- início;
- alteração de grupo;
- inclusão ou remoção de setor;
- resposta de checklist;
- criação de pendência;
- alteração de pendência;
- upload;
- download de evidência;
- alteração de valor;
- decisão;
- liberação;
- cancelamento;
- reabertura;
- integração;
- alteração de permissões.

A abertura implementada gera `PROCESS_OPENED` na mesma transação do processo e
do snapshot. O evento contém IDs técnicos, chaves organizacionais, datas,
prioridade, estado e correlation ID; nome, e-mail e CPF não são copiados para
o JSON de auditoria.

A seleção gera `DRAFT_SELECTION_UPDATED`, incluindo IDs de versões e
justificativas de ajuste. O início gera `PROCESS_STARTED` com contagens, IDs de
versões e hash da chave idempotente, nunca a chave original. Falha de qualquer
evento desfaz a operação funcional correspondente.

## 9. Imutabilidade

A auditoria deve ser append-only para usuários comuns.

A administração operacional de contas não usa o Django Admin para escrita. O
admin expõe os registros apenas para diagnóstico; criação, alteração,
revogação e vínculo AD passam por services transacionais que geram eventos.
Os eventos rejeitam alteração e exclusão por instância e também
`QuerySet.update()` e `QuerySet.delete()`.

A auditoria funcional de setores e responsáveis segue a mesma propriedade
append-only. Criação, alteração, ativação, inativação, associação, atualização
de validade e revogação registram ator, motivo operacional padronizado,
correlation ID e estados anterior/posterior. Setores e responsabilidades não
possuem endpoint de exclusão; os models rejeitam exclusão física e a
responsabilidade é revogada logicamente.

Configurações de workflow publicadas e perguntas rejeitam mutação/exclusão; a
auditoria `SGPD_WORKFLOW_CONFIG_AUDIT` também é append-only. Os snapshots de
tarefa preservam pergunta e configuração sem depender da versão vigente.
Rascunhos de template e grupo só podem ser substituídos pelos services
autorizados, sob lock, versão otimista e evento de auditoria na mesma transação.

Alternativas futuras:

- tabela protegida;
- trigger controlada;
- assinatura de lote;
- armazenamento externo;
- integração com SIEM.

## 10. Sessão

Controles implementados:

- cookies `HttpOnly`;
- flags `Secure` configuráveis por ambiente e desabilitadas no DEV HTTP local;
- proteção CSRF, também nas requisições da SPA;
- `SameSite` compatível com a origem única exigida pela ADR-026;
- revogação explícita no logout.

Controles que dependem de política corporativa ou do workflow:

- timeout e bloqueio por inatividade;
- revogação automática em desligamento;
- controle de dispositivos.

A aplicação e a API precisam permanecer na mesma origem. A introdução futura de
proxy reverso, de outro domínio para o frontend ou de um ambiente HML/PRD
reabre a ADR-026 junto com a ADR-014.

## 11. Logs

Não registrar em log:

- senhas;
- tokens;
- CPF completo;
- conteúdo de documentos;
- dados médicos;
- segredos;
- strings de conexão.

Nos eventos operacionais de contas, a projeção permitida limita-se a tipo do
evento, IDs do ator, usuário, papel e atribuição, escopo, resultado e indicação
booleana de papel inicial.

## 12. Banco

- conta única `SGPD` para runtime e migrations no DEV, conforme risco aceito na ADR-022;
- `CREATE TABLE` concedido diretamente ao `SGPD`, sem `ADMIN OPTION`;
- `CREATE SEQUENCE` concedido diretamente ao `SGPD`, sem `ADMIN OPTION`,
  porque as chaves `IDENTITY` do Django usam geradores internos de sequência;
- quota finita de 500 MB em `PIMS_DATA`, sem `UNLIMITED TABLESPACE`;
- grants externos mínimos, especialmente nos objetos `VETORH`;
- rotação de senha;
- segredo fora do código;
- backup criptografado;
- acesso restrito por rede;
- auditoria administrativa;
- conexão criptografada.

## 12.1 Secrets no DEV

- credenciais ficam somente no `.env` ignorado pelo Git;
- usuários individuais seguem `nome.sobrenome`;
- a convenção de usuário não se aplica a senhas;
- senhas devem ser fortes, não previsíveis e rotacionáveis;
- usuário, senha e e-mail SMTP não devem aparecer no `.env.example`;
- restringir a leitura do `.env` ao usuário da aplicação.

## 12.2 Consulta direta ao Senior

- usar somente `SELECT` nos objetos `VETORH` homologados;
- qualificar todos os nomes de objetos pelo schema;
- usar bind variables e nunca interpolar filtros;
- usar somente `SGPD` no runtime DEV e nunca usar `VETORH`;
- não criar models para objetos do Senior;
- excluir CPF das listagens;
- limitar projeção, volume, paginação e tempo de consulta;
- registrar falhas e latência sem incluir SQL com dados pessoais;
- revisar grants e contrato após atualização do Senior.

## 13. Desenvolvimento seguro

- dependências atualizadas;
- análise estática;
- secret scanning;
- proteção contra mass assignment;
- validação de upload;
- validação de autorização em services;
- testes de permissão;
- revisão de migrations;
- revisão de SQL;
- dependências de frontend fixadas em `package-lock.json` e instaladas por
  `npm ci`;
- atualização de Angular ou PrimeNG somente após revisão explícita;
- nenhum código de terceiros carregado de CDN em tempo de execução.

## 14. Retenção

A definição formal de retenção foi postergada por decisão do projeto em
2026-07-28. Quando retomada, deverá envolver Jurídico, RH e Segurança da
Informação.

O sistema deve suportar:

- retenção por classe;
- bloqueio legal;
- arquivamento;
- anonimização quando aplicável;
- expurgo controlado e autorizado;
- preservação da trilha necessária.
