# Runbook operacional

Procedimentos de operação do SGPD, no DEV e no host de produção da ADR-055. O
inventário do ambiente está em `ENVIRONMENT.md`; as decisões, em
`DECISIONS.md`. Aqui está o que fazer, na ordem, quando algo precisa ser feito
ou parou de funcionar. Deploy, corte e rollback estão na §11.

Premissa que atravessa o documento: **nenhuma rotina do SGPD decide nada por
conta própria**. Liberação, encerramento, cancelamento, reabertura, decisão de
valor e expurgo de evidência são atos humanos explícitos e auditados. O que o
agendador faz é varrer prazos e despachar avisos.

## 1. Rotina diária

| Quando | O quê | Onde |
| --- | --- | --- |
| Início do expediente | Conferir se a fila de avisos andou | `/fe/operacao` |
| Início do expediente | Conferir falhas de envio e reprocessar o que desistiu | `/fe/notificacoes` |
| Ao longo do dia | Acompanhar vencidos e setores atrasados | `/fe/painel` |
| Semanal | Conferir tempo médio, pendências e valores do período | `/fe/relatorios` |

`/fe/operacao` é exclusiva do SuperAdmin; o painel e os relatórios exigem `DP`
vigente no escopo.

## 2. Agendamento das notificações

A fila é uma tabela no Oracle e o envio roda fora da requisição (ADR-049). Sem
agendamento instalado, **nada é enviado e nada quebra** — as mensagens se
acumulam em `PENDENTE` e o sistema segue respondendo. É o risco R63.

**No PRD** (ADR-055), por timers do systemd instalados de `scripts/systemd/`:

```bash
sudo cp scripts/systemd/sgpd-*.service scripts/systemd/sgpd-*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sgpd-notifications.timer sgpd-operations-check.timer
```

Varredura com despacho a cada dez minutos; sonda a cada trinta. A vantagem sobre
o `cron` é o resíduo do R63: a sonda sai com código 1 quando a fila está parada,
o systemd marca `sgpd-operations-check.service` como `failed`, e isso aparece em
`systemctl list-units --failed` — ninguém precisa abrir um log para descobrir.

**No DEV**, entradas no `crontab` do usuário da aplicação desde 2026-08-01:

```cron
*/10 * * * * cd /home/macari/dev/SGPD && /home/macari/.local/bin/uv run manage.py sgpd_scan_notifications --dispatch >> /home/macari/dev/SGPD/var/log/sgpd-notificacoes.log 2>&1
*/30 * * * * cd /home/macari/dev/SGPD && /home/macari/.local/bin/uv run manage.py sgpd_operations_check --quiet >> /home/macari/dev/SGPD/var/log/sgpd-operacao.log 2>&1
```

Caminho absoluto do `uv` e `cd` explícito não são preciosismo: o `cron` roda com
`PATH` mínimo e a partir do `HOME`, e `uv run manage.py` fora da raiz do projeto
falha com `Failed to spawn: manage.py`. Redirecionar o log por caminho absoluto
pela mesma razão. Os units do PRD usam o binário do venv pelo caminho absoluto
pelo mesmo motivo.

A varredura é idempotente: rodar de dez em dez minutos muda a latência do
aviso, nunca a quantidade. Separar varredura e despacho em duas entradas é
igualmente válido.

Em modo `--quiet` a sonda só escreve quando há problema — assim o log fica
vazio enquanto está tudo bem, e o código de saída é o que qualquer monitor
externo, ou o próprio systemd, enxerga.

### Verificar

```bash
# PRD
systemctl list-timers 'sgpd-*'               # quando rodou e quando roda de novo
systemctl list-units --failed 'sgpd-*'       # a sonda acusou fila parada?
journalctl -u sgpd-notifications -n 50       # a última execução falou o quê

# DEV
crontab -l                                   # o agendamento existe?
tail -n 50 var/log/sgpd-notificacoes.log     # a última execução falou o quê

# Nos dois
uv run manage.py sgpd_operations_check       # o que a sonda vê agora
```

### Sintoma: fila crescendo em `PENDENTE`

1. `/fe/operacao` mostra o veredito e a mensagem pendente mais antiga;
2. confirme o `crontab` e o log acima;
3. rode uma vez à mão para destravar:
   `uv run manage.py sgpd_scan_notifications --dispatch`;
