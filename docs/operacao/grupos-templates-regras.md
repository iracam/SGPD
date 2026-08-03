---
titulo: Manual de Configuração
subtitulo: Setores, templates de checklist, grupos de validação e regras de aplicabilidade — como montar o que o processo vai usar.
selo: Manual operacional
publico: Quem configura o SGPD — administradores do processo demissional e SuperAdmin
versao: 1.0
data: 03/08/2026
sistema: https://sgpd.bsabioenergia.com.br
---

## O que você vai configurar

Este manual trata do que existe **antes** de qualquer desligamento: as peças que
o processo usa quando é iniciado. Configurar bem aqui é o que faz o processo do
dia a dia funcionar sem improviso.

São quatro peças, e elas se encaixam nesta ordem:

| Peça | O que é | Onde fica |
| --- | --- | --- |
| **Setor de validação** | A área que confere alguma coisa: TI, Financeiro, Almoxarifado. Tem prazo, escopo e responsáveis. | Menu **Setores** |
| **Template de checklist** | A lista de perguntas que um setor responde. É versionado. | Menu **Grupos e templates** |
| **Grupo de validação** | O conjunto "setor + template" aplicável a um perfil de colaborador. É versionado. | Menu **Grupos e templates** |
| **Regra de aplicabilidade** | O filtro que sugere um grupo automaticamente conforme o perfil do colaborador. | Menu **Grupos e templates** |

```fluxo
titulo: Como as peças se encaixam
inicio: Você cadastra os **setores** com prazo, escopo e responsáveis
passo: Você cria um **template** com as perguntas e o **publica**
nota: só template publicado pode ser usado por um grupo
passo: Você cria um **grupo** ligando cada setor ao template publicado, e o **publica**
passo: Opcionalmente, cria uma **regra** que sugere esse grupo por empresa, filial, cargo etc.
seta: a configuração está pronta
passo: O DP abre um processo — a regra **sugere** os grupos
passo: O DP confirma a seleção e inicia o processo
fim: Cada setor recebe a tarefa com as perguntas daquela versão do template
```

---

## A regra de ouro: versão publicada é imutável

Templates e grupos são **versionados**. Uma versão pode estar em três situações:

| Situação | O que significa | O que dá para fazer |
| --- | --- | --- |
| `Rascunho` | Em edição. Nenhum processo a usa. | Editar livremente, pré-visualizar, publicar ou excluir. |
| `Publicada` | É a versão vigente. Processos novos a usam. | Nada — é imutável. Para mudar, crie outra versão. |
| `Substituída` | Foi publicada e depois trocada por uma versão mais nova. | Nada. Continua existindo porque processos antigos dependem dela. |

> **Regra** Depois de publicada, uma versão **nunca** muda. Isso não é
> burocracia: é o que garante que um processo aberto há seis meses continue
> mostrando exatamente as perguntas que o setor respondeu na época. Se as
> perguntas pudessem mudar retroativamente, a auditoria não valeria nada.

Consequência prática: **mudanças só valem para processos futuros**. Alterar um
template hoje não altera nenhuma tarefa já criada.

[pagina]

### O ciclo de uma versão

```fluxo
titulo: Como evoluir um template ou um grupo já publicado
inicio: Existe a versão **v1 publicada**, em uso
passo: Você clica em **Nova versão** — nasce a **v2 em rascunho**, cópia da v1
nota: só pode existir um rascunho por vez
passo: Você edita o rascunho quantas vezes quiser e usa **Pré-visualizar**
decisao: O rascunho está pronto?
  Sim: **Publicar** — a v2 passa a vigente e a v1 vira *Substituída*
  Não ficou bom: **Excluir rascunho** — a v1 continua vigente, intocada
fim: Processos iniciados dali em diante usam a v2; os antigos seguem na v1
```

O primeiro rascunho de um template ou grupo **não pode ser excluído** — só as
versões seguintes.

---

## Setores de validação

