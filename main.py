import csv
import logging
import os
import re
from urllib.parse import urlparse
import random
import time
from src.cookies import carregar_cookies_instagram
import instaloader
import sys

UA_CHROME = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)  # idealmente o mesmo User-Agent do seu Chrome

CAMPOS = ["tipo", "id", "id_pai", "usuario", "texto", "curtidas", "data"]

# Configura o logger para mostrar as mensagens no terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():

    #print()
    #print("=" * 60)
    #print("      COLETOR DE COMENTÁRIOS DO INSTAGRAM")
    #print("=" * 60)
    #print()
#
    ## --------------------------------------------------------
    ## Pede o link
    ## --------------------------------------------------------
#
    #link = input(
    #    "Qual link do post que deseja analisar?\n> "
    #).strip()

    if len(sys.argv) > 1:
        link = sys.argv[1].strip()
        logging.info(f"Link recebido via argumento: {link}")
    else:
        link = input(
            "Qual link do post que deseja analisar?\n> "
        ).strip()

    # --------------------------------------------------------
    # Valida e extrai o shortcode
    # --------------------------------------------------------

    resultado = extrair_shortcode(link)

    if not resultado:
        return

    tipo, shortcode = resultado

    logging.info(
        f"Shortcode identificado: {shortcode} (tipo: {tipo})"
    )

    # --------------------------------------------------------
    # Cria o Instaloader
    # --------------------------------------------------------

    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        save_metadata=False,
    )

    # --------------------------------------------------------
    # Login
    # --------------------------------------------------------

    usuario = fazer_login(L)

    if not usuario:
        logging.error("Não foi possível autenticar.")
        return

    # --------------------------------------------------------
    # Carrega o post
    # --------------------------------------------------------

    try:
        logging.info("Carregando informações do post...")
        post = carregar_post_pela_api_web(L, tipo, shortcode)   # ← NOVA FUNÇÃO
    except Exception as erro:
        logging.error(f"Erro ao carregar o post: {erro}")
        return

    # --------------------------------------------------------
    # Informações do post
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("INFORMAÇÕES DO POST")
    print("=" * 60)

    print(
        f"Autor: @{post.owner_profile.username}"
    )

    print(
        f"Curtidas: {post.likes}"
    )

    print(
        f"Comentários: {post.comments}"
    )

    print(
        f"Data: {post.date_local}"
    )

    print("=" * 60)
    print()

    # --------------------------------------------------------
    # Nome do arquivo
    # --------------------------------------------------------

    arquivo_csv = f"posts/{post.owner_profile.username}_instagram_{shortcode}.csv"

    # --------------------------------------------------------
    # Coleta e exporta
    # --------------------------------------------------------

    try:

        exportar_comentarios(
            L,
            post,
            arquivo_csv
        )

    except KeyboardInterrupt:

        logging.warning(
            "Coleta interrompida pelo usuário."
        )

    except Exception as erro:

        logging.error(
            f"Erro durante a coleta: {erro}"
        )

class PostSimples:
    """Substitui o objeto do Instaloader. Só guarda o que precisamos."""
    pass