4. se o comando falhar, o erro é de transporte ou de configuração: confira
   `/fe/configuracoes/email` — servidor, remetente, interruptor de envio;
5. nada se perde no caminho: a fila é durável e a chave de deduplicação impede
   aviso repetido quando a varredura roda de novo.

### Sintoma: mensagens em `FALHA`

O despacho tenta de novo com backoff crescente e desiste em `max_attempts`. Só
a mensagem que desistiu volta para a fila, e apenas por ato explícito em
`/fe/notificacoes` — reenviar uma entregue duplicaria o e-mail. O
reprocessamento é auditado e a numeração das tentativas nunca se repete.

Aviso conhecido: a entrega é **ao menos uma vez**. Se o processo morrer entre o
envio SMTP e a confirmação no banco, a mensagem volta para a fila e pode chegar
duplicada. Duplicar aviso é aceitável; perder aviso não é.

### Sintoma: marco sem destinatário

Setor sem responsável vigente, ou processo sem `DP` no escopo, faz o marco ser
contado e registrado em log — o aviso não sai e ninguém é avisado disso
automaticamente. Corrija o vínculo em `/fe/setores` ou a atribuição em
`/fe/usuarios`; a varredura seguinte volta a alcançar o marco.

## 3. Configuração de e-mail

Transporte, remetente, URL base dos links, ritmo da fila e marcos de lembrete
são editados em `/fe/configuracoes/email` por SuperAdmin (ADR-050). O `.env` é
apenas o baseline do primeiro boot; enquanto o registro não existir, a tela
mostra `Origem efetiva: Ambiente`.

- mudar servidor, remetente ou marco **não exige reinício**;
- a senha SMTP nunca volta pela API: campo em branco preserva a vigente;
- o interruptor de envio desligado retém a fila em `PENDENTE` sem perder
  mensagem; religar despacha o acumulado;
- a prova de envio vai obrigatoriamente para o endereço da própria conta que a
  pediu;
- com a URL base vazia, o link da mensagem sai relativo e não é clicável no
  cliente de e-mail. É configuração, não código.

## 4. Exportações e dado pessoal

`/fe/relatorios` exporta processos, tarefas e pendências em CSV. Cada download
grava uma linha em `SGPD_REPORT_EXPORT` com ator, conjunto, período, linhas e
correlation ID — a trilha é escrita antes de o arquivo sair, porque download
interrompido continua sendo acesso ao dado (`SECURITY.md` §6).

O arquivo não leva CPF, motivo do desligamento, justificativa da pretensão nem
parecer da decisão. Recorte acima de 5000 linhas é recusado: reduza o período.

Ao atender pedido de titular ou auditoria, a consulta é
`SELECT * FROM SGPD_REPORT_EXPORT ORDER BY EXPORTED_AT DESC` — a tabela é
append-only e não é alterada por ninguém.

## 5. Evidências e retenção

- os arquivos ficam fora do Oracle, em storage privado, e **nunca** são
  servidos pelo WhiteNoise;
- o download é autorizado e auditado por evento no processo;
- a retenção operacional é de **5 anos**, contados do encerramento formal
  (`SECURITY.md` §14), e ainda depende de validação com Jurídico, RH e
  Segurança da Informação;
- **o expurgo é manual e autorizado**: nenhuma rotina apaga evidência.
  `/fe/operacao` conta quantos processos encerrados já passaram da retenção; a
  decisão de apagar, quando existir, será ato humano registrado.

Antes de qualquer expurgo: confirmar o parecer jurídico, conferir bloqueio
legal em curso, preservar a trilha de auditoria (que não é apagada) e registrar
o ato.

## 6. Backup e restauração

O banco do SGPD faz parte da política corporativa de backup (RNF-011); o
schema `SGPD` no Oracle 19c é o alvo. O que precisa estar coberto:

1. **Oracle** — schema `SGPD` inteiro. Contém processo, snapshot, tarefas,
   checklists, pendências, valores, decisões, notificações, auditoria e a
   trilha de exportações;
2. **Storage de evidências** — o diretório privado do `.env`
   (`media/evidence` no DEV, `/var/lib/sgpd/evidence` no PRD). Os bytes não
   estão no banco: backup do Oracle sozinho não restaura evidência;
