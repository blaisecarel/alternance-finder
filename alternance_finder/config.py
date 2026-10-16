import tomllib
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_DONNEES = RACINE / "donnees"
DOSSIER_RESULTATS = RACINE / "resultats"


def charger(chemin: str | Path | None = None) -> dict:
    chemin = Path(chemin) if chemin else RACINE / "config.toml"
    if not chemin.exists():
        raise SystemExit(
            f"Fichier de configuration introuvable : {chemin}\n"
            f"Copie config.example.toml en config.toml et remplis-le."
        )
    with open(chemin, "rb") as f:
        return tomllib.load(f)
