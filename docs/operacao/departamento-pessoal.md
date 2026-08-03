---
titulo: Manual do Departamento Pessoal
subtitulo: Conduzir o desligamento de ponta a ponta — abertura, acompanhamento, decisão de valores, liberação e encerramento.
selo: Manual operacional
publico: Quem tem a atribuição DP no SGPD e coordena o processo demissional
versao: 1.0
data: 03/08/2026
sistema: https://sgpd.bsabioenergia.com.br
---

## O seu papel no sistema

Você é quem conduz o processo. O SGPD organiza o desligamento entre o
Departamento Pessoal e as áreas: você abre o processo, escolhe quais setores
precisam validar, acompanha o que cada um respondeu, decide sobre os valores que
as áreas pediram, libera a rescisão e encerra o caso.

Todos os atos importantes são registrados com o seu nome, a data e o motivo. Não
existe alteração silenciosa: a trilha de auditoria é permanente e não pode ser
apagada.

> **Importante** O SGPD **não substitui o Senior**. Ele não calcula rescisão, não
> aplica desconto, não movimenta o vínculo e não escreve nada nas tabelas do
> Senior. O Senior continua sendo a fonte oficial. O SGPD organiza a conferência
> que acontece **antes** da rescisão e guarda a prova de que ela foi feita.

### O que só você pode fazer

- Abrir um processo de desligamento e escolher os grupos de validação.
- Iniciar o processo, o que gera as tarefas dos setores.
- **Apurar** e **decidir** os valores que as áreas informaram.
- **Liberar** o processo para rescisão.
- Registrar que a rescisão foi processada e **encerrar** o processo.
- **Cancelar** um processo.

Reabrir um processo já liberado ou encerrado é ato exclusivo de SuperAdmin — nem
mesmo quem liberou desfaz o próprio ato sozinho.

### Escopo: o que você enxerga

A sua atribuição DP tem um escopo organizacional: pode ser **global**, de uma
**empresa** ou de uma **filial**. Você só enxerga e movimenta processos dentro
do seu escopo. Se um processo que você espera ver não aparece, quase sempre é
disso que se trata.

---

## O caminho completo do processo

```fluxo
titulo: Da abertura até o processo ficar pronto para liberar
inicio: Você abre o processo escolhendo o colaborador — ele nasce **Rascunho**
passo: O sistema copia os dados do colaborador do Senior (o **snapshot**) e sugere os grupos
passo: Você confirma ou ajusta os grupos e clica em **Salvar seleção**
passo: Você clica em **Iniciar processo e gerar tarefas** — o processo passa a **Iniciado**
seta: cada setor recebe e-mail
passo: Os setores respondem os checklists, anexam evidências e registram pendências
decisao: Alguma área informou valor a cobrar?
  Sim: Você **apura** e **decide** cada pretensão — aprovar, rejeitar ou abonar
  Não: Siga o acompanhamento normal
fim: Sem impedimentos, o processo fica **Pronto para análise do DP**
```

Daí em diante vem o **ciclo formal** — liberar, registrar o processamento da
rescisão e encerrar. Ele tem um diagrama próprio na seção *Liberar, registrar o
processamento e encerrar*.

Em qualquer momento antes da liberação, o processo pode ser **cancelado** com
justificativa. Cancelamento é terminal: não há volta.

---

## Abrir um processo

Vá em **Processos** e clique em **Abrir processo**, ou vá direto pelo menu. A
tela tem duas partes: escolher o colaborador e preencher os dados da abertura.

### Escolher o colaborador

A busca é em cascata: cada passo depende do anterior, e os dados vêm do Senior
em tempo real.

1. **Empresa** — identificada pela razão social.
2. **Filial** — só carrega depois que a empresa é escolhida.
3. **Tipo de colaborador** — só carrega depois da filial.
4. **Colaborador** — a lista final. Há um campo de busca por **nome ou
   matrícula** para não precisar rolar tudo.

Escolhido o colaborador, os dados dele aparecem para conferência. Confira o
nome e a matrícula antes de seguir: é esse retrato que será congelado.

