---
titulo: Manual do Responsável de Área
subtitulo: Como validar a saída de um colaborador pelo SGPD — checklist, evidências, pendências e valores.
selo: Manual operacional
publico: Quem responde por um setor de validação (TI, Financeiro, Almoxarifado, Segurança do Trabalho e demais áreas)
versao: 1.0
data: 03/08/2026
sistema: https://sgpd.bsabioenergia.com.br
---

## O que o SGPD faz e o que ele não faz

O SGPD (também chamado **DesligaFlow**) organiza o que cada área precisa
verificar quando um colaborador é desligado. Quando o Departamento Pessoal abre
um processo de desligamento, o sistema cria uma **tarefa** para cada setor
envolvido. Você responde a tarefa do seu setor: confere o que precisa ser
conferido, anexa comprovantes e registra o que ficou pendente.

Enquanto a sua tarefa não estiver concluída, o desligamento não é liberado. É
esse o papel do sistema: garantir que nenhuma área seja esquecida e que fique
registrado quem verificou o quê, quando e com qual comprovante.

> **Importante** O SGPD não calcula rescisão, não aplica desconto em folha e não
> altera nada no Senior. Ele registra o que as áreas apuraram. O Senior continua
> sendo o sistema oficial da rescisão, e quem decide o que vira cobrança é o
> Departamento Pessoal.

### O que se espera de você

- Responder a tarefa do seu setor **dentro do prazo** indicado na tela.
- Anexar comprovante sempre que a pergunta exigir.
- Registrar uma **pendência** quando encontrar algo que impeça ou atrase a saída
  do colaborador — devolução não feita, acesso não removido, material não
  entregue, valor a acertar.
- Concluir a tarefa quando tudo estiver resolvido ou devidamente registrado.

### Uma tarefa é do setor, não de uma pessoa

Se três pessoas respondem pelo mesmo setor, as três veem a mesma tarefa e
qualquer uma delas pode agir. Não existe "tarefa do fulano". Isso significa
duas coisas na prática: você pode continuar o trabalho que um colega começou, e
os lembretes de prazo chegam para todos os responsáveis do setor ao mesmo tempo.

---

## Entrar no sistema

O SGPD é acessado pelo navegador, no endereço:

**https://sgpd.bsabioenergia.com.br**

Use o **mesmo usuário e senha da rede** (o mesmo do computador e do e-mail). Se
a sua conta ainda não estiver liberada, ou se o acesso for recusado, procure o
Departamento Pessoal — não existe autocadastro.

Funciona em celular, tablet e computador. As telas se adaptam ao tamanho da
tela; em celular o menu fica no ícone de três traços, no topo.

### O menu

Você provavelmente verá apenas dois itens. Isso é normal: o menu mostra somente
o que o seu perfil pode usar.

| Item do menu | Para que serve |
| --- | --- |
| **Painel** | Visão geral: quantas tarefas você tem, quantas estão atrasadas. |
| **Minhas tarefas** | Onde você trabalha. Todas as tarefas dos seus setores. |

Se você também tiver atribuições de Departamento Pessoal, verá mais itens —
nesse caso, consulte também o *Manual do Departamento Pessoal*.

---

## O caminho completo, do começo ao fim

```fluxo
titulo: Da abertura do processo até a sua tarefa concluída
inicio: O Departamento Pessoal abre e inicia o processo de desligamento
seta: você recebe um e-mail de aviso
passo: A tarefa do seu setor aparece em **Minhas tarefas** com a situação **Pendente**
passo: Você clica em **Iniciar análise** — a situação passa para **Em análise**
passo: Você responde o checklist e anexa as evidências pedidas
decisao: Encontrou algo que impede ou atrasa a saída do colaborador?
  Sim: Registre uma **pendência** descrevendo o problema, e resolva ou encaminhe
  Não: Siga direto para a conclusão
passo: Você preenche as **Observações da conclusão** e clica em **Concluir tarefa**
seta: o sistema confere se falta algo
decisao: O sistema aceitou a conclusão?
  Aceitou: A situação passa para **Concluída**
  Recusou: A tela diz exatamente o que falta. Resolva e tente de novo
fim: Com todos os setores concluídos, o Departamento Pessoal libera a rescisão
```

