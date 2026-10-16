"""Offres LinkedIn via les pages publiques (sans connexion).

Attention : les CGU de LinkedIn interdisent la collecte automatisée. Volume limité
et pauses entre les requêtes ; désactivable dans config.toml ([linkedin] actif = false).
"""
import re
import time
from urllib.parse import quote

from bs4 import BeautifulSoup

from ..models import Offre
from ..skills import mentionne_alternance, titre_exclu
from ..web import session

URL_RECHERCHE = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
URL_DETAIL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"


def rechercher(conf: dict, mots_cles: list[str], ville: str, rayon_km: int) -> list[Offre]:
    s = session()
    pause = float(conf.get("pause_secondes", 2.0))
    maxi = int(conf.get("max_offres_par_recherche", 50))
    distance_miles = max(5, min(100, round(rayon_km / 1.6)))

    offres: dict[str, Offre] = {}
    for mot in mots_cles:
        for start in range(0, maxi, 10):
            r = _get(s, URL_RECHERCHE, pause, params={
                "keywords": f"alternance {mot}",
                "location": f"{ville}, France",
                "distance": distance_miles,
                "start": start,
            })
            if r.status_code == 429:
                print("  [LinkedIn] trop de requêtes (429), arrêt de la collecte LinkedIn.")
                return _completer(s, list(offres.values()), pause)
            if r.status_code != 200 or not r.text.strip():
                break
            cartes = BeautifulSoup(r.text, "html.parser").select("li")
            if not cartes:
                break
            for c in cartes:
                o = _carte(c)
                if o and o.id not in offres:
                    offres[o.id] = o
            if len(cartes) < 10:
                break
    return _completer(s, list(offres.values()), pause)


def _get(s, url: str, pause: float, params: dict | None = None):
    """GET avec attente progressive si LinkedIn limite le débit (HTTP 429)."""
    for attente in (0, 15, 45, 90):
        if attente:
            print(f"  [LinkedIn] limite de débit, nouvel essai dans {attente} s…")
            time.sleep(attente)
        r = s.get(url, params=params, timeout=20)
        time.sleep(pause)
        if r.status_code != 429:
            return r
    return r


def _texte(noeud, selecteur: str) -> str:
    el = noeud.select_one(selecteur)
    return el.get_text(" ", strip=True) if el else ""


def _carte(c) -> Offre | None:
    div = c.select_one("[data-entity-urn]")
    if not div:
        return None
    m = re.search(r"(\d+)$", div.get("data-entity-urn", ""))
    if not m:
        return None
    lien = c.select_one("a.base-card__full-link")
    date = c.select_one("time")
    return Offre(
        source="LinkedIn",
        id=m.group(1),
        titre=_texte(c, ".base-search-card__title"),
        entreprise=_texte(c, ".base-search-card__subtitle"),
        lieu=_texte(c, ".job-search-card__location"),
        url=(lien.get("href", "").split("?")[0] if lien else f"https://www.linkedin.com/jobs/view/{m.group(1)}"),
        date=date.get("datetime", "") if date else "",
    )


def _completer(s, offres: list[Offre], pause: float) -> list[Offre]:
    """Récupère la description de chaque offre et ne garde que l'alternance."""
    gardees = []
    for o in offres:
        if titre_exclu(o.titre):
            continue
        try:
            r = _get(s, URL_DETAIL.format(o.id), pause / 2)
            if r.status_code == 429:
                print("  [LinkedIn] limite atteinte pendant la lecture des descriptions.")
                gardees.extend(x for x in offres[offres.index(o):] if mentionne_alternance(x.titre))
                break
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                o.description = _texte(soup, ".show-more-less-html__markup")
                criteres = [li.get_text(" ", strip=True) for li in soup.select(".description__job-criteria-item")]
                o.type_contrat = " | ".join(criteres)
        except Exception as e:  # une offre en erreur ne doit pas bloquer les autres
            print(f"  [LinkedIn] offre {o.id} ignorée : {e}")
        if mentionne_alternance(f"{o.titre} {o.type_contrat}", o.description):
            gardees.append(o)
    return gardees


def lien_recherche_rh(entreprise: str) -> str:
    return ("https://www.linkedin.com/search/results/people/?keywords="
            + quote(f"recrutement OR RH OR talent acquisition {entreprise}"))
