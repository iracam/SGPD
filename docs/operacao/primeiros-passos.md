---
titulo: Primeiros Passos no SGPD
subtitulo: Entrar, entender o menu do seu papel, ler o Painel e cuidar da própria senha.
selo: Manual operacional
publico: Qualquer pessoa com acesso ao SGPD, em qualquer papel
versao: 1.0
data: 03/08/2026
sistema: https://sgpd.bsabioenergia.com.br
---

## Para que serve o SGPD

O SGPD — também chamado **DesligaFlow** — organiza o desligamento de um
colaborador entre o Departamento Pessoal e as áreas da empresa. Ele registra
quem verificou o quê, quando, com qual comprovante, e o que ficou pendente antes
de a rescisão ser liberada.

> **Importante** O SGPD **não** calcula rescisão, não aplica desconto e não
> altera nada no Senior. O Senior continua sendo o sistema oficial do vínculo e
> da rescisão. O SGPD organiza a conferência que acontece **antes** dela e guarda
> a prova de que ela foi feita.

Este manual vale para todo mundo e cobre só o começo: entrar, se localizar e
cuidar da própria conta. O que **você** faz no dia a dia está no manual do seu
papel — a última seção diz qual é o seu.

---

## Entrar no sistema

O endereço é **https://sgpd.bsabioenergia.com.br**, pelo navegador. Funciona em
computador, tablet e celular; em telas estreitas o menu fica no ícone de três
traços, no alto.

Na tela de entrada, informe **Usuário** e **Senha**:

- se o login pelo Active Directory estiver ativo no ambiente, use **o mesmo
  usuário e senha da rede** — o mesmo do computador e do e-mail;
- caso contrário, use o login e a **senha temporária** que a administração de
  usuários lhe passou.

Não existe autocadastro e não existe “esqueci minha senha” automático. Sem
acesso, o caminho é pedir a quem administra usuários.

> **Cuidado** Ninguém do SGPD pede sua senha por e-mail, telefone ou mensagem.
> Um pedido desses é golpe, mesmo que pareça vir da TI.

### Quando a senha é temporária

Conta criada com senha temporária cai direto em **Minha senha** e não sai de lá
até a troca. Não é travamento: é a regra, e ela vale também para a API — não há
como desviar dela por outro caminho.

---

## Minha senha

O botão **Minha senha** fica nas ações do rodapé do menu, junto de *Tema* e
*Sair*.

Informe a **senha atual**, a **nova senha** e a **confirmação**. A nova senha
precisa passar pelas regras do sistema:

| Regra | Detalhe |
| --- | --- |
| Tamanho | Pelo menos **8 caracteres**. |
| Não parecida com você | Não pode se parecer com o seu login, nome ou e-mail. |
| Não pode ser comum | Senhas de listas públicas conhecidas são recusadas. |
| Não pode ser só números | `12345678` não passa. |

A tela diz exatamente qual regra falhou. Se aparecer *“A senha atual está
incorreta”*, é a senha antiga que está errada, não a nova.

Se a mensagem disser que a senha da conta é **gerenciada pelo Active
Directory**, sua senha é a da rede: troque-a pelo caminho normal da TI, não
aqui.

---

## O Painel

O **Painel** é a primeira tela depois da entrada, e é a única que todo mundo vê.
Ele calcula os números na hora da leitura, sobre **o que você enxerga** — dois
usuários nunca veem os mesmos totais.

O Painel mostra até três blocos, conforme o seu acesso.

### Coordenação

Só aparece para quem coordena processos (papel *Departamento Pessoal* ou
gerência). Traz processos em aberto, concluídos, rascunhos, vencidos, próximos
do prazo, pendências abertas, bloqueantes e valores aguardando decisão, além dos
recortes por estado formal, setores em atraso, valores em análise e a lista de
**processos críticos** — cada um com atalho para a tela de encerramento.

### Meus setores

Só aparece para quem é responsável vigente de algum setor. Traz tarefas
pendentes, vencidas e a vencer, os recortes por empresa e por filial, e os
processos com tarefa vencida — com atalho para *Minhas tarefas*.

### Seu acesso

Aparece para todos, e é a seção mais útil quando algo parece faltar. Ela mostra
a sua identidade autenticada, os seus **papéis** e os seus **escopos** (todas as
empresas, uma empresa, ou empresa e filial).

> **Dica** Antes de abrir um chamado dizendo “não vejo o processo/a tarefa”,
> leia *Seu acesso*. Papel ausente e escopo mais estreito do que você imaginava
> explicam a maioria dos casos.

Se o Painel disser que você ainda não coordena processos nem responde por um
setor, está correto: a conta existe, mas ainda não recebeu papel nem vínculo.

---

## O menu e o que cada papel vê

O menu mostra **apenas** o que o seu acesso permite usar. Ver menu curto é o
normal — a maioria das pessoas usa duas telas.

