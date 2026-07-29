# Integração Active Directory

## 1. Estado

A integração foi implementada em 2026-07-28 com dois estágios independentes:

1. descoberta administrativa, habilitada por `LDAP_ENABLED`;
2. autenticação corporativa, habilitada separadamente por
   `LDAP_AUTHENTICATION_ENABLED`.

O bind, as bases e o grupo foram validados no DEV. A autenticação corporativa
permanece desligada até o teste controlado da configuração escolhida. Conforme
a ADR-032, descoberta e login usam o mesmo transporte: TLS monta LDAPS
automaticamente; sem TLS, LDAP simples permanece funcional com warning sobre
credenciais e senhas sem criptografia. A autenticação local existente continua
inalterada.

A configuração também pode ser mantida por SuperAdmin em
`/fe/configuracoes/autenticacao`. Enquanto o singleton não existir, o `.env`
continua sendo o baseline efetivo; após o primeiro salvamento, o registro
versionado do schema SGPD passa a ser a fonte dinâmica.

## 2. Componentes e versões

- Django 5.2.16 LTS;
- Django REST Framework 3.17.1;
- `django-auth-ldap` 5.3.0;
- `python-ldap` 3.4.7;
- `cryptography` 49.x para Fernet e validação X.509;
- OpenLDAP 2.6.10 no DEV.

O projeto não reduz versões de Django ou DRF para atender ao LDAP. O `uv.lock`
fixa as versões resolvidas.

### Pré-requisitos Debian

```bash
sudo apt-get install \
  build-essential \
  ldap-utils \
  libldap2-dev \
  libsasl2-dev \
  libssl-dev \
  python3-dev
```

No Debian 13, `libldap-dev` pode aparecer como o pacote concreto provido por
`libldap2-dev`. Depois:

```bash
uv sync --dev
```

## 3. Fronteiras de segurança

- o AD é somente provedor de descoberta e autenticação;
- nome, e-mail local, situação, papéis funcionais, associações, permissões e
  escopos pertencem ao SGPD;
- grupos AD não concedem `DP` nem associam usuários a setores;
  `RESPONSAVEL_SETOR` deriva exclusivamente do vínculo local vigente;
- credenciais AD válidas nunca criam uma conta implicitamente no login;
- somente uma ação administrativa explícita cria ou vincula a conta;
- `objectGUID`, convertido para UUID canônico, é a chave estável e única;
- e-mail e login são usados para apresentação e detecção de conflito, não como
  chave do vínculo;
- usuários desabilitados no AD são excluídos pelo filtro;
- a senha digitada pelo usuário é usada apenas no bind e nunca é persistida ou
  registrada;
- contas comuns vinculadas não fazem fallback para senha local quando o login AD
  está ativo;
- definição, redefinição e troca de senha local usam a mesma política do
  backend de autenticação e são bloqueadas quando essa credencial não pode ser
  usada;
- um superusuário local de contingência pode continuar autenticando conforme
  `LDAP_LOCAL_SUPERUSER_FALLBACK=true`.

Enquanto `LDAP_AUTHENTICATION_ENABLED=false`, uma senha local pode ser definida
para uma conta vinculada durante testes controlados. Isso não altera o vínculo
nem antecipa o login AD.

O campo de login aceita o `sAMAccountName` armazenado em `AD_USERNAME`. O UPN é
exibido na descoberta para conferência, mas não é usado como alias de login,
pois o modelo local preserva uma única chave de autenticação inequívoca.

## 4. Contrato do `.env`

```dotenv
LDAP_ENABLED=false
LDAP_AUTHENTICATION_ENABLED=false

LDAP_SERVER_ADDRESS=dc01.example.internal
# true: LDAPS automático; false: LDAP simples com warning.
LDAP_USE_TLS=true

LDAP_TLS_REQUIRE_CERTIFICATE=true
LDAP_TLS_CA_CERT_FILE=/caminho/ca-corporativa.pem

# Conta técnica somente leitura, preferencialmente UPN ou DN completo.
LDAP_BIND_DN=svc.sgpd@example.internal
LDAP_BIND_PASSWORD=

# Descoberta pode deixá-las vazias e usar defaultNamingContext do RootDSE.
# Para autenticação, LDAP_USER_SEARCH_BASE é obrigatória.
LDAP_USER_SEARCH_BASE=OU=Usuarios,OU=Corporativo,DC=example,DC=internal
LDAP_GROUP_SEARCH_BASE=OU=Grupos,OU=Corporativo,DC=example,DC=internal

# Opcional: restringe descoberta, importação, vínculo e login a um grupo.
LDAP_REQUIRED_GROUP_DN=CN=SGPD-Usuarios,OU=Grupos,DC=example,DC=internal
LDAP_NESTED_GROUP_SEARCH=true

# Opcional: filtro administrativo fixo, sempre entre parênteses.
LDAP_USER_EXTRA_FILTER=

LDAP_CONNECT_TIMEOUT_SECONDS=5
LDAP_RECEIVE_TIMEOUT_SECONDS=10
LDAP_PAGE_SIZE=100
LDAP_RESULT_LIMIT=50
LDAP_LOCAL_SUPERUSER_FALLBACK=true

# Storage privado dos certificados enviados pela central.
SYSTEM_CONFIGURATION_STORAGE_PATH=media/system-configuration
```