O setor é a base de tudo: um grupo só pode apontar para setores que existam, e
uma tarefa só é gerada se o setor tiver responsável.

Acesse **Setores** e use **Novo setor**, ou **Editar** em um existente.

### Os campos do setor

| Campo | Obrigatório | O que informar |
| --- | --- | --- |
| **Nome** | Sim | Até 120 caracteres. Como a área aparece para todo mundo: `Tecnologia da Informação`, `Almoxarifado BSA`. |
| **Descrição** | Não | O que a área confere no desligamento. Ajuda quem for configurar depois. |
| **Prazo padrão em horas** | Sim | Maior que zero. É o SLA do setor — usado quando nem o grupo nem o template definirem um prazo próprio. `48` significa dois dias corridos. |
| **Setor de escalada** | Não | Para onde vai o aviso quando a tarefa passa 48 h do vencimento. Um setor não pode escalar para si mesmo. Deixe vazio para não escalar. |
| **Bloqueia o processo** | — | Ver tabela abaixo. |
| **Permite lançar valores** | — | Ver tabela abaixo. |
| **Exige evidência** | — | Ver tabela abaixo. |
| **Setor ativo** | — | Desmarcado, o setor não entra em novas seleções. Setores **não são excluídos**, apenas inativados — há histórico dependendo deles. |

### As três chaves de comportamento

| Chave | Ligada | Desligada |
| --- | --- | --- |
| **Bloqueia o processo** | A tarefa deste setor precisa estar concluída para o processo ser liberado. É o padrão. | A tarefa é opcional para a liberação: fica como aviso na prontidão, não como impedimento. |
| **Permite lançar valores** | Este setor pode registrar pretensão de cobrança em pendências de categoria `Valor`. | Os campos de valor simplesmente não aparecem para a área. |
| **Exige evidência** | Marca a postura padrão do setor quanto a comprovantes. A exigência efetiva de cada pergunta é definida no template. | Sem postura padrão. |

> **Atenção** **Permite lançar valores** costuma ser o campo mais esquecido. Se
> uma área reclamar que não consegue informar um valor, verifique aqui primeiro.
> A mudança vale para pendências criadas dali em diante.

### Escopos de atendimento

Um setor não atende necessariamente a empresa inteira. Cada escopo é uma linha,
e um setor pode ter vários.

| Abrangência | Campos que exige | Quando usar |
| --- | --- | --- |
| `Global` | Nenhum | O setor atende todas as empresas e filiais. Típico de TI corporativo e Departamento Pessoal. |
| `Empresa` | Empresa | O setor atende só aquela empresa, em todas as filiais dela. |
| `Filial` | Empresa **e** Filial | O setor atende só aquela filial. Típico de almoxarifado e portaria. |

Filial sem empresa é recusado — a filial só existe dentro de uma empresa.

> **Importante** O escopo decide se o setor pode aparecer em um processo. Um
> grupo pode listar o setor, mas se o escopo dele não alcançar a empresa ou a
> filial do colaborador, o setor não gera tarefa.

### Responsáveis

Cada linha liga um **usuário** ao setor, com **Início da validade** e,
opcionalmente, **Fim da validade**.

- Todos os responsáveis vigentes têm **a mesma autoridade** sobre a tarefa. Não
  existe dono individual: qualquer um pode iniciar, responder e concluir.
- Os avisos de prazo vão para **todos** eles.
- Responsabilidade se **revoga** (preenchendo o fim da validade), não se exclui.

> **Nunca** Não deixe um setor obrigatório sem responsável vigente. O início do
> processo é **bloqueado** quando isso acontece, e o DP fica travado sem poder
> resolver sozinho. Ao desligar alguém que responde por um setor, transfira a
> responsabilidade antes.

---

## Templates de checklist

O template é a lista de perguntas de um setor. Um mesmo template pode ser
reutilizado por vários setores e vários grupos.

