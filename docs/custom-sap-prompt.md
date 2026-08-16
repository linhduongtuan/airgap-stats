
# Nhánh Phân Tích Tự Do (Custom SAP)

Tài liệu này chứa **một prompt duy nhất** để copy vào agent. Dùng khi bạn muốn tự quyết định hướng phân tích thay vì đi theo track Medical hoặc track SEM có sẵn của pack.

Luồng: bạn nhập câu hỏi nghiên cứu → agent soạn **SAP** (Statistical Analysis Plan) → **bạn duyệt** → agent mới viết code R.

## Khi Nào Dùng

Dùng nhánh này khi:

- Câu hỏi nghiên cứu của bạn không nằm gọn trong "hồi quy + hiệu chỉnh nhiễu" (Medical) hay "mô hình đo lường + mô hình cấu trúc" (SEM).
- Bạn cần phương pháp mà 2 track chính không phủ: phân tích sống còn, mixed model, phân tích lặp lại, thời gian - chuỗi, dữ liệu đếm, xử lý missing nâng cao...
- Bạn đã đủ tự tin để tự chịu trách nhiệm về lựa chọn thống kê của mình.

**Điều kiện tiên quyết** — nhánh này bắt đầu *sau* privacy gate, bạn phải đã có trong project của mình:

```text
projects/<tên-project>/
  pattern/dataset_pattern.csv        (đã duyệt)
  data_synthetic/synthetic_dataset.csv
```

Nếu chưa có, quay lại `dr-workflow-orchestrator` chạy Stage A–C trước. Nhánh này **không thay thế** privacy gate.

## Prompt Để Copy

Mở project của bạn, dán nguyên khối dưới đây vào agent, chỉ sửa 2 chỗ trong ngoặc vuông.

````text
Tôi muốn chạy NHÁNH PHÂN TÍCH TỰ DO (custom SAP) cho project: [tên-project]

Câu hỏi nghiên cứu của tôi:
[viết câu hỏi nghiên cứu ở đây, càng cụ thể càng tốt: quần thể, outcome,
yếu tố quan tâm, và điều bạn muốn kết luận]

=== LUẬT BẮT BUỘC (không được vi phạm ở bất kỳ bước nào) ===

1. Dữ liệu thật nằm NGOÀI repo. Không hỏi đường dẫn, tên folder hay tên file
   của nó. Không bảo tôi copy nó vào repo. Mọi script đọc dữ liệu thật chỉ
   bằng file.choose() để tôi tự chọn file trong RStudio.
2. Không yêu cầu tôi paste dữ liệu thô, thống kê thật (mean, median, min, max,
   SD) hay số dòng thật. Nếu tôi lỡ paste, hãy dừng tôi lại.
3. Mọi file bạn tạo chỉ nằm trong projects/[tên-project]/ và phải có tiền tố
   custom_ để không đè lên file của track chính.
4. KHÔNG sửa dr_workflow_state.yaml. Đây là nhánh ngoài workflow chính.
5. Code là base R. Nếu phương pháp tôi cần bắt buộc phải dùng package ngoài
   (survival, lme4, mice...), hãy HỎI TÔI TRƯỚC khi dùng, và chỉ ghi
   install.packages() dưới dạng comment ở đầu file, không bao giờ đặt nó
   trong phần code chạy.
6. PLAN TRƯỚC, CODE SAU. Không viết một dòng R nào trước khi tôi duyệt SAP.
7. Số liệu chạy trên dữ liệu giả lập KHÔNG phải kết quả nghiên cứu. Chúng chỉ
   chứng minh code chạy được. Không diễn giải chúng như phát hiện khoa học.

=== BƯỚC 1: XÁC NHẬN BỐI CẢNH ===

Đọc pattern/dataset_pattern.csv và data_synthetic/synthetic_dataset.csv.

Nhắc lại cho tôi bằng ngôn ngữ ngắn gọn:
- Bạn hiểu câu hỏi nghiên cứu của tôi là gì
- Biến outcome bạn đề xuất, và kiểu của nó theo pattern file
- Biến phơi nhiễm / yếu tố quan tâm chính
- Các biến còn lại có thể dùng, và biến nào phải loại (id_like, date,
  unsupported)
- Bất kỳ chỗ nào bạn đang phải đoán

