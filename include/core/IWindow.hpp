#pragma once

#include "Types.hpp"
#include <expected>

namespace DisneyInfinity {

/**
 * @brief Interface abstraite représentant une fenêtre d'application.
 * 
 * Respecte le principe d'Inversion de Dépendance (DIP) et de Responsabilité Unique (SRP).
 */
class IWindow {
public:
    virtual ~IWindow() = default;

    /**
     * @brief Initialise et affiche la fenêtre selon la configuration.
     * @param config Configuration initiale de la fenêtre.
     * @return std::expected<void, ErrorMessage> Succès ou message d'erreur.
     */
    [[nodiscard]] virtual std::expected<void, ErrorMessage> initialize(const WindowConfig& config) = 0;

    /**
     * @brief Échange les tampons d'affichage (Double Buffering).
     */
    virtual void swapBuffers() noexcept = 0;

    /**
     * @brief Récupère les dimensions actuelles de la fenêtre.
     * @return Dimensions de la fenêtre.
     */
    [[nodiscard]] virtual Extent2D getSize() const noexcept = 0;

    /**
     * @brief Vérifie si la fenêtre a reçu une demande de fermeture.
     * @return true si la fenêtre doit être fermée, false sinon.
     */
    [[nodiscard]] virtual bool shouldClose() const noexcept = 0;

    /**
     * @brief Définit l'état de fermeture de la fenêtre.
     * @param close Nouvel état de fermeture.
     */
    virtual void setShouldClose(bool close) noexcept = 0;

    /**
     * @brief Traite les événements de fenêtre et d'entrée.
     */
    virtual void pollEvents() = 0;

    /**
     * @brief Récupère le pointeur natif de la fenêtre si nécessaire.
     * @return Pointeur générique opaque.
     */
    [[nodiscard]] virtual void* getNativeHandle() const noexcept = 0;
};

} // namespace DisneyInfinity
