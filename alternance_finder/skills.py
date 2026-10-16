"""Référentiel de compétences systèmes & réseaux et détection dans un texte."""
import re
import unicodedata

# compétence affichée -> motifs regex (appliqués sur un texte minuscule et sans accents)
COMPETENCES = {
    # Réseau
    "TCP/IP": [r"tcp\s*/?\s*ip", r"\bmodele osi\b", r"\bosi\b"],
    "VLAN": [r"\bvlans?\b"],
    "Routage (OSPF/BGP)": [r"\broutage\b", r"\bospf\b", r"\bbgp\b", r"\brip\b", r"\beigrp\b"],
    "Switching": [r"\bswitch(s|es|ing)?\b", r"\bcommutateurs?\b", r"\bcommutation\b"],
    "Cisco": [r"\bcisco\b", r"\bccna\b", r"\bios\b(?! ?apple)"],
    "Fortinet / Stormshield": [r"\bfortinet\b", r"\bfortigate\b", r"\bstormshield\b"],
    "Pare-feu": [r"pare-?feu", r"\bfirewalls?\b", r"\bpfsense\b", r"\bopnsense\b"],
    "VPN": [r"\bvpn\b", r"\bipsec\b", r"\bopenvpn\b", r"\bwireguard\b"],
    "DNS / DHCP": [r"\bdns\b", r"\bdhcp\b"],
    "Wi-Fi": [r"\bwi-?fi\b", r"\bwlan\b", r"\baruba\b", r"\bmeraki\b"],
    "LAN / WAN": [r"\blan\b", r"\bwan\b", r"\bsd-?wan\b", r"\bmpls\b"],
    "Wireshark": [r"\bwireshark\b"],
    "Packet Tracer / GNS3": [r"packet ?tracer", r"\bgns3\b", r"\beve-?ng\b"],
    "Câblage / Baie": [r"\bcablage\b", r"\bbaies?\b", r"\bbrassage\b", r"\bfibre optique\b"],
    "Téléphonie / ToIP": [r"\btoip\b", r"\bvoip\b", r"\btelephonie\b", r"\b3cx\b"],
    # Systèmes
    "Windows Server": [r"windows ?server", r"\bserveurs? windows\b"],
    "Active Directory": [r"active ?directory", r"\bad ds\b", r"\bentra ?id\b", r"\bazure ad\b"],
    "GPO": [r"\bgpos?\b", r"strategies? de groupe"],
    "Linux": [r"\blinux\b", r"\bdebian\b", r"\bubuntu\b", r"\bred ?hat\b", r"\brhel\b", r"\bcentos\b", r"\brocky\b"],
    "Windows (postes)": [r"windows (10|11)\b", r"\bpostes? de travail\b", r"\bmasterisation\b", r"\bmaster(s)? windows\b"],
    "Déploiement (MDT/SCCM/Intune)": [r"\bmdt\b", r"\bsccm\b", r"\bmecm\b", r"\bwds\b", r"\bintune\b", r"\bfog\b"],
    "Virtualisation VMware": [r"\bvmware\b", r"\bvsphere\b", r"\besxi?\b", r"\bvcenter\b"],
    "Hyper-V": [r"hyper-?v\b"],
    "Proxmox": [r"\bproxmox\b"],
    "VirtualBox": [r"\bvirtualbox\b"],
    "Virtualisation": [r"\bvirtualisation\b", r"\bvirtualization\b"],
    "Docker": [r"\bdocker\b", r"\bconteneur", r"\bcontainers?\b"],
    "Kubernetes": [r"\bkubernetes\b", r"\bk8s\b", r"\bk3s\b"],
    "Ansible": [r"\bansible\b"],
    "Terraform": [r"\bterraform\b"],
    "PowerShell": [r"\bpowershell\b"],
    "Bash / Shell": [r"\bbash\b", r"\bshell\b"],
    "Python": [r"\bpython\b"],
    "Scripting / Automatisation": [r"\bscript(s|ing)?\b", r"\bautomatisation\b"],
    "Microsoft 365": [r"office ?365", r"\bm365\b", r"microsoft 365", r"\bexchange\b", r"\bsharepoint\b", r"\bteams\b"],
    "Azure": [r"\bazure\b(?! ?devops| ?ad)"],
    "AWS": [r"\baws\b", r"amazon web services"],
    "Cloud": [r"\bcloud\b"],
    "Sauvegarde (Veeam…)": [r"\bsauvegardes?\b", r"\bbackups?\b", r"\bveeam\b", r"\bpra\b", r"\bpca\b"],
    "Supervision (Zabbix…)": [r"\bsupervision\b", r"\bzabbix\b", r"\bnagios\b", r"\bcentreon\b", r"\bprtg\b", r"\bgrafana\b"],
    "Stockage (SAN/NAS)": [r"\bsan\b", r"\bnas\b", r"\bsynology\b", r"\braid\b"],
    "Serveurs web (Apache/Nginx)": [r"\bapache\b", r"\bnginx\b", r"\biis\b", r"serveur web"],
    "Bases de données (SQL)": [r"\bsql\b", r"\bmysql\b", r"\bmariadb\b", r"\bpostgre(sql)?\b"],
    "Git": [r"\bgit\b", r"\bgithub\b", r"\bgitlab\b"],
    "Cybersécurité": [r"\bcyber", r"\bsecurite\b", r"\bsecurisation\b", r"\bsiem\b", r"\bedr\b", r"\bantivirus\b"],
    # Support / ITSM
    "Support utilisateurs / Helpdesk": [r"\bsupport\b", r"help ?desk", r"service ?desk", r"assistance (aux )?utilisateurs", r"\bn1\b", r"\bn2\b", r"niveau [12]\b"],
    "Ticketing (GLPI…)": [r"\bglpi\b", r"\btickets?\b", r"\bticketing\b", r"\bservicenow\b", r"\bjira\b", r"azure devops"],
    "ITIL": [r"\bitil\b"],
    "Maintenance matériel": [r"\bmaintenance\b", r"\bdepannage\b", r"detection de panne", r"\bhardware\b", r"\bmateriel informatique\b"],
    "Inventaire / Parc informatique": [r"\bparc informatique\b", r"\binventaire\b", r"\bocs\b"],
    "Documentation technique": [r"\bdocumentation\b", r"\bprocedures?\b"],
    # Langues
    "Anglais": [r"\banglais\b", r"\benglish\b"],
}

