"""Point d'entrée : py -m alternance_finder [--config config.toml] [--cv mon_cv.pdf] [--sans-contacts]"""
import argparse
import json
import sys
import webbrowser
from datetime import datetime

from . import config, contacts, cv, matcher, rapport
from .geo import geocoder
from .skills import est_pertinente
from .sources import france_travail, la_bonne_alternance, linkedin


def _etape(msg: str):
    print(f"\n=== {msg}")


def _historique(offres):
    chemin = config.DOSSIER_DONNEES / "deja_vues.json"
    vues = set(json.loads(chemin.read_text(encoding="utf-8"))) if chemin.exists() else set()
    for o in offres:
        o.nouveau = o.cle not in vues
    chemin.write_text(json.dumps(sorted(vues | {o.cle for o in offres}), ensure_ascii=False), encoding="utf-8")


def _dedoublonner(offres):
    """Une même offre peut venir de plusieurs sources : on garde la plus complète."""
    vues = {}
    for o in offres:
        cle = (o.titre.lower().strip(), o.entreprise.lower().strip())
        if cle not in vues or len(o.emails_rh) + len(o.description) > len(vues[cle].emails_rh) + len(vues[cle].description):
            vues[cle] = o
    return list(vues.values())


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Recherche d'alternances systèmes & réseaux + matching CV")
    ap.add_argument("--config", help="chemin du fichier config.toml")
    ap.add_argument("--cv", help="remplace le CV indiqué dans la configuration")
    ap.add_argument("--sans-contacts", action="store_true", help="ne pas rechercher les e-mails RH")
    ap.add_argument("--pas-de-navigateur", action="store_true", help="ne pas ouvrir le tableau de bord")
    args = ap.parse_args()

    conf = config.charger(args.config)
    config.DOSSIER_DONNEES.mkdir(exist_ok=True)
    config.DOSSIER_RESULTATS.mkdir(exist_ok=True)
    pr, rech = conf["profil"], conf["recherche"]

    _etape("Analyse du CV")
    profil = cv.analyser(args.cv or pr["cv"])
    print(cv.resume(profil))

    lieu = geocoder(pr["ville"])
    rayon = int(pr.get("rayon_km", 50))
    print(f"\nZone : {lieu.nom} ({lieu.departement}), rayon {rayon} km")

    offres, spontanees = [], []

    ft = conf.get("france_travail", {})
    if ft.get("actif") and ft.get("client_id") and ft.get("client_secret"):
        _etape("France Travail")
        try:
            r = france_travail.rechercher(ft, rech["mots_cles"], lieu, rayon)
            print(f"  {len(r)} offres d'alternance")
            offres += r
        except Exception as e:
            print(f"  Erreur France Travail : {e}")
    elif ft.get("actif"):
        print("\n[France Travail] ignoré : client_id / client_secret manquants dans config.toml")

    lba = conf.get("la_bonne_alternance", {})
    if lba.get("actif") and lba.get("api_key"):
        _etape("La Bonne Alternance")
        try:
            r_off, r_ent = la_bonne_alternance.rechercher(lba, rech["codes_rome"], lieu, rayon, pr.get("niveau_diplome"))
            print(f"  {len(r_off)} offres, {len(r_ent)} entreprises pour candidatures spontanées")
            offres += r_off
            spontanees += r_ent
        except Exception as e:
            print(f"  Erreur La Bonne Alternance : {e}")
    elif lba.get("actif"):
        print("\n[La Bonne Alternance] ignoré : api_key manquante dans config.toml")

    li = conf.get("linkedin", {})
    if li.get("actif"):
        _etape("LinkedIn (pages publiques)")
        try:
            r = linkedin.rechercher(li, li.get("mots_cles") or rech["mots_cles"], lieu.nom, rayon)
            print(f"  {len(r)} offres d'alternance")
            offres += r
        except Exception as e:
            print(f"  Erreur LinkedIn : {e}")

    _etape("Filtrage et matching avec le CV")
    avant = len(offres)
    offres = _dedoublonner([o for o in offres if est_pertinente(o.titre, o.description)])
    print(f"  {len(offres)} offres systèmes & réseaux retenues (sur {avant})")
    matcher.scorer(profil, offres + spontanees)
    offres = [o for o in offres if o.score >= int(rech.get("score_minimum", 0))]
    offres.sort(key=lambda o: o.score, reverse=True)
    spontanees.sort(key=lambda o: o.score, reverse=True)
    _historique(offres + spontanees)

    if conf.get("contacts", {}).get("actif", True) and not args.sans_contacts:
        _etape("Recherche des e-mails RH")
        contacts.enrichir(conf["contacts"], offres + spontanees)
        n = sum(1 for o in offres + spontanees if any("@" in e["email"] for e in o.emails_rh))
        print(f"  {n} offres/entreprises avec au moins un e-mail")

    a_travailler = matcher.competences_a_travailler(profil, offres)

    _etape("Export")
    horodatage = datetime.now().strftime("%Y-%m-%d_%H%M")
    xlsx = config.DOSSIER_RESULTATS / f"alternances_{horodatage}.xlsx"
    page = config.DOSSIER_RESULTATS / f"alternances_{horodatage}.html"
    rapport.excel(xlsx, profil, offres, spontanees, a_travailler)
    rapport.html_dashboard(page, profil, offres, spontanees, a_travailler)
    print(f"  Excel : {xlsx}\n  Tableau de bord : {page}")

    print("\nTop 10 des offres :")
    for o in offres[:10]:
        mail = next((e["email"] for e in o.emails_rh if "@" in e["email"]), "-")
        print(f"  {o.score:3d}  {o.titre[:45]:45}  {o.entreprise[:25]:25}  {mail}")
    if a_travailler:
        print("\nCompétences souvent demandées absentes de ton CV : "
              + ", ".join(f"{c} ({n})" for c, n in a_travailler))

    if not args.pas_de_navigateur:
        webbrowser.open(page.as_uri())


if __name__ == "__main__":
    main()