---

## A tela Minhas tarefas

As tarefas vêm agrupadas em duas seções: as **ativas**, que ainda esperam algo
de você, e as **concluídas**, que ficam disponíveis para consulta.

Dentro de cada seção, as tarefas são agrupadas **por colaborador**. Você vê o
nome da pessoa, a matrícula, a empresa, a filial e quantas tarefas existem ali.
Clique na linha para abrir e ver as tarefas.

### O cartão da tarefa

Cada tarefa mostra, no alto, o nome do seu setor e uma etiqueta colorida com a
situação. Logo abaixo, três informações de registro:

| Campo | O que significa |
| --- | --- |
| **Prazo** | Data e hora limite para concluir esta tarefa. Depois disso ela conta como atrasada e o Departamento Pessoal é avisado. |
| **Template** | Qual modelo de checklist está sendo usado e em que versão (por exemplo `12 · v3`). Serve para rastreabilidade: se o checklist mudar depois, a sua tarefa continua com as perguntas que existiam quando o processo começou. |
| **Versão** | Contador de alterações da tarefa. Só importa em um caso: se aparecer o aviso de que a tarefa foi alterada por outra sessão, é porque um colega mexeu nela. Recarregue a página. |

### As três situações da tarefa

| Situação | O que quer dizer | O que você pode fazer |
| --- | --- | --- |
| `Pendente` | A tarefa foi criada e ninguém abriu ainda. | Só uma coisa: clicar em **Iniciar análise**. O checklist só aparece depois disso. |
| `Em análise` | Alguém do setor já começou. | Tudo: responder o checklist, anexar evidências, registrar e tratar pendências, informar valores e concluir. |
| `Concluída` | O setor terminou. | Apenas consultar. As respostas aparecem como texto, com a data em que foram registradas. Para reabrir, é preciso pedir ao Departamento Pessoal. |

> **Atenção** Não deixe a tarefa em `Pendente` só porque você ainda não vai
> resolver. Clicar em **Iniciar análise** é o que registra que a área tomou
> ciência, e as respostas só podem ser salvas a partir daí.

### De onde vem o prazo

O prazo é calculado quando o processo é iniciado, pela seguinte regra: vale o
que vier primeiro entre a **data limite do processo** e o **início mais o tempo
padrão do seu setor** (o SLA). Quem define esse tempo padrão é o Departamento
Pessoal, na configuração do setor ou do grupo.

O prazo não se recalcula sozinho depois. Se ele estiver irreal para o seu
setor, o caminho é falar com o Departamento Pessoal — não há como alterá-lo
pela tela da tarefa.

---

## Responder o checklist

O checklist é a lista de perguntas do seu setor. Perguntas marcadas com
asterisco (**\***) são **obrigatórias**: sem elas a tarefa não conclui.

Conforme você responde, o item ganha uma marca de conferido — é o seu controle
visual do que já foi feito.

### Os tipos de resposta

Cada pergunta tem um tipo, e o tipo determina o campo que aparece na tela.

| Tipo | Como aparece | O que informar |
| --- | --- | --- |
| **Sim / Não** | Lista com três opções: *Selecione*, *Sim* e *Não*. | Escolha uma. Deixar em *Selecione* equivale a não responder — e reprova a conclusão se a pergunta for obrigatória. |
| **Texto** | Caixa de texto livre, de várias linhas. | Escreva o que a pergunta pede. Use para descrever situações, números de patrimônio, nomes de sistemas. |
| **Número** | Campo numérico. | Apenas números. Use ponto para decimais se o campo pedir. |
| **Data** | Campo de data, com calendário. | A data pedida (devolução, exame, desativação). |
| **Seleção** | Lista com as opções cadastradas. | Escolha **uma** opção. As opções foram definidas por quem montou o checklist; não há como digitar outra. |
| **Múltipla seleção** | Lista onde dá para marcar várias. | Selecione **todas** as que se aplicam. Em computador, segure `Ctrl` para marcar mais de uma. |
| **Arquivo** | Não há campo de resposta: aparece direto a área de **Evidências privadas**. | A resposta *é* o arquivo. Anexe o documento e pronto. |
| **Confirmação obrigatória** | Uma caixa de marcação escrita *Confirmo a validação*. | Marque apenas se você de fato conferiu. É uma declaração sua, registrada com o seu nome. |