> **Atenção** Os dados são copiados na abertura e **não se atualizam mais**. Se
> o colaborador mudar de cargo ou centro de custo no Senior depois disso, o
> processo continua com o que valia no dia da abertura. É proposital: o processo
> precisa refletir a situação que motivou a conferência.

### Preencher a abertura

| Campo | Obrigatório | O que informar |
| --- | --- | --- |
| **Data prevista de desligamento** | Sim | A data em que o desligamento deve ocorrer. É informativa para as áreas. |
| **Data limite** | Sim | Até quando todo o processo precisa estar concluído. **Este campo influencia os prazos das tarefas** — veja abaixo. |
| **Prioridade** | Sim | Campo de texto livre, até 50 caracteres. O sistema não interpreta o conteúdo: use o vocabulário combinado na sua equipe, como `Normal`, `Urgente` ou `Alta`. Padronize — o texto aparece nas listagens e nos relatórios. |
| **Motivo** | Sim | Até 2000 caracteres. O motivo do desligamento, no nível de detalhe que a empresa exige. |
| **Observações** | Não | Até 4000 caracteres. Contexto adicional para quem for ler o processo depois. |

Clique em **Abrir processo**. O sistema consulta o Senior mais uma vez, confere
a sua autoridade, cria o processo, grava o snapshot e registra o evento — tudo
em uma única operação. Se qualquer parte falhar, nada é gravado.

### Por que o sistema pode recusar a abertura

- **Já existe processo em aberto para esse colaborador.** Não é permitido ter
  dois processos vivos para a mesma pessoa. Encerre ou cancele o anterior — o
  cancelamento libera o colaborador para um processo novo imediatamente.
- **O colaborador não foi encontrado no Senior** no instante da gravação.
- **A sua atribuição DP não alcança a empresa ou filial** do colaborador.

---

## O rascunho: escolher os grupos

Um processo recém-aberto fica em **Rascunho**. Ele ainda não gerou tarefa
nenhuma e ninguém foi avisado. Abra-o em **Processos → Rascunhos**.

### A sugestão automática

Se houver **regras de aplicabilidade** cadastradas que combinem com o snapshot
do colaborador, a tela mostra um aviso com os grupos sugeridos e o nome da regra
que sugeriu cada um. Os grupos vêm **pré-marcados**.

> **Importante** A regra **sugere, não aplica**. Nada é selecionado de verdade
> até você clicar em **Salvar seleção**. A responsabilidade da escolha continua
> sendo sua: desmarque o que não se aplica e acrescente o que faltou.

Se não houver regra cadastrada, não há sugestão e você escolhe manualmente.

### Escolher e salvar

No campo **Grupos aplicáveis**, marque os grupos. Só aparecem grupos que tenham
**versão publicada** e que atendam ao escopo do processo. Clique em **Salvar
seleção**.

O bloco **Setores que serão gerados** mostra o resultado: cada setor que vai
receber tarefa, com o template e a versão que serão usados, o SLA em horas e as
marcas **Obrigatório** e **Bloqueante**.

### Iniciar o processo

Clique em **Iniciar processo e gerar tarefas**. A partir daí não há mais volta
para o rascunho: as tarefas são criadas, os checklists são congelados na versão
vigente e os setores recebem e-mail.

Se o botão estiver indisponível, o bloco **O início está bloqueado** lista o
motivo:

| Impedimento | Como resolver |
| --- | --- |
| Nenhum setor foi resolvido | Nenhum grupo selecionado, ou os grupos não têm setor aplicável ao escopo. Revise a seleção. |
| Setor sem responsável vigente | Algum setor obrigatório não tem ninguém respondendo por ele hoje. Cadastre ou renove o responsável em **Setores**. |
| Templates diferentes para o mesmo setor | Dois grupos selecionados mandam o mesmo setor usar templates diferentes. Escolha só um dos grupos, ou ajuste a configuração. |
| A seleção foi alterada e não salva | Clique em **Salvar seleção** antes de iniciar. |

