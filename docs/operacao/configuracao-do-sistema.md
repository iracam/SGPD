---
titulo: Manual do SuperAdmin
subtitulo: Papéis, autenticação, e-mail, monitoramento e os atos que só a autoridade global executa.
selo: Manual operacional
publico: Quem opera uma conta SuperAdmin do SGPD (autoridade global)
versao: 1.0
data: 03/08/2026
sistema: https://sgpd.bsabioenergia.com.br
---

## O que é ser SuperAdmin

A conta SuperAdmin é a **autoridade global** do SGPD. Ela enxerga todos os
processos, todas as tarefas, todos os menus e todas as telas, sem precisar de
papel funcional nem de vínculo com setor.

É conta **técnica**, não posição funcional. Use-a para configurar o ambiente,
distribuir papéis e destravar o que ninguém mais destrava — não para conduzir o
dia a dia do processo demissional. Para isso existem os papéis: quem coordena
desligamentos deve ter *Departamento Pessoal*, mesmo que também tenha acesso
técnico.

### O que só você faz

| Ato | Onde |
| --- | --- |
| Atribuir e revogar papel | ficha do usuário, em **Usuários** |
| Configurar LDAP e o login pelo Active Directory | **Configurações → LDAP e autenticação** |
| Configurar SMTP, remetente, fila e marcos de aviso | **Configurações → E-mail e notificações** |
| Conferir se a fila de avisos está andando | **Configurações → Operação e monitoramento** |
| Reabrir um processo liberado ou encerrado | tela de encerramento do processo |

### O que a sua autoridade não dispensa

Este é o ponto mais importante do manual. Ser SuperAdmin remove a barreira de
**autorização**, e nada além disso.

> **Regra** Continuam valendo, para você exatamente como para todos: a ordem dos
> estados do processo, todas as validações de dados, a exigência de justificativa
> onde ela existe, o controle de alteração concorrente, a imutabilidade de
> snapshots e versões publicadas, e a auditoria de tudo o que você faz.

Duas consequências práticas:

- você **não** libera um processo com impedimento sem escrever a justificativa.
  A autoridade global dispensa o papel `DP_GERENTE`, não o texto;
- quando você decide uma pretensão de valor que você mesmo informou, o sistema
  aceita — e **grava na trilha que a segregação foi rompida**. É registro
  permanente, com o seu nome.

---

## A central de Configurações

O item **Configurações** aparece no menu somente para SuperAdmin, e reúne os
módulos técnicos:

| Cartão | Para que serve |
| --- | --- |
| **LDAP e autenticação** | Transporte, conta técnica de bind, bases de busca, grupo elegível, certificado da CA e testes de conexão. |
| **E-mail e notificações** | SMTP, remetente, URL base, ritmo da fila, lembretes e escaladas. |
| **Operação e monitoramento** | Estado da fila de avisos, armazenamento de evidências e retenção. Somente leitura. |
| **Processo demissional** | Atalho para **Grupos e templates**. O procedimento está no *Manual de Configuração*. |
| **Arquivos e evidências** | Marcado como *Em breve*: limites, extensões e retenção ainda vivem no ambiente, não em tela. |

Cada módulo valida e audita no servidor. Nenhuma tela “apenas grava o que você
digitou”.

---

## LDAP e autenticação

Esta tela governa duas coisas **independentes**, e confundi-las é o erro mais
comum:

| Chave | O que liga |
| --- | --- |
| **Habilitar descoberta LDAP** | A busca no diretório: importar usuário, vincular identidade, buscar grupo. Nada a ver com login. |
| **Habilitar login pelo Active Directory** | As pessoas passam a entrar no SGPD com a senha da rede. |

A terceira caixa, **Preservar contingência local de SuperAdmin**, é obrigatória
para ligar o login AD. Ela existe para um cenário concreto: o AD fica
indisponível e, sem contingência, ninguém entraria no sistema — inclusive para
desligar a integração.

### A ordem correta, e por que ela é essa

