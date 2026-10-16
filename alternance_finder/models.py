from dataclasses import dataclass, field, asdict


@dataclass
class Offre:
    """Une offre d'alternance, ou une entreprise à démarcher en candidature spontanée."""

    source: str                      # "France Travail", "La Bonne Alternance", "LinkedIn"
    id: str
    titre: str
    entreprise: str
    lieu: str = ""
    url: str = ""                    # lien pour postuler / voir l'offre
    description: str = ""
    candidature: str = "offre"       # "offre" ou "spontanée"
    type_contrat: str = ""
    date: str = ""
    siret: str = ""
    site_web: str = ""
    telephone: str = ""
    secteur: str = ""
    competences_offre: list = field(default_factory=list)

    # rempli par le matching
    categorie: str = ""              # "Administrateur", "Technicien", "Systèmes & Réseaux"
    score: int = 0
    competences_ok: list = field(default_factory=list)
    competences_manquantes: list = field(default_factory=list)
    nouveau: bool = True

    # rempli par la recherche de contacts
    emails_rh: list = field(default_factory=list)      # [{"email","nom","poste","source"}]
    lien_recherche_rh: str = ""
    page_recrutement: str = ""                         # page recrutement / carrières du site
    lien_recherche_site: str = ""                      # recherche Google si le site est introuvable

    @property
    def cle(self) -> str:
        return f"{self.source}:{self.id}"

    def to_dict(self) -> dict:
        return asdict(self)
