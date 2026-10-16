"""API La Bonne Alternance (api.apprentissage.beta.gouv.fr).

Renvoie deux listes :
- jobs       : offres d'alternance publiées (LBA, France Travail et partenaires)
- recruiters : entreprises « susceptibles de recruter » -> candidatures spontanées
"""
from ..geo import Lieu
from ..models import Offre
from ..skills import score_naf
from ..web import session

URL_RECHERCHE = "https://api.apprentissage.beta.gouv.fr/api/job/v1/search"


def rechercher(conf: dict, codes_rome: list[str], lieu: Lieu, rayon_km: int,
               niveau_diplome: str | None) -> tuple[list[Offre], list[Offre]]:
    s = session()
    s.headers["Authorization"] = "Bearer " + conf["api_key"]
    params = {
        "romes": ",".join(codes_rome),
        "latitude": lieu.latitude,
        "longitude": lieu.longitude,
        "radius": min(rayon_km, 200),
    }
    if niveau_diplome:
        params["target_diploma_level"] = str(niveau_diplome)

    r = s.get(URL_RECHERCHE, params=params, timeout=60)
    if r.status_code != 200:
        print(f"  [La Bonne Alternance] erreur {r.status_code} : {r.text[:200]}")
        return [], []
    data = r.json()
    for w in data.get("warnings") or []:
        print(f"  [La Bonne Alternance] avertissement : {w.get('message')}")

    offres = [_offre(j) for j in data.get("jobs") or []]
    entreprises = [_entreprise(e) for e in data.get("recruiters") or []]
    entreprises.sort(key=lambda o: score_naf(o.secteur.split(" ")[0]), reverse=True)
    return offres, entreprises[: conf.get("max_entreprises_spontanees", 150)]


def _nom(workplace: dict) -> str:
    return workplace.get("brand") or workplace.get("name") or workplace.get("legal_name") or "(sans nom)"


def _naf(workplace: dict) -> str:
    naf = ((workplace.get("domain") or {}).get("naf")) or {}
    return f"{naf.get('code', '')} {naf.get('label') or ''}".strip()


def _offre(j: dict) -> Offre:
    wp = j.get("workplace") or {}
    off = j.get("offer") or {}
    apply = j.get("apply") or {}
    ident = j.get("identifier") or {}
    partenaire = ident.get("partner_label", "")
    return Offre(
        source="La Bonne Alternance" + (f" ({partenaire})" if partenaire and partenaire != "La bonne alternance" else ""),
        id=ident.get("id") or ident.get("partner_job_id", ""),
        titre=off.get("title", ""),
        entreprise=_nom(wp),
        lieu=(wp.get("location") or {}).get("address", ""),
        url=apply.get("url", ""),
        description=" ".join(filter(None, [
            off.get("description", ""),
            " ".join(off.get("desired_skills") or []),
            " ".join(off.get("to_be_acquired_skills") or []),
        ])),
        type_contrat=", ".join((j.get("contract") or {}).get("type") or []),
        date=((off.get("publication") or {}).get("creation") or "")[:10],
        siret=wp.get("siret") or "",
        site_web=wp.get("website") or "",
        telephone=apply.get("phone") or "",
        secteur=_naf(wp),
        competences_offre=off.get("desired_skills") or [],
    )


def _entreprise(e: dict) -> Offre:
    wp = e.get("workplace") or {}
    apply = e.get("apply") or {}
    return Offre(
        source="La Bonne Alternance",
        id=(e.get("identifier") or {}).get("id") or wp.get("siret", ""),
        titre="Candidature spontanée",
        entreprise=_nom(wp),
        lieu=(wp.get("location") or {}).get("address", ""),
        url=apply.get("url", ""),
        description=wp.get("description") or "",
        candidature="spontanée",
        siret=wp.get("siret") or "",
        site_web=wp.get("website") or "",
        telephone=apply.get("phone") or "",
        secteur=_naf(wp),
    )
