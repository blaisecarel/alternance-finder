"""Score de correspondance CV <-> offre (0 à 100).

score = 60 % couverture des compétences demandées par l'offre
      + 25 % similarité de vocabulaire (TF-IDF cosinus) entre le CV et l'offre
      + 15 % adéquation du type de poste (admin / technicien) avec le CV
Pour les candidatures spontanées (pas de description), le score dépend du secteur
d'activité de l'entreprise (ESN, infogérance, télécoms… = plus pertinent).
"""
import math
import re
from collections import Counter

from .cv import ProfilCV
from .models import Offre
from .skills import categoriser, detecter_competences, normaliser, score_naf

MOTS_VIDES = set("""
a au aux avec ce ces dans de des du elle en et eux il je la le les leur lui ma mais me meme mes moi mon ne nos
notre nous on ou par pas pour qu que qui sa se ses son sur ta te tes toi ton tu un une vos votre vous c d j l m n s t y
est sont etre avoir as ont plus tres bien faire fait ainsi afin entre sous chez votre vos nos dont cette cet
h f hf poste mission missions profil entreprise equipe alternance alternant contrat recherche recherchons
the and of to in for with you we our your are is be
""".split())


def _mots(texte: str) -> list[str]:
    return [m for m in re.findall(r"[a-z0-9+#/.-]{2,}", normaliser(texte)) if m not in MOTS_VIDES]


def _tfidf(documents: list[list[str]]) -> list[dict]:
    n = len(documents)
    df = Counter(m for doc in documents for m in set(doc))
    vecteurs = []
    for doc in documents:
        tf = Counter(doc)
        v = {m: (c / len(doc)) * math.log((1 + n) / (1 + df[m]) + 1) for m, c in tf.items()} if doc else {}
        norme = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecteurs.append({m: x / norme for m, x in v.items()})
    return vecteurs


def _cosinus(a: dict, b: dict) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(x * b.get(m, 0.0) for m, x in a.items())


def scorer(profil: ProfilCV, offres: list[Offre]) -> None:
    docs = [_mots(profil.texte)] + [_mots(f"{o.titre} {o.titre} {o.description}") for o in offres]
    vecteurs = _tfidf(docs)
    v_cv = vecteurs[0]

    for o, v in zip(offres, vecteurs[1:]):
        o.categorie = categoriser(o.titre) if o.candidature == "offre" else "Candidature spontanée"

        if o.candidature == "spontanée":
            o.score = round(score_naf(o.secteur.split(" ")[0]) * 0.75)
            continue

        demandees = detecter_competences(f"{o.titre} {o.description} {' '.join(o.competences_offre)}")
        o.competences_ok = sorted(demandees & profil.competences)
        o.competences_manquantes = sorted(demandees - profil.competences)
        couverture = len(o.competences_ok) / len(demandees) if demandees else 0.4

        similarite = min(1.0, _cosinus(v_cv, v) * 4)

        if o.categorie in profil.cible:
            type_poste = 1.0
        elif o.categorie == "Systèmes & Réseaux":
            type_poste = 0.7
        else:
            type_poste = 0.4

        o.score = round(100 * (0.60 * couverture + 0.25 * similarite + 0.15 * type_poste))


def competences_a_travailler(profil: ProfilCV, offres: list[Offre], top: int = 10) -> list[tuple[str, int]]:
    """Compétences les plus demandées par les offres et absentes du CV."""
    c = Counter(m for o in offres for m in o.competences_manquantes)
    return c.most_common(top)
