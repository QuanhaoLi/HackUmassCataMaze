# Created at: 2026-11-14 23:59 EST
# Created by: Codex
# Last Modified at: 2026-11-15 00:56 EST
# Last Modified by: Codex

idf_component_register(
    SRCS "main.cpp"
    PRIV_REQUIRES esp_timer esp_psram heap espressif__esp-dl
)

get_filename_component(catamaze_repo_root "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
set(catamaze_model "${catamaze_repo_root}/src/esp32/model/catamaze_policy.espdl")
if(NOT EXISTS "${catamaze_model}")
    message(FATAL_ERROR "Missing accepted ESP-DL model: ${catamaze_model}")
endif()
set(catamaze_embedded_model "${CMAKE_CURRENT_BINARY_DIR}/catamaze_policy.espdl")
configure_file("${catamaze_model}" "${catamaze_embedded_model}" COPYONLY)
target_add_binary_data(${COMPONENT_LIB} "${catamaze_embedded_model}" BINARY)