```fluxo
titulo: Ativação da autenticação pelo Active Directory
inicio: Preencha servidor, conta técnica de bind e senha
passo: Escolha o transporte — com TLS, envie e valide o certificado da CA
passo: **Salvar configuração** com o login AD ainda **desligado**
seta: agora existe configuração salva para testar
passo: **Testar conexão salva** — o sistema faz bind e lê o RootDSE
decisao: O teste passou nessa mesma configuração?
  Passou: Marque **Habilitar login pelo AD** e salve de novo
  Falhou: Corrija o que a mensagem apontou e teste outra vez
alerta: Não altere servidor, bind ou CA depois de habilitar sem testar de novo
fim: Login AD habilitado, com contingência local preservada
```

O sistema **impõe** essa ordem. Ao tentar habilitar o login, ele recusa com
mensagem específica quando:

| Mensagem | O que fazer |
| --- | --- |
| *Teste com sucesso esta mesma configuração antes de ativar o login AD.* | Salve, use **Testar conexão salva** e só então habilite. O teste vale para a configuração exata que foi testada: mudar o servidor invalida o teste anterior. |
| *A autenticação AD exige contingência local de SuperAdmin.* | Marque a terceira caixa. |
| *É necessário preservar ao menos um SuperAdmin ativo com senha local utilizável.* | Existe conta SuperAdmin ativa, mas nenhuma com senha local. Defina uma antes. |
| *Envie e valide a CA antes de ativar o login AD com TLS.* | Com TLS ligado o certificado é pré-requisito, não recomendação. |
| *O arquivo da CA não corresponde ao hash registrado.* | O arquivo mudou desde o envio. Reenvie. |
| *A configuração foi alterada por outra sessão.* | Outro SuperAdmin salvou enquanto você editava. Recarregue e refaça. |

### Os quatro cartões de estado

No alto da tela:

| Cartão | Leitura |
| --- | --- |
| **Origem efetiva** | `Schema SGPD` significa que vale o que está salvo na tela. `Ambiente` significa que ainda vale o arquivo de configuração do servidor — a tela nunca foi salva. |
| **Descoberta** | Habilitada ou não, e se o transporte é seguro. |
| **Login AD** | Habilitado ou não, e se a contingência local está preservada. |
| **Último teste** | Aprovado, Falhou ou Não executado, com a data. |

### Servidor, bind e bases

| Campo | O que informar |
| --- | --- |
| **Servidor LDAP** | Host, ou `host:porta`. **Sem** `ldap://` e sem caminho: o protocolo sai da escolha de TLS. |
| **Conta técnica — UPN ou DN** | A conta de leitura do diretório. Nunca uma conta pessoal: quando a pessoa sai, a integração cai. |
| **Senha de bind** | Enviada só para atualizar, guardada cifrada e **nunca devolvida** pela API. Campo em branco mantém a senha atual. |
| **Base de usuários** | Onde procurar pessoas. Obrigatória para habilitar o login. |
| **Base de grupos** | Onde procurar grupos. |
| **DN do grupo obrigatório** | Restringe tudo — descoberta, importação, vínculo e login — a quem pertence a este grupo. Use o botão **Buscar grupo** em vez de digitar o DN à mão. |
| **Filtro adicional revisado** | Filtro LDAP entre parênteses, por exemplo `(department=RH)`. Fora desse formato o sistema recusa. |
| **Considerar grupos aninhados** | Aceita quem pertence ao grupo por herança. |

> **Atenção** O grupo obrigatório é o controle de acesso mais forte desta tela:
> ele decide quem consegue existir e entrar no SGPD. Trocá-lo pode deixar gente
> de fora imediatamente.

Os quatro números de **Limites e timeouts** — conexão, resposta, tamanho da
página e limite de resultados — protegem a disponibilidade e a exposição da
busca. Página entre 1 e 1000, limite de resultados entre 1 e 200.

### TLS e certificado da CA

