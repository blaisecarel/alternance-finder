# Alternance Finder — systèmes & réseaux

Recherche les offres d'alternance **administrateur / technicien systèmes et réseaux**, analyse ton CV,
calcule un score de correspondance pour chaque offre et cherche les **e-mails RH** des entreprises.

## Sources

| Source | Contenu | Clé nécessaire |
|---|---|---|
| **France Travail** (API officielle) | Offres en apprentissage / professionnalisation, parfois avec l'e-mail du recruteur | Gratuite : créer une appli sur https://francetravail.io et y ajouter l'API « Offres d'emploi v2 » |
| **La Bonne Alternance** (API officielle de l'État) | Offres d'alternance **+ entreprises susceptibles de recruter** (candidatures spontanées) | Gratuite : https://api.apprentissage.beta.gouv.fr/fr/compte/profil |
| **LinkedIn** (pages publiques) | Offres LinkedIn contenant « alternance » | Aucune. LinkedIn interdit le scraping dans ses CGU : volume limité, désactivable |
| **Hunter.io** (optionnel) | E-mails professionnels du service RH | Gratuite : 25 recherches/mois sur https://hunter.io |

Sans clé, seul LinkedIn fonctionne. Ajoute les clés France Travail et La Bonne Alternance pour avoir beaucoup plus d'offres et les candidatures spontanées.

## Installation

```
py -m pip install -r requirements.txt
copy config.example.toml config.toml
```
Puis remplis `config.toml` (CV, ville, rayon, clés).

## Utilisation

Double-clic sur `lancer.bat`, ou :
```
py -m alternance_finder
py -m alternance_finder --cv "C:\chemin\autre_cv.pdf"
py -m alternance_finder --sans-contacts
```

Résultats dans `resultats/` :
- **tableau de bord HTML** (s'ouvre tout seul) : filtres, score, compétences ✓/✗, e-mails, liens pour postuler ;
- **Excel** : onglets *Offres matchées*, *Candidatures spontanées*, *Contacts RH*, *Mon profil*.

Les offres déjà vues lors d'un lancement précédent ne sont plus marquées « nouveau ».

## Score de matching (0–100)

- 60 % : part des compétences demandées par l'offre présentes dans ton CV (référentiel de ~50 compétences systèmes/réseaux dans `alternance_finder/skills.py`)
- 25 % : proximité du vocabulaire entre le CV et l'offre (TF-IDF)
- 15 % : type de poste (administrateur / technicien) cohérent avec ton CV

Pour les candidatures spontanées, la « pertinence » dépend du secteur de l'entreprise (ESN, infogérance, télécoms en tête).

## E-mails RH

Dans l'ordre : e-mail de l'offre (France Travail) → pages publiques du site (contact, recrutement, mentions légales) → Hunter.io.
Si rien n'est trouvé, un lien de recherche LinkedIn des recruteurs de l'entreprise est fourni.
N'utilise ces adresses que pour candidater (RGPD), pas pour un envoi en masse.
