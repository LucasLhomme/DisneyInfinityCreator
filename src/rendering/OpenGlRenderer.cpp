#include "rendering/OpenGlRenderer.hpp"

#include <SDL.h>
#include <SDL_opengl.h>
#include <string>

namespace DisneyInfinity {

void SdlGlContextDeleter::operator()(void* context) const noexcept {
    if (context != nullptr) {
        SDL_GL_DeleteContext(context);
    }
}

std::expected<void, ErrorMessage> OpenGlRenderer::initialize(void* nativeWindow) {
    if (nativeWindow == nullptr) {
        return std::unexpected("Cannot create an OpenGL context without a window");
    }

    context_.reset(SDL_GL_CreateContext(static_cast<SDL_Window*>(nativeWindow)));
    if (!context_) {
        return std::unexpected(std::string{"SDL_GL_CreateContext failed: "} + SDL_GetError());
    }

    if (SDL_GL_MakeCurrent(static_cast<SDL_Window*>(nativeWindow), context_.get()) != 0) {
        return std::unexpected(std::string{"SDL_GL_MakeCurrent failed: "} + SDL_GetError());
    }

    SDL_GL_SetSwapInterval(1);
    glClearColor(0.055f, 0.07f, 0.10f, 1.0f);
    return {};
}

void OpenGlRenderer::render() noexcept {
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
}

} // namespace DisneyInfinity