Em **Grupos e templates**, clique em **Novo template** — ou em **Editar
rascunho** se já houver um em aberto.

### O cabeçalho do template

| Campo | Obrigatório | O que informar |
| --- | --- | --- |
| **Nome** | Sim | Até 120 caracteres. Descreva o uso: `Conferência de TI — desligamento`. |
| **SLA padrão (horas)** | Não | De 1 a 8760 horas (um ano). Se preenchido, tem precedência sobre o prazo padrão do setor. Deixe vazio para usar o prazo do setor. |
| **Descrição** | Não | Para quem for manter o template depois. |

O **código numérico** do template e o de cada pergunta são gerados
automaticamente ao salvar. Você não escolhe nem edita esses códigos.

### As perguntas

Cada pergunta tem um texto, um tipo de resposta e quatro marcadores.

#### Tipo de resposta

Escolher o tipo certo é o que torna o checklist utilizável. Este é o campo que
mais compensa pensar antes.

| Tipo | O setor vê | Use quando |
| --- | --- | --- |
| `Sim/Não` | Lista com *Selecione*, *Sim* e *Não* | A conferência é binária: *O crachá foi devolvido?* |
| `Texto` | Caixa de texto livre, várias linhas | Precisa de descrição: *Descreva os acessos removidos.* |
| `Número` | Campo numérico | Quantidade ou identificador numérico: *Quantas chaves foram devolvidas?* |
| `Data` | Campo de data com calendário | Precisa registrar quando algo ocorreu: *Data da devolução do notebook.* |
| `Seleção` | Lista com as opções que você cadastrar | Há um conjunto fechado e só uma resposta cabe: *Estado do equipamento: Novo / Usado / Danificado.* |
| `Múltipla seleção` | Lista onde marcar várias | Há um conjunto fechado e mais de uma resposta cabe: *Quais sistemas foram bloqueados?* |
| `Arquivo` | Nenhum campo — só a área de evidências | A resposta **é** o documento: *Anexe o termo de devolução assinado.* |
| `Confirmação obrigatória` | Caixa de marcação escrita *Confirmo a validação* | Você quer uma declaração pessoal e registrada: *Confirmo que todos os acessos foram revogados.* |

> **Atenção** `Seleção` e `Múltipla seleção` **exigem** uma lista de opções
> cadastrada. Sem opções, a pergunta é recusada ao salvar.

#### Os quatro marcadores

| Marcador | Ligado | Desligado |
| --- | --- | --- |
| **Obrigatória** | A tarefa **não conclui** sem esta resposta. A pergunta aparece com asterisco. | O setor pode deixar em branco. |
| **Bloqueante** | Sinaliza que esta pergunta é crítica para a liberação. | Pergunta comum. |
| **Exige evidência** | O setor precisa anexar arquivo. Combinada com *Obrigatória*, a falta do arquivo impede a conclusão. | Sem exigência de comprovante. |
| **Permite pendência** | O setor pode vincular uma pendência a esta pergunta específica. | A pergunta não aparece na lista *Item relacionado* do formulário de pendência. |

> **Dica** Nem toda pergunta precisa ser obrigatória. Excesso de obrigatoriedade
> leva a resposta de fachada — o setor preenche qualquer coisa para conseguir
> concluir. Reserve o obrigatório para o que de fato não pode faltar.

### Pré-visualizar antes de publicar

O botão **Pré-visualizar** abre uma simulação da tela **Minhas tarefas** com o
rascunho atual: as perguntas na ordem, os campos reais de cada tipo, a área de
evidências onde ela aparecerá e as notas de configuração.

Use sempre antes de publicar. Depois de publicada, a versão não muda mais.

### Publicar

O botão **Publicar** torna a versão vigente. A partir daí ela pode ser usada por
grupos e passa a ser imutável.

Enquanto houver rascunho aberto, aparecem também **Editar rascunho** e **Excluir
rascunho**. Quando não houver, aparece **Nova versão**.

---

## Grupos de validação

