"""Recherche des e-mails RH / recrutement des entreprises.

Ordre des sources :
1. e-mail de contact fourni dans l'offre (France Travail)
2. pages publiques du site (deviné à partir du nom s'il manque) de l'entreprise (contact, recrutement, mentions légales)
3. Hunter.io (optionnel, clé API) : e-mails professionnels du service RH
Si rien n'est trouvé, un lien de recherche LinkedIn des recruteurs de l'entreprise est fourni.

Rappel RGPD : n'utilise ces adresses que pour candidater, sans envoi massif automatisé.
"""
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote_plus, urljoin, urlparse

from bs4 import BeautifulSoup

from .models import Offre
from .sites import trouver_site
from .sources.linkedin import lien_recherche_rh
from .web import session

RE_EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PREFIXES_RH = ("rh", "drh", "recrutement", "recrutements", "recruit", "recruiting", "recruitment", "jobs", "job",
               "emploi", "emplois", "careers", "career", "carriere", "carrieres", "candidature", "candidatures",
               "talent", "talents", "hr", "alternance", "stage", "stages")
PREFIXES_GENERIQUES = ("contact", "info", "infos", "accueil", "bonjour", "hello", "direction", "secretariat")
MOTS_RECRUTEMENT = ("recrut", "carri", "career", "job", "emploi", "rejoindre", "join", "talent", "alternance")
MOTS_LIENS = ("contact", "recrut", "carri", "career", "job", "emploi", "rejoindre", "join", "mentions", "legal", "equipe")
PAGES_STANDARD = ("/contact", "/nous-contacter", "/recrutement", "/carrieres", "/mentions-legales")
PAGES_RECRUTEMENT = ("/recrutement", "/carrieres")
EXCLUS = ("example.", "exemple.", "sentry", "wixpress", "domain.", "votre", "email@", "nom@", "@2x", ".png", ".jpg",
          ".svg", ".webp", "godaddy", "wordpress", "cloudflare")


def _domaine(url: str) -> str:
    if not url:
        return ""
    if not url.startswith("http"):
        url = "https://" + url
    d = urlparse(url).netloc.lower()
    return d[4:] if d.startswith("www.") else d


def _priorite(email: str) -> int:
    local = email.split("@")[0].lower()
    if local.startswith(PREFIXES_RH) or any(p in local for p in ("recrut", "rh.", ".rh", "talent", "career", "carriere")):
        return 0
    if local.startswith(PREFIXES_GENERIQUES):
        return 1
    return 2


def scanner_site(site: str) -> tuple[list[dict], str]:
    """Extrait les e-mails publiés sur quelques pages clés du site, et la page recrutement / carrières."""
    domaine = _domaine(site)
    if not domaine:
        return [], ""
    base = f"https://{urlparse(site if site.startswith('http') else 'https://' + site).netloc}"
    s = session()
    a_visiter, vus, emails = [base], set(), {}
    page_recrutement = ""

    def lire(url: str):
        try:
            r = s.get(url, timeout=8, allow_redirects=True)
            if r.status_code == 200 and "html" in r.headers.get("Content-Type", ""):
                return r.text
        except Exception:
            pass
        return None

    html = lire(base)
    if html:
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select("a[href]"):
            href = a["href"]
            texte = (a.get_text() + " " + href).lower()
            if href.startswith("mailto:"):
                continue
            if any(m in texte for m in MOTS_LIENS):
                u = urljoin(base, href).split("#")[0]
                if _domaine(u) == domaine and u not in a_visiter:
                    a_visiter.append(u)
                    if not page_recrutement and any(m in texte for m in MOTS_RECRUTEMENT):
                        page_recrutement = u
        _extraire(html, emails)
        vus.add(base)
    a_visiter += [base + p for p in PAGES_STANDARD]

    for url in a_visiter[:9]:
        if url in vus:
            continue
        vus.add(url)
        html = lire(url)
        if html:
            _extraire(html, emails)
            if not page_recrutement and url.endswith(PAGES_RECRUTEMENT):
                page_recrutement = url

    # on garde les adresses du domaine de l'entreprise (ou de ses sous-domaines / domaines proches)
    racine = domaine.split(".")[-2] if domaine.count(".") >= 1 else domaine
    retenus = [e for e in emails if racine in e.split("@")[1]] or [e for e in emails if _priorite(e) <= 1]
    retenus.sort(key=_priorite)
    libelles = {0: "RH / recrutement", 1: "Contact général", 2: "Autre adresse (pas RH)"}
    emails_rh = [{"email": e, "nom": "", "poste": libelles[_priorite(e)], "source": "Site web"} for e in retenus[:5]]
    return emails_rh, page_recrutement


