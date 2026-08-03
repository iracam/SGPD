#!/usr/bin/env node
/**
 * Gera as versões HTML e PDF dos manuais operacionais a partir dos `.md`.
 *
 * O `.md` é a fonte: corrija sempre lá e rode `node docs/operacao/build.mjs`.
 * Sem dependências novas — o conversor Markdown vive neste arquivo e o PDF sai
 * do Chromium já instalado, dirigido por CDP (o mesmo caminho da homologação
 * visual). Nada é baixado: o CSS é embutido no HTML gerado.
 *
 * Uso:
 *   node docs/operacao/build.mjs             # todos os manuais
 *   node docs/operacao/build.mjs --html      # só o HTML, sem abrir o Chromium
 *   node docs/operacao/build.mjs arquivo.md  # um manual específico
 */

import { spawn } from 'node:child_process';
import { mkdtemp, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { existsSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const AQUI = path.dirname(fileURLToPath(import.meta.url));

/* ------------------------------------------------------------------ *
 * Markdown — subconjunto suficiente para estes manuais
 * ------------------------------------------------------------------ */

const escapar = (texto) =>
  texto
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');

/**
 * Negrito, itálico, código e link. O texto já chega escapado como HTML.
 *
 * Código entre crases e caracteres protegidos por contrabarra saem de cena
 * antes das demais substituições — senão um asterisco dentro deles viraria
 * ênfase. Os marcadores usam caracteres de controle justamente por não poderem
 * aparecer no texto original.
 */
function inline(texto) {
  const codigos = [];
  const literais = [];

  let saida = texto.replace(/`([^`]+)`/g, (_, conteudo) => {
    codigos.push(conteudo);
    return `\u0000${codigos.length - 1}\u0000`;
  });
  saida = saida.replace(/\\([\\`*_{}[\]()#+\-.!|])/g, (_, caractere) => {
    literais.push(caractere);
    return `\u0001${literais.length - 1}\u0001`;
  });

  saida = saida
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>');

  return saida
    .replace(/\u0001(\d+)\u0001/g, (_, indice) => literais[Number(indice)])
    .replace(/\u0000(\d+)\u0000/g, (_, indice) => `<code>${codigos[Number(indice)]}</code>`);
}

const slug = (texto) =>
  texto
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');

/** Palavra em negrito no início do bloco de citação vira o tom do destaque. */
const TONS_DESTAQUE = {
  atencao: 'atencao',
  atenção: 'atencao',
  cuidado: 'atencao',
  importante: 'importante',
  nunca: 'proibido',
  proibido: 'proibido',
  dica: 'dica',
  exemplo: 'dica',
  regra: 'regra',
  lembre: 'dica',
};

/* --- fluxogramas -------------------------------------------------- */

const TIPOS_NO = {
  inicio: 'inicio',
  passo: 'passo',
  decisao: 'decisao',
  fim: 'fim',
  alerta: 'alerta',
};

/**
 * Bloco ```fluxo — uma linha por elemento:
 *
 *   titulo: Legenda do fluxograma
 *   inicio: | passo: | decisao: | fim: | alerta:   nós
 *   seta:   rótulo da seta que vem logo abaixo
 *   nota:   observação presa ao nó anterior
 *   <dois espaços>rótulo: texto                    ramo de uma decisão
 */
function renderizarFluxo(fonte) {
  const linhas = fonte.split('\n').filter((linha) => linha.trim() !== '');
  let titulo = '';
  const partes = [];
  let ramosAbertos = null;

  const fecharRamos = () => {
    if (!ramosAbertos) return;
    // `--ramos` alimenta a barra de distribuição do CSS, que precisa saber
    // quantas colunas ligar.
    partes.push(
      `<div class="fx-ramos" style="--ramos:${ramosAbertos.length}">${ramosAbertos
        .map(
          (ramo) =>
            `<div class="fx-ramo"><span class="fx-ramo__rotulo">${ramo.rotulo}</span>` +
            `<div class="fx-no fx-no--ramo">${ramo.texto}</div></div>`,
        )
        .join('')}</div>`,
    );
    ramosAbertos = null;
  };

  for (const linha of linhas) {
    const indentada = /^\s{2,}\S/.test(linha);
    const conteudo = linha.trim();
    const separador = conteudo.indexOf(':');
    if (separador === -1) continue;
    const chave = conteudo.slice(0, separador).trim().toLowerCase();
    const valor = inline(escapar(conteudo.slice(separador + 1).trim()));

    if (indentada) {
      ramosAbertos ??= [];
      ramosAbertos.push({ rotulo: inline(escapar(conteudo.slice(0, separador).trim())), texto: valor });
      continue;
    }

    fecharRamos();

    if (chave === 'titulo') {
      titulo = valor;
    } else if (chave === 'seta') {
      partes.push(`<div class="fx-seta"><span>${valor}</span></div>`);
    } else if (chave === 'nota') {
      partes.push(`<p class="fx-nota">${valor}</p>`);
    } else if (TIPOS_NO[chave]) {
      partes.push(`<div class="fx-no fx-no--${TIPOS_NO[chave]}">${valor}</div>`);
    }
  }
  fecharRamos();

  const legenda = titulo ? `<figcaption class="fx-titulo">${titulo}</figcaption>` : '';
  return `<figure class="fluxo">${legenda}<div class="fx-corpo">${partes.join('')}</div></figure>`;
}

