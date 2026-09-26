#pragma once

#include "core/IRenderer.hpp"
#include <memory>

namespace DisneyInfinity {

struct SdlGlContextDeleter final {
    void operator()(void* context) const noexcept;
};

using UniqueSdlGlContext = std::unique_ptr<void, SdlGlContextDeleter>;

/**
 * @brief Rendu OpenGL minimal, indépendant de la boucle applicative.
 */
class OpenGlRenderer final : public IRenderer {
public:
    OpenGlRenderer() = default;
    ~OpenGlRenderer() override = default;

    OpenGlRenderer(const OpenGlRenderer&) = delete;
    OpenGlRenderer& operator=(const OpenGlRenderer&) = delete;

    [[nodiscard]] std::expected<void, ErrorMessage> initialize(void* nativeWindow) override;
    void render() noexcept override;

private:
    UniqueSdlGlContext context_{nullptr};
};

} // namespace DisneyInfinity