> **Dica** Quando dois grupos mandam o **mesmo** setor com o **mesmo** template,
> o sistema consolida sozinho: obrigatoriedade e bloqueio somam (basta um dos
> dois exigir), e prevalece o **menor** prazo. Só templates diferentes é que
> travam.

### De onde vem o prazo de cada tarefa

O prazo é fixado no início e não se recalcula depois. Vale o que vier primeiro
entre a **data limite do processo** e o **momento do início mais o SLA
resolvido**.

O SLA resolvido segue esta ordem de precedência — vale o primeiro que existir:

1. ajuste manual feito no rascunho;
2. SLA específico definido no grupo para aquele setor;
3. SLA padrão do template;
4. prazo padrão do setor.

---

## Acompanhar os processos

A tela **Processos** é o centro do acompanhamento. Ela tem quatro cartões:

| Cartão | O que reúne |
| --- | --- |
| **Rascunhos** | Abertos e ainda não iniciados. Não geraram tarefa nem aviso. |
| **Em Aberto** | Iniciados com ao menos uma tarefa ainda não concluída. |
| **Concluídos** | Todas as tarefas concluídas, ou processo já encerrado. |
| **Cancelados** | Cancelados com justificativa. O histórico permanece inteiro. |

Expandindo um processo, você vê as tarefas de cada setor com a situação de cada
uma, além de dois atalhos:

- **Conferir valores do processo** — o consolidado das pretensões de cobrança.
- **Conferir encerramento do processo** — prontidão, atos formais e as ações de
  liberação, processamento, encerramento, cancelamento e reabertura.

### Estado formal e situação calculada: não confunda

Esta é a distinção mais importante da tela de encerramento, e vale entendê-la
bem.

O **estado formal** é o que foi **decidido por alguém**. São seis valores, e
cada um só muda por um ato humano explícito:

| Estado formal | Significa |
| --- | --- |
| `Rascunho` | Aberto, sem tarefas geradas. |
| `Iniciado` | Tarefas criadas, setores trabalhando. |
| `Liberado para rescisão` | Você autorizou o prosseguimento. |
| `Rescisão processada` | Você declarou que a rescisão foi processada no Senior. |
| `Encerrado` | Processo fechado. |
| `Cancelado` | Processo cancelado com justificativa. Terminal. |

A **situação calculada** é **onde o trabalho está** neste instante. Ela não é
gravada em lugar nenhum: o sistema a recalcula toda vez que a tela é aberta.

| Situação calculada | Significa |
| --- | --- |
| `Rascunho` | Espelha o estado formal. |
| `Em validação` | Há tarefas em andamento e nada de especial travando. |
| `Com pendências` | Existe pendência aberta. |
| `Aguardando regularização` | Alguma pendência está em regularização. |
| `Aguardando decisão` | Existe pretensão de valor esperando a sua decisão. |
| `Pronto para análise do DP` | Nenhum impedimento resta: dá para liberar. |
| `Liberado para rescisão`, `Rescisão processada`, `Encerrado`, `Cancelado` | Espelham o estado formal, que já responde tudo. |

> **Atenção** Um processo pode estar formalmente `Iniciado` e calculadamente
> `Pronto para análise do DP`. Isso **não** quer dizer que ele foi liberado —
> quer dizer que já pode ser. A liberação continua sendo um clique seu.

---

## Decidir sobre valores

Quando uma área informa uma pretensão de cobrança, ela vai para a sua mesa e
você recebe um e-mail. As ações ficam dentro da pendência, em **Minhas tarefas**.

> **Nunca** Informar um valor no SGPD **não desconta nada de ninguém**. A
> pretensão é um pedido de análise. Mesmo aprovada, o desconto só existe se for
> lançado no Senior, fora deste sistema. O campo *Processado no Senior*
> permanece vazio até que isso aconteça.

### As duas ações que são suas

**Registrar apuração** — você informa o **Valor apurado** e a **Justificativa da
apuração**. É o valor que o DP entende como correto depois de analisar. Pode ser
menor, igual ou maior que o informado pela área.

Se a área discordar, ela pode **contestar**, e a pendência volta para você com o
valor contestado registrado.

**Registrar decisão** — o ato final. Escolha o resultado, escreva o **Parecer**
e confirme:

| Decisão | Efeito | Quando usar |
| --- | --- | --- |
| `Aprovada para cobrança` | Registra o **Valor aprovado**, que você informa. Exige o campo preenchido. | A cobrança procede, no valor que você determinou. |
| `Rejeitada` | Valor aprovado resolvido em **zero**. O campo de valor aprovado é recusado se preenchido. | A cobrança não procede: o pedido não se sustenta. |
| `Abonada` | Valor aprovado resolvido em **zero**. O campo de valor aprovado é recusado se preenchido. | A cobrança procederia, mas a empresa decide perdoar. |

A diferença entre *Rejeitada* e *Abonada* não muda o valor — muda o registro.
Uma diz que não havia o que cobrar; a outra diz que havia e foi perdoado. O
parecer explica.

### A regra de segregação

**Quem informou o valor não pode decidir sobre ele.** Se você mesmo registrou a
pretensão, o sistema recusa a sua decisão com uma mensagem explícita: outro DP
precisa decidir.

A única exceção é o SuperAdmin, que decide sem barreira — e nesse caso o sistema
marca a decisão como **segregação rompida**, com destaque na tela de conferência
e registro permanente na trilha. É exceção auditada, não atalho.

### Conferir os valores do processo

O atalho **Conferir valores do processo** abre uma tela somente de leitura com:

- o **total por moeda** — valores em moedas diferentes nunca são somados juntos;
- uma linha por pretensão, com o setor de origem, os cinco montantes e a
  situação;
- a contagem das que **ainda aguardam decisão**;
- uma seção **Segregação rompida**, quando houver decisão de SuperAdmin sobre
  valor que ele mesmo informou.

> **Atenção** O total por moeda soma **o valor informado de todas as
> pretensões**, inclusive as rejeitadas e as abonadas. Para saber o que de fato
> vira cobrança, leia a coluna do **valor aprovado**, não o total.

---

## Liberar, registrar o processamento e encerrar

Tudo isso acontece na tela aberta pelo atalho **Conferir encerramento do
processo**.

```fluxo
titulo: O ciclo formal, ato por ato
inicio: Processo **Iniciado**, com os setores trabalhando
passo: A **prontidão** é recalculada toda vez que a tela abre
decisao: Restou algum impedimento?
  Sim: O botão de liberar fica indisponível e a lista mostra o que falta
  Não: O botão de liberar fica disponível
passo: **Liberar para rescisão** — com observação opcional
seta: a rescisão é processada no Senior, fora do SGPD
passo: **Registrar processamento** — número declarado e data
passo: **Encerrar processo** — exige que nenhuma pendência siga em curso
fim: Processo **Encerrado**
```

### A prontidão

O quadro de prontidão mostra quatro contagens — tarefas concluídas, tarefas em
aberto, pendências bloqueantes e pretensões sem decisão — e duas listas.

**Impedimentos** travam a liberação. Cada linha diz exatamente o que falta:

| Impedimento típico | O que fazer |
| --- | --- |
| A tarefa obrigatória de *X* não foi concluída | Cobre o setor. Se a tarefa for desnecessária neste caso, cancele o processo e abra outro com os grupos corretos. |
| A pendência bloqueante *X* de *Y* não foi regularizada | O setor precisa marcá-la como regularizada ou encerrada. |
| A pendência *X* de *Y* aguarda a decisão sobre a pretensão | É a sua decisão que falta. Vá a **Minhas tarefas** e decida. |
| A pretensão de *X* em *Y* ainda não foi decidida | Mesmo caso do anterior. |
| O item obrigatório *X* de *Y* está sem resposta / sem evidência | Um dado mudou depois que a tarefa foi concluída. Peça a reabertura da tarefa a um SuperAdmin. |
| O processo não possui tarefas de setor | Processo iniciado sem setor resolvido. Cancele e abra corretamente. |

**Avisos** não travam nada — são conferência. Aparecem, por exemplo, quando uma
tarefa **opcional** segue em aberto ou quando existe pendência não bloqueante
ainda aberta. Leia antes de liberar; a decisão de seguir é sua.

