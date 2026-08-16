# Ghi chú Stage D2b — Khám phá bằng hình ảnh

Script: `scripts/plots.R` (base R thuần, không cần cài gói nào)

## Chạy trên dữ liệu thật trong RStudio

1. Mở `scripts/plots.R` trong RStudio.
2. Đặt working directory về thư mục project:
   `Session > Set Working Directory > To Source File Location`, rồi lùi lên một cấp nếu cần.
3. Chạy cả script. Hộp thoại chọn file sẽ hiện lên — chọn **file dữ liệu thật** của bạn.
4. Hình sẽ được ghi vào thư mục `dr_figures/` **nằm cạnh file dữ liệu thật**, tức là bên ngoài repo này.

Bạn không cần sửa đường dẫn. Script tự tính chỗ ghi hình từ file bạn chọn.

## Hai hình được tạo

**`fig1_correlation_heatmap.png`** — ma trận tương quan Pearson giữa các biến liên tục
(age, bmi, sbp, dbp, egfr, hba1c, crp, length_of_stay).

Cách đọc:
- Đỏ = tương quan dương, xanh = tương quan âm, trắng = gần bằng 0.
- Thang màu cố định từ −1 đến 1, nên màu ở mọi project đều mang cùng ý nghĩa.
- Đường chéo luôn bằng 1.00 (biến tương quan với chính nó) — dùng để kiểm tra hình vẽ đúng.
- Ma trận đối xứng: ô (age, bmi) phải bằng ô (bmi, age).

**`fig2_boxplot_series.png`** — phân bố từng biến liên tục theo nhóm `mortality_30day`
(Sống / Tử vong), kèm số n của mỗi nhóm trên đầu mỗi ô.

Cách đọc:
- Vạch đậm giữa hộp = trung vị. Hộp = khoảng tứ phân vị (25%–75%).
- Râu = phạm vi dữ liệu thông thường; chấm rời = giá trị ngoại lai.
- Hai hộp lệch nhau rõ = biến đó **có thể** khác nhau giữa 2 nhóm.

## Giới hạn quan trọng

Hình chỉ mô tả phân bố và liên hệ. **Hình không phải là kiểm định thống kê.**

- Hai hộp trông lệch nhau không có nghĩa là khác biệt có ý nghĩa thống kê.
- Tương quan cao không có nghĩa là quan hệ nhân quả.
- Tương quan ở đây là **thô**, chưa hiệu chỉnh biến gây nhiễu. Kết luận vẫn phải lấy từ mô hình ở Stage D3/D4 (`scripts/infer.R`).

Hình dùng để phát hiện sớm: biến lệch mạnh, giá trị bất thường, đa cộng tuyến (hai biến tương quan rất cao > 0.8 thì cân nhắc khi đưa cùng vào mô hình).

## Quy tắc bảo mật

Mỗi chấm trên boxplot là **một bệnh nhân**. Chấm ngoại lai thường chính là người dễ nhận diện nhất.

- ✅ Được phép paste cho AI: bảng số tổng hợp (Table 1, hệ số hồi quy, CI, p-value).
- ❌ **Không** paste/upload hình vẽ từ dữ liệu thật cho AI, kể cả để "nhờ đọc hộ".
- Hình thật nằm ngoài repo nên không thể vô tình bị `git push` lên GitHub. Đừng chép nó vào repo.

Nếu muốn được hỗ trợ diễn giải: mô tả bằng lời, hoặc paste **ma trận tương quan dưới dạng số**.

## Tuỳ chọn

Dòng `show_individual_points <- TRUE` ở đầu script bật/tắt các chấm dữ liệu và điểm ngoại lai.

Để `TRUE` khi phân tích cho chính mình — điểm ngoại lai có ý nghĩa lâm sàng thật.
Đổi thành `FALSE` khi định đưa hình vào slide, bản thảo, hoặc buổi báo cáo có người khác xem.