As variáveis LDAP continuam necessárias como baseline de primeiro boot e
contingência de implantação. A tela nunca escreve no `.env`. A senha de bind
informada pela SPA é cifrada antes da persistência e nunca é devolvida pela
API; deixar o campo vazio preserva o segredo já salvo ou o baseline do
ambiente.

`LDAP_TLS_REQUIRE_CERTIFICATE` deve permanecer `true`; com TLS selecionado, a
validação do SGPD rejeita ativação sem CA válida. Se a cadeia corporativa não
estiver no trust store do sistema, instale-a e informe
`LDAP_TLS_CA_CERT_FILE`.

Com `LDAP_USE_TLS=false`, descoberta e autenticação usam LDAP simples. O system
check e a SPA exibem warning permanente porque a credencial técnica e as
senhas dos usuários trafegam sem criptografia.

### Sequência de ativação

1. preencher servidor, escolher o transporte e informar o bind;
2. se TLS estiver selecionado, enviar a CA;
3. manter os dois switches falsos e revisar os valores;
4. habilitar somente `LDAP_ENABLED=true`;
5. executar `uv run manage.py check` e
   `uv run manage.py check_active_directory`;
6. validar a busca de grupos em Configurações e a busca de usuários em
   `/fe/usuarios`;
7. criar ou vincular uma conta de teste sem conceder papel automaticamente;
8. manter um superusuário local de contingência testado;
9. preencher `LDAP_USER_SEARCH_BASE`;
10. habilitar `LDAP_AUTHENTICATION_ENABLED=true`;
11. testar login AD, rejeição de conta desabilitada, rejeição fora do grupo,
    ausência de provisionamento implícito e fallback local bloqueado para conta
    comum.

## 5. Como descobrir domínio, OUs e grupos

Use uma conta técnica somente leitura e `-W`, para que a senha não apareça na
linha de comando.

Os exemplos abaixo usam uma variável de shell derivada da mesma escolha da
aplicação:

```bash
export LDAP_SERVER_URI="ldaps://dc01.example.internal"
# Sem TLS, use: export LDAP_SERVER_URI="ldap://dc01.example.internal"
```

Quando a CA corporativa não estiver no trust store do sistema, informe-a ao
cliente antes do diagnóstico:

```bash
export LDAPTLS_CACERT=/caminho/ca-corporativa.pem
```

Não use `LDAPTLS_REQCERT=never`.

### Base padrão do domínio

```bash
ldapsearch -LLL -x \
  -H "$LDAP_SERVER_URI" \
  -D "$LDAP_BIND_DN" -W \
  -b "" -s base \
  "(objectClass=*)" defaultNamingContext
```

O valor de `defaultNamingContext` pode ser usado como base ampla. Para reduzir
volume e exposição, prefira uma OU específica quando a organização a possuir.

### Procurar OUs

```bash
ldapsearch -LLL -x \
  -H "$LDAP_SERVER_URI" \
  -D "$LDAP_BIND_DN" -W \
  -b "DC=example,DC=internal" -s sub \
  "(objectClass=organizationalUnit)" distinguishedName ou
```

O DN escolhido vai em `LDAP_USER_SEARCH_BASE` ou
`LDAP_GROUP_SEARCH_BASE`. O escopo usado pelo SGPD é `SUBTREE`, portanto inclui
OUs descendentes.

### Procurar o DN de um grupo