def carregar_post_pela_api_web(L, tipo, shortcode):
    """
    1. Pega o media_id numérico a partir do shortcode,
       lendo o HTML público do post.
    2. Com o media_id em mãos, chama a API de info.
    """
    import re
    from datetime import datetime

    sessao = L.context._session

    headers = {
        "User-Agent": UA_CHROME,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-CA,en;q=0.9,pt-BR;q=0.8,pt;q=0.7,en-GB;q=0.6,en-US;q=0.5",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Referer": f"https://www.instagram.com/{tipo}/{shortcode}/",
    }

    # --------------------------------------------------------
    # Passo 1: descobrir o media_id numérico
    # --------------------------------------------------------
    url_pagina = f"https://www.instagram.com/reels/{shortcode}/"

    try: 
        r = sessao.get(url_pagina, headers=headers, timeout=20)
    except Exception as e: 
        logging.error(f"Erro ao fazer .get {e}")


    logging.info(f"Status code {r}")
    #logging.info(r.text)

    # Procura por "media_id":"1234567890" ou "pk":"1234567890" no HTML
    match = re.search(r'"media_id"\s*:\s*"(\d+)"', r.text)

    if not match:
        match = re.search(r'"pk"\s*:\s*"(\d+)"', r.text)

    if not match:
        raise RuntimeError(
            "Não consegui encontrar o media_id no HTML do post. "
            "O Instagram pode ter mudado o layout ou estar bloqueando."
        )

    media_id = match.group(1)
    logging.info(f"media_id encontrado: {media_id}")

    # --------------------------------------------------------
    # Passo 2: buscar infos do post pelo media_id
    # --------------------------------------------------------
    url_info = f"https://www.instagram.com/api/v1/media/{media_id}/info/"
    r = sessao.get(url_info, headers=headers, timeout=20)
    dados = r.json()

    if dados.get("status") != "ok":
        raise RuntimeError(f"Instagram respondeu: {str(dados)[:200]}")

    item = dados["items"][0]

    # --------------------------------------------------------
    # Passo 3: montar objeto simples
    # --------------------------------------------------------
    post = PostSimples()
    post.mediaid   = media_id
    post.shortcode = item.get("code", shortcode)
    post.likes     = item.get("like_count", 0)
    post.comments  = item.get("comment_count", 0)
    post.date_local = datetime.fromtimestamp(item.get("taken_at", 0))

    class _Owner:
        username = item["user"]["username"]
    post.owner_profile = _Owner()

    return post

# ============================================================
# LOGIN
# ============================================================

def fazer_login(L):
    """
    Carrega a sessão do Instagram diretamente dos cookies
    do Chrome Flatpak.
    """

    logging.info("Carregando sessão do Chrome...")

    try:
        cookies = carregar_cookies_instagram()

        if not cookies:
            logging.error(
                "Nenhum cookie do Instagram foi encontrado."
            )
            return None

        # Coloca os cookies dentro da sessão do Instaloader
        L.context.update_cookies(cookies)

        logging.info(
            f"{len(cookies)} cookies do Instagram carregados."
        )

        # Verifica quem está autenticado
        usuario = L.test_login()

        if not usuario:
            logging.error(
                "Os cookies foram encontrados, mas a sessão "
                "do Instagram não está autenticada."
            )
            return None

        logging.info(
            f"Sessão autenticada como @{usuario}."
        )

        # Guarda o usuário na sessão do Instaloader
        L.context.username = usuario

        return usuario

    except Exception as erro:
        logging.error(
            f"Erro ao carregar cookies do Chrome: {erro}"
        )
        return None

# ============================================================
# FUNÇÃO PARA VALIDAR E EXTRAIR O SHORTCODE DO INSTAGRAM
# ============================================================

def extrair_shortcode(link):
    """
    Recebe a URL de um post do Instagram e retorna (tipo, shortcode).

    Exemplos aceitos:

    https://www.instagram.com/p/ABC123/
    https://instagram.com/p/ABC123/
    https://www.instagram.com/reel/ABC123/
    https://www.instagram.com/reels/ABC123/
    """

    link = link.strip()

    # Analisa a URL
    url_analisada = urlparse(link)

    logging.info(url_analisada)

    if url_analisada.scheme != "https":
        logging.error(
            "A URL fornecida não utiliza o protocolo seguro HTTPS."
        )
        return None
    
    dominio = url_analisada.netloc.lower()

    # Remove "www." para facilitar a comparação
    dominio = dominio.removeprefix("www.")

    if dominio != "instagram.com":
        logging.error(
            f"O link informado não pertence ao Instagram: {url_analisada.netloc}"
        )
        return None

    # --------------------------------------------------------
    # 3. Extrai o caminho
    # --------------------------------------------------------

    caminho = url_analisada.path.strip("/")

    partes = caminho.split("/")

    if len(partes) < 2:
        logging.error("Não foi possível identificar um post/reel nessa URL.")
        return None

    tipo = partes[0].lower()

    if tipo not in ("p", "reel", "reels"):
        logging.error(
            "A URL não parece ser um post ou reel do Instagram."
        )
        return None

    shortcode = partes[1]

    if not shortcode:
        logging.error("Não foi possível encontrar o shortcode do post.")
        return None

    return tipo, shortcode
    