| Item do menu | Quem vê | Para que serve |
| --- | --- | --- |
| **Painel** | Todos | Visão geral do que é seu. |
| **Minhas tarefas** | Responsável vigente de algum setor | Onde a área responde o checklist do desligamento. |
| **Processos** | Departamento Pessoal e gerência do DP | Abertura, rascunhos, acompanhamento, valores e encerramento. |
| **Relatórios** | Departamento Pessoal e gerência do DP | Tempo médio, atrasos, pendências e valores por período. |
| **Notificações** | Departamento Pessoal e gerência do DP | Fila de avisos por e-mail, falhas e reprocessamento. |
| **Setores** | Administração de setores | Setores, responsáveis, prazos e escopos de atendimento. |
| **Grupos e templates** | Administração de grupos e templates | Templates versionados, perguntas, grupos e regras. |
| **Usuários** | Administração de usuários | Contas, senhas temporárias e vínculo com o Active Directory. |
| **Auditoria** | Administração de usuários | Trilha imutável dos eventos de conta. |
| **Configurações** | SuperAdmin | LDAP, e-mail, monitoramento. |

Duas regras explicam quase todo o resto:

- **papel dá autoridade; vínculo de setor dá tarefa.** São coisas diferentes.
  Quem coordena processos não recebe as tarefas dos setores por causa disso, e
  quem responde por um setor não passa a coordenar processos;
- **escopo limita o que o papel alcança.** Um *Departamento Pessoal* da empresa 1
  não enxerga processos da empresa 2. Os três papéis administrativos, ao
  contrário, só existem em escopo global.

> **Atenção** Esconder um item de menu **não** é a proteção do sistema. Quem
> tentar alcançar uma tela sem autorização recebe recusa do servidor. O menu é
> conveniência, não a barreira.

### Qual manual é o seu

| Se você… | Leia |
| --- | --- |
| responde por um setor (TI, Financeiro, Almoxarifado, Segurança do Trabalho…) | *Manual do Responsável de Área* |
| coordena desligamentos (`DP` ou `DP_GERENTE`) | *Manual do Departamento Pessoal* |
| cadastra setores, templates, grupos ou regras | *Manual de Configuração* |
| administra contas e lê a auditoria | *Manual de Administração de Usuários* |
| opera uma conta SuperAdmin | *Manual do SuperAdmin* |

Cada tela tem um botão **Ajuda** no alto, que abre o manual correspondente em
aba nova, já na seção daquela tela.

---

## Detalhes do dia a dia

**Tema claro e escuro.** O botão *Tema* no rodapé do menu alterna, e a escolha
fica guardada no seu navegador.

**Menu recolhido.** Em telas largas, o botão de recolher deixa só os ícones — e
o sistema lembra da escolha.

**Celular.** Todas as telas funcionam; as listas viram cartões em vez de tabelas,
com a mesma informação.

**Sessão.** A entrada vale por sessão do navegador. Ao terminar, use **Sair** —
especialmente em computador compartilhado.

**E-mails.** Os avisos do SGPD dizem o que fazer e onde, e nunca trazem nome de
colaborador, CPF, valores ou pareceres: o dado fica no sistema, atrás do login.
Pode acontecer de um aviso chegar duas vezes; o sistema prefere avisar duas
vezes a deixar de avisar.

---

## Dúvidas frequentes

**Entrei e só vejo o Painel.**
A conta existe, mas ainda não tem papel nem vínculo de setor. Papel é atribuído
pelo SuperAdmin; vínculo de setor, por quem administra setores.

**Meu login é recusado.**
Confira se está usando a senha da rede ou a senha temporária do SGPD — depende de
como o ambiente está configurado. Repetir a tentativa errada não resolve, e cada
falha fica registrada na auditoria. Procure quem administra usuários.

**O sistema me leva sempre para Minha senha.**
Sua senha é temporária. Troque-a e o restante do sistema se abre.

**Vejo menos itens de menu que um colega da mesma área.**
Vocês têm papéis ou escopos diferentes. Compare a seção *Seu acesso* do Painel
dos dois.

**Um número do Painel não bate com o do meu colega.**
Nem deveria: os indicadores são calculados sobre o que **cada** pessoa enxerga.

**Preciso de acesso a mais uma empresa ou filial.**
É mudança de escopo do seu papel — pedido para o SuperAdmin, com a justificativa
do negócio.

**Quem vê meus dados no sistema?**
Toda leitura é autorizada e toda alteração relevante é registrada com o nome de
quem fez. Download de evidência também é registrado.

---

## Em uma página

1. Acesse **https://sgpd.bsabioenergia.com.br** e entre com o usuário da rede ou
   com o login e a senha temporária que você recebeu.
2. Se cair em **Minha senha**, troque a senha — pelo menos 8 caracteres, nada
   parecido com o seu nome, nada de senha comum, nada só de números.
3. Leia o **Painel**: os blocos que aparecem já dizem o que você é no sistema.
4. Confira **Seu acesso** para saber seus papéis e escopos.
5. Trabalhe pelo item de menu do seu papel — **Minhas tarefas** para quem
   responde por setor, **Processos** para quem coordena.
6. Em dúvida sobre uma tela, clique em **Ajuda** no alto dela.
7. Falta acesso? Papel é com o SuperAdmin; conta e senha, com a administração de
   usuários; vínculo de setor, com a administração de setores.