> **Dica** Respostas ficam salvas junto com a tarefa quando você conclui. Se
> precisar sair no meio, registre o andamento em uma pendência ou nas
> observações — assim o próximo colega sabe onde você parou.

---

## Anexar evidências

Algumas perguntas exigem comprovante. Nesses casos aparece o bloco **Evidências
privadas**, com o botão *Selecionar PDF, PNG ou JPEG*.

| Regra | Valor |
| --- | --- |
| Formatos aceitos | `PDF`, `PNG`, `JPG` / `JPEG` — e mais nenhum |
| Tamanho máximo | **10 MiB** por arquivo |
| Quantidade | Vários arquivos por pergunta, sem limite fixo |
| Classificação | Todo arquivo enviado pela tela entra como **Restrita** |

O sistema confere o **conteúdo** do arquivo, não só o nome. Renomear um `.docx`
para `.pdf` não funciona: o envio é recusado.

Os arquivos ficam guardados em área privada, fora do alcance de quem não tem
permissão. Todo download é registrado com o nome de quem baixou. Depois de
enviado, o arquivo aparece na lista com o nome original e o tamanho, e pode ser
baixado clicando no nome.

> **Atenção** Fotografe ou digitalize documentos de forma legível. A evidência
> existe para provar a conferência anos depois, quando ninguém mais lembrar do
> caso.

---

## Registrar uma pendência

Pendência é o registro estruturado de algo que **precisa ser resolvido,
decidido ou documentado** antes de o desligamento seguir. É diferente de uma
observação: a pendência tem dono, situação, histórico e pode travar o processo.

Registre uma pendência quando o colaborador não devolveu algo, quando falta um
documento, quando um acesso não pôde ser removido, quando há valor a acertar —
qualquer coisa que você não consiga simplesmente responder e fechar.

O formulário aparece na seção **Pendências** do cartão da tarefa, quando ela
está `Em análise`.

### Os campos do formulário

| Campo | Obrigatório | O que informar |
| --- | --- | --- |
| **Título** | Sim | Frase curta e específica, até 200 caracteres. `Notebook Dell não devolvido` é bom; `Pendência` não é. |
| **Categoria** | Sim | O tipo do problema. Veja a tabela abaixo. |
| **Bloqueio** | Sim | O quanto isso trava o processo. Veja a tabela adiante — é o campo mais importante. |
| **Item relacionado** | Não | A qual pergunta do checklist a pendência se refere. Deixe em *Tarefa em geral* se não for de nenhuma pergunta específica. Só aparecem as perguntas que aceitam pendência. |
| **Descrição** | Sim | O relato completo, até 4000 caracteres. Escreva para quem vai ler depois sem contexto nenhum: o que aconteceu, o que falta, o que já foi tentado. |

### Categorias disponíveis

| Categoria | Quando usar |
| --- | --- |
| `Valor` | Há quantia a ser analisada para eventual cobrança. **Só use esta se o seu setor estiver habilitado a lançar valores** — veja a seção sobre valores. |
| `Material` | Insumos, materiais de consumo, EPI. |
| `Ferramenta` | Ferramentas de trabalho não devolvidas. |
| `Equipamento` | Notebook, celular, monitor, rádio, máquina. |
| `Documento` | Documento que falta assinar, entregar ou apresentar. |
| `Acesso` | Login, crachá, e-mail, VPN, sistema, acesso físico a área controlada. |
| `Exame` | Exame demissional ou complementar não realizado. |
| `Atividade` | Trabalho, entrega ou passagem de conhecimento não concluída. |
| `Veículo` | Carro, moto, empilhadeira — inclusive multas e documentação. |
| `Patrimônio` | Bem patrimoniado da empresa, identificado por plaqueta ou número. |
| `Contrato` | Cláusula contratual pendente: aviso, treinamento a ressarcir, acordo. |
| `Outro` | Nenhuma das anteriores. Use com parcimônia e capriche na descrição. |

