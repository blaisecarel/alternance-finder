"""Lecture et analyse du CV."""
import re
from dataclasses import dataclass, field
from pathlib import Path

from .skills import COMPETENCES, detecter_competences, normaliser


@dataclass
class ProfilCV:
    fichier: str
    texte: str
    email: str = ""
    telephone: str = ""
    competences: set = field(default_factory=set)
    cible: str = ""        # "Administrateur", "Technicien" ou les deux


def lire_texte(chemin: Path) -> str:
    ext = chemin.suffix.lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(chemin).pages)
    if ext == ".docx":
        from docx import Document
        return "\n".join(p.text for p in Document(chemin).paragraphs)
    return chemin.read_text(encoding="utf-8", errors="ignore")


def analyser(chemin: str) -> ProfilCV:
    p = Path(chemin)
    if not p.exists():
        raise SystemExit(f"CV introuvable : {p}")
    texte = lire_texte(p)
    if len(texte.strip()) < 50:
        raise SystemExit("Impossible de lire le texte du CV (PDF scanné ?). Fournis un PDF texte, un DOCX ou un TXT.")

    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", texte)
    tel = re.search(r"(?:\+33\s?|0)[1-9](?:[\s.-]?\d{2}){4}", texte)
    t = normaliser(texte)
    cibles = []
    if re.search(r"administrat|admin sys", t):
        cibles.append("Administrateur")
    if re.search(r"technicien|support|maintenance", t):
        cibles.append("Technicien")
    return ProfilCV(
        fichier=str(p),
        texte=texte,
        email=email.group(0) if email else "",
        telephone=tel.group(0) if tel else "",
        competences=detecter_competences(texte),
        cible=" / ".join(cibles) or "Systèmes & Réseaux",
    )


def resume(profil: ProfilCV) -> str:
    lignes = [
        f"CV : {profil.fichier}",
        f"Contact : {profil.email}  {profil.telephone}",
        f"Postes visés : {profil.cible}",
        f"{len(profil.competences)} compétences détectées sur {len(COMPETENCES)} du référentiel :",
        "  " + ", ".join(sorted(profil.competences)),
    ]
    return "\n".join(lignes)
