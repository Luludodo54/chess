# Assistant d'échecs (Minimal) — Installation & usage (Windows)

Ce dépôt fournit une version minimale d'un assistant d'échecs capable de:
- Capturer l'écran,
- Rechercher un échiquier simple et découper les 64 cases,
- Reconnaître des pièces via templates (optionnel) ou heuristique,
- Analyser la position avec Stockfish via python-chess,
- Interface graphique pour démarrer/arrêter, afficher l'échiquier, le meilleur coup et le journal.

Prérequis
- Windows 10/11
- Python 3.9+ (recommandé 3.10 ou 3.11)
- Pip

Installation rapide
1. Créez et activez un environnement virtuel :
   python -m venv venv
   venv\Scripts\activate

2. Installez les dépendances :
   pip install -r requirements.txt

3. Installez Stockfish :
   - Téléchargez la version Windows depuis https://stockfishchess.org/download/
   - Dézippez l'exécutable `stockfish_*.exe` dans un dossier, par exemple `C:\tools\stockfish\stockfish.exe`
   - Notez le chemin vers l'exécutable.

4. (Optionnel) Préparez des templates de pièces :
   - Si vous souhaitez une reconnaissance plus fiable, placez des images de templates dans le dossier `templates/`.
   - Nommez-les `wP.png`, `wN.png`, `wB.png`, `wR.png`, `wQ.png`, `wK.png` pour pièces blanches
     et `bP.png`, `bN.png`, `bB.png`, `bR.png`, `bQ.png`, `bK.png` pour pièces noires.
   - Les templates doivent être des images cadrées sur la pièce, fond transparent ou uniforme.

Lancement
1. Configurez Stockfish dans l'interface:
   - Lancez `python main.py`
   - Entrez le chemin vers `stockfish.exe` dans la zone prévue et cliquez "Set Stockfish".

2. Démarrer l'analyse :
   - Cliquez "Start" pour lancer la boucle de capture/analyse.
   - Le programme capture tout l'écran et tente de détecter le plus grand contour carré
     (fonctionne pour la plupart des vues top-down/ orthogonales).

Notes sur la reconnaissance
- La méthode fournie est une base : détection du quadrilatère, transformation perspective et découpage en 8x8.
- La reconnaissance des pièces est basique :
  - Si des templates sont fournis, on fait du template matching.
  - Sinon on applique une heuristique (détection de présence mais pas d'identité précise).
- Pour fiabiliser la reconnaissance :
  - Fournir des templates adaptés à votre style d'échiquier (plateau, pièces).
  - Envisager un modèle ML (CNN) entraîné sur captures (je peux fournir une pipeline d'entraînement si besoin).

Sécurité & automatisation
- PyAutoGUI n'est pas utilisé dans le workflow principal — uniquement pour tests locaux explicites.
- N'automatisez que sur un environnement local autorisé.

Prochaines améliorations possibles (à implémenter progressivement)
- Remplacement de la reconnaissance heuristique par un modèle CNN (détection multi-classe).
- Correction manuelle via une interface graphique (sélection/déplacement de pièces directement sur l'image).
- Gestion automatique de la détection de mouvements entre captures (comparer deux FEN et détecter le coup joué, avec vérification de legalité).
- Enregistrement automatique des journaux et export FEN/PGN.

Support & tests
- Testez sur une fenêtre d'échiquier bien orientée (vue presque perpendiculaire).
- Si vous avez des captures d'écran exemple (anonymisées), je peux aider à créer des templates adaptés ou entraîner un modèle.
