
# Ghi chú Stage D2b — Khám phá bằng hình ảnh (track SEM)

Script: `scripts/plots.R` (base R thuần, **không cần lavaan** ở bước này)

## Chạy trên dữ liệu thật trong RStudio

1. Mở `scripts/plots.R` trong RStudio.
2. Đặt working directory về thư mục project.
3. Chạy cả script, chọn **file dữ liệu thật** khi hộp thoại hiện lên.
4. Hình được ghi vào `dr_figures/` **nằm cạnh file dữ liệu thật**, bên ngoài repo này.

## Hai hình được tạo

**`fig1_item_correlation_heatmap.png`** — tương quan giữa các item, sắp xếp theo construct
(js_q1–js_q5 = Job Satisfaction, bo_q1–bo_q5 = Burnout, turnover_intent).

Đây là hình quan trọng nhất trước khi chạy CFA. Cách đọc:

- Các khung viền đậm trên đường chéo đánh dấu **các item được cho là cùng một nhân tố tiềm ẩn**.
- Trên dữ liệu thật, nếu thang đo tốt bạn sẽ thấy **các khối đỏ sáng rõ bên trong khung**, và màu nhạt bên ngoài khung. Đó chính là nhân tố tiềm ẩn hiện ra bằng mắt thường — chưa cần chạy mô hình nào.
- Nếu một item **không** sáng cùng khối của nó → item đó có vấn đề, xem lại trước khi đưa vào CFA.
- Nếu một item sáng mạnh với khối **khác** → có thể bị cross-loading.

> ⚠️ Trên **dữ liệu giả** (`data_synthetic/`), các item được sinh độc lập nhau nên **sẽ không có khối nào hiện ra** — toàn bộ hệ số quanh 0. Đây là điều đã lường trước. Nó chỉ chứng minh code chạy được, không phải kết quả nghiên cứu. Khối chỉ xuất hiện trên dữ liệu thật của bạn.

**`fig2_item_boxplot_series.png`** — phân bố từng item, tô màu theo construct.

Cách đọc:

- Item có hộp dí sát trần (toàn 5) hoặc sát sàn (toàn 1) → **hiệu ứng trần/sàn**, phương sai thấp, sẽ làm yếu hệ số tải trong CFA.
- Item lệch hẳn so với các item cùng nhóm → xem lại cách diễn đạt câu hỏi, hoặc kiểm tra có cần đảo điểm (reverse coding) không.

## Giới hạn quan trọng

Hình chỉ mô tả. Tương quan giữa các item **không thay thế** được:

- Cronbach's alpha và CFA ở Stage D3 (`scripts/sem_measurement.R`)
- Mô hình cấu trúc và hiệu ứng trung gian ở Stage D4 (`scripts/sem_structural.R`)

Kết luận về đo lường và về đường dẫn chỉ được lấy từ hai script đó, chạy trên dữ liệu thật.

## Quy tắc bảo mật

Mỗi chấm là **một người trả lời**.

- ✅ Được paste cho AI: alpha, chỉ số fit CFA, hệ số đường dẫn, CI, p-value.
- ❌ **Không** paste/upload hình từ dữ liệu thật cho AI.
- Hình thật nằm ngoài repo nên không thể vô tình bị `git push`. Đừng chép vào repo.

Muốn nhờ diễn giải heatmap: mô tả bằng lời, hoặc paste **ma trận tương quan dưới dạng số**.

## Tuỳ chọn

`show_individual_points <- TRUE` bật/tắt chấm dữ liệu và điểm ngoại lai.
Với thang Likert, các chấm được jitter cả 2 chiều nên bạn thấy được **mật độ** câu trả lời ở từng mức — hữu ích để phát hiện đáp viên chọn cùng một đáp án cho mọi câu.
Đổi thành `FALSE` nếu định đưa hình cho người khác xem.
