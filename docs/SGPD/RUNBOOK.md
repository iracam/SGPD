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
| Início do expediente | Conferir se a fila de avisos andou e se o agendamento bateu ponto | `/fe/operacao` |
| Início do expediente | Conferir falhas de envio e reprocessar o que desistiu | `/fe/notificacoes` |
| Ao longo do dia | Acompanhar vencidos e setores atrasados | `/fe/painel` |
| Semanal | Conferir tempo médio, pendências e valores do período | `/fe/relatorios` |

`/fe/operacao` é exclusiva do SuperAdmin; o painel e os relatórios exigem `DP`
vigente no escopo.

## 2. Agendamento das notificações

A fila é uma tabela no Oracle e o envio roda fora da requisição (ADR-049). Quem
executa é o worker; quem dispara a agenda periódica é o Beat (ADR-057). Com os
dois fora, **nada é enviado e nada quebra** — as mensagens se acumulam em
`PENDENTE` e o sistema segue respondendo. É o risco R63.

O aviso que nasce de um ato na tela não espera a varredura: o enfileiramento
pede o despacho daquela mensagem assim que a transação confirma, e ela sai em
segundos. A varredura periódica é a rede de segurança do que esse pedido não
alcançou.

### Serviços

```bash
sudo systemctl status sgpd-celery-worker sgpd-celery-beat
sudo systemctl restart sgpd-celery-worker sgpd-celery-beat
journalctl -u sgpd-celery-worker -n 100 -f
journalctl -u sgpd-celery-beat -n 50
```

Instalação, uma vez, de `scripts/systemd/`:

```bash
sudo cp scripts/systemd/sgpd-*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sgpd-celery-worker sgpd-celery-beat
```

**Só pode haver um Beat.** Dois disparariam a mesma agenda em dobro — o que não
duplica aviso, porque a varredura é idempotente e cada mensagem é tomada sob
lock, mas dobra o trabalho à toa.

O Redis é do host e compartilhado com outras aplicações (`ENVIRONMENT.md` §3):
o SGPD o consome e não o gerencia. Reiniciar o container é operação de
infraestrutura, e o efeito no SGPD é perder os sinais ainda não consumidos e o
limite de tentativas de login em curso — nunca a fila, que está no Oracle.

**No DEV**, os mesmos dois processos em terminais separados:

```bash
uv run celery -A config worker -Q sgpd -l info
uv run celery -A config beat -l info
```

### Verificar

```bash
systemctl status sgpd-celery-worker sgpd-celery-beat   # os dois de pé?
uv run celery -A config inspect ping                   # o worker responde?
uv run manage.py sgpd_operations_check                 # o que a sonda vê agora
```

Na tela, `/fe/operacao` responde as duas perguntas separadamente: **a fila está
andando?** e **o agendamento está vivo?**. A segunda existe porque a primeira
não distingue silêncio de tranquilidade — sem mensagem esperando, uma fila vazia
parece saudável mesmo com o Beat morto. O batimento é gravado a cada rodada da
sonda e lido pelo processo web; batimento com mais de sessenta minutos denuncia
o agendamento parado.

O `sgpd_operations_check` continua saindo com código 1 quando a **fila** está
parada, para quem quiser consumir por monitor externo. O batimento ausente não
derruba o código de saída: logo depois de um boot ele está vazio por definição,
e sonda que reclama sempre deixa de ser lida.

### Sintoma: fila crescendo em `PENDENTE`

1. `/fe/operacao` mostra os dois vereditos e a mensagem pendente mais antiga;
2. confira os serviços e o log acima; um worker morto aparece em
   `systemctl status`, e um que não responde ao `inspect ping` está preso;
3. rode uma vez à mão para destravar, sem depender do worker:
   `uv run manage.py sgpd_scan_notifications --dispatch`;
4. se o comando falhar, o erro é de transporte ou de configuração: confira
   `/fe/configuracoes/email` — servidor, remetente, interruptor de envio;
5. nada se perde no caminho: a fila é durável e a chave de deduplicação impede
   aviso repetido quando a varredura roda de novo.

### Sintoma: agendamento sem batimento, fila em dia

O Beat parou, ou o cache compartilhado foi reiniciado e perdeu a marca. Confira
`systemctl status sgpd-celery-beat` e o Redis do host. Enquanto isso, a
varredura à mão do item 3 acima cobre o que precisar sair.

### Sintoma: mensagens em `FALHA`

O despacho tenta de novo com backoff crescente e desiste em `max_attempts`. Só
a mensagem que desistiu volta para a fila, e apenas por ato explícito em
`/fe/notificacoes` — reenviar uma entregue duplicaria o e-mail. O
reprocessamento é auditado e a numeração das tentativas nunca se repete.

Aviso conhecido: a entrega é **ao menos uma vez**. Se o processo morrer entre o
envio SMTP e a confirmação no banco, a mensagem volta para a fila e pode chegar
duplicada. Vale também para o worker: com `acks_late`, a tarefa interrompida é
reentregue pelo broker. Duplicar aviso é aceitável; perder aviso não é.

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
   (`media/evidence` no DEV, `/home/macari/prd/sgpd-data/evidence` no PRD). Os
   bytes não estão no banco: backup do Oracle sozinho não restaura evidência;
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