```bash
ldapsearch -LLL -x \
  -H "$LDAP_SERVER_URI" \
  -D "$LDAP_BIND_DN" -W \
  -b "$LDAP_GROUP_SEARCH_BASE" -s sub \
  "(&(objectCategory=group)(|(cn=*SGPD*)(sAMAccountName=*SGPD*)))" \
  distinguishedName cn sAMAccountName description
```

Copie o `distinguishedName` exato para `LDAP_REQUIRED_GROUP_DN`.

### Validar usuários ativos de uma OU

```bash
ldapsearch -LLL -x \
  -H "$LDAP_SERVER_URI" \
  -D "$LDAP_BIND_DN" -W \
  -b "$LDAP_USER_SEARCH_BASE" -s sub \
  "(&(objectCategory=person)(objectClass=user)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))" \
  objectGUID sAMAccountName userPrincipalName displayName givenName sn mail
```

### Validar usuários de um grupo, inclusive grupos aninhados

Substitua o DN de exemplo pelo DN exato encontrado:

```bash
ldapsearch -LLL -x \
  -H "$LDAP_SERVER_URI" \
  -D "$LDAP_BIND_DN" -W \
  -b "$LDAP_USER_SEARCH_BASE" -s sub \
  "(&(objectCategory=person)(objectClass=user)(!(userAccountControl:1.2.840.113556.1.4.803:=2))(memberOf:1.2.840.113556.1.4.1941:=CN=SGPD-Usuarios,OU=Grupos,DC=example,DC=internal))" \
  objectGUID sAMAccountName userPrincipalName displayName givenName sn mail
```

Para somente associação direta, use `(memberOf=<DN>)` e configure
`LDAP_NESTED_GROUP_SEARCH=false`.

### Alternativa com PowerShell da Infraestrutura

Em uma estação com o módulo ActiveDirectory, o mesmo recorte pode ser validado
sem conhecer antecipadamente nomes de tabelas ou atributos não padronizados:

```powershell
Get-ADUser `
  -SearchBase 'OU=Usuarios,OU=Corporativo,DC=example,DC=internal' `
  -SearchScope Subtree `
  -LDAPFilter '(&(objectCategory=person)(objectClass=user)(!(userAccountControl:1.2.840.113556.1.4.803:=2))(memberOf:1.2.840.113556.1.4.1941:=CN=SGPD-Usuarios,OU=Grupos,DC=example,DC=internal))' `
  -Properties objectGUID,sAMAccountName,userPrincipalName,displayName,givenName,sn,mail
```

O `-SearchBase` faz o recorte por OU; a expressão `memberOf` faz o recorte por
grupo. Remova somente a cláusula `memberOf` para validar a OU inteira.

## 6. Filtros aplicados pelo SGPD

Filtro base não configurável:

```ldap
(&(objectCategory=person)
  (objectClass=user)
  (!(userAccountControl:1.2.840.113556.1.4.803:=2)))
```

A busca administrativa adiciona, com escape contra LDAP injection:

```ldap
(|(sAMAccountName=*texto*)
  (userPrincipalName=*texto*)
  (displayName=*texto*)
  (mail=*texto*))
```

O `LDAP_REQUIRED_GROUP_DN`, quando definido, é sempre combinado por `AND`. A
importação não aceita outro grupo por requisição: usa exatamente o grupo salvo.
O `LDAP_USER_EXTRA_FILTER`, se usado, também é combinado por `AND` e deve ser
tratado como configuração revisada, não como entrada do usuário.

## 7. API e interface

Endpoints, todos autenticados e protegidos por `link_ad_identity`:

```text
GET  /api/v1/accounts/directory/status/
GET  /api/v1/accounts/directory/groups/?q=
GET  /api/v1/accounts/directory/users/?q=
POST /api/v1/accounts/directory/users/create/
```

A criação também exige `manage_users` no service. A resposta de busca informa
identidade já vinculada, conflito de login/e-mail e atributos ausentes. O POST
de criação recebe somente `{"identifier": "<objectGUID>"}`; não há justificativa
manual, e os dois eventos de auditoria recebem um motivo operacional
padronizado. A SPA:

- importa usuário pela lista em `/fe/usuarios`;
- só habilita `Criar vinculada` quando login, nome, sobrenome e e-mail estão
  presentes e não há vínculo ou conflito local, informando o requisito ausente;
- respeita exatamente a base, o grupo obrigatório e o filtro salvos;
- abre a conta local em caso de conflito, evitando duplicidade;
- pesquisa a identidade dentro do detalhe da conta antes de vincular;
- nunca solicita ou armazena a senha AD na administração.

