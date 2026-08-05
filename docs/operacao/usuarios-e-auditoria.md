---
titulo: Manual de Administração de Usuários
subtitulo: Contas, senhas, vínculo com o Active Directory e leitura da trilha de auditoria.
selo: Manual operacional
publico: Quem tem o papel Administração de usuários (USUARIOS_ADMIN) no SGPD
versao: 1.0
data: 03/08/2026
sistema: https://sgpd.bsabioenergia.com.br
---

## O que este papel faz e o que ele não faz

Você administra o **acesso** ao SGPD: cria contas, corrige dados cadastrais,
redefine senha temporária, liga a conta à identidade do Active Directory,
desativa quem saiu e lê a trilha de auditoria das contas.

Você **não** distribui autoridade. Quem decide que alguém passa a ser
Departamento Pessoal, gerência do DP ou administrador de qualquer coisa é o
SuperAdmin, e só ele. Você prepara a conta; a atribuição do papel é um segundo
ato, de outra pessoa.

> **Importante** Essa separação é deliberada. Se quem administra contas também
> atribuísse papéis, bastaria uma conta de administrador para se promover a
> qualquer autoridade do sistema. O sistema recusa a operação mesmo que a tela
> pareça oferecê-la.

### O que você pode fazer

| Ato | Onde |
| --- | --- |
| Criar conta local | **Usuários → Novo usuário** |
| Criar conta a partir do AD | **Usuários → Importar do AD** |
| Corrigir nome, sobrenome e e-mail | ficha do usuário → **Editar** |
| Ativar ou desativar a conta | ficha do usuário → **Editar** |
| Definir nova senha temporária | ficha do usuário → **Redefinir senha** |
| Vincular ou desvincular identidade do AD | ficha do usuário → seção *Active Directory* |
| Ler a trilha de eventos de conta | **Auditoria** |

### O que você não pode fazer

- **Atribuir ou revogar papel.** Os botões *Atribuir papel* e *Revogar* não
  aparecem para você — a lista de papéis do usuário é somente leitura.
- **Excluir uma conta.** O sistema não tem exclusão de usuário: a trilha de
  auditoria aponta para a conta e apagá-la apagaria histórico. Quem sai da
  empresa é **desativado**.
- **Vincular um responsável a um setor.** Isso é feito na tela **Setores**, por
  quem administra setores. Na ficha do usuário os vínculos aparecem, mas só para
  consulta.
- **Apagar ou editar auditoria.** A trilha é acrescentada e nunca alterada.

### Escopo: você é global

O papel *Administração de usuários* só existe em escopo **global** — não há
administrador de contas “da empresa 1” ou “da filial 2”. Você vê e administra
todas as contas do SGPD.

---

## O caminho de um acesso novo

```fluxo
titulo: De um pedido de acesso até a pessoa trabalhando no sistema
inicio: Chega o pedido de acesso para alguém
decisao: A pessoa tem conta no Active Directory da empresa?
  Tem: Use **Importar do AD** — a conta nasce já vinculada à identidade
  Não tem: Use **Novo usuário** e defina uma senha temporária
passo: A conta existe e está **Ativa**
seta: falta a autoridade
passo: O **SuperAdmin** atribui o papel, se a pessoa for coordenar processos ou administrar algo
passo: Quem administra setores cria o **vínculo de setor**, se a pessoa for responsável de área
nota: sem papel e sem vínculo, a pessoa entra e vê apenas o Painel
fim: A pessoa entra, troca a senha temporária e passa a enxergar o seu menu
```

---

## A tela Usuários

A lista traz todas as contas. O campo de busca no alto filtra por **login, nome
ou e-mail** conforme você digita — não há botão de buscar.

Em telas estreitas cada conta é um cartão; a partir de tablet, a mesma
informação vira tabela com as colunas Login, Nome, E-mail, Situação, Setores e
AD.

### As etiquetas da lista

| Etiqueta | O que quer dizer |
| --- | --- |
| `Ativo` / `Inativo` | Se a conta consegue entrar no sistema. Conta inativa não autentica e não recebe papel. |
| `Senha temporária` | A pessoa ainda não trocou a senha que você definiu. Até trocar, o sistema a leva para *Minha senha*. |
| `AD: nome.sobrenome` | A conta está ligada a uma identidade do Active Directory. |
| `N vínculo(s)` e `N vigente(s)` | Quantos vínculos de setor a conta tem, e quantos estão dentro da vigência. Vínculo fora da vigência não dá acesso a tarefa nenhuma. |

