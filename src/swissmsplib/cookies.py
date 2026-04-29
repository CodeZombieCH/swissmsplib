import os
from http.cookiejar import MozillaCookieJar

import requests


def _load_cookies(session: requests.Session, name: str):
    path = f".data/{name}.cookies.txt"
    cookies = MozillaCookieJar(filename=path)
    session.cookies = cookies  # type: ignore

    if os.path.exists(path):
        cookies.load(ignore_discard=True)
        return True
    else:
        return False


def _save_cookies(
    session: requests.Session,
):
    if session.cookies and isinstance(session.cookies, MozillaCookieJar):
        session.cookies.save(ignore_discard=True)