3. **Configuração** — o `.env` (fora do Git, com segredos) e, no banco, os
   singletons de LDAP e de e-mail.

Verificação periódica sugerida, com o DBA:

- confirmar que o schema `SGPD` está no plano de backup e a data do último
  backup válido;
- restaurar em ambiente separado e conferir contagem de
  `SGPD_OFFBOARDING_PROCESS`, `SGPD_EVIDENCE` e `SGPD_ACCOUNT_AUDIT`;
- conferir que o hash SHA-256 de uma amostra de evidências restauradas confere
  com o metadado no banco — é o teste que prova que banco e storage foram
  restaurados do mesmo instante.

**Pendente no DEV**: a validação com o DBA ainda não foi executada. Enquanto
não for, considere que só existe o backup corporativo do Oracle, sem prova de
restauração e sem cobertura confirmada do storage de evidências.

## 7. Saúde da aplicação

O host é publicado em `https://sgpd.bsabioenergia.com.br` por um proxy que roda
em outro servidor e encaminha para a porta `8002` deste (ADR-052). A aplicação
sobe pelo Gunicorn sob systemd (ADR-055), com os settings escolhidos pelo
`DJANGO_SETTINGS_MODULE` do `.env`:

```bash
sudo systemctl status sgpd-web        # está de pé?
sudo systemctl restart sgpd-web       # reinício limpo
sudo systemctl reload sgpd-web        # recarga graciosa, sem derrubar conexão
journalctl -u sgpd-web -n 100 -f      # log de acesso e de erro
```

**Um worker é trava, não default.** O limite de tentativas de login vive no
cache local de cada processo, então dois workers dobrariam a taxa efetiva do
controle que protege o login contra força bruta. `config.settings.production`
recusa subir com `WEB_CONCURRENCY` acima de 1 enquanto o cache for local — subir
a concorrência exige cache compartilhado antes. Threads podem crescer à vontade:
compartilham o mesmo cache.

Verificação, sempre pela URL publicada — em HTTP puro o navegador descarta o
cookie `Secure` e o login não completa:

```bash
curl -s https://sgpd.bsabioenergia.com.br/health/live/    # o processo está de pé
curl -s https://sgpd.bsabioenergia.com.br/health/ready/   # dependências respondem
uv run manage.py sgpd_operations_check                    # fila, storage e retenção
uv run manage.py check --deploy                           # postura de segurança
```

`check --deploy` deve terminar apenas com os avisos de `SECURE_HSTS_PRELOAD` e
`SECURE_HSTS_INCLUDE_SUBDOMAINS`, que são opções deliberadamente não adotadas.
Qualquer aviso de cookie, redirecionamento ou `DEBUG` significa que a aplicação
subiu com o módulo de settings errado.

Para desenvolver localmente sem as travas de transporte, passe o módulo na mão:
`uv run manage.py runserver --settings=config.settings.development`.

Logs são JSON na saída padrão, com correlation ID em cada requisição
(`X-Correlation-ID` aceito ou gerado). Ao investigar um caso, pegue o
correlation ID da resposta e filtre o log por ele: auditoria, notificação e
exportação carregam o mesmo identificador.

## 8. Migrations

Nunca aplicar sem revisar. A sequência é sempre:

```bash
uv run manage.py makemigrations --check --dry-run --settings=config.settings.test
uv run manage.py sqlmigrate <app> <numero>     # ler o SQL Oracle
uv run manage.py migrate <app>                 # aplicar
```

Conferir no SQL: nomes dentro de 30 caracteres, condição de check anulável no
idioma `IS NULL OR …`, ausência de índice redundante com FK, lock e volume.
Depois de aplicar, conferir `USER_CONSTRAINTS`/`USER_INDEXES` com
`ENABLED`/`VALIDATED`/`VALID`.

Nunca `migrate <app> zero` com dados reais: processo, auditoria, pendência,
notificação e exportação são append-only por decisão.

## 9. Armadilhas do Oracle já pagas

Todas passaram pelo SQLite dos testes sem reclamar e só apareceram no DEV.
Antes de escrever consulta nova, confira se ela cai em alguma:

- `SELECT DISTINCT` sobre tabela com coluna NCLOB (`REASON`, `NOTES`) é
  `ORA-00932`. Resolva a duplicidade do join em subconsulta;
