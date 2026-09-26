#pragma once

#include "core/IWindow.hpp"
#include <SDL.h>
#include <memory>

namespace DisneyInfinity {

struct SdlWindowDeleter final {
    void operator()(SDL_Window* window) const noexcept;
};

using UniqueSdlWindow = std::unique_ptr<SDL_Window, SdlWindowDeleter>;

/**
 * @brief Adaptateur SDL implémentant l'abstraction de fenêtre.
 */
class SdlWindow final : public IWindow {
public:
    SdlWindow() = default;
    ~SdlWindow() override;

    SdlWindow(const SdlWindow&) = delete;
    SdlWindow& operator=(const SdlWindow&) = delete;
    SdlWindow(SdlWindow&&) = delete;
    SdlWindow& operator=(SdlWindow&&) = delete;

    [[nodiscard]] std::expected<void, ErrorMessage> initialize(const WindowConfig& config) override;
    void swapBuffers() noexcept override;
    [[nodiscard]] Extent2D getSize() const noexcept override;
    [[nodiscard]] bool shouldClose() const noexcept override;
    void setShouldClose(bool close) noexcept override;
    void pollEvents() override;
    [[nodiscard]] void* getNativeHandle() const noexcept override;

private:
    UniqueSdlWindow window_;
    bool shouldClose_{false};
    bool sdlInitialized_{false};
};

} // namespace DisneyInfinity
