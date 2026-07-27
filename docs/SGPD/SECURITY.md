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
- vincular futuramente a conta SGPD a uma identidade do Active Directory;
- usar identificador corporativo estável e único para a vinculação;
- não criar perfis ou permissões automaticamente a partir do Senior;
- manter papéis e escopos no SGPD mesmo após a vinculação ao AD;
- desabilitar a senha local comum após ativar a autenticação AD, preservando somente contingência administrativa controlada;
- exigir TLS na integração futura com AD;
- MFA quando a infraestrutura permitir.

## 3. Autorização

Autorização deve considerar:

- papel;
- setor;
- empresa;
- filial;
- atribuição ao processo;
- sensibilidade do dado;
- estado do processo.

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

Classificação sugerida:

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

- antivírus;
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
- acesso somente por endpoint autenticado e autorizado;
- permissões restritas ao usuário da aplicação;
- backup, retenção e antivírus obrigatórios antes de usar dados reais.

## 8. Auditoria

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

Alternativas futuras:

- tabela protegida;
- trigger controlada;
- assinatura de lote;
- armazenamento externo;
- integração com SIEM.

## 10. Sessão

- cookies `HttpOnly`;
- cookies `Secure`;
- proteção CSRF;
- timeout;
- bloqueio por inatividade;
- revogação em desligamento;
- controle de dispositivos conforme política.

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
- revisão de SQL.

## 14. Retenção

A retenção deve ser definida com Jurídico, RH e Segurança da Informação.

O sistema deve suportar:

- retenção por classe;
- bloqueio legal;
- arquivamento;
- anonimização quando aplicável;
- expurgo controlado e autorizado;
- preservação da trilha necessária.
