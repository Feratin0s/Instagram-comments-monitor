import json
import logging
import os

import browser_cookie3

ARQUIVO_JSON = "cookies_instagram.json"


def _do_navegador(func, nome):
    try:
        jar = func(domain_name="instagram.com")
        cookies = {c.name: c.value for c in jar}
        if cookies.get("sessionid"):
            logging.info(f"Cookies carregados do {nome}.")
            return cookies
    except Exception as e:
        logging.warning(f"Falhou ao ler cookies do {nome}: {e}")
    return None


def carregar_cookies_instagram():
    # 1) Arquivo manual
    if os.path.exists(ARQUIVO_JSON):
        with open(ARQUIVO_JSON, encoding="utf-8") as f:
            dados = json.load(f)
        if dados.get("sessionid"):
            logging.info("Cookies carregados do arquivo JSON.")
            return dados
        logging.warning("cookies_instagram.json existe mas não tem 'sessionid'.")

    # 2) Firefox
    cookies = _do_navegador(browser_cookie3.firefox, "Firefox")
    if cookies:
        return cookies

    # 3) Chrome (provavelmente falha no Windows com Chrome recente)
    return _do_navegador(browser_cookie3.chrome, "Chrome")