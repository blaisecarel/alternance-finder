"""API officielle France Travail « Offres d'emploi v2 » (https://francetravail.io)."""
from ..geo import Lieu
from ..models import Offre
from ..web import session

URL_TOKEN = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
URL_RECHERCHE = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
URL_OFFRE = "https://candidat.francetravail.fr/offres/recherche/detail/{}"

# E2 = contrat d'apprentissage, FS = contrat de professionnalisation
NATURES_ALTERNANCE = {"E2": "Apprentissage", "FS": "Professionnalisation"}


def _token(s, client_id: str, client_secret: str) -> str:
    r = s.post(
        URL_TOKEN,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "api_offresdemploiv2 o2dsoffre",
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def rechercher(conf: dict, mots_cles: list[str], lieu: Lieu, rayon_km: int) -> list[Offre]:
    s = session()
    s.headers["Authorization"] = "Bearer " + _token(s, conf["client_id"], conf["client_secret"])
    s.headers["Accept"] = "application/json"

    offres: dict[str, Offre] = {}
    for mot in mots_cles:
        for nature, libelle_nature in NATURES_ALTERNANCE.items():
            params = {
                "motsCles": mot,
                "natureContrat": nature,
                "commune": lieu.code_insee,
                "distance": min(rayon_km, 200),
                "range": "0-149",
            }
            r = s.get(URL_RECHERCHE, params=params, timeout=30)
            if r.status_code == 204:          # aucun résultat
                continue
            if r.status_code not in (200, 206):
                print(f"  [France Travail] '{mot}' ({nature}) : erreur {r.status_code} {r.text[:150]}")
                continue
            for o in r.json().get("resultats", []):
                if o["id"] not in offres:
                    offres[o["id"]] = _convertir(o, libelle_nature)
    return list(offres.values())


def _convertir(o: dict, libelle_nature: str) -> Offre:
    entreprise = o.get("entreprise") or {}
    contact = o.get("contact") or {}
    origine = o.get("origineOffre") or {}
    url = contact.get("urlPostulation") or origine.get("urlOrigine") or URL_OFFRE.format(o["id"])

    offre = Offre(
        source="France Travail",
        id=o["id"],
        titre=o.get("intitule", ""),
        entreprise=entreprise.get("nom") or "(entreprise non communiquée)",
        lieu=(o.get("lieuTravail") or {}).get("libelle", ""),
        url=url,
        description=o.get("description", ""),
        type_contrat=libelle_nature,
        date=(o.get("dateCreation") or "")[:10],
        site_web=entreprise.get("url") or "",
        secteur=o.get("secteurActiviteLibelle", ""),
        competences_offre=[c.get("libelle", "") for c in o.get("competences") or []],
    )
    if contact.get("courriel") and "@" in contact["courriel"]:
        offre.emails_rh.append({
            "email": contact["courriel"].strip(),
            "nom": contact.get("nom", ""),
            "poste": "Contact de l'offre",
            "source": "France Travail",
        })
    return offre
