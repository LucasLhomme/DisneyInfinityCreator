#pragma once

#include "Types.hpp"
#include <expected>

namespace DisneyInfinity {

/**
 * @brief Abstraction du moteur de rendu.
 */
class IRenderer {
public:
    virtual ~IRenderer() = default;

    [[nodiscard]] virtual std::expected<void, ErrorMessage> initialize(void* nativeWindow) = 0;
    virtual void render() noexcept = 0;
};

} // namespace DisneyInfinity