Hỏi tôi xác nhận trước khi sang Bước 2. Nếu tôi nói "cứ tiếp tục", hãy tiếp
tục nhưng đánh dấu rõ những chỗ bạn đã giả định.

=== BƯỚC 2: SOẠN SAP RỒI DỪNG LẠI ===

Viết plans/custom_sap.md — kế hoạch phân tích thống kê. Cấu trúc:

A. Câu hỏi nghiên cứu (viết lại chuẩn xác)
B. Thiết kế nghiên cứu và quần thể phân tích (tiêu chí đưa vào / loại ra,
   cách xử lý missing)
C. Biến số: outcome, phơi nhiễm chính, biến điều chỉnh / biến kiểm soát,
   biến bị loại và lý do
D. Mô tả mẫu: mỗi biến sẽ mô tả bằng thống kê gì, và bảng nào sẽ được tạo
E. Các bước phân tích chính — đây là phần quan trọng nhất.
   Với TỪNG bước, bắt buộc khai đủ 6 mục, không được để trống mục nào:

   - Câu hỏi con: bước này trả lời điều gì
   - Phương pháp đề xuất: tên kiểm định / mô hình cụ thể
   - Giả định: phương pháp này giả định điều gì về dữ liệu
   - Cách kiểm giả định: kiểm bằng gì, nhìn vào đâu
   - PHƯƠNG ÁN THAY THẾ NẾU GIẢ ĐỊNH VI PHẠM: nếu giả định không đạt thì
     chuyển sang phương pháp nào
   - Effect measure và cách báo cáo: ước lượng gì, khoảng tin cậy nào, đơn vị

F. Phân tích độ nhạy / phân tích phụ (nếu có)
G. Những gì SẼ KHÔNG làm, và vì sao (chống việc dò p-value)

Quan trọng về giả định: bạn KHÔNG nhìn thấy dữ liệu thật, nên bạn KHÔNG biết
biến nào lệch, biến nào có ô tần số quá nhỏ. Vì vậy SAP phải viết lựa chọn
theo dạng CÓ ĐIỀU KIỆN, ví dụ: "nếu CRP lệch phải rõ → Wilcoxon; nếu xấp xỉ
đối xứng → t-test". Đừng chốt cứng một phương pháp khi nó phụ thuộc vào phân
phối thật.

Viết xong SAP thì DỪNG. Tóm tắt cho tôi 5-7 dòng những quyết định quan trọng
nhất trong SAP và hỏi tôi có duyệt không. Không viết code ở bước này.

=== BƯỚC 3: CHỈ SAU KHI TÔI DUYỆT SAP ===

Viết scripts/custom_analysis.R theo đúng SAP đã duyệt. Yêu cầu về script:

- Có khối SETTINGS ở đầu file, có công tắc để chạy trên dữ liệu giả lập
  (data_synthetic/synthetic_dataset.csv) hoặc dữ liệu thật (file.choose()).
  Mặc định để ở chế độ giả lập.
- PHẦN ĐẦU TIÊN của script là kiểm tra phân phối và giả định: in ra hình dạng
  phân phối của các biến liên quan (summary, histogram, số ca theo nhóm, tần
  số các ô). Đây là phần tôi sẽ đọc trên máy mình.
- Sau phần kiểm tra, code phải TỰ RẼ NHÁNH theo đúng các lựa chọn có điều
  kiện trong SAP, và in ra rõ ràng nó đã chọn nhánh nào và vì sao.
- Mọi bảng kết quả ghi ra outputs_synthetic/ bằng write.csv khi chạy chế độ
  giả lập.
- Comment tiếng Việt, giải thích từng khối làm gì.

Sau đó TỰ KIỂM TRA: chạy `Rscript scripts/custom_analysis.R` từ thư mục
project, sửa lỗi và chạy lại tới khi thoát sạch (exit code 0). Báo cáo trung
thực kết quả kiểm tra. Nếu bạn không chạy được R, hãy nói thẳng và đưa tôi
lệnh chính xác để tự kiểm tra trong RStudio.

Cuối cùng viết plans/custom_analysis_notes.md gồm:
- Cách chạy script này trên dữ liệu thật trong RStudio
- Cách đọc từng phần output
- Những cảnh báo cần chú ý khi chạy trên dữ liệu thật (cỡ mẫu nhỏ, ô tần số
  nhỏ, mô hình không hội tụ...)
- Nhắc lại: kết quả trên dữ liệu giả lập không phải kết quả nghiên cứu
````

