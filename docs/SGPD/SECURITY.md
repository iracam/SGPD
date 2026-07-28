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
- usar autenticação local no MVP;
- usar o model customizado `accounts.User` desde a primeira migration;
- manter e-mail único e identificador AD único e anulável;
- permitir vínculo administrativo auditado da conta SGPD a uma identidade do
  Active Directory, sem ativar autenticação LDAP;
- usar identificador corporativo estável e único para a vinculação;
- exigir confirmação humana e justificativa para vínculo e desvínculo;
- exigir troca da senha temporária no próximo acesso quando configurado;
- não criar perfis ou permissões automaticamente a partir do Senior;
- manter papéis e escopos no SGPD mesmo após a vinculação ao AD;
- desabilitar a senha local comum após ativar a autenticação AD, preservando somente contingência administrativa controlada;
- exigir TLS na integração futura com AD;
- MFA quando a infraestrutura permitir.

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
  middleware devolve `403` com código próprio em vez de redirecionar, e a SPA
  conduz o usuário à tela de troca.

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

Com a adoção da SPA pela ADR-025, a API passa a ser a única superfície
funcional da aplicação. A renderização deixa de funcionar como barreira
auxiliar de autorização, e disso decorrem duas obrigações:

- cada endpoint valida permissão e escopo por conta própria, sem depender do
  que o cliente exibe ou deixa de exibir;
- cada endpoint possui teste de permissão negada.

O contexto de autorização devolvido por `GET /api/v1/auth/context/` serve
apenas para orientar a navegação da SPA. Ele não concede acesso: um cliente
adulterado que exiba um item de menu indevido continua recebendo `403` do
endpoint correspondente.

Nenhum código é carregado de CDN. Componentes, ícones e fontes são empacotados
no build, mantendo a restrição estabelecida originalmente para o HTMX.

A interface HTMX, enquanto permanecer em operação, aplica a mesma autorização
em toda requisição parcial, não confia nos valores já renderizados no navegador
e remove seleções descendentes quando o escopo anterior muda. Nenhuma listagem,
HTML ou JSON, contém CPF.

As permissões delegáveis atuais são:

- `manage_users`;
- `manage_roles`;
- `link_ad_identity`;
- `view_account_audit`;
- `query_senior_references`.

Permissões diretas são globais. Permissões provenientes de papéis respeitam o
escopo e a validade da atribuição. Superusuário é reservado ao bootstrap e à
contingência administrativa.

As views e os services administrativos validam autorização. A checagem no
service preserva o limite de segurança quando o caso de uso for chamado por
outra interface, comando ou API. A desativação de contas bloqueia os
superusuários ativos em ordem determinística e impede transacionalmente a
remoção do último superusuário ativo.

Exemplo:

- responsável do setor vê somente tarefas do próprio setor;
- DP vê todos os processos no escopo autorizado;
- auditor vê sem editar;
- Financeiro vê valores, mas não acessa documentos médicos;
- Medicina do Trabalho vê dados clínicos estritamente necessários.

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

## 9. Imutabilidade

A auditoria deve ser append-only para usuários comuns.

A administração operacional de contas não usa o Django Admin para escrita. O
admin expõe os registros apenas para diagnóstico; criação, alteração,
revogação e vínculo AD passam por services transacionais que geram eventos.
Os eventos rejeitam alteração e exclusão por instância e também
`QuerySet.update()` e `QuerySet.delete()`.

Alternativas futuras:

- tabela protegida;
- trigger controlada;
- assinatura de lote;
- armazenamento externo;
- integração com SIEM.

## 10. Sessão

- cookies `HttpOnly`;
- cookies `Secure`;
- proteção CSRF, também nas requisições da SPA;
- `SameSite` compatível com a origem única exigida pela ADR-026;
- timeout;
- bloqueio por inatividade;
- revogação em desligamento;
- controle de dispositivos conforme política.

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
- mascarar CPF nas listagens;
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