# ============================================================
# EXPORTAÇÃO DOS COMENTÁRIOS
# ============================================================

# ------------------------------------------------------------
# Fonte 2: endpoint web (fallback)
# ------------------------------------------------------------
def _paginar(sessao, url, headers, chave_cursor):
    params = {"can_support_threading": "true", "permalink_enabled": "false"}
    while True:
        r = sessao.get(url, params=params, headers=headers, timeout=30)
        dados = r.json()
        if dados.get("status") != "ok":
            raise RuntimeError(f"Endpoint web falhou: {str(dados)[:200]}")
        yield from dados.get("comments", []) or dados.get("child_comments", [])
        cursor = dados.get(chave_cursor)
        if not (cursor and (dados.get("has_more_comments") or dados.get("has_more_headload_comments") or dados.get("has_more_tail_child_comments"))):
            break
        params["min_id"] = cursor
        time.sleep(random.uniform(2, 5))


def _normalizar(c, tipo, id_pai=""):
    from datetime import datetime, timezone
    return {
        "tipo": tipo, "id": c.get("pk"), "id_pai": id_pai,
        "usuario": (c.get("user") or {}).get("username", ""),
        "texto": c.get("text", ""),
        "curtidas": c.get("comment_like_count", 0),
        "data": datetime.fromtimestamp(
            c.get("created_at", 0), tz=timezone.utc
        ).isoformat(),
    }


def _linhas_web(L, post):
    sessao = L.context._session
    headers = {
        "User-Agent": UA_CHROME,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-CA,en;q=0.9,pt-BR;q=0.8,pt;q=0.7,en-GB;q=0.6,en-US;q=0.5",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Referer": f"https://www.instagram.com/reels/{post.shortcode}/",
    }
    base = f"https://www.instagram.com/api/v1/media/{post.mediaid}/comments/"

    for c in _paginar(sessao, base, headers, "next_min_id"):
        yield _normalizar(c, "comentario")

        if c.get("child_comment_count", 0) > 0:
            url_filhos = f"{base}{c['pk']}/child_comments/"
            for r in _paginar(sessao, url_filhos, headers, "next_min_child_cursor"):
                yield _normalizar(r, "resposta", c["pk"])
            time.sleep(random.uniform(1, 3))


# ------------------------------------------------------------
# Exportação (grava linha a linha)
# ------------------------------------------------------------
def exportar_comentarios(L, post, arquivo_csv):
    logging.info("Iniciando coleta dos comentários...")

    total_com = total_resp = 0

    with open(arquivo_csv, "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS)
        escritor.writeheader()

        #logging.info(f"{L} and {post}")

        for linha in _linhas_web(L, post):

            #logging.info("passou aqui")

            escritor.writerow(linha)
            f.flush()
            if linha["tipo"] == "comentario":
                total_com += 1
            else:
                total_resp += 1
            logging.info(f"[Exportado] {linha['tipo']} @{linha['usuario']} | curtidas: {linha['curtidas']}")

    logging.info(f"Comentários: {total_com} | Respostas: {total_resp}")
    logging.info(f"Arquivo salvo em: {os.path.abspath(arquivo_csv)}")

# ============================================================
# EXECUTA O PROGRAMA
# ============================================================

if __name__ == "__main__":
    main()