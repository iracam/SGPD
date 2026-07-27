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

Preferência:

- Active Directory/LDAP;
- TLS obrigatório quando disponível;
- grupos corporativos mapeados para papéis;
- contas locais apenas para contingência controlada;
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
- owner do banco não deve ser usuário da aplicação;
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

- contas separadas;
- grants mínimos;
- rotação de senha;
- segredo fora do código;
- backup criptografado;
- acesso restrito por rede;
- auditoria administrativa;
- conexão criptografada.

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