O grupo é a resposta à pergunta: *para este perfil de colaborador, quais setores
precisam validar e com qual checklist cada um?*

Clique em **Novo grupo**. O botão fica indisponível se não existir nenhum
template publicado — sem template, não há o que atribuir.

### O cabeçalho do grupo

| Campo | Obrigatório | O que informar |
| --- | --- | --- |
| **Nome** | Sim | Até 120 caracteres. Descreva o perfil que o grupo atende: `Administrativo — matriz`, `Operacional — usina`. |
| **Descrição** | Não | O critério de uso, para quem for manter depois. |

### Os setores do grupo

Cada linha liga um setor a um template publicado.

| Campo | Obrigatório | O que informar |
| --- | --- | --- |
| **Setor** | Sim | Um setor cadastrado. Não pode repetir o mesmo setor duas vezes no grupo. |
| **Template publicado** | Sim | Só aparecem versões **publicadas**. Um rascunho não pode ser usado. |
| **SLA específico (horas)** | Não | De 1 a 8760. Sobrepõe o SLA do template e o prazo do setor **apenas neste grupo**. |
| **Obrigatório** | — | Ligado, a tarefa deste setor precisa ser concluída para liberar o processo. Desligado, ela vira aviso na prontidão, não impedimento. |
| **Bloqueante** | — | Ligado, marca a validação deste setor como crítica dentro do grupo. |

### A precedência do prazo

Quatro camadas podem definir o prazo de uma tarefa. Vale **a primeira que
existir**, de cima para baixo:

1. **ajuste manual no rascunho do processo** — decisão do DP, caso a caso;
2. **SLA específico do grupo** — o campo desta tela;
3. **SLA padrão do template**;
4. **prazo padrão do setor**.

Resolvido o SLA, o prazo final da tarefa é o que vier primeiro entre a **data
limite do processo** e o **início mais o SLA**. Não há cálculo por dia útil: as
horas são corridas.

### Quando dois grupos mandam o mesmo setor

Um processo pode selecionar mais de um grupo, e é comum que dois grupos incluam
o mesmo setor. O comportamento depende do template:

| Situação | O que acontece |
| --- | --- |
| Mesmo setor, **mesmo** template | O sistema consolida sozinho. Obrigatoriedade e bloqueio somam (basta um dos grupos exigir para valer) e prevalece o **menor** prazo. Uma única tarefa é criada. |
| Mesmo setor, **templates diferentes** | O início do processo é **bloqueado**. O sistema não escolhe por você qual checklist vale. |

> **Atenção** Este é o erro de configuração mais comum e ele só aparece na hora
> em que o DP tenta iniciar o processo. Ao montar grupos que possam ser
> selecionados juntos, use o **mesmo template** para os setores em comum.

### Pré-visualizar e publicar

**Pré-visualizar** mostra, para cada setor do grupo, o cartão de tarefa que será
criado: nome do setor, prazo efetivo, template resolvido e o checklist completo
com os controles reais.

**Publicar** torna a versão vigente. A partir daí, ela pode ser selecionada em
processos e não muda mais.

**Nova versão** clona a versão publicada e atualiza cada setor para a **versão
vigente do seu template** — é assim que um grupo incorpora as perguntas novas de
um template que você republicou.

---

## Regras de aplicabilidade

A regra é opcional. Ela existe para poupar o DP de escolher os mesmos grupos
manualmente todas as vezes.

Clique em **Nova regra**. O botão fica indisponível se não houver nenhum grupo
publicado.

> **Importante** A regra **sugere**, nunca aplica. Ela pré-marca os grupos no
> rascunho do processo e mostra qual regra sugeriu cada um. Nada é selecionado
> de verdade até o DP clicar em **Salvar seleção**. Se nenhuma regra existir, o
> DP simplesmente escolhe à mão — nada quebra.

### Como a regra decide

A regra tem seis campos de filtro. O funcionamento é simples e vale a pena
memorizar:

- **Campo vazio é curinga**: não filtra nada, aceita qualquer valor.
- **Campo preenchido exige igualdade** com o dado do colaborador no snapshot.
- Uma regra combina quando **todos** os campos preenchidos batem.
- Uma regra sem nenhum filtro combina com **todo mundo**.

[pagina]

```fluxo
titulo: O que acontece quando o DP abre um processo
inicio: O DP escolhe o colaborador e o snapshot é criado
passo: O sistema percorre **todas** as regras ativas e dentro da validade
decisao: Os campos preenchidos da regra batem com o snapshot?
  Bateram: O grupo daquela regra entra na sugestão
  Não bateram: A regra é ignorada, sem efeito nenhum
passo: Os grupos sugeridos aparecem pré-marcados no rascunho, com o nome da regra de origem
alerta: A prioridade **não** suprime ninguém — toda regra que bate contribui o seu grupo
passo: O DP confere, ajusta e clica em **Salvar seleção**
fim: A seleção salva é o que vale; o início usa ela, não a sugestão
```

### Os campos da regra

| Campo | Obrigatório | O que informar |
| --- | --- | --- |
| **Nome** | Sim | Até 120 caracteres. Descreva o critério: `Operacional da usina de Sertãozinho`. Este nome aparece para o DP no rascunho. |
| **Prioridade** | Sim | De 1 a 9999. Padrão `100`. **Só ordena a exibição** — não desempata nem suprime regra nenhuma. |
| **Grupo sugerido** | Sim | O grupo que a regra propõe. Só grupos publicados. A sugestão sempre resolve a **versão publicada vigente** no momento da consulta. |
| **Empresa** | Não | Código da empresa. Vazio = qualquer empresa. |
| **Filial** | Não | Código da filial. **Exige a empresa preenchida na mesma regra.** Vazio = qualquer filial. |
| **Tipo de colaborador** | Não | Código do tipo. Vazio = qualquer tipo. |
| **Estrutura de cargos** | Não | Código da estrutura. Vazio = qualquer estrutura. |
| **Cargo** | Não | Código do cargo, texto. Vazio = qualquer cargo. |
| **Centro de custo** | Não | Código do centro de custo, texto. Vazio = qualquer centro. |
| **Válida de** / **Válida até** | Não | Janela de vigência. O fim não pode anteceder o início. Ambos vazios = vale sempre. |
| **Ativa** | — | Desmarcada, a regra não sugere nada. Regras **não são excluídas**, apenas inativadas. |

### Combinar regras: união, não disputa

Este é o ponto que mais gera engano. **Todas as regras vigentes que combinam
contribuem o seu grupo.** Não há regra vencedora.

| Cenário | Resultado |
| --- | --- |
| Regra A (sem filtro) sugere `Grupo Padrão`; Regra B (filial 3) sugere `Grupo Usina`. Colaborador da filial 3. | A sugestão traz **os dois** grupos. |
| Duas regras sugerem o **mesmo** grupo | O grupo aparece uma vez só. |
| Nenhuma regra combina | Não há sugestão. O DP escolhe manualmente. |
| Regra com prioridade 9999 e outra com 1, ambas combinando | **As duas** contribuem. A prioridade só define a ordem de exibição. |

> **Atenção** Se você quer que um perfil receba **menos** grupos, o caminho não é
> criar uma regra de prioridade maior — é **restringir os filtros** das regras
> existentes ou inativá-las. Não existe regra de exclusão.

### Um roteiro comum

*"Quero que todo desligamento na filial 3 passe também pelo Almoxarifado."*

1. Confirme que existe o setor **Almoxarifado** com escopo que alcance a filial
   3 (`Filial` empresa X / filial 3, ou `Empresa` X, ou `Global`).
2. Confirme que o setor tem responsável vigente.
3. Crie ou reutilize um template com as perguntas do almoxarifado e **publique**.
4. Crie um grupo — digamos `Almoxarifado — filial 3` — com esse setor e esse
   template, e **publique**.
