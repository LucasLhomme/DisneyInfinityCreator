# Disney Infinity Creator

Application C++23 basée sur SDL2 et OpenGL, structurée autour d'une architecture OOP et SOLID.

## Prérequis

- Visual Studio 2022 avec le workload **Desktop development with C++**
- CMake 3.25 ou plus récent
- Git accessible dans le `PATH`

SDL2 est récupéré automatiquement par CMake via `FetchContent` si aucun package SDL2 local n'est disponible.

## Configuration et compilation

Depuis la racine du projet :

```powershell
cmake -S . -B build
cmake --build build --config Debug
```

L'exécutable est généré dans `build/Debug/DisneyInfinityCreator.exe`.

## Architecture

- `include/core/` : contrats et types métier (`IWindow`, `IRenderer`)
- `include/platform/` et `src/platform/` : adaptation SDL2 et gestion RAII de la fenêtre
- `include/rendering/` et `src/rendering/` : rendu OpenGL
- `include/app/` et `src/app/` : orchestration du cycle de vie
- `src/main.cpp` : composition racine et injection des dépendances

`Application` ne dépend que des interfaces. Les implémentations concrètes peuvent donc être remplacées par des doubles de test ou une autre plateforme sans modifier la logique applicative.
