"""Géocodage d'une ville via le service public de la Géoplateforme (IGN)."""
from dataclasses import dataclass

from .web import session


@dataclass
class Lieu:
    nom: str
    latitude: float
    longitude: float
    code_insee: str
    departement: str


def geocoder(ville: str) -> Lieu:
    r = session().get(
        "https://data.geopf.fr/geocodage/search",
        params={"q": ville, "index": "address", "type": "municipality", "limit": 1},
        timeout=15,
    )
    r.raise_for_status()
    features = r.json().get("features") or []
    if not features:
        raise SystemExit(f"Ville introuvable : {ville}")
    f = features[0]
    lon, lat = f["geometry"]["coordinates"]
    p = f["properties"]
    code_insee = p.get("citycode", "")
    dep = code_insee[:3] if code_insee.startswith("97") else code_insee[:2]
    return Lieu(p.get("city") or p.get("label", ville), lat, lon, code_insee, dep)