## Điểm Dừng Giữa Chừng: SAP Là Của Bạn

Khi agent đưa SAP ra và dừng lại, **đừng duyệt cho xong**. Đây là chỗ bạn học được nhiều nhất.

Đọc kỹ mục E. Với mỗi bước phân tích, tự hỏi:

- Phương pháp này có thật sự trả lời câu hỏi con đó không?
- Giả định agent liệt kê có đúng và đủ không?
- Phương án thay thế có hợp lý không, hay agent viết cho có?
- Effect measure có phải thứ tạp chí trong lĩnh vực của bạn thường báo cáo không?

Sửa thẳng vào SAP rồi bảo agent viết lại. SAP là tài liệu của bạn, không phải của agent.

## Vì Sao Phải Rẽ Nhánh Có Điều Kiện

Agent chỉ nhìn thấy `synthetic_dataset.csv` — mà file này do chính agent sinh ra từ pattern file. **Phân phối của dữ liệu giả lập là do agent bịa ra.**

Nếu để agent "xem phân phối" trên dữ liệu giả lập rồi chốt cứng t-test, bạn sẽ mang một lựa chọn vô căn cứ sang dữ liệu thật vốn có thể lệch nặng. Vì vậy SAP viết cả hai nhánh, script in phần kiểm tra ở đầu, và **bạn** là người nhìn thấy phân phối thật trên máy mình.

Nếu sau khi chạy thật bạn thấy phân phối khác hẳn dự kiến, hãy quay lại nói với agent bằng **mô tả định tính** — "CRP lệch phải nặng, có đuôi dài", "nhóm C chỉ có vài ca" — chứ đừng paste con số. Agent đủ thông tin để chỉnh SAP mà vẫn không biết gì về dữ liệu thật của bạn.

## Checklist Tự Kiểm

Trước khi coi nhánh này là xong, xác nhận đủ 7 dòng:

- [ ] Agent chưa bao giờ hỏi đường dẫn hay tên file dữ liệu thật của tôi
- [ ] Tôi chưa paste dữ liệu thô hay thống kê thật vào cuộc hội thoại
- [ ] Tất cả file mới đều nằm trong `projects/<tên-project>/` và có tiền tố `custom_`
- [ ] `dr_workflow_state.yaml` không bị sửa
- [ ] SAP có đủ 6 mục cho từng bước phân tích, đặc biệt là phương án thay thế
- [ ] Tôi đã thật sự đọc và duyệt SAP, không bấm duyệt cho xong
- [ ] `custom_analysis.R` chạy sạch trên dữ liệu giả lập trước khi tôi mang sang dữ liệu thật

## Lỗi Thường Gặp

**Agent viết code luôn, bỏ qua SAP.** Dừng lại, nhắc luật số 6, yêu cầu quay về Bước 2. Đừng chấp nhận code chưa có plan — bạn sẽ mất khả năng phản biện lựa chọn thống kê.

**Agent chốt cứng một phương pháp phụ thuộc phân phối.** Yêu cầu viết lại thành dạng có điều kiện. Đây là lỗi phổ biến nhất.

**Agent tự thêm package.** Nhắc luật số 5. Hỏi lại vì sao base R không làm được — nhiều khi làm được.

**Agent diễn giải số trên dữ liệu giả lập như phát hiện.** Nhắc luật số 7. Số đó vô nghĩa về mặt khoa học.

**Agent đề xuất chạy hàng loạt kiểm định trên mọi biến.** Từ chối. Mục G của SAP tồn tại chính để chặn việc này.

## Giới Hạn Đã Biết

Nhánh này **không đi qua Stage E** của workflow chính. `dr-05-present-results` chỉ hiểu track Medical và track SEM, nên nó không kiểm tra được tính truy vết cho `custom_sap.md`.

Nghĩa là: sau khi chạy `custom_analysis.R` trên dữ liệu thật, bạn tự đọc output, hoặc paste cho agent viết phần Results dạng tự do — nhưng **sẽ không có bước đối chiếu tự động** giữa con số cuối cùng và kế hoạch ban đầu. Trách nhiệm truy vết thuộc về bạn.

Đó là cái giá của việc rời workflow chính. Nếu câu hỏi nghiên cứu của bạn vẫn nằm gọn trong track Medical hoặc SEM, hãy dùng track có sẵn.