**Um worker continua sendo o número em produção, agora por escolha.** A trava
que o impunha caiu com o cache compartilhado no Redis (ADR-057): o limite de
tentativas de login passou a ser um número só para todos os processos.
`config.settings.production` ainda recusa subir com `WEB_CONCURRENCY` acima de 1
se alguém devolver o cache ao processo. Subir a concorrência é decisão
operacional — mede-se antes o Oracle e o pool de conexões, e muda-se
`WEB_CONCURRENCY` em `sgpd-web.service`.

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

O ambiente produtivo é o da ADR-055: `/home/macari/prd/SGPD`, Gunicorn sob
systemd e **o mesmo schema `SGPD` do host anterior**. Não há carga inicial: o
acervo atual é promovido a produtivo.

O serviço roda como `macari`, dono do diretório — `/home/macari` é `0700` e uma
conta de serviço separada não leria a árvore. O mesmo usuário roda o DEV em
`/home/macari/dev/SGPD`: os dois `.env` são visíveis um ao outro, e o cuidado
com o diretório corrente deixa de ser cosmético (R72).

### 11.1 Provisionamento (uma vez)

```bash
install -d -m 750 /home/macari/prd
install -d -m 700 /home/macari/prd/sgpd-data/evidence
install -d -m 700 /home/macari/prd/sgpd-data/system-configuration
# Oracle Instant Client 19.28, Node 24 e uv conforme ENVIRONMENT.md §2.

git clone git@github.com:iracam/SGPD.git /home/macari/prd/SGPD

# As units precisam existir antes do primeiro deploy: o script termina com
# `systemctl restart` e abortaria sem elas. Instalar sem `enable` — o serviço só
# sobe depois que o primeiro `uv sync` criar o .venv.
sudo cp /home/macari/prd/SGPD/scripts/systemd/sgpd-*.service /etc/systemd/system/
sudo systemctl daemon-reload
```

O Redis é pré-requisito do host, não deste provisionamento (ADR-057): ele já
roda em container e atende outras aplicações. O que precisa existir aqui é o
acesso — `SGPD_REDIS_URL` no `.env` e a porta alcançável de `127.0.0.1`.

O storage fica **fora** de `/home/macari/prd/SGPD` de propósito: `git checkout`,
`npm ci` e `collectstatic` nunca chegam perto dos bytes das evidências.

O `.env` é criado à mão, com modo `600`, a partir do bloco **Host de produção**
do `.env.example`.

### 11.2 Deploy

```bash
/home/macari/prd/SGPD/scripts/deploy.sh              # origin/main
/home/macari/prd/SGPD/scripts/deploy.sh v1.2.0       # uma tag
```

Rode **de dentro do diretório do PRD**, ou pelo caminho absoluto acima. O script
opera sobre a árvore onde ele mesmo está, então chamá-lo pelo caminho certo é o
que separa um deploy de produção de um deploy no DEV.

**Na primeira execução, aponte a sonda para o próprio host.** O passo final bate
na URL publicada, que ainda resolve para o host anterior: sem isto o script
diria "ok" depois de checar a máquina errada.

```bash
SGPD_HEALTH_BASE_URL=http://127.0.0.1:8002 /home/macari/prd/SGPD/scripts/deploy.sh
```

`/health/` é isento do redirecionamento para HTTPS justamente para isso
(ADR-052), e `DJANGO_ALLOWED_HOSTS` precisa incluir `127.0.0.1` — a verificação
de host acontece antes da view.

O script busca a referência, sincroniza pelo `uv.lock`, constrói a SPA e os
manuais, coleta estáticos, roda `check --deploy`, confere que o Redis responde,
reinicia web, worker e Beat e verifica os dois health checks pela URL publicada.
Reiniciar os três é obrigatório: worker e Beat carregam o mesmo código, e deixar
só o web novo faria as tarefas rodarem a versão anterior.

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
- [ ] `/home/macari/prd/sgpd-data/evidence` populado a partir do host anterior. Os bytes não
      estão no Oracle: sem essa cópia, o banco aponta para arquivos que não
      existem. Conferir o SHA-256 de uma amostra contra `SGPD_EVIDENCE`
- [ ] Oracle alcançável do host novo; porta `8002` liberada só para `192.168.1.6`
- [ ] Redis do host respondendo em `127.0.0.1:6379`, com os índices 0 e 1 livres
      para o SGPD (`ENVIRONMENT.md` §3)
- [ ] saneamento do acervo: processos de teste encerrados ou cancelados, contas
      de teste desativadas. Auditoria, fila de notificações e
      `SGPD_REPORT_EXPORT` são append-only e permanecem
- [ ] validação padrão completa executada (`CONTEXT.md`)

**Corte**

- [ ] serviço do host anterior parado e desabilitado — dois hosts não podem
      escrever no mesmo schema
- [ ] `scripts/deploy.sh` no host novo
- [ ] `sudo systemctl enable --now sgpd-web sgpd-celery-worker sgpd-celery-beat`
- [ ] proxy de `192.168.1.6` reapontado para o IP novo em `:8002`
- [ ] `uv run manage.py check --deploy` — só os dois avisos de HSTS deliberados

**Depois**

- [ ] login real pela URL publicada, com cookie `Secure` aceito
- [ ] `/health/live/` e `/health/ready/` em 200
- [ ] `uv run manage.py sgpd_operations_check` sem veredito de fila parada
- [ ] `/fe/operacao` com batimento do agendamento recente — é o que prova que o
      Beat subiu e que o worker está executando
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
