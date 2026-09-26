#include "app/Application.hpp"
#include "platform/SdlWindow.hpp"
#include "rendering/OpenGlRenderer.hpp"

#include <iostream>

int main() {
    using namespace DisneyInfinity;

    Application application{
        std::make_unique<SdlWindow>(),
        std::make_unique<OpenGlRenderer>()};

    const WindowConfig config{};
    if (const auto result = application.initialize(config); !result) {
        std::cerr << result.error() << '\n';
        return 1;
    }

    return application.run();
}