# vocab_factory_v2_full.py

## Giới thiệu

`vocab_factory_v2_full.py` là một ứng dụng Python giúp tự động hóa việc tạo video học từ vựng tiếng Anh. Ứng dụng hỗ trợ nhập từ nhanh, tra nghĩa và ví dụ bằng AI (Gemini API hoặc offline), xuất file CSV, và render video từng nhóm từ với hiệu ứng đẹp mắt. Ngoài ra, chương trình còn hỗ trợ đóng gói thành file `.exe` để dễ dàng phân phối.

## Cấu trúc chính

### 1. Cấu hình (CONFIG)
- Đường dẫn thư mục, file mặc định, font, kích thước video.
- Danh sách màu nền gradient cho video.
- Từ điển offline nhỏ (MINI_DICT) dùng khi không có internet.

### 2. AI Lookup Module
- Hỗ trợ tra nghĩa và ví dụ bằng Gemini API hoặc offline.
- Chuẩn hóa kết quả trả về dạng JSON.

### 3. Helpers
- Các hàm tiện ích: kiểm tra ffmpeg, chuẩn hóa text, chia nhóm từ, kiểm tra dữ liệu CSV.

### 4. Video Engine
- Tạo audio bằng PowerShell TTS.
- Render từng segment video cho mỗi từ.
- Ghép các segment thành video hoàn chỉnh.
- Quản lý tiến trình render đa luồng.

### 5. Giao diện người dùng (GUI)
- Sử dụng Tkinter với 4 tab chức năng:
    - **Nhập từ nhanh**: Nhập danh sách từ, tự động tra nghĩa/ví dụ, chia nhóm, xuất CSV, render nhanh.
    - **Quản lý CSV**: Chọn, kiểm tra, xem nội dung, tạo file CSV mẫu.
    - **Render Video**: Quản lý tiến trình render, xem log, mở thư mục output.
    - **Đóng gói EXE**: Hỗ trợ cài PyInstaller và build file `.exe`.

## Quy trình sử dụng

1. **Nhập từ hoặc chọn file CSV**
    - Nhập danh sách từ tiếng Anh (mỗi từ một dòng) hoặc chọn file CSV có sẵn.
2. **Tự động tra nghĩa + ví dụ**
    - Chương trình sẽ tự động tra nghĩa và ví dụ cho từng từ (ưu tiên AI, fallback offline).
3. **Chia nhóm và xuất CSV**
    - Tự động chia thành các nhóm 6 từ, mỗi nhóm là một video.
4. **Render video**
    - Render từng video với hiệu ứng đẹp, audio TTS, xuất ra thư mục output.
5. **Đóng gói EXE (tuỳ chọn)**
    - Build file `.exe` để chạy độc lập trên Windows.

## Một số hàm và class quan trọng

| Tên hàm/class         | Chức năng chính                                                                 |
|----------------------|--------------------------------------------------------------------------------|
| `ai_lookup_word`     | Tra nghĩa và ví dụ cho từ bằng AI hoặc offline                                  |
| `auto_split_words`   | Chia danh sách từ thành các nhóm 6 từ                                          |
| `build_row_from_words` | Tạo một dòng dữ liệu (18 cột) từ 6 từ                                         |
| `validate_row`       | Kiểm tra tính hợp lệ của một dòng dữ liệu CSV                                  |
| `VideoEngine`        | Quản lý quá trình render video, audio, ghép segment, đa luồng                  |
| `App`                | Giao diện người dùng, quản lý các tab và thao tác chính                        |

## Yêu cầu hệ thống

- Python 3.8+
- Windows (yêu cầu PowerShell và font Arial)
- ffmpeg.exe, ffprobe.exe đặt cùng thư mục script
- Thư viện: tkinter, csv, json, threading, subprocess, urllib
- Để build EXE: cài đặt PyInstaller

## Lưu ý sử dụng

- Đảm bảo đã có `ffmpeg.exe` và `ffprobe.exe` trong thư mục chạy.
- Để sử dụng AI tra nghĩa, cần có internet và API key Gemini hợp lệ.
- Khi build EXE, copy `ffmpeg.exe` vào cùng thư mục với file EXE.

## Liên hệ & Bản quyền

- Tác giả: [Tên tác giả hoặc nhóm phát triển]
- Phiên bản: V2
- Bản quyền: Sử dụng nội bộ, không phát hành thương mại khi chưa được phép.

---

**Mọi thắc mắc hoặc góp ý vui lòng liên hệ tác giả qua email hoặc github.**