> **Importante** O que a tela mostrou não decide nada. Ao clicar em liberar, o
> sistema **refaz** a verificação. Se um setor registrou uma pendência
> bloqueante nos segundos em que você lia a página, a liberação é recusada — e
> está certo.

### Registrar o processamento

Disponível quando o processo está `Liberado para rescisão`.

| Campo | Obrigatório | Regras |
| --- | --- | --- |
| **Número declarado da rescisão** | Sim | Até 60 caracteres. É o número que identifica a rescisão no Senior. |
| **Data do processamento** | Sim | **Não pode ser futura** e **não pode ser anterior à liberação**. |
| **Observação** | Não | Até 1000 caracteres. |

> **Atenção** Isto é uma **declaração sua**, feita por conferência humana. O
> SGPD não lê nem escreve a rescisão no Senior: ele registra que você conferiu e
> qual número você conferiu. Confira no Senior antes de declarar.

### Encerrar

Disponível quando o processo está `Rescisão processada`. Exige que **nenhuma
pendência continue em curso** — ou seja, nenhuma em `Aberta`, `Em regularização`,
`Encaminhada para análise` ou `Contestada`. Pendências `Regularizada`,
`Encerrada` ou já decididas não impedem.

Se houver impedimento, a tela lista qual pendência e em que situação ela está.

### Cancelar

Disponível para processo em `Rascunho` ou `Iniciado`. Exige **Motivo do
cancelamento** preenchido.

O cancelamento cancela as tarefas ainda abertas, libera o colaborador para um
processo novo e preserva todo o histórico — pendências, evidências, comentários
e trilha continuam existindo.

> **Nunca** Cancelamento é **terminal**. Um processo cancelado não volta. Para
> retomar o desligamento, abra um processo novo — os dois ficam registrados.

### Reabrir

Só aparece para **SuperAdmin**, e apenas em processo `Liberado para rescisão`,
`Rescisão processada` ou `Encerrado`.

A reabertura exige **Motivo**, desfaz as marcas formais, registra o estado
anterior inteiro na trilha e permite escolher quais tarefas concluídas voltam
para análise do setor. Sem nenhuma marcada, corrige apenas a marca formal sem
devolver trabalho a ninguém.

A reabertura é recusada se, nesse meio-tempo, outro processo já tiver sido
aberto para o mesmo colaborador.

---

## Relatórios

O menu **Relatórios** responde por período: escolha a data inicial e a final.
Todo número é calculado na hora da consulta — não há contador guardado que possa
envelhecer.

| Bloco | O que mostra |
| --- | --- |
| **Tempo médio** | Duração média do ciclo, o mesmo tempo aberto por setor, processos liberados por mês e distribuição por empresa. |
| **Pendências e valores** | Pendências agrupadas por categoria; total informado e total aprovado. |
| **Atrasos** | Processos vencidos e os setores que mais atrasam. |
| **Exportações** | Histórico de quem exportou o quê e quando. |

> **Atenção** O bloco de atrasos é uma **fotografia do instante da consulta**,
> não um recorte do período. Ele responde "o que está atrasado agora", não "o
> que atrasou naquele mês".

### Exportar

A exportação sai em **CSV** e cobre três conjuntos: `Processos`, `Tarefas de
setor` e `Pendências e valores`. Toda exportação é registrada de forma
permanente com o seu nome, o conjunto e o momento — o arquivo sai do sistema
levando dados pessoais, e a empresa precisa saber quem o levou.

Trate o arquivo exportado com o mesmo cuidado do sistema: ele não tem login.

---

## Notificações

O SGPD avisa por e-mail e guarda a fila em **Notificações**. Nada é enviado
durante a sua navegação: os avisos entram em uma fila e um serviço agendado os
despacha.

### Os avisos automáticos de prazo

| Aviso | Quando dispara | Quem recebe |
| --- | --- | --- |
| **Tarefa a vencer** | 48 h antes do prazo | responsáveis do setor |
| **Tarefa próxima do vencimento** | 24 h antes | responsáveis do setor |
| **Tarefa vencida** | no vencimento | responsáveis do setor **e você** |
| **Tarefa vencida em nível crítico** | 48 h após o vencimento | os anteriores mais o setor de escalada |
| **Processo próximo do limite** | 72 h antes da data limite, com tarefa em aberto | **você** |

