# Journal des versions

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/), versions [SemVer](https://semver.org/lang/fr/).

## [Non publié]
### Corrigé
- Modèles `.dae` avec plusieurs jeux d'UV : la texture utilise bien le premier jeu (set 0), comme dans Blender.

## [1.1.1] - 2026-10-19
### Corrigé
- `Launch_Creator.bat` reprend une installation des dépendances interrompue (fenêtre fermée, coupure réseau) au lieu
  de planter ensuite sur `No module named 'customtkinter'`.

## [1.1.0] - 2026-10-17
### Ajouté
- Extraction des données du jeu au premier lancement : Creator trouve le dossier de Disney Infinity 3.0 (ou le fait
  choisir) et construit les 99 figures de base depuis la copie du joueur (2 à 3 minutes, une seule fois). Aucun
  fichier du jeu n'est distribué avec Creator.

## [1.0.1] - 2026-10-17
### Corrigé
- Message clair au lieu d'un plantage quand des fichiers de Creator manquent.

## [1.0.0] - 2026-10-17
### Ajouté
- Icônes en jeu : portrait du HUD et figure de la grille de sélection, capturés sur le modèle, au format du jeu.
- Relief : normal map tirée de la texture, pour l'aspect « figurine sculptée » des personnages officiels.
- Os de torsion du jeu sur les bras et les cuisses : épaules et hanches tournent comme sur les figures officielles.
- Mod partagé `zz_creator_shared` : les textures et icônes de tous les personnages dans un seul mod, au lieu d'une
  archive d'environ 13 Mo par personnage. Installation d'un personnage en quelques secondes.
- `Manage_Mods.bat` : liste, désactive, supprime (corbeille) et nettoie les personnages ; un personnage supprimé ne
  laisse rien dans le jeu.
- Curseur « V-shape » : comble le vide entre le torse et les bras en pose de jeu.
- Bouton « ⇅ Flip » pour retourner un modèle tête en bas.
- Documentation en anglais (`README.en.md`).
### Amélioré
- Placement automatique du squelette calibré sur les figures du jeu : épaules et mains bien mieux placées, même avec
  des manches bouffantes ou des cheveux longs.
- Orientation automatique : les modèles couchés ou tête en bas sont redressés.
- Import d'un `.zip` à plusieurs modèles : le personnage principal est choisi, avec une liste si besoin.
- Aperçu « Preview in game pose » plus fidèle au rig final ; le squelette reste visible et suit les curseurs.
### Modifié
- Lanceurs en anglais : `Launch_Creator.bat` (installe les dépendances au premier lancement) et `Manage_Mods.bat`.
- Nouvelle dépendance : `cryptography`.
### Corrigé
- Nettoyage des `.dae` avec Blender 5 (qui n'a plus d'import COLLADA).
- Menton et cou étirés en pose de jeu ; tête agrandie qui s'enfonçait dans le col.
- Sens des tangentes inversé par rapport au jeu (indispensable au relief).
- Bloc des proportions qui sortait de l'écran dans l'onglet Squelette.

## [0.4.0] - 2026-10-17
### Ajouté
- Bouton « Disney Infinity style » (proportions moyennes des personnages du jeu), « Match the base » et « Reset ».
- Curseurs « Head », « Torso » et « Forearms » ; aperçu en direct des épaisseurs.
- Curseur « Shoulder roundness » : épaules rabattues (vestes) ou rondes (bras nus).
- Case « Preview in game pose » pendant le réglage du squelette.
- Aperçu en direct des filtres de texture, avec comparaison à l'original.
### Modifié
- Poids des doigts désactivés par défaut (expérimental).
- Filtre de texture environ 2,5× plus rapide.
### Corrigé
- Fausse alerte « Mostly black » dans l'aperçu de l'atlas.

## [0.3.0] - 2026-10-16
### Ajouté
- Épaisseur des membres, avec « Match the base ».
- Filtre de texture « Game look » et calage de la luminosité sur la base.
- Exclusion des accessoires (cape, queue, arme) : ignorer ou retirer.
### Corrigé
- Chaussures qui se détachaient des pieds.
- Plantage des curseurs de placement après la construction du rig.

## [0.2.0] - 2026-10-15
### Ajouté
- Lecture des `.dae`, poids des doigts, champs de saisie à côté des curseurs.
- Liste complète des bases avec test à la demande, nouvelles poses de test.
- Suggestion de bases refaite, transfert robuste des poids.
### Corrigé
- Cou trouvé au bout des cheveux, entrejambe sur les manteaux longs.
- Textures noires en jeu.

## [0.1.0] - 2026-10-15
- Première version.
