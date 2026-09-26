#include "platform/SdlWindow.hpp"

#include <string>

namespace DisneyInfinity {

void SdlWindowDeleter::operator()(SDL_Window* window) const noexcept {
    if (window != nullptr) {
        SDL_DestroyWindow(window);
    }
}

SdlWindow::~SdlWindow() {
    window_.reset();
    if (sdlInitialized_) {
        SDL_Quit();
    }
}

std::expected<void, ErrorMessage> SdlWindow::initialize(const WindowConfig& config) {
    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        return std::unexpected(std::string{"SDL_Init failed: "} + SDL_GetError());
    }
    sdlInitialized_ = true;

    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 3);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 3);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_CORE);
    SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER, 1);

    const auto flags = SDL_WINDOW_OPENGL | (config.isResizable ? SDL_WINDOW_RESIZABLE : 0u);
    window_.reset(SDL_CreateWindow(
        config.title.c_str(),
        SDL_WINDOWPOS_CENTERED,
        SDL_WINDOWPOS_CENTERED,
        static_cast<int>(config.width),
        static_cast<int>(config.height),
        flags));

    if (!window_) {
        return std::unexpected(std::string{"SDL_CreateWindow failed: "} + SDL_GetError());
    }

    return {};
}

void SdlWindow::swapBuffers() noexcept {
    if (window_) {
        SDL_GL_SwapWindow(window_.get());
    }
}

Extent2D SdlWindow::getSize() const noexcept {
    if (!window_) {
        return {};
    }

    int width = 0;
    int height = 0;
    SDL_GetWindowSize(window_.get(), &width, &height);
    return {static_cast<std::uint32_t>(width), static_cast<std::uint32_t>(height)};
}

bool SdlWindow::shouldClose() const noexcept {
    return shouldClose_;
}

void SdlWindow::setShouldClose(const bool close) noexcept {
    shouldClose_ = close;
}

void SdlWindow::pollEvents() {
    SDL_Event event{};
    while (SDL_PollEvent(&event)) {
        if (event.type == SDL_QUIT) {
            shouldClose_ = true;
        }
    }
}

void* SdlWindow::getNativeHandle() const noexcept {
    return window_.get();
}

} // namespace DisneyInfinity