Uma única escolha de transporte vale para tudo. Desmarcar **Negociar TLS** faz a
credencial técnica e as senhas das pessoas trafegarem sem criptografia — a tela
avisa, e o aviso é literal.

O certificado aceita `.pem`, `.crt` e `.cer`, até **512 KiB**. Depois de
enviado, a tela mostra situação, arquivo, *subject*, *issuer*, validade final e o
hash SHA-256. **Revalidar certificado** confere o arquivo salvo — vale como
rotina antes do vencimento.

> **Dica** Um certificado de CA vence. Quando vencer, o login AD para de
> funcionar para todos ao mesmo tempo. Anote a *validade final* que a tela mostra
> e revalide antes disso.

---

## E-mail e notificações

O SGPD não envia nada dentro da requisição: cada aviso é gravado numa fila e
despachado depois, por um comando agendado no servidor. Esta tela governa o
transporte e o ritmo dessa fila.

### O interruptor de envio

**Habilitar envio de e-mail** desligado não perde mensagem: a fila acumula em
*Pendente* e entrega tudo quando você religar. Use isso em janela de manutenção
sem medo.

Habilitar exige servidor SMTP e remetente — sem eles a tela recusa. E se você
informar usuário SMTP, a senha passa a ser obrigatória.

### Erros e avisos são coisas diferentes

A tela separa os dois deliberadamente:

- **“A configuração precisa de ajustes”** — impede salvar. Porta fora de 1 a
  65535, remetente sem `@`, URL base que não começa com `http://` ou `https://`,
  envio habilitado sem servidor ou sem remetente;
- **“Funciona, mas vale conferir”** — apenas avisa. Sem URL base, sem TLS, porta
  fora das usuais de submissão, envio sem usuário SMTP (dependendo de relay
  anônimo autorizado).

> **Atenção** O aviso da **URL base** é o que mais atrapalha na prática: sem
> ela, o link dentro do e-mail sai relativo e o cliente de e-mail não o torna
> clicável. A mensagem chega, ninguém consegue clicar.

### Ritmo da fila

| Campo | O que decide |
| --- | --- |
| **Tentativas por mensagem** | Quantas vezes o sistema insiste antes de desistir e marcar `Falha`. |
| **Mensagens por despacho** | Quantas cada execução do agendador tenta entregar. |
| **Minutos para reabrir envio preso** | Se o processo morre entre o envio e a confirmação, a mensagem fica travada em *Em envio*; depois desse tempo ela volta para a fila. |

A entrega é **ao menos uma vez**: nessa reabertura, um aviso pode chegar
duplicado. É escolha de projeto — duplicar aviso é aceitável, perder aviso não.

### Lembretes e escaladas

Quatro marcos, em horas:

| Marco | Quem recebe |
| --- | --- |
| **Primeiro lembrete, antes do prazo** | Responsáveis vigentes do setor. |
| **Lembrete final, antes do prazo** | Os mesmos. Precisa ser mais próximo do prazo que o primeiro. |
| **Atraso crítico, após o prazo** | Responsáveis e também o setor de escalada. |
| **Alerta do processo, antes do limite** | O DP do escopo, enquanto houver tarefa em aberto. |

Mudar um marco não reescreve o passado: cada marco dispara uma vez por tarefa e
por destinatário, e o que já foi avisado não volta.

### A mensagem de prova

**Enviar mensagem de prova** usa a configuração **salva** — salve antes de
testar. A prova vai obrigatoriamente para o endereço da **sua própria conta**,
nunca para um endereço digitado, e o envio fica registrado na auditoria.

> **Importante** O e-mail de aviso do SGPD nunca carrega nome de colaborador,
> CPF, valor ou parecer. Ele diz o que fazer e onde; o dado fica no sistema,
> atrás de login. Isso é exigência de proteção de dados — não mude os templates
> para “facilitar”.

---

## Operação e monitoramento

Tela somente leitura. Ela não envia, não reprocessa e não apaga: responde uma
pergunta que nenhuma outra responde — **o ambiente está andando?**

### Fila de avisos

