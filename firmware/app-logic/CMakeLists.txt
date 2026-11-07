cmake_minimum_required(VERSION 3.16)
project(tsensor_app_logic CXX)

# Logic ứng dụng không phụ thuộc phần cứng — biên dịch được cả cho host (test) lẫn
# cho EFR32MG24 (thêm các file src/*.cpp và include/ vào project Simplicity Studio).
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(tsensor_app_logic STATIC
    src/report_policy.cpp
    src/battery_estimator.cpp
)
target_include_directories(tsensor_app_logic PUBLIC include)
target_compile_options(tsensor_app_logic PRIVATE -Wall -Wextra -Wpedantic -Wconversion -Werror
    -fno-exceptions -fno-rtti)

enable_testing()
add_executable(app_logic_tests tests/test_main.cpp)
target_link_libraries(app_logic_tests PRIVATE tsensor_app_logic)
target_compile_options(app_logic_tests PRIVATE -Wall -Wextra)
add_test(NAME app_logic_tests COMMAND app_logic_tests)
