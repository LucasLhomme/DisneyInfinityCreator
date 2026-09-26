#pragma once

#include "core/IRenderer.hpp"
#include "core/IWindow.hpp"
#include <expected>
#include <memory>

namespace DisneyInfinity {

/**
 * @brief Orchestre le cycle de vie de l'application.
 *
 * La classe dépend uniquement d'abstractions : DIP et injection de dépendances.
 */
class Application final {
public:
    Application(std::unique_ptr<IWindow> window, std::unique_ptr<IRenderer> renderer);
    ~Application() = default;

    Application(const Application&) = delete;
    Application& operator=(const Application&) = delete;
    Application(Application&&) noexcept = default;
    Application& operator=(Application&&) noexcept = default;

    [[nodiscard]] std::expected<void, ErrorMessage> initialize(const WindowConfig& config);
    int run() noexcept;

private:
    std::unique_ptr<IWindow> window_;
    std::unique_ptr<IRenderer> renderer_;

    void update() noexcept;
};

} // namespace DisneyInfinity
