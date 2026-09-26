#pragma once

#include <string>
#include <cstdint>

namespace DisneyInfinity {

/**
 * @brief Structure décrivant la configuration de création d'une fenêtre.
 */
struct WindowConfig final {
    std::string title{"Disney Infinity Creator"};
    std::uint32_t width{1280};
    std::uint32_t height{720};
    bool isResizable{true};
};

/**
 * @brief Structure représentant les dimensions en pixels.
 */
struct Extent2D final {
    std::uint32_t width{0};
    std::uint32_t height{0};
};

/**
 * @brief Type d'erreur standardisé pour le projet.
 */
using ErrorMessage = std::string;

} // namespace DisneyInfinity
