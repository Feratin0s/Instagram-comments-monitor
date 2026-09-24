**# Instagram Comments Monitor**

Ferramenta CLI para coletar comentários e respostas de posts e reels do Instagram usando uma sessão autenticada.

**## O que faz**

* Extrai o `shortcode` do post/reel a partir da URL
* Autentica usando os cookies da sessão do Instagram
* Descobre o `media_id` numérico lendo o HTML público do post
* Coleta todos os comentários e respostas via endpoint web do Instagram
* Exporta tudo para CSV (uma linha por comentário/resposta)

**## Estrutura do projeto**

```text
Instagram-reactions-monitor/

├── main.py
├── src/
│   ├── __init__.py
│   └── cookies.py
├── cookies_instagram.txt
├── posts/
├── requirements.txt
└── venv/
```

**## Requisitos**

* Python 3.10+
* Google Chrome instalado e logado no Instagram
* Linux (testado no Kali) ou Windows

**## Instalação**

Primeiro, clone o projeto e entre no diretório:

```bash
cd Instagram-reactions-monitor
```

### Linux

Crie o ambiente virtual:

```bash
python3 -m venv venv
```

Ative:

```bash
source venv/bin/activate
```

Depois instale as dependências:

```bash
pip install -r requirements.txt
```

### Windows — PowerShell

Crie o ambiente virtual:

```powershell
python -m venv venv
```

Ative:

```powershell
.\venv\Scripts\Activate.ps1
```

Depois instale as dependências:

```powershell
pip install -r requirements.txt
```

> Se o PowerShell bloquear a execução do script de ativação, execute o PowerShell como usuário normal e rode:
>
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```
>
> Depois tente novamente:
>
> ```powershell
> .\venv\Scripts\Activate.ps1
> ```

### Windows — CMD

Crie o ambiente virtual:

```cmd
python -m venv venv
```

Ative:

```cmd
venv\Scripts\activate.bat
```

Depois instale as dependências:

```cmd
pip install -r requirements.txt
```

Dependências principais:

```text
instaloader
browser-cookie3
```

**## Configuração da sessão do Instagram**

Antes de executar o programa, é necessário renomear o arquivo:

```text
cookies_instagram.txt
```

Para: 

```text
cookies_instagram.json
```

Esse arquivo deve conter os cookies da sua sessão autenticada do Instagram no seguinte formato:

```json
{
  "sessionid": "COLE_AQUI",
  "csrftoken": "COLE_AQUI",
  "ds_user_id": "COLE_AQUI"
}
```

### Como obter os cookies

1. Abra o **Instagram** no Chrome e faça login normalmente.
2. Abra as ferramentas de desenvolvedor com `F12` ou `Ctrl + Shift + I`.
3. Acesse a aba **Application**.
4. No menu lateral, procure por **Cookies**.
5. Selecione:

```text
https://www.instagram.com
```

6. Localize:

   * `sessionid`
   * `csrftoken`
   * `ds_user_id`

7. Copie o valor de cada cookie para o `cookies_instagram.json`.

Por exemplo:

```json
{
  "sessionid": "SEU_SESSIONID",
  "csrftoken": "SEU_CSRFTOKEN",
  "ds_user_id": "SEU_DS_USER_ID"
}
```

Depois de preencher o arquivo, o programa pode ser executado normalmente.

> **⚠️ IMPORTANTE:** esses valores são credenciais da sua sessão do Instagram. **Nunca compartilhe o conteúdo do `cookies_instagram.json`**, publique esses valores no GitHub ou envie para outra pessoa.

**## Uso**

### Linux

Com o ambiente virtual ativado:

```bash
python main.py "<URL_DO_POST>"
```

### Windows

Com o ambiente virtual ativado:

```powershell
python main.py "<URL_DO_POST>"
```

Exemplos:

```bash
python main.py "https://www.instagram.com/reels/DdjHE2HBLBR/"

python main.py "https://www.instagram.com/reel/ABC123/"