### O campo Bloqueio — leia antes de escolher

Este campo decide se a sua tarefa pode ou não ser concluída. Escolher errado
trava o desligamento sem necessidade, ou deixa passar um problema real.

| Valor | O que faz | Quando usar |
| --- | --- | --- |
| `Bloqueante` | **Impede concluir a tarefa** até que a pendência seja marcada como *Regularizada* ou *Encerrada*. | O problema tem solução e você espera resolvê-lo: o equipamento vai ser devolvido, o exame vai ser feito. |
| `Bloqueante até decisão` | **Impede concluir a tarefa** até que o Departamento Pessoal **decida** sobre o valor. Regularizar não basta. | Você está informando um valor a ser cobrado e a saída depende dessa decisão. Anda junto com a categoria `Valor`. |
| `Não bloqueante` | Fica registrada, **não impede** a conclusão. | O problema existe, está sendo tratado, mas não deve segurar o desligamento. |
| `Informativa` | Só registro, **não impede** nada. | Contexto útil para quem for ler o processo depois. Não é um problema a resolver. |

> **Atenção** `Bloqueante` sem intenção real de resolver trava o processo de
> todo mundo. Se o problema não deve segurar a saída do colaborador, use `Não
> bloqueante` e descreva bem.

---

## O ciclo de vida de uma pendência

```fluxo
titulo: Como uma pendência caminha até ser encerrada
inicio: Você registra a pendência — ela nasce **Aberta**
seta: comece a tratar
passo: **Iniciar regularização** — a situação passa para **Em regularização**
nota: use enquanto estiver cobrando, buscando ou providenciando a solução
passo: **Marcar regularizada** — a situação passa para **Regularizada**
decisao: O problema voltou ou a solução não se sustentou?
  Voltou: **Iniciar regularização** de novo — ela retorna para *Em regularização*
  Resolvido: Siga para o encerramento
passo: **Encerrar** — a situação passa para **Encerrada**
fim: A pendência não aceita mais comentários nem alterações
```

Cada botão desses **exige um comentário**. Escreva o comentário na caixa
*Comentário* antes de clicar. É esse texto que forma o histórico da pendência —
os comentários nunca são apagados nem editados, e aparecem com o nome de quem
escreveu e a data.

### As situações e o que cada uma libera

| Situação | Significado | Botões disponíveis |
| --- | --- | --- |
| `Aberta` | Registrada, ninguém começou a tratar. | *Iniciar regularização* |
| `Em regularização` | Alguém está resolvendo. | *Marcar regularizada* |
| `Regularizada` | O problema foi resolvido. Já libera a conclusão de uma pendência `Bloqueante`. | *Iniciar regularização*, *Encerrar* |
| `Encerrada` | Fechada em definitivo. | Nenhum — nem comentar |
| `Encaminhada para análise` | Um valor foi informado e aguarda o Departamento Pessoal. | Apenas *Contestar valor* |
| `Contestada` | O setor discordou do valor apurado. Voltou para o DP. | Nenhum — aguarde a decisão |
| `Aprovada para cobrança` | O DP decidiu que o valor será cobrado. | Nenhum |
| `Rejeitada` | O DP recusou a cobrança. O valor aprovado fica zero. | Nenhum |
| `Abonada` | O DP perdoou o valor. O valor aprovado fica zero. | Nenhum |

Uma pendência **decidida** — aprovada, rejeitada ou abonada — já não impede a
conclusão da tarefa, mesmo continuando aberta na tela. Não é preciso fazer mais
nada com ela.

> **Dica** Também dá para anexar arquivo diretamente à pendência, pelo botão
> *Anexar evidência à pendência*. Use para o comprovante de devolução, o
> protocolo, a foto do equipamento entregue.

---

## Valores: quando o seu setor pode cobrar algo

Alguns setores são habilitados pelo Departamento Pessoal a **informar valores**.
Se o seu não for, esta seção não se aplica — os campos simplesmente não
aparecem.