_COMPILES = {nom: [re.compile(m) for m in motifs] for nom, motifs in COMPETENCES.items()}


def normaliser(texte: str) -> str:
    texte = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", texte.lower())


def detecter_competences(texte: str) -> set:
    t = normaliser(texte)
    return {nom for nom, motifs in _COMPILES.items() if any(m.search(t) for m in motifs)}


# ---- classification des postes -------------------------------------------------

_ADMIN = re.compile(r"administrat|sysadmin|admin sys|ingenieur (systeme|reseau|infra)|devops|ingenieur cloud")
_TECH = re.compile(r"technicien|support|help ?desk|service ?desk|maintenance|deploiement|assistant|helpdesk|n1|n2")
_DOMAINE_SR = re.compile(
    r"systemes?|reseaux?|infra|informatique|\bit\b|\bsi\b|helpdesk|help desk|support|cloud|cyber|devops|sysadmin|telecom"
)
_EXCLUS = re.compile(
    r"developp|commercial|comptab|vendeu|marketing|data analyst|data scien|chef de projet|graphiste|ressources humaines"
    r"|\bfibre\b.*raccord|electricien|frigori|automobile|cvc|plombier|mecani|electrotech|ascenseur|\bsav\b"
    r"|vehicule|batiment|chauffage|climatisation|usinage|logistique|\bbtp\b|travaux|fonctionnel"
)
_ALTERNANCE = re.compile(r"alternan|apprenti|professionnalisation|contrat pro\b|work[- ]?study")
# dans une description, "alternance" seul est ambigu ("télétravail en alternance")
_ALTERNANCE_DESC = re.compile(
    r"\balternant|\bapprenti(e|\(e\))?s?\b|contrat d.?apprentissage|en apprentissage (au sein|dans|de \d|sur \d)|professionnalisation|contrat pro\b|rythme d.?alternance"
    r"|(poste|offre|contrat|formation|cursus|ecole) en alternance|en alternance (au sein|dans|de \d|sur \d)"
)
# compétences trop génériques pour juger seules qu'un poste est informatique
_GENERIQUES = {"Maintenance matériel", "Documentation technique", "Anglais", "Support utilisateurs / Helpdesk",
               "Cybersécurité", "Scripting / Automatisation", "Cloud", "Ticketing (GLPI…)"}


def categoriser(titre: str) -> str:
    t = normaliser(titre)
    if _ADMIN.search(t):
        return "Administrateur"
    if _TECH.search(t):
        return "Technicien"
    return "Systèmes & Réseaux"


def titre_exclu(titre: str) -> bool:
    return bool(_EXCLUS.search(normaliser(titre)))


def est_pertinente(titre: str, description: str) -> bool:
    """Garde les postes systèmes/réseaux, admin ou technicien, et écarte le reste."""
    t = normaliser(titre)
    if _EXCLUS.search(t):
        return False
    if _DOMAINE_SR.search(t) or _ADMIN.search(t):
        return True
    # titre vague ("Technicien H/F") : on regarde la description
    if _TECH.search(t):
        return len(detecter_competences(description) - _GENERIQUES) >= 3
    return False


def mentionne_alternance(titre: str, description: str = "") -> bool:
    if re.search(r"stage|stagiaire|internship", normaliser(titre)) and not _ALTERNANCE.search(normaliser(titre)):
        return False
    return bool(_ALTERNANCE.search(normaliser(titre)) or _ALTERNANCE_DESC.search(normaliser(description)))


# ---- pertinence des entreprises pour les candidatures spontanées (codes NAF) ---

def score_naf(code_naf: str) -> int:
    code = (code_naf or "").upper().replace(".", "")
    if code.startswith(("6202", "6203", "6209", "6311")):   # ESN, infogérance, hébergement
        return 100
    if code.startswith(("6201", "61", "9511", "4651", "3320")):  # édition logicielle, télécoms, réparation/vente info
        return 85
    if code.startswith(("63", "58", "7112", "7022")):
        return 70
    return 50