Há ainda avisos ligados a fatos: tarefa atribuída ao setor, pendência bloqueante
registrada, valor aguardando decisão, valor decidido, processo cancelado e
processo reaberto.

### O painel da fila

A tela mostra o resumo por situação — `Pendente`, `Em envio`, `Enviada`,
`Falha`, `Cancelada` — e permite abrir cada mensagem para ver o erro da última
tentativa e o corpo enviado.

Mensagens em **Falha** podem ser reprocessadas pelo botão correspondente.
Mensagens já entregues não podem: reenviar duplicaria o e-mail.

> **Importante** O e-mail **nunca** carrega nome do colaborador, CPF, valor ou
> parecer. O corpo diz o que fazer e onde; o dado fica no sistema, protegido por
> login. É exigência de proteção de dados.
>
> A entrega é *ao menos uma vez*: em caso de falha na confirmação, o aviso pode
> chegar duplicado. Duplicar aviso é aceitável; perder aviso não é.

### Quando ninguém é avisado

Se um setor estiver **sem responsável vigente**, ou se um processo estiver **sem
DP no escopo**, o marco de prazo é contado mas o aviso não sai — e ninguém é
avisado disso automaticamente. Vale conferir periodicamente se os setores ativos
têm responsável com vínculo válido.

Se a fila parar de andar (mensagens acumulando em `Pendente`), acione o
responsável técnico: o serviço agendado de despacho pode ter parado.

---

## Dúvidas frequentes

**Abri o processo com a data limite errada.**
Cancele o processo — se ainda estiver em rascunho, nada foi gerado — e abra
outro. Não há edição da data limite depois da abertura.

**Selecionei o grupo errado e já iniciei.**
As tarefas já foram criadas e os setores já foram avisados. Cancele o processo
com justificativa e abra outro com os grupos corretos. O cancelamento libera o
colaborador imediatamente.

**Um setor concluiu a tarefa errado.**
Só um SuperAdmin reabre tarefa concluída, pela reabertura do processo — e isso
exige que o processo já esteja liberado, processado ou encerrado. Se o processo
ainda estiver `Iniciado`, a alternativa é registrar o ocorrido e tratar por
pendência.

**A prontidão diz que falta evidência em uma tarefa que já foi concluída.**
Isso indica que algo mudou depois da conclusão. É a "inconsistência crítica":
peça a reabertura ao SuperAdmin para o setor corrigir.

**Preciso cobrar um valor mas o setor não tem a opção.**
O setor precisa estar configurado com **Permite lançar valores**. Ajuste em
**Setores** — a mudança vale para as pendências criadas dali em diante.

**Encerrei e percebi um erro.**
Só SuperAdmin reabre. A reabertura registra o estado anterior inteiro e exige
motivo.

**Um processo sumiu da lista.**
Confira o cartão certo: ao concluir a última tarefa, o processo sai de **Em
Aberto** e vai para **Concluídos**. Cancelados têm cartão próprio. E confira o
seu escopo.

---

## Em uma página

1. **Processos → Abrir processo**. Escolha empresa, filial, tipo e colaborador.
2. Preencha data prevista, data limite, prioridade e motivo. **Abrir processo**.
3. No rascunho, confirme os grupos sugeridos e clique em **Salvar seleção**.
4. Confira os setores resolvidos e clique em **Iniciar processo e gerar tarefas**.
5. Acompanhe pelo cartão **Em Aberto**. Cobre os atrasados.
6. Decida as pretensões de valor: **apurar** e depois **decidir**. Lembre que
   quem informou não decide.
7. Abra **Conferir encerramento do processo** e leia os impedimentos.
8. Sem impedimento, **Liberar para rescisão**.
9. Processe a rescisão no Senior e volte para **Registrar processamento** com
   número e data.
10. **Encerrar processo** quando nenhuma pendência seguir em curso.
