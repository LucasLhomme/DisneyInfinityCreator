#include "app/Application.hpp"

#include <utility>

namespace DisneyInfinity {

Application::Application(std::unique_ptr<IWindow> window, std::unique_ptr<IRenderer> renderer)
    : window_(std::move(window)), renderer_(std::move(renderer)) {
}

std::expected<void, ErrorMessage> Application::initialize(const WindowConfig& config) {
    if (!window_ || !renderer_) {
        return std::unexpected("Application dependencies are not configured");
    }

    if (const auto result = window_->initialize(config); !result) {
        return std::unexpected(result.error());
    }

    if (const auto result = renderer_->initialize(window_->getNativeHandle()); !result) {
        return std::unexpected(result.error());
    }

    return {};
}

int Application::run() noexcept {
    while (!window_->shouldClose()) {
        window_->pollEvents();
        update();
        renderer_->render();
        window_->swapBuffers();
    }

    return 0;
}

void Application::update() noexcept {
    // La logique métier sera ajoutée via des services dédiés.
}

} // namespace DisneyInfinity
