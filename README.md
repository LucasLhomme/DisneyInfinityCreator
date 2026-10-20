# Disney Infinity Creator

**Français** · [English](README.en.md)

Transforme n'importe quel modèle 3D en **personnage jouable** pour **Disney Infinity 3.0 Gold Edition (PC)**.

Tu importes un modèle (Sketchfab, The Models Resource, ton propre travail Blender…), tu choisis une figure du jeu
comme base, et Creator ajuste un squelette, calcule le skinning, te laisse prévisualiser le résultat en mouvement puis
l'installe sous forme de mod. Le personnage apparaît dans le jeu comme une **nouvelle figure à part entière** : il
reprend les animations, les attaques et les capacités de la figure de base, et aucun personnage d'origine n'est
remplacé.

> Outil de fan, sans lien avec Disney, Avalanche Software ni aucun ayant droit. Il faut posséder sa propre copie du jeu.

---

## Sommaire

- [Fonctionnalités](#fonctionnalités)
- [Prérequis](#prérequis)
- [Installation et lancement](#installation-et-lancement)
- [Créer un personnage](#créer-un-personnage)
- [Réglages avancés](#réglages-avancés)
- [Comprendre le score de déformation](#comprendre-le-score-de-déformation)
- [Gérer ses personnages](#gérer-ses-personnages)
- [Jouer avec son personnage](#jouer-avec-son-personnage)
- [Conseils pour un bon résultat](#conseils-pour-un-bon-résultat)
- [Fonctionnement](#fonctionnement)
- [Limites connues](#limites-connues)
- [Dépannage](#dépannage)
- [Crédits](#crédits)

---

## Fonctionnalités

- **99 figures de base** : tous les personnages jouables de Disney Infinity 3.0 (Marvel, Star Wars, Disney, Pixar,
  y compris ceux des versions 1.0 et 2.0), avec recherche et aperçu 3D texturé.
- **Rien n'est écrasé** : chaque création est une nouvelle figure avec sa propre tuile dans la grille. Luke, Thor ou
  Elsa restent intacts, et tu peux installer autant de personnages que tu veux.
- **Nettoyage intégré** : Blender (en arrière-plan) fusionne les morceaux, corrige l'échelle et l'orientation,
  retrouve les textures perdues et fige un éventuel squelette, sans laisser de fichier chez toi.
- **Rigging automatique** : épaules, coudes, poignets, cou, hanches, genoux et chevilles sont détectés, avec un
  curseur par articulation pour affiner, et une vue 3 plans (face, profil, dessus).
- **Aperçu en mouvement** et **score de déformation** sur 100, avec les arêtes trop étirées en rouge.
- **Suggestion de bases** : classe les figures selon leur compatibilité avec ton modèle.
- **Icônes en jeu** et **relief** (normal map tirée de la texture), comme les figures officielles.
- **Mod partagé léger** : textures et icônes de tous tes personnages dans un seul mod ; `Manage_Mods.bat` liste,
  désactive et supprime proprement tes personnages.
- **Installation vérifiée** : chaque installation est contrôlée et l'ancienne version du mod est sauvegardée.

## Prérequis

| Quoi | Remarques |
| :--- | :--- |
| Windows 10 ou 11 | |
| Disney Infinity 3.0 Gold Edition (PC) | Ta propre copie installée |
| [CrabeLoader](https://github.com/LucasLhomme/CrabeLoader) et [CrabeMenu](https://github.com/LucasLhomme/CrabeMenu) | Le chargeur de mods qui charge ton personnage. CrabeMenu (menu `F5` en jeu) est conseillé pour passer sur ton personnage |
| Python 3.12 ou plus récent | Cocher « Add python.exe to PATH » à l'installation |
| Blender 4.x ou 5.x | Recommandé : nettoyage des modèles (obligatoire pour `.fbx`) et meilleurs poids. Creator le lance en arrière-plan, tu n'as jamais à l'ouvrir |

## Installation et lancement

1. Télécharge ou clone ce dépôt.
2. Double-clique sur **`Launch_Creator.bat`**. Au premier lancement, il installe les dépendances Python dans un
   environnement `.venv` (`customtkinter`, `moderngl`, `numpy`, `Pillow`, `trimesh`, `scipy`, `cryptography`), puis
   ouvre Creator. Les fois suivantes, il démarre directement.
3. Si l'appli s'arrête, la fenêtre reste ouverte et renvoie vers `build\creator.log`. Après une mise à jour de Creator,
`run.ps1` (PowerShell) réinstalle les dépendances puis lance l'appli.

## Créer un personnage

Le panneau de gauche a cinq onglets ; on les parcourt dans l'ordre.

### 0. Base : choisir la figure

La figure dont le squelette, les animations et le moveset serviront à ton personnage.

| Marque | Sens |
| :---: | :--- |
| ● | Squelette standard : toutes les articulations nécessaires existent |
| ◐ | Squelette adapté : quelques os en remplacent d'autres (ex. la base du pied pour la cheville). Fonctionne, avec de petites approximations |
| ✕ | Non humanoïde (Olaf, Randall…) : ne peut pas recevoir un maillage humanoïde |

Choisis une base de gabarit proche : un héros mince va mieux sur Spider-Man que sur Hulk, une longue robe mieux sur
Elsa que sur Captain America. Le bouton **« Suggest the best bases for my model »** (onglet Modèle) fait ce choix
pour toi (voir [Suggestion de bases](#suggestion-de-bases)).

### 1. Modèle : importer

Clique sur **Import a 3D model** et choisis un `.obj`, `.glb`, `.gltf`, `.fbx` (ou `.dae`, `.ply`, `.stl`, `.off`),
ou un `.zip` qui le contient avec ses textures.

- **« Clean with Blender while importing »** (coché par défaut) lance le nettoyage. Sans Blender, les `.glb`, `.obj`
  et `.zip` s'importent tels quels ; les `.fbx` demandent Blender.
- Le modèle doit être en **T-pose** (bras écartés) ; une A-pose passe aussi.
- Creator détecte l'orientation. Sinon : **↻ 90°**, **↻ 180°**, **Stand up**, **⇅ Flip**.
- **Model height** est préréglée à la taille de la base. Coche **Show … alongside** pour comparer côte à côte.
- **Position** : curseurs et boutons de 1 cm ; **Recentre** revient au centrage automatique.
- **Pièces** : Ctrl+clic sur une pièce, **Grow** pour inclure les petites pièces voisines, choisis l'os et **Lock** :
  la pièce suivra cet os de façon rigide (ex. des mèches de cheveux sur la tête).
- **Preview the texture atlas** montre la texture que le jeu recevra, avec des alertes (image trop sombre, texture
  manquante ou répétée…).

### 2. Skeleton : vérifier les articulations

Points jaunes = articulations, lignes vertes = os. Creator les place seul ; le texte au-dessus des curseurs indique ce
qui est **détecté** et ce qui n'est qu'**estimé** (à vérifier en premier).

- Chaque curseur a une note (sur quoi aligner le point) et une **case de saisie** pour la valeur exacte.
- L'icône à droite de chaque point : ✓ trouvé sur le maillage, ⚠ jaune estimé, ⚠ orange loin des proportions de la
  base, ✎ réglé par toi. Survole-la pour lire la raison.
- Des avertissements ⚠ signalent les proportions qui s'écartent de la base de 20 % ou plus.
- **Auto-Fit** repart du placement automatique ; **« 3 views »** (sous la vue 3D) montre face, profil et dessus.

### 3. Abilities & Moveset

Capacités et mouvements du personnage, hérités de la base, que tu peux ajuster.

### 4. Rig & Export : construire et installer

1. **Character name** : nom affiché dans les menus (ex. `Mario`) ; il nomme aussi le dossier du mod.
2. **Internal actor name** : nom interne du moteur (ex. `MAR_Mari`), 3 à 32 caractères, lettres/chiffres/`_`,
   commence par une lettre ; prérempli.
3. **Game folder** et **Blender** : mémorisés d'une fois sur l'autre.
4. **1. Build the rig**, puis contrôle **In-game pose**, **Arms up**, **Walk** et le **score de déformation**. Si
   quelque chose cloche, retourne en onglet 1 ou 2, ajuste, reconstruis.
5. **2. Install into the game** : le journal liste les contrôles, tous doivent afficher `OK`.

Le mod est écrit dans `<jeu>/mods/<nom du personnage>/`. Réinstaller sous le même nom remplace le mod et déplace
l'ancienne version dans `backups/`. **Ferme le jeu avant d'installer** : il garde ses archives ouvertes.

## Réglages avancés

### Suggestion de bases

Le bouton compare la silhouette de ton modèle à celle de chaque figure, garde des types de corps différents, puis
construit le vrai rig des meilleures et mesure l'étirement dans les poses de test et la déformation au passage en
pose du jeu. Toute la liste reste affichée : les 12 meilleures sont testées d'office, **« Test the next 12 figures »**
teste le lot suivant, et le filtre cherche par nom ou par licence (Avengers, Star Wars…).

### Proportions et V-shape

Onglet Squelette, curseurs **Head** (×0,8 à ×1,5, la tête grandit depuis la mâchoire), **Torso**, **Arms**,
**Forearms** et **Legs** (×0,8 à ×1,8, gonflés autour de leur axe sans changer de longueur). Aperçu en direct.

- **Disney Infinity style** : rapproche le modèle des proportions moyennes des personnages du jeu (tête ≈ 21 % de la
  hauteur, avant-bras plus épais que le bras…), sans jamais le rétrécir.
- **Match the base** : copie l'épaisseur de la base (sans toucher à la tête). **Reset** revient au modèle.
- **V-shape** (0 à 1) : en pose du jeu, les bras pendent depuis les épaules de la base ; un torse étroit laisse alors
  un vide sous les bras. Le V-shape élargit la poitrine jusqu'aux bras, sans toucher à la taille ni au cou.

### Pose du jeu et épaules

- **Preview in game pose** (onglet Squelette) : le modèle bras baissés, comme le jeu l'affichera, mis à jour à
  chaque curseur.
- **Shoulder roundness** (onglet Rig & Export, après la construction du rig) : à 0, la jonction poitrine/bras est
  rabattue (vestes, manches larges) ; à 1, elle garde son volume (bras nus).
- **in T-pose** (sous « Show the base figure alongside ») remet la figure de comparaison en T-pose.

### Accessoires (cape, queue, ailes, arme)

Une cape qui pend derrière le bassin fausse les mesures et se fait déchirer par les jambes. Onglet Modèle, boîte
« Accessories » : **Find** repère ce qui dépasse derrière le corps (profondeur réglable) et les pièces séparées
(surlignées en magenta, ou Ctrl+clic). **Ignore** garde la partie mais la fait suivre le torse ; **Remove** la
retire ; **✕** annule.

### Textures : rendu du jeu, relief, icônes

- **Game look** (onglet Modèle) : adoucit le bruit et les ombres peintes, éclaircit et sature, comme les personnages
  du jeu (0 = texture d'origine). **Match the base figure's brightness** rapproche la luminosité de celle de la base.
  Aperçu en direct, et c'est ce rendu qui est exporté.
- **Relief** (onglet Rig & Export, activé par défaut) : normal map tirée de la texture (coutures, plis, bords de
  couleur légèrement creusés), au format du jeu.
- **Character icons** (onglet Modèle) : portrait du HUD et figure de la grille, capturés sur ton modèle à
  l'installation. Le bouton « Preview » les montre.

### Doigts (expérimental)

**Finger weights** fait suivre les os de doigts de la base à la main du modèle. Tant que les doigts ne tombent pas
sur ceux de la base, les prises du jeu (sabre, poing) froissent la main : la main rigide reste le réglage par défaut.
La pose **Fist** montre le résultat.

### Transfert robuste des poids

**Robust weight transfer** (onglet Modèle) construit le rig deux fois (poids Blender, puis poids copiés depuis la
figure de base) et garde celui qui déforme le moins. Utile pour les jupes, capes et manteaux longs. Méthode : « Robust
Skin Weights Transfer via Weight Inpainting » (Abdrashitov, Raichstat, Monsen, Hill, SIGGRAPH Asia 2023).

### Format `.dae` (COLLADA)

Creator le lit lui-même : géométrie, UV, textures (cherchées à côté du fichier), unité et axe vertical ; un modèle
skinné est lu dans sa pose de repos. Avec le nettoyage, il est converti en `.glb` avant de passer dans Blender.

## Comprendre le score de déformation

Après « Build the rig », Creator mesure combien le maillage s'étire ou s'écrase dans six poses de test (bras levés,
marche, bras au-dessus de la tête, bras devant, coudes pliés, torsion du buste ; « Pose amount » change l'amplitude).
Le score (0 à 100) mélange l'étirement moyen des arêtes (50 %), la part des arêtes déformées de plus de 2 fois (30 %)
et la part de celles déchirées à plus de 3 fois (20 %).

| Score | Niveau |
| :---: | :--- |
| 75 et plus | Bon |
| 50 à 74 | Acceptable |
| moins de 50 | Forte déformation |

- Les arêtes étirées de plus de 3 fois sont dessinées en **rouge**.
- « FAILED - the model is collapsed » signale des poids cassés.
- Le score mesure la géométrie, **pas l'apparence** : des cheveux qui suivent les bras peuvent obtenir un bon score.
  Contrôle toujours visuellement et verrouille les pièces gênantes sur le bon os.

## Gérer ses personnages

Le jeu ne lit les textures et les icônes que dans ses propres archives, qu'un mod doit fournir entières. Pour ne pas
répéter ces archives dans chaque personnage :

- chaque personnage (`mods/<nom>/`) garde seulement ses propres fichiers ;
- le mod **`mods/zz_creator_shared`** contient les archives reconstruites une fois pour tous les personnages actifs.
  Ne le modifie pas à la main.

**`Manage_Mods.bat`** (jeu fermé) :

| Choix | Effet |
| :--- | :--- |
| 1. Supprimer | Envoie le personnage à la corbeille et refait les archives : il ne reste rien de lui dans le jeu |
| 2. Désactiver / réactiver | Préfixe `_` sur le dossier (ignoré par CrabeLoader), puis refait les archives |
| 3. Nettoyer | Range les personnages faits avec une ancienne version et propose d'envoyer les sauvegardes de `backups/` à la corbeille |
| 4. Reconstruire | Refait les archives partagées |

À lancer pour supprimer ou désactiver un personnage (plutôt que d'effacer son dossier), après avoir effacé un dossier
à la main, ou si l'installation signale « shared archives NOT rebuilt » (jeu ouvert). En ligne de commande : `--list`,
`--rebuild`, `--clean`.

## Jouer avec son personnage

1. **Redémarre le jeu** : les nouveaux personnages ne sont chargés qu'au démarrage.
2. Dans le jeu, soit **F5** (CrabeMenu) → **Heroes › ★ Modded Characters**, soit la grille
   **My collection › Characters**, où ton personnage a sa propre tuile.

## Conseils pour un bon résultat

- **Moins d'environ 65 000 sommets** (limite du moteur). Le nettoyage décime si besoin.
- **Un maillage propre** : un modèle découpé en dizaines de morceaux se rigge moins bien.
- **Une vraie T-pose** : bras droits et horizontaux, jambes légèrement écartées, de face.
- **Installe Blender** : plis plus doux aux épaules, coudes et genoux.
- **Des proportions proches de la base** : les membres sont étirés pour coller aux os de la base.
- **Textures** : importe un `.zip` avec les images à côté du modèle, ou un `.glb` avec textures intégrées.

## Fonctionnement

Chaque figure jouable est un **acteur** : un squelette, un maillage skinné, des matériaux et textures, et les
animations et capacités qui le pilotent. Creator crée un **acteur cloné** : une copie de la figure de base dont le
maillage est remplacé par le tien, sous un nouveau nom.

1. **Ajustement du squelette** : des coupes horizontales du modèle donnent les bras, le cou, l'entrejambe, les genoux
   et les chevilles ; les articulations sont placées dessus, puis corrigées par des modèles calibrés sur les figures du
   jeu.
2. **Skinning** : poids de chaleur de Blender, ou à défaut distance aux os, puis règles par zone (tête rigide, pièces
   sous les genoux liées aux chevilles, jupes lissées entre les jambes, os de torsion du jeu).
3. **Cuisson dans la pose de repos** : chaque partie du corps est amenée de l'articulation de ton modèle vers celle de
   la base. Le squelette de la base ne change pas : **toutes les animations du jeu s'appliquent telles quelles**.
4. **Écriture des fichiers** dans les formats du jeu (scènes Octane, Lua compilé, matériaux, interface, archives
   chiffrées), sans perte.

### Contenu d'un mod de personnage

| Fichier | Rôle |
| :--- | :--- |
| `characters/<acteur>/<acteur>.oct`, `_0.vbuf`, `_0.ibuf` | Le maillage : sommets, poids, triangles |
| `characters/<acteur>/<acteur>.mtb` | Les matériaux |
| `characters/<acteur>/<acteur>.dnax`, `.bent`, `.animtreeoverrides` | La définition de l'acteur |
| `textures/<id>.tbody` | Textures (couleur et relief) |
| `ui/…`, `<acteur>_icon.png` | Icônes |
| `skilltrees/ActorList.patch`, `skilltrees/DataMap.patch` | Enregistrent l'acteur dans le jeu |
| `characters/<Acteur>.lua` | Ajoute la figure à la grille de personnages |
| `<nom>.lua`, `mod.json` | Point d'entrée CrabeLoader et entrée CrabeMenu |

## Limites connues

- **Moveset** : le personnage reprend les mouvements, la voix et les capacités de sa base ; pas d'animations
  personnalisées.
- **Textures** : une seule texture par personnage (atlas, 2048 px au plus) ; le relief est déduit de la couleur.
- **Figures non humanoïdes** (Olaf, Randall, Maleficent, Elastigirl) : inutilisables comme base.
- **Placement automatique du squelette** : vérifie toujours les épaules, les coudes et le bassin dans l'onglet
  Skeleton, c'est la principale source d'écart.
- **Capes, jupes, cheveux** : contrôle les poses et verrouille les pièces si besoin.

## Dépannage

| Problème | À essayer |
| :--- | :--- |
| L'appli se ferme au lancement | Lance `Launch_Creator.bat` (la fenêtre reste ouverte) et consulte `build\creator.log` |
| Textures noires ou icône « IN » en jeu | Ferme le jeu, `Manage_Mods.bat` → 4. Reconstruire ; l'icône n'existe que si « Character icons » était coché |
| Le personnage n'apparaît pas en jeu | Redémarre le jeu ; vérifie CrabeLoader ; consulte `loader.log` dans le dossier du jeu |
| « model too detailed » | Réduis sous ~65 000 sommets (le nettoyage le fait) |
| Modèle couché ou de dos | Onglet 1 : **Stand up**, **↻ 90°** / **↻ 180°**, **⇅ Flip** |
| Squelette décalé par rapport au corps | Onglet 1 : curseurs de position ou **Recentre** ; vue « 3 views » pour vérifier |
| Le modèle devient une aiguille / « collapsed » | Les poids Blender ont échoué ; reconstruis le rig et lis le journal |
| Modèle gris à l'import | Texture non liée : mets les images à côté du modèle (dans le même `.zip`) |
| Coudes ou genoux qui plient mal | Onglet 2 : bouge le curseur concerné puis reconstruis |
| Cheveux ou cape qui suivent les bras | Ctrl+clic sur la pièce, Grow, choisis l'os (ex. Head), Lock, puis reconstruis |
| Le personnage glisse sans bouger les jambes | Animations de la base absentes : vérifie les fichiers du jeu via Steam |
| « already a figure of the game » | Choisis un autre nom d'acteur interne |

## Crédits

- **Disney Infinity Creator** : projet créé par **Crabe** ([LucasLhomme](https://github.com/LucasLhomme)) ;
  versions 1.x par **Nyzarion**, co-développées avec
  [Claude](https://claude.ai) (Anthropic).
- Outils fournis dans `src/tools` : [QuickBMS](https://aluigi.altervista.org/quickbms.htm) de Luigi Auriemma
  (GPL-2.0) avec le script BMS Disney Infinity de la communauté, et `offsetting.exe` de
  [Team Offsetting](https://github.com/offsetting/offsetting) (MIT / Apache-2.0).
- La communauté de modding Disney Infinity (recherches sur les formats).
- [trimesh](https://trimesh.org), [ModernGL](https://github.com/moderngl/moderngl),
  [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter), NumPy, SciPy, Pillow,
  [cryptography](https://cryptography.io) et [Blender](https://www.blender.org).
- Transfert robuste des poids inspiré de [Robust Weight Transfer](https://github.com/sentfromspacevr/robust-weight-transfer)
  et de [RobustSkinWeightsTransferCode](https://github.com/rin-23/RobustSkinWeightsTransferCode).

Disney Infinity et tous les personnages associés sont des marques de leurs propriétaires respectifs. Ce projet est
destiné aux possesseurs du jeu.
