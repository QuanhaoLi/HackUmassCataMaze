# Created at: 2026-11-14 23:59 EST
# Created by: Codex
# Last Modified at: 2026-11-14 23:59 EST
# Last Modified by: Codex

idf_component_register(
    SRCS "main.cpp"
    PRIV_REQUIRES esp_timer esp_psram heap espressif__esp-dl
)

set(catamaze_model "${CMAKE_CURRENT_LIST_DIR}/model/catamaze_policy.espdl")
if(NOT EXISTS "${catamaze_model}")
    message(FATAL_ERROR "Missing accepted ESP-DL model: ${catamaze_model}")
endif()
target_add_binary_data(${COMPONENT_LIB} "model/catamaze_policy.espdl" BINARY)