- `GROUP BY` que arraste coluna LOB tem o mesmo destino: `annotate(Count(...))`
  sobre o processo leva todas as colunas projetadas ao agrupamento;
- `AVG` sobre `INTERVAL DAY TO SECOND` — a subtração de dois `TIMESTAMP` —
  também é `ORA-00932`. Média de duração se calcula fora do banco;
- check constraint sobre coluna anulável precisa admitir o nulo:
  `IS NULL OR …`. No Oracle, `NULL >= 0` é desconhecido e derruba
  `full_clean()`;
- `CharField` anulável volta como `''`, nunca `None`. Regra que testa ausência
  usa `not valor`;
- `FOR UPDATE` combinado a `FETCH FIRST` não existe: materialize antes de
  paginar.

## 10. Treinamento e primeiro contato

Ordem sugerida para quem vai operar o sistema:

1. **Conceito** — `VISION.md` e `GLOSSARY.md`: o SGPD orquestra o processo
   demissional; o Senior HCM continua sendo a fonte oficial do vínculo e da
   rescisão. O SGPD nunca calcula rescisão nem aplica desconto;
2. **Fluxo** — `WORKFLOWS.md` §1 a §5: abertura, seleção de grupos, início,
   tarefas, pendências, prontidão, liberação, encerramento;
3. **Prática guiada** — abrir um processo de teste, selecionar grupos,
   iniciar, concluir uma tarefa com pendência e evidência, liberar e encerrar;
4. **Conferência** — `/fe/painel`, `/fe/processos/<uuid>/valores` e
   `/fe/processos/<uuid>/encerramento`;
5. **Operação** — este runbook, para quem tem SuperAdmin.

Pontos que costumam gerar dúvida e valem ser ditos em voz alta no treinamento:

- valor é **pretensão sujeita a análise**: quem informa não decide, e o valor
  processado só existe quando o Senior o registra (ADR-009, ADR-048);
- a regra de aplicabilidade **sugere** grupos; a seleção continua sendo ato
  explícito do `DP` (ADR-046);
- estado formal e situação calculada são coisas diferentes: o primeiro é o que
  alguém decidiu, com data e ator; a segunda é lida do estado atual das
  tarefas e pendências (ADR-051);
- cancelamento é terminal; reabertura é exclusiva do SuperAdmin e registra o
  estado anterior inteiro;
- o e-mail nunca carrega nome, CPF, valor ou parecer: ele diz o que fazer e
  onde (`SECURITY.md` §13.1).

## 11. Deploy e go-live do PRD

O ambiente produtivo é o da ADR-055: host próprio em `/opt/sgpd`, usuário de
serviço `sgpd`, Gunicorn sob systemd e **o mesmo schema `SGPD` do host anterior**.
Não há carga inicial: o acervo atual é promovido a produtivo.

### 11.1 Provisionamento (uma vez)

```bash
sudo useradd --system --home-dir /opt/sgpd --shell /usr/sbin/nologin sgpd
sudo install -d -o sgpd -g sgpd -m 750 /opt/sgpd
sudo install -d -o sgpd -g sgpd -m 700 /var/lib/sgpd/evidence
sudo install -d -o sgpd -g sgpd -m 700 /var/lib/sgpd/system-configuration
# Oracle Instant Client 19.28, Node 24 e uv conforme ENVIRONMENT.md §2.

sudo -u sgpd git clone git@github.com:iracam/SGPD.git /opt/sgpd

# As units precisam existir antes do primeiro deploy: o script termina com
# `systemctl restart` e abortaria sem elas. Instalar sem `enable` — o serviço
# só sobe depois que o primeiro `uv sync` criar o /opt/sgpd/.venv.
sudo cp /opt/sgpd/scripts/systemd/sgpd-*.service /opt/sgpd/scripts/systemd/sgpd-*.timer /etc/systemd/system/
sudo systemctl daemon-reload
```

O deploy roda como `sgpd`, para que os artefatos fiquem com o dono que o serviço
usa. O script só precisa de privilégio para reiniciar o próprio serviço:

```bash
# /etc/sudoers.d/sgpd-deploy
sgpd ALL=(root) NOPASSWD: /usr/bin/systemctl restart sgpd-web
```