> **Dica** A diferença entre *vínculo* e *vínculo vigente* explica a dúvida mais
> comum do suporte: “o responsável não vê a tarefa dele”. Quase sempre o vínculo
> existe, mas com data de fim já passada.

Clique em **Abrir** para ir à ficha completa da conta.

---

## Criar uma conta local

Use **Novo usuário** quando a pessoa não tem conta no Active Directory, ou
quando o diretório ainda não está configurado no ambiente.

| Campo | Obrigatório | O que informar |
| --- | --- | --- |
| **Login** | Sim | O identificador de entrada. Sem espaços e sem maiúsculas — use o mesmo padrão da rede, `nome.sobrenome`. |
| **Nome** e **Sobrenome** | Sim | Nome civil da pessoa. É o que aparece no cabeçalho do sistema e na auditoria. |
| **E-mail** | Sim | Endereço válido e único. É por ele que chegam os avisos de prazo. |
| **Senha temporária** | Sim | A senha do primeiro acesso. Combine com a pessoa por canal separado. |
| **Confirme a senha** | Sim | Repetição exata da anterior. |
| **Exigir troca da senha no próximo acesso** | — | Já vem marcado. **Deixe marcado.** |

A senha precisa passar pelas regras do sistema: no mínimo **8 caracteres**, não
pode ser parecida com o login, o nome ou o e-mail, não pode ser uma senha
comum de lista pública e não pode ser só números. A tela devolve exatamente
qual regra falhou.

> **Atenção** Se você desmarcar *Exigir troca da senha no próximo acesso*, a
> senha que **você** escolheu passa a ser a senha definitiva da pessoa — e você
> a conhece. Só desmarque com motivo.

Se aparecer *“Já existe um usuário com o login, e-mail ou identidade
informada”*, procure a conta na busca antes de tentar outro login: quase sempre
a conta já existe, às vezes inativa.

### O bloco Papel inicial

Se você não é SuperAdmin, esse bloco não aparece no formulário — é o desenho
correto. Crie a conta e peça o papel ao SuperAdmin.

Quando aparece (para SuperAdmin), o papel é criado junto com a conta, na mesma
operação: se o papel for recusado — escopo inválido, por exemplo — **a conta
também não é criada**. Não fica conta pela metade.

---

## Importar do Active Directory

O botão **Importar do AD** só aparece quando o seu papel permite vincular
identidade *e* administrar contas, e a janela só funciona se a descoberta LDAP
estiver configurada no ambiente.

No alto da janela, o estado do diretório:

| Etiqueta | Leitura |
| --- | --- |
| `Conexão segura configurada` | O diálogo com o AD usa TLS. |
| `LDAP sem TLS` | A credencial técnica e as senhas trafegam sem criptografia. Reporte ao SuperAdmin. |
| `Login AD ativo` / `ainda desativado` | Se as pessoas entram com a senha da rede ou ainda com senha local. |

A busca exige **pelo menos 2 caracteres** e respeita a base, o grupo
obrigatório e o filtro salvos nas configurações — ou seja, quem não está no
grupo elegível **não aparece**, e isso não é defeito da busca.

Cada resultado traz nome, login, e-mail e o caminho da identidade no diretório,
com uma ação:

| Botão | Quando aparece | O que faz |
| --- | --- | --- |
| **Criar vinculada** | A identidade não tem conta no SGPD. | Cria a conta local já ligada à identidade do AD. Sem senha local. |
| **Abrir vínculo** | A identidade já tem conta. | Leva à ficha existente. Não duplique. |
| **Abrir conta local** | Existe conta local com o mesmo login ou e-mail, ainda não vinculada. | Leva à conta para você vincular a identidade lá, em vez de criar uma segunda. |

Quando o aviso diz *“Não é possível criar: faltam no AD …”*, a identidade não
tem os atributos mínimos (login, nome ou e-mail) e o botão fica indisponível.
Isso se resolve no Active Directory, não aqui.

> **Nunca** Não crie uma segunda conta para quem já tem uma. Duas contas para a
> mesma pessoa dividem histórico, vínculos e tarefas — e o SGPD não junta contas
> depois.

---

## A ficha do usuário

A ficha é onde tudo acontece depois da criação. Ela tem quatro seções, nesta
ordem: **Situação**, **Papéis**, **Setores vinculados** e **Active Directory**.

### Situação

| Etiqueta | O que quer dizer |
| --- | --- |
| `Ativo` / `Inativo` | Se a conta entra no sistema. |
| `Senha temporária pendente` | A pessoa ainda vai ser obrigada a trocar a senha. |
| `Superusuário` | Conta técnica com autoridade global. Trate com cuidado: ela enxerga tudo. |

### Editar