def _extraire(html: str, emails: dict) -> None:
    html = html.replace("[at]", "@").replace("(at)", "@").replace(" [dot] ", ".").replace("&#64;", "@")
    for e in RE_EMAIL.findall(html):
        e = e.strip(".").lower()
        if not any(x in e for x in EXCLUS):
            emails[e] = True


def hunter(api_key: str, site: str, entreprise: str) -> list[dict]:
    params = {"api_key": api_key, "limit": 10, "department": "hr"}
    domaine = _domaine(site)
    if domaine:
        params["domain"] = domaine
    else:
        params["company"] = entreprise
    try:
        r = session().get("https://api.hunter.io/v2/domain-search", params=params, timeout=20)
        if r.status_code != 200:
            return []
        data = r.json().get("data") or {}
    except Exception:
        return []
    res = []
    for e in data.get("emails") or []:
        nom = f"{e.get('first_name') or ''} {e.get('last_name') or ''}".strip()
        res.append({"email": e["value"], "nom": nom, "poste": e.get("position") or "RH",
                    "source": f"Hunter ({e.get('confidence', '?')}%)"})
    if not res and data.get("pattern") and data.get("domain"):
        res.append({"email": f"format : {data['pattern']}@{data['domain']}", "nom": "", "poste": "Format d'e-mail",
                    "source": "Hunter"})
    return res


def enrichir(conf: dict, offres: list[Offre]) -> None:
    """Ajoute les contacts RH à chaque offre (une recherche par entreprise)."""
    par_entreprise: dict[str, list[Offre]] = {}
    for o in offres:
        cle = (_domaine(o.site_web) or o.entreprise).lower()
        par_entreprise.setdefault(cle, []).append(o)

    def site_de(groupe):
        return next((o.site_web for o in groupe if o.site_web), "")

    # 0) site web absent des sources : on le devine à partir du nom
    if conf.get("deviner_sites_web", True):
        sans_site = [g for g in par_entreprise.values()
                     if not site_de(g) and g[0].entreprise and not g[0].entreprise.startswith("(")]
        print(f"  Recherche du site web de {len(sans_site)} entreprises…")
        with ThreadPoolExecutor(max_workers=12) as pool:
            for g, site in zip(sans_site, pool.map(lambda g: trouver_site(g[0].entreprise), sans_site)):
                for o in g:
                    o.site_web = site
        print(f"  {sum(1 for g in sans_site if site_de(g))} sites trouvés")

    # 1) sites web, en parallèle
    if conf.get("scanner_sites_web", True):
        groupes = [(cle, g) for cle, g in par_entreprise.items() if site_de(g)]
        print(f"  Lecture des sites web de {len(groupes)} entreprises…")
        with ThreadPoolExecutor(max_workers=8) as pool:
            for (cle, g), (trouves, page) in zip(groupes, pool.map(lambda x: scanner_site(site_de(x[1])), groupes)):
                for o in g:
                    _ajouter(o, trouves)
                    o.page_recrutement = o.page_recrutement or page

    # 2) Hunter pour les entreprises sans e-mail RH, en priorisant les meilleurs scores
    cle_api = conf.get("hunter_api_key", "")
    if cle_api:
        restants = [g for g in par_entreprise.values()
                    if not any(_priorite(e["email"]) == 0 for o in g for e in o.emails_rh)
                    and g[0].entreprise and not g[0].entreprise.startswith("(")]
        restants.sort(key=lambda g: max(o.score for o in g), reverse=True)
        restants = restants[: int(conf.get("max_recherches_hunter", 25))]
        print(f"  Recherche Hunter.io pour {len(restants)} entreprises…")
        for g in restants:
            trouves = hunter(cle_api, site_de(g), g[0].entreprise)
            for o in g:
                _ajouter(o, trouves)

    for o in offres:
        o.emails_rh.sort(key=lambda e: (_priorite(e["email"]) if "@" in e["email"] and " " not in e["email"] else 3))
        if not o.lien_recherche_rh and o.entreprise and not o.entreprise.startswith("("):
            o.lien_recherche_rh = lien_recherche_rh(o.entreprise)
        if not o.site_web and o.entreprise and not o.entreprise.startswith("("):
            o.lien_recherche_site = "https://www.google.com/search?q=" + quote_plus(f"{o.entreprise} {o.lieu}")


def _ajouter(o: Offre, contacts: list[dict]) -> None:
    deja = {e["email"] for e in o.emails_rh}
    for c in contacts:
        if c["email"] not in deja:
            o.emails_rh.append(dict(c))
            deja.add(c["email"])