/* --- blocos ------------------------------------------------------- */

const TAGS_BLOCO = /^<(div|figure|section|aside|table|nav|p|ul|ol|h[1-6]|blockquote)\b/;

function converter(markdown) {
  const linhas = markdown.split('\n');
  const html = [];
  const sumario = [];
  let i = 0;

  const listaAninhada = (nivelInicial) => {
    // Devolve o HTML de uma lista a partir da linha corrente, respeitando o
    // aninhamento por dois espaços.
    //
    // O texto de cada item é acumulado cru e só passa por `inline()` no fim:
    // processar linha a linha quebraria um `**negrito**` que atravessa a
    // quebra de linha.
    const ordenada = /^\s*\d+\.\s/.test(linhas[i]);
    const itens = [];
    while (i < linhas.length) {
      const linha = linhas[i];
      if (linha.trim() === '') {
        const proxima = linhas[i + 1] ?? '';
        if (!/^\s*([-*]|\d+\.)\s/.test(proxima)) break;
        i += 1;
        continue;
      }
      const marcador = linha.match(/^(\s*)([-*]|\d+\.)\s+(.*)$/);
      if (!marcador) {
        // Continuação preguiçosa: item de lista quebrado em mais de uma linha.
        // Sem isso, a segunda linha viraria um parágrafo solto fora da lista.
        const conteudo = linha.trim();
        const inicioDeBloco =
          conteudo.startsWith('#') ||
          conteudo.startsWith('>') ||
          conteudo.startsWith('```') ||
          TAGS_BLOCO.test(linha);
        if (itens.length === 0 || inicioDeBloco) break;
        itens[itens.length - 1].texto += ` ${conteudo}`;
        i += 1;
        continue;
      }
      const nivel = Math.floor(marcador[1].length / 2);
      if (nivel < nivelInicial) break;
      if (nivel > nivelInicial) {
        itens[itens.length - 1].sub += listaAninhada(nivel);
        continue;
      }
      i += 1;
      itens.push({ texto: marcador[3], sub: '' });
    }
    const tag = ordenada ? 'ol' : 'ul';
    const corpo = itens
      .map((item) => `<li>${inline(escapar(item.texto))}${item.sub}</li>`)
      .join('');
    return `<${tag}>${corpo}</${tag}>`;
  };

  while (i < linhas.length) {
    const linha = linhas[i];
    const cru = linha.trim();

    if (cru === '') {
      i += 1;
      continue;
    }

    // Bloco cercado: código ou fluxograma.
    if (cru.startsWith('```')) {
      const idioma = cru.slice(3).trim();
      const corpo = [];
      i += 1;
      while (i < linhas.length && !linhas[i].trim().startsWith('```')) {
        corpo.push(linhas[i]);
        i += 1;
      }
      i += 1;
      html.push(
        idioma === 'fluxo'
          ? renderizarFluxo(corpo.join('\n'))
          : `<pre><code>${escapar(corpo.join('\n'))}</code></pre>`,
      );
      continue;
    }

    // HTML cru: passa direto até a tag de fechamento na coluna zero.
    const bloco = linha.match(TAGS_BLOCO);
    if (bloco) {
      const fechamento = `</${bloco[1]}>`;
      const corpo = [linha];
      i += 1;
      while (i < linhas.length && linhas[i].trim() !== fechamento) {
        corpo.push(linhas[i]);
        i += 1;
      }
      if (i < linhas.length) corpo.push(linhas[i]);
      i += 1;
      html.push(corpo.join('\n'));
      continue;
    }

    // Quebra de página manual: usada quando um fluxograma longo seria partido
    // ao meio e vale mais começá-lo no alto da página seguinte.
    if (cru === '[pagina]') {
      html.push('<div class="quebra-pagina"></div>');
      i += 1;
      continue;
    }

    // Régua.
    if (/^-{3,}$/.test(cru)) {
      html.push('<hr />');
      i += 1;
      continue;
    }

    // Título.
    const titulo = cru.match(/^(#{1,4})\s+(.*)$/);
    if (titulo) {
      const nivel = titulo[1].length;
      const texto = titulo[2].trim();
      const id = slug(texto);
      if (nivel === 2) sumario.push({ id, texto });
      html.push(`<h${nivel} id="${id}">${inline(escapar(texto))}</h${nivel}>`);
      i += 1;
      continue;
    }

    // Destaque.
    if (cru.startsWith('>')) {
      const corpo = [];
      while (i < linhas.length && linhas[i].trim().startsWith('>')) {
        corpo.push(linhas[i].trim().replace(/^>\s?/, ''));
        i += 1;
      }
      const texto = corpo.join('\n');
      const marca = texto.match(/^\*\*([^*:]+)\*?\*?/);
      const tom = marca ? TONS_DESTAQUE[marca[1].trim().toLowerCase().replace(/[.:!]$/, '')] : undefined;
      const paragrafos = texto
        .split(/\n{2,}/)
        .map((par) => `<p>${inline(escapar(par.replace(/\n/g, ' ')))}</p>`)
        .join('');
      html.push(`<blockquote class="destaque destaque--${tom ?? 'neutro'}">${paragrafos}</blockquote>`);
      continue;
    }

    // Tabela.
    if (cru.includes('|') && /^\s*\|?[\s:-]*-[\s:|-]*$/.test(linhas[i + 1] ?? '')) {
      const celulas = (texto) =>
        texto
          .trim()
          .replace(/^\||\|$/g, '')
          .split('|')
          .map((celula) => celula.trim());
      const cabecalho = celulas(cru);
      const alinhamento = celulas(linhas[i + 1]).map((marca) =>
        marca.endsWith(':') && marca.startsWith(':')
          ? 'center'
          : marca.endsWith(':')
            ? 'right'
            : 'left',
      );
      i += 2;
      const corpo = [];
      while (i < linhas.length && linhas[i].includes('|') && linhas[i].trim() !== '') {
        corpo.push(celulas(linhas[i]));
        i += 1;
      }
      const th = cabecalho
        .map((texto, indice) => `<th style="text-align:${alinhamento[indice] ?? 'left'}">${inline(escapar(texto))}</th>`)
        .join('');
      const tr = corpo
        .map(
          (celulasLinha) =>
            `<tr>${celulasLinha
              .map(
                (texto, indice) =>
                  `<td style="text-align:${alinhamento[indice] ?? 'left'}">${inline(escapar(texto))}</td>`,
              )
              .join('')}</tr>`,
        )
        .join('');
      html.push(`<div class="tabela-rolagem"><table><thead><tr>${th}</tr></thead><tbody>${tr}</tbody></table></div>`);
      continue;
    }

    // Lista.
    if (/^\s*([-*]|\d+\.)\s/.test(linha)) {
      html.push(listaAninhada(0));
      continue;
    }

    // Parágrafo.
    const corpo = [];
    while (
      i < linhas.length &&
      linhas[i].trim() !== '' &&
      !/^\s*([-*]|\d+\.)\s/.test(linhas[i]) &&
      !linhas[i].trim().startsWith('#') &&
      !linhas[i].trim().startsWith('>') &&
      !linhas[i].trim().startsWith('```') &&
      !TAGS_BLOCO.test(linhas[i])
    ) {
      corpo.push(linhas[i].trim());
      i += 1;
    }
    html.push(`<p>${inline(escapar(corpo.join(' ')))}</p>`);
  }

  return { corpo: html.join('\n'), sumario };
}

/** Front matter simples `chave: valor` entre duas réguas no topo do arquivo. */
function separarMeta(fonte) {
  if (!fonte.startsWith('---\n')) return { meta: {}, markdown: fonte };
  const fim = fonte.indexOf('\n---', 4);
  if (fim === -1) return { meta: {}, markdown: fonte };
  const meta = {};
  for (const linha of fonte.slice(4, fim).split('\n')) {
    const separador = linha.indexOf(':');
    if (separador === -1) continue;
    meta[linha.slice(0, separador).trim()] = linha.slice(separador + 1).trim();
  }
  return { meta, markdown: fonte.slice(fim + 4) };
}

/* ------------------------------------------------------------------ *
 * Página
 * ------------------------------------------------------------------ */

const CSS = readFileSync(path.join(AQUI, 'manual.css'), 'utf8');

function montarPagina({ meta, corpo, sumario }) {
  const titulo = meta.titulo ?? 'Manual operacional';
  const itens = sumario
    .map((secao, indice) => {
      const numero = String(indice + 1).padStart(2, '0');
      return `<li><a href="#${secao.id}"><span class="sumario__num">${numero}</span><span>${inline(escapar(secao.texto))}</span></a></li>`;
    })
    .join('');

  return `<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>${escapar(titulo)} — SGPD / DesligaFlow</title>
<style>${CSS}</style>
</head>
<body>
<main class="documento">
  <header class="capa">
    <p class="capa__sistema">SGPD <span>DesligaFlow</span></p>
    <p class="capa__selo">${escapar(meta.selo ?? 'Manual operacional')}</p>
    <h1 class="capa__titulo">${escapar(titulo)}</h1>
    ${meta.subtitulo ? `<p class="capa__subtitulo">${inline(escapar(meta.subtitulo))}</p>` : ''}
    <dl class="capa__ficha">
      ${meta.publico ? `<div><dt>Para quem é</dt><dd>${inline(escapar(meta.publico))}</dd></div>` : ''}
      ${meta.versao ? `<div><dt>Versão</dt><dd>${escapar(meta.versao)}</dd></div>` : ''}
      ${meta.data ? `<div><dt>Atualizado em</dt><dd>${escapar(meta.data)}</dd></div>` : ''}
      ${meta.sistema ? `<div><dt>Endereço do sistema</dt><dd>${escapar(meta.sistema)}</dd></div>` : ''}
    </dl>
    <p class="capa__rodape">
      Este manual descreve o uso do sistema. Ele não substitui a política de
      desligamento da empresa nem a orientação do Departamento Pessoal.
    </p>
  </header>

  <nav class="sumario" aria-label="Sumário">
    <h2 class="sumario__titulo">Sumário</h2>
    <ol class="sumario__lista">${itens}</ol>
  </nav>

  <article class="conteudo">
${corpo}
  </article>
</main>
</body>
</html>
`;
}

/* ------------------------------------------------------------------ *
 * PDF por CDP
 * ------------------------------------------------------------------ */

function acharChromium() {
  const candidatos = [
    process.env.CHROME_BIN,
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
    '/usr/bin/google-chrome-stable',
    '/usr/bin/google-chrome',
  ].filter(Boolean);
  const encontrado = candidatos.find((caminho) => existsSync(caminho));
  if (!encontrado) throw new Error('Chromium não encontrado. Defina CHROME_BIN.');
  return encontrado;
}

const esperar = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

class Sessao {
  #ws;
  #id = 0;
  #pendentes = new Map();
  #ouvintes = new Map();

  constructor(ws) {
    this.#ws = ws;
    ws.addEventListener('message', (evento) => {
      const dados = JSON.parse(evento.data);
      if (dados.id !== undefined) {
        const pendente = this.#pendentes.get(dados.id);
        this.#pendentes.delete(dados.id);
        if (!pendente) return;
        dados.error ? pendente.reject(new Error(dados.error.message)) : pendente.resolve(dados.result);
        return;
      }
      this.#ouvintes.get(dados.method)?.forEach((resolver) => resolver(dados.params));
      this.#ouvintes.delete(dados.method);
    });
  }

  enviar(method, params = {}, sessionId) {
    const id = (this.#id += 1);
    return new Promise((resolve, reject) => {
      this.#pendentes.set(id, { resolve, reject });
      this.#ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
    });
  }

  aguardar(evento) {
    return new Promise((resolve) => {
      const atuais = this.#ouvintes.get(evento) ?? [];
      atuais.push(resolve);
      this.#ouvintes.set(evento, atuais);
    });
  }

  fechar() {
    this.#ws.close();
  }
}

const CABECALHO = `
<div style="width:100%;font-size:7pt;font-family:Arial,sans-serif;color:#9aa3a0;
            padding:0 14mm;display:flex;justify-content:space-between;">
  <span>SGPD / DesligaFlow — TITULO_DOC</span><span>VERSAO_DOC</span>
</div>`;

const RODAPE = `
<div style="width:100%;font-size:7pt;font-family:Arial,sans-serif;color:#9aa3a0;
            padding:0 14mm;display:flex;justify-content:space-between;">
  <span>Documento de uso interno</span>
  <span>Página <span class="pageNumber"></span> de <span class="totalPages"></span></span>
</div>`;

async function gerarPdfs(trabalhos) {
  const perfil = await mkdtemp(path.join(tmpdir(), 'sgpd-manual-'));
  const chromium = spawn(
    acharChromium(),
    [
      '--headless=new',
      '--disable-gpu',
      '--no-sandbox',
      '--no-first-run',
      '--disable-extensions',
      '--remote-debugging-port=0',
      `--user-data-dir=${perfil}`,
      'about:blank',
    ],
    { stdio: ['ignore', 'ignore', 'pipe'] },
  );

  try {
    // A porta real é publicada no arquivo DevToolsActivePort do perfil.
    const arquivoPorta = path.join(perfil, 'DevToolsActivePort');
    let porta = null;
    for (let tentativa = 0; tentativa < 100 && porta === null; tentativa += 1) {
      await esperar(100);
      if (!existsSync(arquivoPorta)) continue;
      const conteudo = await readFile(arquivoPorta, 'utf8');
      const primeira = conteudo.split('\n')[0].trim();
      if (primeira) porta = primeira;
    }
    if (porta === null) throw new Error('O Chromium não publicou a porta de depuração.');

    const versao = await (await fetch(`http://127.0.0.1:${porta}/json/version`)).json();
    const ws = new WebSocket(versao.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      ws.addEventListener('open', resolve, { once: true });
      ws.addEventListener('error', reject, { once: true });
    });
    const sessao = new Sessao(ws);

    for (const trabalho of trabalhos) {
      const { targetId } = await sessao.enviar('Target.createTarget', { url: 'about:blank' });
      const { sessionId } = await sessao.enviar('Target.attachToTarget', { targetId, flatten: true });
      await sessao.enviar('Page.enable', {}, sessionId);
      const carregou = sessao.aguardar('Page.loadEventFired');
      await sessao.enviar('Page.navigate', { url: `file://${trabalho.html}` }, sessionId);
      await carregou;
      await esperar(250);

      const { data } = await sessao.enviar(
        'Page.printToPDF',
        {
          printBackground: true,
          preferCSSPageSize: true,
          displayHeaderFooter: true,
          headerTemplate: CABECALHO.replace('TITULO_DOC', trabalho.titulo).replace(
            'VERSAO_DOC',
            trabalho.versao,
          ),
          footerTemplate: RODAPE,
          marginTop: 0.7,
          marginBottom: 0.6,
          marginLeft: 0,
          marginRight: 0,
        },
        sessionId,
      );
      await writeFile(trabalho.pdf, Buffer.from(data, 'base64'));
      await sessao.enviar('Target.closeTarget', { targetId });
      console.log(`  PDF  ${path.basename(trabalho.pdf)}`);
    }

    sessao.fechar();
  } finally {
    chromium.kill();
    await esperar(200);
    await rm(perfil, { recursive: true, force: true });
  }
}

/* ------------------------------------------------------------------ *
 * Execução
 * ------------------------------------------------------------------ */

const argumentos = process.argv.slice(2);
const somenteHtml = argumentos.includes('--html');
const alvos = argumentos.filter((argumento) => argumento.endsWith('.md'));

const arquivos = alvos.length
  ? alvos.map((alvo) => path.resolve(alvo))
  : (await readdir(AQUI))
      .filter((nome) => nome.endsWith('.md') && nome !== 'README.md')
      .sort()
      .map((nome) => path.join(AQUI, nome));

const trabalhos = [];
for (const arquivo of arquivos) {
  const fonte = await readFile(arquivo, 'utf8');
  const { meta, markdown } = separarMeta(fonte);
  const { corpo, sumario } = converter(markdown);
  const destinoHtml = arquivo.replace(/\.md$/, '.html');
  await writeFile(destinoHtml, montarPagina({ meta, corpo, sumario }));
  console.log(`  HTML ${path.basename(destinoHtml)}`);
  trabalhos.push({
    html: destinoHtml,
    pdf: arquivo.replace(/\.md$/, '.pdf'),
    titulo: meta.titulo ?? 'Manual operacional',
    versao: meta.versao ?? '',
  });
}

if (!somenteHtml) await gerarPdfs(trabalhos);
console.log(`\n${trabalhos.length} manual(is) gerado(s) em ${AQUI}`);