O botão **Editar** abre nome, sobrenome, e-mail e a caixa **Conta ativa**.
Login não se altera — é a identidade da pessoa na trilha de auditoria.

Desmarcar *Conta ativa* é o desligamento de acesso: a pessoa deixa de
autenticar, mas o histórico dela permanece inteiro. O sistema recusa a operação
em dois casos, com a mensagem na tela:

| Mensagem | Por quê |
| --- | --- |
| *Um administrador não pode desativar a própria conta.* | Evita você se trancar fora do sistema. Peça a outro administrador. |
| *O último superusuário ativo não pode ser desativado.* | Sem nenhum SuperAdmin ativo ninguém mais atribui papel, e o sistema fica sem saída. |
| *O usuário foi alterado por outra sessão. Recarregue a página.* | Outra pessoa mexeu na mesma conta enquanto você tinha a tela aberta. Recarregue e confira antes de refazer. |
| *O e-mail informado já está em uso.* | Dois usuários não podem ter o mesmo e-mail. |

### Redefinir senha

Define uma nova senha temporária. A caixa *Exigir troca no próximo acesso* já
vem marcada — mantenha.

O botão fica **indisponível** quando a senha da conta não é gerenciada aqui. A
mensagem no alto da ficha diz qual é o caso:

| Mensagem | Leitura |
| --- | --- |
| *Autenticação AD ativa: a senha local está bloqueada para esta conta.* | A pessoa entra com a senha da rede. Trocar senha é assunto do suporte de TI, não do SGPD. |
| *Senha local disponível somente pela contingência configurada para superusuário.* | Conta técnica preservada de propósito, para o caso de o AD ficar indisponível. |
| *Autenticação AD desativada: a senha local permanece disponível para testes.* | O login pelo AD está desligado no ambiente; a senha local ainda vale. |

> **Cuidado** Redefinir senha é ato registrado com o seu nome. Confirme com quem
> pediu por um canal confiável — pedido de redefinição por e-mail é o golpe mais
> antigo que existe.

### Papéis

A seção lista os papéis ativos da conta, cada um com o escopo em que vale
(*Global*, *Empresa 1*, *Empresa 1 · filial 2*), e guarda as atribuições
revogadas em um bloco recolhido — histórico não desaparece.

Para você, essa seção é **leitura**. Os cinco papéis atribuíveis e o que cada um
autoriza:

| Papel | Autoriza | Escopo |
| --- | --- | --- |
| **Departamento Pessoal** | Conduzir o processo demissional: abrir, iniciar, decidir valores, liberar e encerrar. | Global, empresa ou filial |
| **Gerência do Departamento Pessoal** | Tudo do DP e, além disso, liberar ou encerrar processo **com impedimento**, sob justificativa. | Global, empresa ou filial |
| **Administração de grupos e templates** | Manter templates, perguntas, grupos e regras de aplicabilidade. | Somente global |
| **Administração de setores** | Manter setores, escopos, prazos e responsáveis. | Somente global |
| **Administração de usuários** | O que este manual descreve. | Somente global |

Duas coisas que costumam confundir:

- **responsável de setor não é papel.** Aparece na seção seguinte, como
  vínculo, e vale enquanto a vigência valer;
- **a gerência do DP não precisa também de DP.** Quem tem a gerência já
  satisfaz toda exigência de Departamento Pessoal. Atribuir os dois é redundante.

### Setores vinculados

Cada vínculo mostra o setor, o início, o fim (ou *sem término*), os escopos que
ele herda do próprio setor e uma etiqueta:

| Etiqueta | O que quer dizer |
| --- | --- |
| `Vigente` | O vínculo vale agora. A pessoa vê as tarefas desse setor. |
| `Fora da vigência` | Já terminou, ou ainda não começou. Não dá acesso a nada. |

Vínculo se cria e se encerra em **Setores**. Se o pedido for “dar acesso às
tarefas do Almoxarifado para o Fulano”, encaminhe a quem administra setores.

### Active Directory

Quando há identidade vinculada, a seção mostra o usuário do AD, o identificador
técnico e quem fez o vínculo. Quando não há, aparece **Vincular**.

**Vincular** abre uma busca no diretório: pesquise, clique em *Selecionar* na
identidade certa e confirme. Uma identidade já vinculada a outra conta não pode
ser selecionada — o sistema recusa a duplicidade, e o identificador é
reconferido no servidor antes de gravar.

**Desvincular** solta a conta da identidade do AD. Faça isso com consciência: se
o login pelo AD estiver ativo, a pessoa deixa de conseguir entrar até que exista
senha local válida.

---

## A tela Auditoria