python main.py "https://www.instagram.com/p/XYZ789/"
```

> **Atenção:** sempre use **aspas** em volta da URL, porque ela pode conter `?`, `&` e `=` que o shell pode interpretar de outra forma.

**## Saída**

O script imprime as informações do post no terminal:

```text
============================================================

INFORMAÇÕES DO POST

============================================================

Autor: @usuario

Curtidas: 16269

Comentários: 273

Data: 2026-09-21 09:00:08

============================================================
```

E gera um CSV no diretório atual:

```text
instagram_<shortcode>_comentarios.csv
```

Colunas:

| Campo    | Descrição                                |
| -------- | ---------------------------------------- |
| tipo     | `comentario` ou `resposta`               |
| id       | ID do comentário/resposta                |
| id_pai   | ID do comentário pai (só para respostas) |
| usuario  | Nome de usuário do autor                 |
| texto    | Conteúdo do comentário                   |
| curtidas | Número de curtidas                       |
| data     | Timestamp UTC em ISO 8601                |

O CSV é gravado **linha a linha** com `flush()`. Se a coleta for interrompida, o que já foi coletado fica salvo.

**## Como funciona (fluxo)**

1. **Validação da URL** — `extrair_shortcode()` aceita `/p/`, `/reel/` e `/reels/`, retornando `(tipo, shortcode)`.
2. **Login** — `fazer_login()` carrega os cookies de `cookies_instagram.txt` e injeta a sessão autenticada.
3. **Descoberta do `media_id`** — faz GET na página do post e extrai `media_id` ou `pk` do HTML via regex.
4. **Metadados** — chama `/api/v1/media/{media_id}/info/` para obter autor, curtidas e contagem de comentários.
5. **Coleta** — pagina via `/api/v1/media/{media_id}/comments/` e, para cada comentário com respostas, busca `/comments/{id}/child_comments/`.
6. **Exportação** — grava no CSV a cada linha recebida.

**## Limitações conhecidas**

* Só funciona **logado**. Posts privados que você não segue retornam erro.
* O Instagram pode responder HTTP 200 com **página de erro** (`httpErrorPage`) quando a sessão está inválida. O script detecta e levanta exceção.
* Rate limit: a paginação tem delay aleatório de 2–5s entre páginas e 1–3s entre threads de respostas. Não remova esses delays.
* Cookies do Instagram podem expirar ou ser invalidados. Se a autenticação falhar, obtenha os valores atuais novamente pelo navegador.

**## Troubleshooting**

**`There are multiple cookies with name, 'csrftoken'`**

O Instagram pode definir `csrftoken` em `.instagram.com` e `www.instagram.com`. O `requests` não aceita duplicados. Solução: `_deduplicar_cookies()` antes de cada requisição.

**`Expecting value: line 1 column 1 (char 0)`**

A resposta não é JSON — provavelmente HTML de erro/login. Falta o header `X-CSRFToken` na requisição, ou a sessão expirou.

**`'PostSimples' object has no attribute 'get_comments'`**

Esperado. `PostSimples` substitui o objeto do Instaloader e não implementa `get_comments`. Use o fallback `_linhas_web`.

**Página de erro com `httpErrorPage` no HTML**

Post privado, removido, sessão inválida ou URL com o tipo errado (`/reel/` vs `/reels/`). Use o tipo correto da URL original.

**`ImportError: attempted relative import with no known parent package`**

Você está rodando `python main.py` (script), mas o import usa `.code.cookies` (relativo). Troque por `from code.cookies import ...` e garanta que existe `code/__init__.py`.

**## Notas de segurança**

* O arquivo `cookies_instagram.txt` contém **credenciais de sessão**. Trate-o como uma senha.
* **Nunca compartilhe ou publique** o conteúdo de `cookies_instagram.txt`.
* Não commite `cookies_instagram.txt`, cookies ou o `venv/` no Git.
* Não compartilhe o CSV gerado se ele contiver dados sensíveis.
* Use por sua conta e risco — automação do Instagram pode violar os Termos de Uso da plataforma.

**## Licença**

Uso pessoal. Sem garantias.