5. Crie uma regra: nome descritivo, **Empresa** X, **Filial** 3, grupo sugerido
   `Almoxarifado — filial 3`, ativa.
6. Abra um processo de teste para um colaborador da filial 3 e confira se a
   sugestão aparece com o nome da sua regra.

---

## Antes de publicar: conferência final

Passe por esta lista antes de tornar qualquer coisa vigente.

**Setor**

- Prazo padrão faz sentido para o trabalho real da área?
- O escopo alcança as empresas e filiais certas?
- Há responsável com vínculo **vigente**?
- **Permite lançar valores** está como deveria?
- O setor de escalada está definido, se a área for crítica?

**Template**

- Pré-visualizou?
- Os tipos de resposta são os certos, e as listas de opções estão completas?
- Só o que é essencial está marcado como obrigatório?
- As perguntas que exigem comprovante estão com **Exige evidência**?

**Grupo**

- Todo setor aponta para o template certo, na versão certa?
- Os prazos específicos são realistas?
- Se este grupo puder ser selecionado junto com outro, os setores em comum usam
  o **mesmo template**?
- Pré-visualizou?

**Regra**

- Os filtros restringem o que você quer e deixam vazio o que é indiferente?
- Filial preenchida tem empresa junto?
- A janela de validade está correta?
- Testou abrindo um processo de teste?

> **Regra** Toda criação, alteração e publicação fica registrada com o seu nome,
> a data e o conteúdo. A trilha de configuração é permanente e não pode ser
> apagada — inclusive a exclusão de um rascunho.

---

## Dúvidas frequentes

**Publiquei um template com erro.**
Crie uma **Nova versão**, corrija e publique. A versão errada vira *Substituída*
e continua existindo, porque processos abertos com ela dependem dela. Processos
já iniciados **não** recebem a correção.

**Preciso apagar um setor que não uso mais.**
Não é possível apagar. Desmarque **Setor ativo** — ele deixa de entrar em novas
seleções e o histórico continua íntegro.

**Mudei o template mas as tarefas antigas continuam iguais.**
É o comportamento correto. Cada tarefa guarda as perguntas da versão vigente
quando o processo foi iniciado.

**O DP diz que o início está bloqueado por templates diferentes.**
Dois grupos selecionados mandam o mesmo setor com templates diferentes. Ou o DP
seleciona apenas um dos grupos, ou você ajusta a configuração para que ambos
usem o mesmo template naquele setor.

**Criei a regra e ela não sugere nada.**
Verifique, nesta ordem: a regra está **Ativa**? Está dentro da janela de
validade? Os filtros batem mesmo com o colaborador — inclusive os códigos? O
grupo apontado tem **versão publicada**? O setor do grupo tem escopo que alcança
a empresa e filial do colaborador?

**Quero um grupo que se aplique a todo mundo.**
Crie a regra sem nenhum filtro preenchido. Todos os campos vazios significam
curinga em tudo.

**Consigo excluir uma versão publicada?**
Não. Só rascunhos são excluídos, e nunca o primeiro rascunho de um template ou
grupo.

---

## Em uma página

1. **Setores**: cadastre a área com prazo, escopo, responsáveis vigentes e as
   chaves de comportamento.
2. **Grupos e templates → Novo template**: monte as perguntas, escolha bem os
   tipos, **pré-visualize** e **publique**.
3. **Novo grupo**: ligue cada setor ao template publicado, defina obrigatoriedade
   e prazo, **pré-visualize** e **publique**.
4. **Nova regra** (opcional): preencha só os filtros que restringem, escolha o
   grupo sugerido e deixe **Ativa**.
5. Abra um processo de teste e confirme a sugestão, os setores resolvidos e os
   prazos.
6. Para evoluir qualquer coisa: **Nova versão** → editar → pré-visualizar →
   **Publicar**. Processos antigos ficam como estavam.