O `.env` é criado à mão, com modo `600` e dono `sgpd`, a partir do bloco
**Host de produção** do `.env.example`.

### 11.2 Deploy

```bash
sudo -u sgpd /opt/sgpd/scripts/deploy.sh              # origin/main
sudo -u sgpd /opt/sgpd/scripts/deploy.sh v1.2.0       # uma tag
```

**Na primeira execução, aponte a sonda para o próprio host.** O passo final bate
na URL publicada, que ainda resolve para o host anterior: sem isto o script
diria "ok" depois de checar a máquina errada.

```bash
sudo -u sgpd SGPD_HEALTH_BASE_URL=http://127.0.0.1:8002 /opt/sgpd/scripts/deploy.sh
```

`/health/` é isento do redirecionamento para HTTPS justamente para isso
(ADR-052), e `DJANGO_ALLOWED_HOSTS` precisa incluir `127.0.0.1` — a verificação
de host acontece antes da view.

O script busca a referência, sincroniza pelo `uv.lock`, constrói a SPA e os
manuais, coleta estáticos, roda `check --deploy`, reinicia o serviço e confere
os dois health checks pela URL publicada.

**Ele para diante de migration pendente** e imprime o `sqlmigrate` a rodar. É
deliberado: aplicar migration sem revisar o SQL Oracle contraria o `AGENTS.md`
§9 e a §8 deste runbook. Revise, aplique à mão, rode o script de novo.

### 11.3 Checklist de corte

**Antes**

- [ ] host provisionado conforme §11.1
- [ ] `.env` de produção criado, modo `600`, com **o mesmo `DJANGO_SECRET_KEY`
      do host anterior**. Dele deriva a cifra dos segredos já gravados pela
      central (senha de bind do AD e senha SMTP): chave nova torna as duas
      ilegíveis (R69). Alternativa aceitável, se a chave mudar: reinformá-las em
      `/fe/configuracoes/ldap` e `/fe/configuracoes/email` logo após o corte
- [ ] `/var/lib/sgpd/evidence` populado a partir do host anterior. Os bytes não
      estão no Oracle: sem essa cópia, o banco aponta para arquivos que não
      existem. Conferir o SHA-256 de uma amostra contra `SGPD_EVIDENCE`
- [ ] Oracle alcançável do host novo; porta `8002` liberada só para `192.168.1.6`
- [ ] saneamento do acervo: processos de teste encerrados ou cancelados, contas
      de teste desativadas. Auditoria, fila de notificações e
      `SGPD_REPORT_EXPORT` são append-only e permanecem
- [ ] validação padrão completa executada (`CONTEXT.md`)

**Corte**

- [ ] serviço do host anterior parado e desabilitado — dois hosts não podem
      escrever no mesmo schema
- [ ] `scripts/deploy.sh` no host novo
- [ ] `sudo systemctl enable --now sgpd-web sgpd-notifications.timer sgpd-operations-check.timer`
- [ ] proxy de `192.168.1.6` reapontado para o IP novo em `:8002`
- [ ] `uv run manage.py check --deploy` — só os dois avisos de HSTS deliberados

**Depois**

- [ ] login real pela URL publicada, com cookie `Secure` aceito
- [ ] `/health/live/` e `/health/ready/` em 200
- [ ] `uv run manage.py sgpd_operations_check` sem veredito de fila parada
- [ ] prova de envio em `/fe/configuracoes/email` — é o que comprova que o
      Fernet decifrou a senha SMTP com a chave em uso
- [ ] descoberta em `/fe/configuracoes/ldap` — mesma prova para a senha de bind
- [ ] `SGPD_BASE_URL` preenchida e link de notificação clicável
- [ ] ensaio de supervisão: `sudo systemctl kill -s SIGKILL sgpd-web` e conferir
      que o systemd sobe de novo e o health volta a 200

### 11.4 Rollback

Parar `sgpd-web`, reapontar o proxy para o host anterior e subi-lo. O schema é o
mesmo e os dados ficam intactos.

O único passo irreversível seria uma migration aplicada durante o corte — e é
exatamente por isso que o script de deploy não aplica nenhuma. Se houve
migration, o rollback deixa de ser reapontar o proxy e passa a exigir plano
próprio, com o DBA.
