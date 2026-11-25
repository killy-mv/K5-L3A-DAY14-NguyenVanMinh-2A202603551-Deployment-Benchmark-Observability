# Day 14 Lab — Mission Answers

## CP0 — Setup

- Repository: đúng mẫu tên Day 14; remote origin thuộc tài khoản cá nhân, nhánh main.
- Python Windows: 3.15.2; môi trường làm bài chọn Ubuntu 24.04 WSL, Python 3.12.3, os.name = posix.
- Docker Compose trên Windows: v5.5.1.
- Đã tạo virtual environment WSL tại /tmp/k5day14-venv và cài dependencies Part 1 thành công.
- Docker Desktop Engine chưa kết nối; docker run --rm hello-world chưa chạy được (dockerDesktopLinuxEngine pipe không tồn tại). Đã thử docker desktop start và kiểm tra lại. WSL chưa nhận Docker CLI. Cần bật Docker Desktop và WSL Integration trước CP2.

## AI log

- CP0: dùng ChatGPT kiểm tra môi trường, đọc hướng dẫn WSL và chạy các lệnh setup; kết quả ghi theo output thực tế. Học viên cần kiểm tra lại Docker và xác nhận môi trường.