> **Nunca** O SGPD **não desconta nada de ninguém**. Informar um valor aqui é
> abrir um pedido de análise. Quem decide se aquilo vira cobrança é o
> Departamento Pessoal, em ato separado e registrado. O desconto, se houver,
> acontece depois, no Senior.

### Como informar

O campo de valor aparece dentro de uma pendência que reúna três condições: a
categoria é `Valor`, a situação é `Aberta` e nenhum valor foi informado ainda.

Preencha os dois campos e clique em **Informar valor**:

| Campo | O que informar |
| --- | --- |
| **Valor pretendido** | A quantia, em número, maior que zero. |
| **Justificativa** | Por que essa quantia. Diga a base do cálculo, o número do patrimônio, a nota fiscal, o que sustentar o pedido. |

Ao informar, a pendência passa para `Encaminhada para análise` e o Departamento
Pessoal é avisado por e-mail.

### O quadro dos cinco valores

Depois de informado, a pendência mostra um quadro com cinco linhas. Elas contam
a história da negociação:

| Linha | Quem preenche | O que é |
| --- | --- | --- |
| **Informado** | Você (o setor) | O valor que a sua área pretende cobrar. |
| **Apurado** | Departamento Pessoal | O valor que o DP calculou depois de analisar. Pode ser menor, maior ou igual. |
| **Contestado** | Você (o setor) | O valor que a sua área defende, caso discorde da apuração. |
| **Aprovado** | Departamento Pessoal | O que foi de fato aprovado na decisão. Fica **zero** se a decisão for *Rejeitada* ou *Abonada*. |
| **Processado no Senior** | Ninguém, pelo SGPD | Fica vazio até que a rescisão seja processada no Senior. O SGPD só reflete; nunca preenche por conta própria. |

### Contestar

Enquanto a pendência estiver em `Encaminhada para análise`, você pode discordar
do valor apurado pelo DP. Preencha **Valor contestado** e **Justificativa da
contestação** e clique em **Contestar valor**.

A pendência passa para `Contestada` e volta à mesa do Departamento Pessoal, que
é avisado novamente.

### A decisão

Apurar e decidir são atos do Departamento Pessoal — os botões correspondentes
não aparecem para você. Se a tela mostrar o aviso *"A decisão sobre a pretensão
é do DP vigente no escopo do processo"*, é exatamente isso.

A decisão tem três resultados possíveis:

| Decisão | Efeito |
| --- | --- |
| `Aprovada para cobrança` | O valor aprovado é registrado e segue para tratamento no Senior. |
| `Rejeitada` | A cobrança é recusada. Valor aprovado igual a zero. |
| `Abonada` | A cobrança é perdoada. Valor aprovado igual a zero. |

Toda decisão vem com um **parecer** escrito, o nome de quem decidiu e a data.
Você recebe um e-mail quando ela sai.

---

## Concluir a tarefa

Quando tudo estiver respondido e resolvido, preencha o campo **Observações da
conclusão** — opcional, mas é o lugar certo para o resumo do que a sua área
apurou — e clique em **Concluir tarefa**.

O sistema faz uma última conferência. Se algo faltar, ele recusa e diz o que é.

### Por que a conclusão pode ser recusada

| Mensagem / causa | O que fazer |
| --- | --- |
| Falta resposta obrigatória | Procure as perguntas marcadas com **\*** que ainda estão em branco. |
| Falta evidência obrigatória | Alguma pergunta exige comprovante e não tem arquivo anexado. |
| Pendência bloqueante não regularizada | Trate a pendência `Bloqueante` até `Regularizada` ou `Encerrada`. |
| Pendência de valor à espera da decisão | A pendência é `Bloqueante até decisão` e o DP ainda não decidiu. Regularizar não resolve — é preciso esperar a decisão ou encerrar a pendência. |
| A tarefa foi alterada por outra sessão | Um colega do setor mexeu na tarefa enquanto você trabalhava. **Recarregue a página** e confira o que mudou antes de refazer. |