A trilha de eventos das contas. Serve para responder “quem fez isso, quando e
por quê” — em investigação de acesso, em conferência com Segurança da Informação
ou quando alguém afirma não ter feito algo.

> **Regra** Os registros são **imutáveis**: não há edição e não há exclusão, nem
> para SuperAdmin. O que entrou fica.

Cada linha traz:

| Coluna | O que é |
| --- | --- |
| **Quando** | Data e hora do evento. |
| **Evento** | O que aconteceu. Veja a lista abaixo. |
| **Ator** | Quem fez. Vazio em evento de sistema. |
| **Afetado** | A conta que sofreu o ato. |
| **Entidade** | O objeto tocado, em código técnico (`USER:12`, `ROLE_ASSIGNMENT:44`). Serve para rastrear, não para ler. |
| **Justificativa** | O motivo padronizado que o servidor registrou. Não é texto livre de quem clicou. |

O filtro no alto restringe a um tipo de evento:

| Evento | Origem |
| --- | --- |
| `Login`, `Logout` | Entrada e saída do sistema. |
| `Falha de autenticação` | Tentativa recusada. Uma sequência delas no mesmo login merece atenção. |
| `Usuário criado`, `Usuário atualizado` | Criação e edição de conta — inclusive ativação e desativação. |
| `Senha alterada` | A própria pessoa trocou a senha. |
| `Senha redefinida` | Um administrador definiu senha temporária para outra pessoa. |
| `Papel criado`, `Papel atualizado` | Manutenção do catálogo de papéis. |
| `Papel atribuído`, `Papel revogado` | Concessão e retirada de autoridade. É o que se audita primeiro. |
| `AD vinculado`, `AD desvinculado` | Ligação da conta com a identidade do diretório. |

A lista traz **50 eventos por página**, do mais recente para o mais antigo, e a
navegação é por **Anteriores** e **Próximos**. Não há contagem total: a consulta
é propositalmente barata, porque contar tudo a cada abertura ficaria lento à
medida que a trilha cresce.

> **Dica** Auditando um caso concreto, filtre primeiro por `Papel atribuído` e
> `Papel revogado`. É onde autoridade aparece e desaparece — o resto do
> histórico costuma ser consequência.

---

## Dúvidas frequentes

**Preciso remover alguém que saiu da empresa.**
Abra a ficha, **Editar**, desmarque *Conta ativa* e confirme. Não existe
exclusão, e é intencional: a trilha de auditoria referencia a conta.

**Criei a conta e a pessoa diz que não vê nada além do Painel.**
Está certo. Conta sem papel e sem vínculo de setor não tem o que mostrar. Peça o
papel ao SuperAdmin, ou o vínculo a quem administra setores.

**A pessoa esqueceu a senha.**
Se a conta é local, **Redefinir senha** com troca obrigatória. Se a conta usa o
Active Directory, o botão fica indisponível: a senha é a da rede e quem resolve
é o suporte de TI.

**O botão Atribuir papel não aparece na ficha.**
Não é falha de tela. Atribuir papel é ato exclusivo do SuperAdmin.

**Importei do AD e o login ficou diferente do que eu esperava.**
O login vem do diretório, não da digitação. Se estiver errado no AD, corrija lá
e vincule de novo.

**Alguém aparece duas vezes na lista.**
Provavelmente uma conta local antiga e uma importada do AD. Decida qual
permanece, vincule a identidade nela, desative a outra e registre o motivo no
pedido de suporte — o histórico das duas continua existindo.

**Não encontro um usuário que sei que existe.**
A busca casa login, nome e e-mail, e traz também contas inativas. Tente o
sobrenome ou parte do e-mail.

**Preciso saber quem liberou um processo.**
Não é aqui. Esta trilha é das **contas**. Os atos do processo demissional ficam
no próprio processo, na tela de encerramento.

---

## Em uma página

1. Entre em **https://sgpd.bsabioenergia.com.br** e abra **Usuários**.
2. Pessoa com conta no AD: **Importar do AD**, busque, **Criar vinculada**.
3. Pessoa sem conta no AD: **Novo usuário**, com senha temporária e troca
   obrigatória marcada.
4. Confira na ficha se falta **papel** (pedir ao SuperAdmin) ou **vínculo de
   setor** (pedir a quem administra setores).
5. Quem saiu da empresa: **Editar → desmarcar Conta ativa**. Nunca há exclusão.
6. Senha perdida: **Redefinir senha** — e, se o botão estiver bloqueado, é conta
   do Active Directory.
7. Para investigar acesso, abra **Auditoria** e filtre por `Papel atribuído`,
   `Papel revogado` ou `Falha de autenticação`.
