cmake_minimum_required(VERSION 3.25)
project(DisneyInfinityCreator
    VERSION 1.0.0
    LANGUAGES CXX
)

# Standard C++23
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Export compile commands for tooling (clangd / VS Code)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Compiler Warnings & Flags
if(MSVC)
    add_compile_options(/W4 /permissive- /utf-8)
else()
    add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Dependencies
include(FetchContent)

find_package(SDL2 CONFIG QUIET)
if(NOT SDL2_FOUND)
    FetchContent_Declare(
        SDL2
        GIT_REPOSITORY https://github.com/libsdl-org/SDL.git
        GIT_TAG release-2.30.9
        GIT_SHALLOW TRUE
    )
    set(SDL_TESTS OFF CACHE BOOL "Disable SDL tests" FORCE)
    set(SDL_EXAMPLES OFF CACHE BOOL "Disable SDL examples" FORCE)
    FetchContent_MakeAvailable(SDL2)
endif()

find_package(OpenGL REQUIRED)

# Includes and Sources
file(GLOB_RECURSE SOURCES CONFIGURE_DEPENDS
    "src/*.cpp"
)

add_executable(${PROJECT_NAME} ${SOURCES})

target_compile_definitions(${PROJECT_NAME} PRIVATE
    SDL_MAIN_HANDLED
)

target_include_directories(${PROJECT_NAME} PRIVATE
    ${PROJECT_SOURCE_DIR}/include
)

target_link_libraries(${PROJECT_NAME} PRIVATE
    SDL2::SDL2
    ${OPENGL_LIBRARIES}
)
