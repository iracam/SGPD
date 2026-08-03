# Manuais operacionais

Documentos entregues a quem **usa** o SGPD — não são documentação técnica. O
público é usuário final: nada de API, tabela, migration ou nome de classe.

| Manual | Para quem | Fonte |
| --- | --- | --- |
| Manual do Responsável de Área | quem responde por um setor de validação | `responsaveis-de-area.md` |
| Manual do Departamento Pessoal | quem tem a atribuição `DP` | `departamento-pessoal.md` |
| Manual de Configuração | quem cadastra setores, templates, grupos e regras | `grupos-templates-regras.md` |

Cada manual tem três arquivos: o `.md` (fonte), o `.html` e o `.pdf` (entregas).

## Corrigir e regerar

**Edite sempre o `.md`.** O `.html` e o `.pdf` são gerados e qualquer alteração
neles é perdida na próxima execução.

```bash
node docs/operacao/build.mjs                             # regera os três
node docs/operacao/build.mjs --html                      # só o HTML, sem abrir o Chromium
node docs/operacao/build.mjs docs/operacao/um-manual.md  # um manual específico
```

O gerador não usa nenhuma dependência do projeto: o conversor Markdown vive em
`build.mjs` e o PDF sai do Chromium já instalado no host, dirigido por CDP. Se o
executável estiver em outro caminho, aponte com `CHROME_BIN`.

A aparência está em `manual.css`, embutida no HTML durante a geração — os
arquivos abrem sem rede.

## O Markdown aceito

Títulos (`##` vira seção do sumário e começa página nova no PDF), parágrafos,
listas, tabelas, `**negrito**`, `*itálico*`, `` `código` ``, links, réguas,
blocos de código e HTML cru.

**Front matter** no topo do arquivo alimenta a capa:

```text
---
titulo: Manual do Responsável de Área
subtitulo: uma linha explicando o escopo
selo: Manual operacional
publico: quem deve ler
versao: 1.0
data: 03/08/2026
sistema: https://sgpd.bsabioenergia.com.br
---
```

**Destaques** saem de blocos de citação, e a primeira palavra em negrito define
a cor: `Atenção` e `Cuidado` (âmbar), `Importante` e `Regra` (verde), `Nunca` e
`Proibido` (vermelho), `Dica` e `Exemplo` (azul).

```text
> **Atenção** Texto do destaque.
```

**Fluxogramas** saem de um bloco ` ```fluxo `, uma linha por elemento:

```text
​```fluxo
titulo: Legenda do fluxograma
inicio: Primeiro nó, arredondado e verde
passo: Nó comum
seta: rótulo da ligação que vem em seguida
nota: observação presa ao nó anterior
decisao: Pergunta que bifurca?
  Sim: o que acontece por este caminho
  Não: o que acontece pelo outro
alerta: Nó de advertência, em vermelho
fim: Último nó, arredondado e escuro
​```
```

Os ramos são as linhas **indentadas com dois espaços** logo abaixo de uma
`decisao:`; o texto antes dos dois-pontos vira o rótulo. Funciona com dois ou
três ramos — acima disso o fluxograma fica ilegível no papel, prefira dividir em
dois diagramas.

**Quebra de página**: uma linha contendo só `[pagina]` força página nova no PDF
(no HTML não tem efeito). Um fluxograma que não cabe é quebrado entre os nós, o
que às vezes deixa um nó órfão na página seguinte — nesse caso ponha um
`[pagina]` antes dele. Fluxograma com mais de dez linhas raramente cabe inteiro:
prefira dividir o diagrama a empurrá-lo.

## Como o sistema entrega estes manuais

A SPA tem um botão **Ajuda** no cabeçalho de três telas, que abre o manual em aba
nova já na seção correspondente (ADR-053):

| Tela | Manual | Âncora |
| --- | --- | --- |
| Minhas tarefas | `responsaveis-de-area` | `a-tela-minhas-tarefas` |
| Processos | `departamento-pessoal` | `acompanhar-os-processos` |
| Grupos e templates | `grupos-templates-regras` | `o-que-voce-vai-configurar` |

O HTML é servido por `apps.core.views.manual` em `/ajuda/<slug>/`, lendo **deste
diretório** e exigindo sessão autenticada — os manuais não vão para o bundle do
Angular, que o WhiteNoise entregaria sem login.

Duas consequências para quem edita:

- **o arquivo gerado precisa existir no host.** Rodar o `build.mjs` faz parte de
  publicar uma correção; sem o `.html`, a ajuda responde 503;
- **renomear um `##` quebra a âncora.** O `id` vem do título, então a tela
  continua abrindo o manual, mas na capa. Ao renomear uma seção da tabela acima,
  ajuste o `secao` do `<app-ajuda-link>` correspondente.

Para acrescentar ajuda a outra tela: registre o slug em `OPERATION_MANUALS`
(`apps/core/views.py`) e ponha `<app-ajuda-link manual="..." secao="...">` nas
ações do cabeçalho.

## Ao alterar o comportamento do sistema

Estes manuais descrevem telas, campos e valores. Mudança em rótulo de tela, em
opção de campo, em regra de bloqueio ou no ciclo de estados **precisa** ser
refletida aqui — do contrário o manual passa a mentir para quem opera.
