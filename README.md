# RADAR VIDEO NEWS AI — QUẢNG NINH NGÀY MỚI

Bộ đóng gói chạy được trên máy tính hoặc máy chủ. Giao diện web tương thích điện thoại; backend có trích xuất bài viết, tạo lời dẫn nháp theo quy chuẩn dự án, tạo giọng đọc tiếng Việt bằng Edge TTS, tạo phụ đề SRT/VTT và kết xuất MP4 bằng FFmpeg.

## Có gì trong gói
- Giao diện newsroom, nguồn bài, tiêu đề, tin vắn, nội dung biên tập, tải ảnh/video.
- Tự trích xuất nội dung trang web qua `trafilatura` (một số website chặn truy cập sẽ không đọc được).
- Quy chuẩn biên tập **QUẢNG NINH NGÀY MỚI**: tiêu đề IN HOA tối đa 20 từ; văn phong khách quan; ghi `Nguồn: ...` và `#QUẢNG_NINH_NGÀY_MỚI`.
- Tạo giọng đọc tiếng Việt bằng `edge-tts` (dịch vụ trực tuyến, có thể thay đổi/giới hạn; không phải SLA chính thức).
- Tạo phụ đề SRT/VTT theo thời lượng các câu ước tính; đây là căn thời gian gần đúng, không phải forced alignment chính xác.
- FFmpeg ghép ảnh/video, logo, tiêu đề, tin vắn, ticker, giọng đọc, phụ đề thành MP4 H.264/AAC.
- Gói TXT để lưu nội dung và phân cảnh.

## Chạy nhanh bằng Docker (khuyến nghị)
1. Cài Docker Desktop (Windows/Mac) hoặc Docker Engine (Linux).
2. Giải nén gói ZIP.
3. Mở terminal tại thư mục có `docker-compose.yml`, chạy:
   ```bash
   docker compose up --build
   ```
4. Mở `http://localhost:8000`.
5. Trên điện thoại, cần máy chủ có địa chỉ IP/URL mà điện thoại truy cập được; `localhost` trên điện thoại là chính điện thoại, không phải máy tính.

## Chạy trực tiếp (máy tính)
Yêu cầu Python 3.11+ và FFmpeg đã cài, lệnh `ffmpeg -version` chạy được.
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Mở `http://127.0.0.1:8000`.

## Cách dùng
1. Nhập URL nguồn hoặc dán bài gốc.
2. Nhấn **Đọc URL** nếu muốn thử trích xuất bài viết.
3. Chỉnh tiêu đề, tin vắn, nội dung biên tập; kiểm tra tên riêng, ngày tháng, số liệu.
4. Tải logo kênh và ảnh/video hiện trường lên.
5. Chọn giọng đọc, thời lượng và nhấn **Tạo bản xem trước** để nghe thử.
6. Chỉnh sửa nội dung trước khi nhấn **Kết xuất MP4**.
7. Tải MP4, SRT hoặc TXT về.

## API endpoints
- `GET /api/health`
- `POST /api/extract` JSON `{ "url": "https://..." }`
- `POST /api/editorial-draft` JSON `{ "source": "...", "url": "...", "text": "..." }`
- `POST /api/tts` multipart `text`, `voice`
- `POST /api/render` multipart `headline`, `brief`, `source`, `brand`, `script`, `duration`, `voice`, `style`, `files[]`, optional `logo`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/video`, `/subtitles.srt`, `/subtitles.vtt`, `/script.txt`

## Dịch vụ/API và chi phí
- **FFmpeg**: miễn phí, mã nguồn mở; tạo MP4 trên máy chủ.
- **Trafilatura**: thư viện miễn phí để trích nội dung; không bảo đảm mọi trang web truy cập được.
- **Edge TTS**: thường dùng được miễn phí nhưng dựa vào dịch vụ trực tuyến của Microsoft Edge; không phải API có cam kết ổn định chính thức, có thể thay đổi hoặc bị giới hạn.
- **AI viết lại bài**: gói này không bắt buộc API trả phí. Khi chưa cấu hình AI, backend tạo bản nháp dựa trên nội dung nguồn (không giả vờ là AI đã xác minh). Có thể cấu hình API tương thích OpenAI bằng biến môi trường `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`; các dịch vụ có thể tính phí.
- Không có API key bí mật nào được nhúng trong mã nguồn.

## Logo
Tệp logo mẫu được đặt trong `app/static/logo.png` nếu có trong gói. Có thể tải logo khác ngay trong giao diện khi làm từng video.

## Lưu ý quan trọng
- Đây là ứng dụng tự lưu trữ, chưa được triển khai trên internet công cộng và chưa có hệ thống tài khoản/phân quyền. Không công khai cổng máy chủ khi chưa bổ sung xác thực, giới hạn dung lượng, quét tệp và HTTPS.
- Bản biên tập là bản nháp hỗ trợ; người biên tập chịu trách nhiệm xác minh nguồn, trích dẫn, quyền sử dụng tư liệu và duyệt nội dung cuối cùng.
- Phụ đề được căn thời gian gần đúng theo câu; muốn đồng bộ từng từ/câu chính xác hơn cần thêm bộ forced-alignment.
- Logo mẫu do người dùng cung cấp cần thay bằng tệp logo chính thức của dự án nếu muốn dùng mặc định.
