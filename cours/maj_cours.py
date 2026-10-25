# -*- coding: utf-8 -*-
"""
Télécharge puis met à jour les cours quotidiens des sociétés suivies.

  python maj_cours.py            -> met à jour toutes les sociétés
  python maj_cours.py 2crsi      -> une seule société
  python maj_cours.py --complet  -> retélécharge tout l'historique

Écrit cours/<code>.csv (version GitHub Actions du script du kit) : date,open,high,low,close,volume
(cours bruts, non ajustés des dividendes ; volumes en nombre de titres).
Prérequis : pip install yfinance
Après la mise à jour, relancer build.py pour régénérer les frises.
"""
import csv, datetime, os, sys

TITRES = {"2crsi": "AL2SI.PA", "vusion": "VU.PA"}
DEBUT = "2021-01-01"
RECOUVREMENT = 7   # jours retéléchargés pour corriger d'éventuelles révisions

ICI = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(ICI)

try:
    import yfinance as yf
except ImportError:
    sys.exit("yfinance manquant : lancer  pip install yfinance")


def lire(chemin):
    lignes = {}
    if os.path.exists(chemin):
        with open(chemin, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                lignes[r["date"]] = r
    return lignes


def telecharger(ticker, depuis):
    fin = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    df = yf.Ticker(ticker).history(start=depuis, end=fin, interval="1d",
                                   auto_adjust=False, actions=False)
    res = {}
    for idx, r in df.iterrows():
        try:
            c = float(r["Close"])
        except (TypeError, ValueError):
            continue
        if c != c or c <= 0:      # NaN ou séance vide
            continue
        d = idx.date().isoformat()
        res[d] = {
            "date": d,
            "open": f'{float(r["Open"]):.4f}',
            "high": f'{float(r["High"]):.4f}',
            "low": f'{float(r["Low"]):.4f}',
            "close": f"{c:.4f}",
            "volume": str(int(r["Volume"] or 0)),
        }
    return res


def maj(code, complet=False):
    ticker = TITRES[code]
    dossier = ICI
    chemin = os.path.join(dossier, code + ".csv")
    lignes = {} if complet else lire(chemin)
    if lignes:
        der = max(lignes)
        depuis = (datetime.date.fromisoformat(der)
                  - datetime.timedelta(days=RECOUVREMENT)).isoformat()
    else:
        depuis = DEBUT
    print(f"{code} ({ticker}) : téléchargement depuis {depuis}…")
    neuves = telecharger(ticker, depuis)
    if not neuves:
        sys.exit(f"  {code} : aucune donnée reçue (réseau, ticker ?) ; fichier inchangé")
    avant = len(lignes)
    lignes.update(neuves)
    tmp = chemin + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "open", "high", "low",
                                          "close", "volume"])
        w.writeheader()
        for d in sorted(lignes):
            w.writerow(lignes[d])
    os.replace(tmp, chemin)
    der = max(lignes)
    print(f"  {len(lignes) - avant} séance(s) ajoutée(s), {len(lignes)} au total ;"
          f" dernière : {der}, clôture {float(lignes[der]['close']):.2f} €")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    codes = args or list(TITRES)
    for c in codes:
        if c not in TITRES:
            print(f"société inconnue : {c} (connues : {', '.join(TITRES)})")
            continue
        maj(c, complet="--complet" in sys.argv)
