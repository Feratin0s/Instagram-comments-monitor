# Instagram Comments Monitor

Ferramenta CLI para coletar comentários e respostas de posts e reels do Instagram usando a sessão autenticada do seu navegador Chrome.

## O que faz

- Extrai o `shortcode` do post/reel a partir da URL
- Autentica usando os cookies do Chrome (sem precisar de senha)
- Descobre o `media_id` numérico lendo o HTML público do post
- Coleta todos os comentários e respostas via endpoint web do Instagram
- Exporta tudo para CSV (uma linha por comentário/resposta)

## Estrutura do projeto

```
Instagram-reactions-monitor/
├── main.py                    # Script principal
├── src/
│   ├── __init__.py            # Marca a pasta como pacote Python
│   └── cookies.py             # Carrega cookies do Chrome
├── posts/                     # CSVs gerados (opcional)
├── requirements.txt           # Dependências
└── venv/                      # Ambiente virtual
```

## Requisitos

- Python 3.10+
- Google Chrome instalado e logado no Instagram (preferencialmente via Flatpak no Linux)
- Linux (testado no Kali)

## Instalação

```bash
# Clona / entra no diretório
cd Instagram-reactions-monitor

# Cria e ativa o venv
python -m venv venv
source venv/bin/activate

# Instala dependências
pip install -r requirements.txt
```

Dependências principais:

```
instaloader
browser-cookie3
```

## Uso

```bash
python main.py "<URL_DO_POST>"
```

Exemplos:

```bash
python main.py "https://www.instagram.com/reels/DdjHE2HBLBR/"
python main.py "https://www.instagram.com/reel/ABC123/"
python main.py "https://www.instagram.com/p/XYZ789/"
```

> **Atenção:** sempre use **aspas** em volta da URL, porque ela pode conter `?`, `&` e `=` que o shell interpretaria de outra forma.

## Saída

O script imprime as informações do post no terminal:

```
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

```
instagram_<shortcode>_comentarios.csv
```

Colunas:

| Campo    | Descrição                                      |
|----------|------------------------------------------------|
| tipo     | `comentario` ou `resposta`                     |
| id       | ID do comentário/resposta                      |
| id_pai   | ID do comentário pai (só para respostas)       |
| usuario  | Nome de usuário do autor                       |
| texto    | Conteúdo do comentário                         |
| curtidas | Número de curtidas                             |
| data     | Timestamp UTC em ISO 8601                      |

O CSV é gravado **linha a linha** com `flush()`. Se a coleta for interrompida, o que já foi coletado fica salvo.

## Como funciona (fluxo)

1. **Validação da URL** — `extrair_shortcode()` aceita `/p/`, `/reel/` e `/reels/`, retorna `(tipo, shortcode)`.
2. **Login** — `fazer_login()` carrega os cookies do Chrome e injeta na sessão do Instaloader. Valida com `L.test_login()`.
3. **Descoberta do `media_id`** — faz GET na página do post, extrai `media_id` ou `pk` do HTML via regex.
4. **Metadados** — chama `/api/v1/media/{media_id}/info/` para obter autor, curtidas, contagem de comentários.
5. **Coleta** — pagina via `/api/v1/media/{media_id}/comments/` e, para cada comentário com respostas, busca `/comments/{id}/child_comments/`.
6. **Exportação** — grava no CSV a cada linha recebida.

## Limitações conhecidas

- Só funciona **logado**. Posts privados que você não segue retornam erro.
- O Instagram pode responder HTTP 200 com **página de erro** (`httpErrorPage`) quando a sessão está inválida. O script detecta e levanta exceção.
- Rate limit: a paginação tem delay aleatório de 2–5s entre páginas e 1–3s entre threads de respostas. Não remova esses delays.
- Cookies do Chrome expiram. Se `test_login()` falhar, reabra o Instagram no navegador e faça login de novo.

## Troubleshooting

**`There are multiple cookies with name, 'csrftoken'`**
O Instagram seta `csrftoken` em `.instagram.com` e `www.instagram.com`. O `requests` não aceita duplicados. Solução: `_deduplicar_cookies()` antes de cada requisição.

**`Expecting value: line 1 column 1 (char 0)`**
A resposta não é JSON — provavelmente HTML de erro/login. Falta o header `X-CSRFToken` na requisição, ou a sessão expirou.

**`'PostSimples' object has no attribute 'get_comments'`**
Esperado. `PostSimples` substitui o objeto do Instaloader e não implementa `get_comments`. Use o fallback `_linhas_web`.

**Página de erro com `httpErrorPage` no HTML**
Post privado, removido, ou URL com o tipo errado (`/reel/` vs `/reels/`). Use `tipo` correto da URL original.

**`ImportError: attempted relative import with no known parent package`**
Você está rodando `python main.py` (script), mas o import usa `.code.cookies` (relativo). Troque por `from code.cookies import ...` e garanta que existe `code/__init__.py`.

## Notas de segurança

- O script **usa sua sessão autenticada** do Chrome. Não compartilhe o CSV gerado se ele contiver dados sensíveis.
- Não commite cookies nem o `venv/` no git.
- Use por sua conta e risco — automação do Instagram pode violar os Termos de Uso da plataforma.

## Licença

Uso pessoal. Sem garantias.