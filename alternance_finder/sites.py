"""Retrouve le site web d'une entreprise à partir de son nom.

La Bonne Alternance ne fournit presque jamais le site des entreprises « susceptibles de recruter ».
On essaie les adresses probables (nom.fr, nom.com, nom-compose.fr…) et on garde la première
page qui répond et qui contient bien le nom de l'entreprise. Résultat à vérifier d'un coup d'œil.
"""
import re
import unicodedata
from urllib.parse import urlparse

from .web import session

FORMES_JURIDIQUES = r"\b(sas|sasu|sarl|eurl|sa|sci|scop|groupe|group|societe|ste|et cie)\b"
EXTENSIONS = ("fr", "com", "io", "net", "eu")
RE_PARKING = re.compile(r"domain.{0,20}(for sale|à vendre|a vendre|parked)|sedo|godaddy|parking", re.I)


def _ascii(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def _mots(nom: str) -> list[str]:
    s = re.sub(r"\(.*?\)", "", _ascii(nom))
    return re.findall(r"[a-z0-9]+", re.sub(FORMES_JURIDIQUES, " ", s))


def _candidats(nom: str) -> list[str]:
    mots = _mots(nom)
    if not mots:
        return []
    bases = dict.fromkeys(["".join(mots), "-".join(mots)])
    return [f"https://{b}.{ext}" for b in bases for ext in EXTENSIONS]


def trouver_site(nom: str) -> str:
    cle = "".join(_mots(nom))
    if len(cle) < 3:
        return ""
    s = session()
    for url in _candidats(nom):
        try:
            r = s.get(url, timeout=6, allow_redirects=True)
        except Exception:
            continue
        if r.status_code != 200 or "html" not in r.headers.get("Content-Type", ""):
            continue
        texte = re.sub(r"[^a-z0-9]", "", _ascii(r.text[:200000]))
        if cle in texte and not RE_PARKING.search(r.text[:20000]):
            u = urlparse(r.url)
            return f"{u.scheme}://{u.hostname}/"
    return ""