A fila só anda quando o agendador do sistema operacional chama os comandos de
varredura e despacho. Se o agendamento parar, nada quebra e **ninguém é avisado
de que ninguém está sendo avisado**. É exatamente esse silêncio que esta tela
rompe.

| Informação | Como ler |
| --- | --- |
| Contagem por situação | `Pendente`, `Em envio`, `Enviada`, `Falha`, `Cancelada`. |
| **Último envio** | `Nunca` num ambiente em uso é sinal claro de agendamento ausente. |
| **Pendente mais antiga** | Se for mais velha que a tolerância, algo está parado. |
| **Tolerância** | Quantos minutos de atraso o sistema aceita antes de dar o veredito. |

Com a fila parada, o veredito sobe em destaque vermelho no alto da tela. A ação
não é aqui: é conferir o agendamento no servidor, pelo runbook.

Mensagens em `Falha` se reprocessam na tela **Notificações**, que é do
Departamento Pessoal — e só a que falhou volta para a fila; reenviar uma
entregue duplicaria o e-mail.

### Armazenamento e retenção

| Indicador | O que é |
| --- | --- |
| **Evidências ativas** | Quantos arquivos existem no storage privado. |
| **Ocupação** | Quanto espaço ocupam. Evidências ficam fora do Oracle. |
| **Processos encerrados** | Base de contagem da retenção. |
| **Além de N anos** | Processos encerrados que já passaram do prazo de retenção. Fica em destaque quando é maior que zero. |

> **Nunca** Nenhuma rotina apaga arquivo de evidência. O expurgo é ato humano
> autorizado, pelo procedimento do runbook. Este indicador diz que há material
> elegível — não que ele deva sair hoje.

---

## Atribuir e revogar papéis

O caminho é **Usuários → abrir a conta → seção Papéis**. Os botões *Atribuir
papel* e *Revogar* aparecem só para você: quem administra usuários prepara a
conta, mas não distribui autoridade. Se essa permissão fosse delegável, um
administrador de contas poderia se promover a qualquer papel do sistema.

### Os cinco papéis, e o escopo de cada um

| Papel | Autoriza | Escopo aceito |
| --- | --- | --- |
| **Departamento Pessoal** | Conduzir o processo: abrir, iniciar, acompanhar, decidir valores, liberar, encerrar e cancelar. | Global, empresa ou filial |
| **Gerência do Departamento Pessoal** | Tudo do DP, mais liberar e encerrar processo **com impedimento**, sob justificativa. | Global, empresa ou filial |
| **Administração de grupos e templates** | Templates, perguntas, grupos de validação e regras de aplicabilidade. Nenhuma autoridade sobre processo. | **Somente global** |
| **Administração de setores** | Setores, escopos, prazos e responsáveis. | **Somente global** |
| **Administração de usuários** | Contas, senhas temporárias, vínculo com o AD e leitura da auditoria de contas. | **Somente global** |

Ao atribuir, escolha o escopo: **Global**, **Empresa** (informe o código) ou
**Filial** (empresa e filial). Para os três papéis administrativos a tela só
aceita Global — oferecer “administrador de setores da empresa 1” seria promessa
que a autorização não cumpre.

### O que o sistema recusa

| Mensagem | Por quê |
| --- | --- |
| *Não é possível atribuir papel a um usuário inativo.* | Ative a conta primeiro. |
| *Este papel só existe em escopo global.* | É um dos três papéis administrativos. Troque o escopo para Global. |
| *Informe a empresa do escopo do papel.* | Escopo de empresa ou filial exige o código. |

### Escolhas que valem lembrar

- **gerência do DP dispensa DP.** Quem tem a gerência já satisfaz toda
  exigência de Departamento Pessoal; atribuir os dois é redundante;
- **responsável de setor não é papel.** Vem do vínculo com o setor, cadastrado
  em **Setores**, e vale enquanto a vigência valer;
- **revogar não apaga.** A atribuição revogada continua visível no histórico da
  ficha, com quem revogou;
