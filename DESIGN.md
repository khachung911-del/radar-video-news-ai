# DESIGN.md — Trang cá nhân Đinh Hùng

Áp dụng cho `app/static/dinh-hung/`. Công cụ RADAR VIDEO NEWS AI (`app/static/index.html`) giữ giao diện riêng.

Hướng thiết kế: **trang báo in trên giấy dó** — chữ serif cho tiêu đề, nền giấy ấm, một màu son làm chủ đạo. Lý do: thương hiệu "giữ hồn cốt cũ, kiến tạo giá trị mới" cần cảm giác biên tập, từng trải, không phải giao diện SaaS. Hướng này chưa được đối chiếu với thư viện website thật (UXKIN không kết nối được).

## Màu

| Token | Sáng | Tối | Vai trò |
|---|---|---|---|
| `--bg` | `#F6F1E7` | `#14110E` | Nền trang (giấy) |
| `--surface` | `#FFFDF8` | `#1E1A15` | Nền thẻ, ô nhập |
| `--text` | `#1D1A16` | `#EDE6D8` | Chữ chính (mực) |
| `--muted` | `#5E564B` | `#B3A996` | Chữ phụ, chú thích |
| `--line` | `#D9CFBD` | `#3A332A` | Đường kẻ, viền |
| `--primary` | `#9B2C1F` | `#E0705F` | Màu son: nút, liên kết, số thứ tự |
| `--on-primary` | `#FFFFFF` | `#14110E` | Chữ trên nền son |
| `--accent` | `#2F5D57` | `#7FB8AE` | Màu đồng xanh: nhãn, thanh tiến độ, trạng thái xong |

Chữ thường đạt tương phản tối thiểu 4.5:1 ở cả hai chế độ. Không dùng gradient.

## Chữ

- Tiêu đề: **Playfair Display** 600/700 (có dấu tiếng Việt).
- Nội dung, giao diện: **Be Vietnam Pro** 400/500/600.
- Thang cỡ: 14 · 16 · 18 · 22 · 28 · 40 · 56 (hero dùng `clamp` 40→64). Dòng 1.65 cho nội dung, 1.15 cho tiêu đề.
- Đoạn văn rộng tối đa 65 ký tự. Nhãn mục: 14px, in hoa, giãn chữ 0.12em.

## Khoảng cách

Thang 4: 4 · 8 · 12 · 16 · 24 · 32 · 48 · 72 · 112. Giữa các mục: 72 (điện thoại) / 112 (máy tính). Bề rộng nội dung: 1120px, lề 20px.

## Hình khối

- Bo góc: 2px (nút, ô nhập, thẻ). Không đổ bóng; phân tầng bằng đường kẻ `--line`.
- Đường kẻ đôi phía trên tiêu đề mục (kiểu măng-sét báo).

## Thành phần

- **Nút chính**: nền `--primary`, chữ `--on-primary`; hover tối đi 8%; focus viền 2px `--text` lệch 2px.
- **Nút phụ**: viền `--text`, nền trong; hover đảo màu.
- **Liên kết**: `--primary`, gạch chân, hover đậm nét gạch.
- **Ô nhập**: nền `--surface`, viền `--line`, focus viền `--primary`.
- **Danh mục dự án**: hàng kẻ ngang có số thứ tự, không dùng lưới thẻ giống nhau.
- **Điều hướng**: thanh trên cùng dính, liên kết chữ; điện thoại thu gọn còn tên và nút liên hệ.

## Hình ảnh, biểu tượng

Không dùng emoji, không dùng ảnh minh họa có sẵn. Chân dung và ảnh dự án là ảnh thật của anh Hùng — hiện để khung giữ chỗ có ghi chú. Số thứ tự kiểu serif thay cho icon.