Depois de concluída, a tarefa sai do grupo de ativas e passa para o de
concluídas, mostrando as respostas registradas como texto, com data e hora.

> **Atenção** Concluir não é irreversível, mas voltar atrás exige o
> Departamento Pessoal — e, na maioria dos casos, um SuperAdmin. Confira antes
> de clicar.

---

## Os e-mails que você recebe

O SGPD avisa por e-mail. Todos os responsáveis vigentes do setor recebem a mesma
mensagem.

| Aviso | Quando chega |
| --- | --- |
| **Tarefa atribuída ao setor** | Assim que o processo é iniciado e a tarefa do seu setor é criada. |
| **Tarefa a vencer** | 48 horas antes do prazo. |
| **Tarefa próxima do vencimento** | 24 horas antes do prazo. |
| **Tarefa vencida** | No momento do vencimento. O Departamento Pessoal recebe junto. |
| **Tarefa vencida em nível crítico** | 48 horas depois do vencimento. Vai também para o setor de escalada. |
| **Valor decidido** | Quando o DP decide uma pretensão que o seu setor informou. |
| **Processo cancelado** / **Processo reaberto** | Quando o processo muda de rumo e afeta a sua tarefa. |

> **Importante** O e-mail **não traz** o nome do colaborador, CPF, valores nem
> pareceres. Ele diz o que fazer e onde. O dado fica no sistema, protegido por
> login — isso é exigência de proteção de dados, não limitação técnica.

Pode acontecer de o mesmo aviso chegar duas vezes. É comportamento previsto: o
sistema prefere avisar duas vezes a deixar de avisar.

---

## Dúvidas frequentes

**Não vejo nenhuma tarefa, mas sei que existe um desligamento em andamento.**
Você só enxerga tarefas dos setores em que tem vínculo **vigente** e dentro do
escopo (empresa e filial) daquele setor. Vínculo com data de fim já passada não
mostra nada. Fale com o Departamento Pessoal.

**Um colega já iniciou a análise. Posso continuar?**
Pode. A tarefa é do setor. Só evite trabalhar os dois ao mesmo tempo na mesma
tarefa — quem salvar depois vai receber o aviso de alteração concorrente.

**Respondi errado e já concluí.**
Peça ao Departamento Pessoal. Reabrir uma tarefa concluída é ato de SuperAdmin,
registrado com motivo.

**A pergunta que preciso responder não existe no checklist.**
O checklist é definido por quem configura os templates. Registre o assunto como
pendência `Informativa` e peça ao Departamento Pessoal a inclusão da pergunta
para os próximos processos. Templates são versionados: mudanças novas não
alteram processos já iniciados.

**Anexei o arquivo errado.**
Anexe o correto e explique em um comentário na pendência ou nas observações da
conclusão. Evidências não são apagadas — o histórico é preservado por
exigência de auditoria.

**O prazo é curto demais para o meu setor.**
O prazo vem da configuração do setor ou do grupo. Peça ao Departamento Pessoal
a revisão do tempo padrão. Tarefas já criadas mantêm o prazo original.

**Errei a classificação de bloqueio da pendência.**
Não há como editar o campo depois de registrada. Encerre a pendência com um
comentário explicando o erro e registre outra com a classificação correta —
tudo fica no histórico.

---

## Em uma página

1. Entre em **https://sgpd.bsabioenergia.com.br** com o usuário da rede.
2. Abra **Minhas tarefas** e localize o colaborador.
3. Clique em **Iniciar análise**.
4. Responda tudo que tiver **\*** e anexe as evidências pedidas (PDF, PNG ou
   JPEG, até 10 MiB).
5. Registre **pendência** para o que ficou pendente — escolhendo o bloqueio com
   cuidado.
6. Trate a pendência: *Iniciar regularização* → *Marcar regularizada* →
   *Encerrar*, sempre com comentário.
7. Se o seu setor lança valores, use **Informar valor** com justificativa. Quem
   decide é o DP.
8. Preencha as **Observações da conclusão** e clique em **Concluir tarefa**.
9. Se for recusada, leia a mensagem: ela diz exatamente o que falta.