- **toda atribuição e revogação vai para a auditoria**, com ator, conta, papel,
  escopo e validade. É a primeira coisa que se lê numa investigação de acesso.

> **Cuidado** `DP_GERENTE` é o papel que passa por cima de impedimento de
> liberação. Atribua-o a quem responde funcionalmente por essa decisão, no
> escopo em que ela cabe — não “para facilitar” a operação de um caso travado.

---

## Reabrir um processo

Reabrir é exclusivo do SuperAdmin, na tela **Conferir encerramento do processo**.
Nem quem liberou desfaz o próprio ato: é o desenho, não uma limitação.

O que a reabertura faz:

- devolve o processo à análise e limpa as marcas formais de liberação,
  processamento e encerramento;
- devolve à análise **as tarefas concluídas que você marcar**. Sem nenhuma
  marcada, corrige apenas a marca formal, sem devolver trabalho a setor nenhum;
- retoma a vinculação do colaborador ao processo — e é **recusada** se outro
  processo já tomou aquele colaborador. Nesse caso, resolva o outro processo
  primeiro;
- exige motivo e grava o estado anterior inteiro na trilha;
- avisa por e-mail os setores cujas tarefas voltaram.

Processo **cancelado** não reabre: o cancelamento é terminal. Para o mesmo
colaborador, abra um processo novo.

---

## Dúvidas frequentes

**Habilitei o login AD e ninguém consegue entrar.**
Confira, nesta ordem: o cartão **Último teste** ainda está *Aprovado* para a
configuração atual? O certificado da CA está válido? O **grupo obrigatório**
mudou? Se precisar de saída rápida, desmarque *Habilitar login pelo Active
Directory* e salve — a contingência local existe para isso.

**Perdi o acesso do último SuperAdmin.**
O sistema impede desativar o último SuperAdmin ativo, e impede habilitar o login
AD sem uma senha local utilizável. Se ainda assim o acesso se perdeu, a saída é
o procedimento de contingência do runbook, no servidor.

**A tela mostra “Origem efetiva: Ambiente”. Está errado?**
Não. Significa que essa configuração nunca foi salva pela tela e o que vale é o
arquivo de configuração do servidor. Ao salvar, a origem passa a `Schema SGPD` e
a tela vira a fonte da verdade.

**Mudei um marco de lembrete e nada aconteceu.**
Marco já disparado não volta. A mudança vale para os próximos vencimentos.

**A fila está cheia de `Pendente` e o último envio é “Nunca”.**
O agendamento não está instalado ou não está rodando. É configuração de
servidor, pelo runbook — nenhuma tela do SGPD substitui o agendador.

**Posso apagar as mensagens antigas da fila, ou a auditoria?**
Não, e nem pela sua autoridade. Fila, auditoria, comentários de pendência e
processos encerrados são acrescentados e nunca removidos.

**Um DP pediu para eu liberar um processo travado.**
Você pode — com justificativa escrita, que fica no processo e na trilha. Antes
disso, pergunte se o certo não é a gerência do DP fazê-lo, sob o papel próprio,
ou resolver o impedimento.

---

## Em uma página

1. **Configurações → LDAP e autenticação**: preencha, salve com o login
   desligado, **Testar conexão salva** e só então habilite o login AD.
2. Com TLS, envie e valide a CA antes — e anote a validade final.
3. **Configurações → E-mail e notificações**: transporte, remetente, **URL
   base**, ritmo e marcos. Salve e **Enviar mensagem de prova**.
4. **Configurações → Operação e monitoramento**: confira *Último envio* e
   *Pendente mais antiga*. Veredito vermelho significa agendamento parado.
5. **Usuários → conta → Papéis**: atribua os cinco papéis pelo escopo correto —
   os três administrativos só em Global.
6. Reabertura de processo: só você, com motivo, escolhendo quais tarefas voltam.
   Cancelado não reabre.
7. Nada do que você faz escapa da auditoria — inclusive o que a sua autoridade
   dispensou.
