import browser_cookie3

def carregar_cookies_instagram():
    """
    Carrega os cookies do Instagram do Chrome Flatpak.
    """

    cookies = browser_cookie3.chrome(
        domain_name=".instagram.com"
    )

    cookies_dict = {}

    for cookie in cookies:
        cookies_dict[cookie.name] = cookie.value

    return cookies_dict