Configuração técnica, sempre exclusiva de `is_superuser`:

```text
GET  PUT /api/v1/settings/ldap/
POST     /api/v1/settings/ldap/validate/
POST     /api/v1/settings/ldap/certificate/
POST     /api/v1/settings/ldap/certificate/validate/
POST     /api/v1/settings/ldap/connection-test/
```

`/fe/configuracoes` apresenta os cards dos módulos técnicos e
`/fe/configuracoes/autenticacao` implementa o primeiro. O endpoint de validação
verifica o candidato sem persistir; o teste de conexão usa somente a
configuração salva, faz bind e RootDSE sem listar pessoas e registra um
fingerprint. O login AD só pode ser habilitado quando esse fingerprint ainda
corresponde à configuração e, com TLS, ao certificado vigentes. Quando TLS
está ativo, o envio de uma nova CA desabilita imediatamente o login AD e
invalida o probe anterior; a reativação exige um novo teste bem-sucedido. Sem
TLS, a CA não participa do transporte e sua manutenção não altera login ou
probe. A mesma tela pesquisa grupos usando a configuração salva e preenche o
DN do grupo obrigatório.

## 8. Falhas e operação

- configuração inválida: `directory_not_configured`, HTTP 503;
- indisponibilidade/bind/TLS: `directory_unavailable`, HTTP 503;
- contrato de atributos inválido: `directory_contract_error`, HTTP 502;
- identidade fora do filtro: `directory_identity_not_found`, HTTP 404;
- autenticação inválida continua indistinguível por usuário, senha, conta
  desabilitada ou grupo, evitando enumeração.

Logs contêm somente operação lógica, duração, quantidade de linhas e correlation
ID. Não contêm filtro preenchido, DN pesquisado, senha ou payload de usuário.

## 9. Referências normativas

- [django-auth-ldap 5.3 — documentação oficial](https://django-auth-ldap.readthedocs.io/en/stable/)
- [Microsoft Learn — Get-ADUser e `-SearchBase`](https://learn.microsoft.com/en-us/powershell/module/activedirectory/get-aduser?view=windowsserver2025-ps)
- [Microsoft Learn — regras de correspondência LDAP do AD](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-adts/4e638665-f466-4597-93c4-12f2ebfabab5)
- [Microsoft Learn — atributo `objectGUID`](https://learn.microsoft.com/en-us/windows/win32/adschema/a-objectguid)

## 10. Estado da homologação no DEV BSA

Descoberta não autenticada executada em 2026-07-28:

- domínio: `bsa.local`;
- controlador primário: `ad.bsa.local`, resolvendo para `192.168.1.20`;
- LDAP `389/tcp` e LDAPS `636/tcp` acessíveis;
- RootDSE confirmou `defaultNamingContext: DC=bsa,DC=local`;
- certificado LDAPS com `CN` e SAN `ad.bsa.local`;
- emissor: `BSA-AD-CA`;
- validade observada: 2026-02-09 a 2027-02-09;
- a CA interna ainda não está no trust store do host SGPD.

Configuração de descoberta validada:

```dotenv
LDAP_ENABLED=true
LDAP_AUTHENTICATION_ENABLED=false
LDAP_SERVER_ADDRESS=ad.bsa.local
LDAP_USE_TLS=false
LDAP_USER_SEARCH_BASE=DC=bsa,DC=local
LDAP_GROUP_SEARCH_BASE=OU=Grupos,OU=BSAbioenergia,DC=bsa,DC=local
LDAP_REQUIRED_GROUP_DN=CN=BSA_SGPD,OU=Grupos,OU=BSAbioenergia,DC=bsa,DC=local
```

O bind técnico e o DN exato do grupo `BSA_SGPD` foram confirmados. O filtro
base, incluindo conta ativa e associação aninhada ao grupo, encontrou quatro
identidades elegíveis dentro do limite de 50, sem projetar seus dados durante o
probe.

Com `LDAP_USE_TLS=false`, descoberta e login usam LDAP simples e exibem warning
permanente. Para usar TLS, instalar a CA `BSA-AD-CA`, marcar `Negociar TLS` e
repetir o probe; a aplicação monta LDAPS automaticamente. Enquanto o login AD
estiver desligado, senha local pode ser definida para contas vinculadas de
teste; ao ativá-lo, a API e a SPA bloquearão essa ação para contas comuns.
