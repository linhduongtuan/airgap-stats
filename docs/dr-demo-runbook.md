# Runbook Demo DR v2: Clinical (Medical Track) + Survey (SEM Track)

Kịch bản demo end-to-end với 2 project mẫu có sẵn trong pack:

- `projects/example-clinical/` — track Medical
- `projects/example-survey-sem/` — track SEM

Thông điệp chính khi demo:

> AI hỗ trợ triển khai workflow. Người nghiên cứu quyết định câu hỏi, biến số, model và diễn giải. Dữ liệu thật không bao giờ rời khỏi máy.

## Kiến Trúc Demo

```text
CSV thật (NGOÀI folder pack, chọn qua file.choose()) --RStudio--> dataset_pattern.csv --BẠN DUYỆT--> agent
agent --> synthesize_data.R --RStudio--> synthetic_dataset.csv --> agent
agent viết desc.R / infer.R / sem_*.R, tự verify bằng Rscript trên dữ liệu giả
BẠN chạy các file .R trên dữ liệu thật --paste output--> agent viết Results
```

Agent chỉ được thấy: pattern đã duyệt, dữ liệu giả, các file plan, code R, và output thật do bạn chủ động paste.

## Phần 1: Demo Clinical (Medical Track)

Câu hỏi nghiên cứu:

```text
Trong nhóm bệnh nhân của clinical dataset, phác đồ điều trị có liên quan tới tử vong 30 ngày không?
Outcome: mortality_30day. Main predictor: treatment.
Candidate covariates: age, sex, bmi, diabetes, hypertension, smoking, egfr, hba1c, crp.
```

### Giai đoạn A-C: Privacy Gate

Prompt:

```text
Use dr-workflow-orchestrator. Project: example-clinical.
Câu hỏi nghiên cứu: [như trên]
Bắt đầu từ privacy gate.
```

Agent sẽ đưa lệnh R. Bạn chạy trong RStudio (working directory = `projects/example-clinical/`):

```r
source("scripts/pattern_extract.R")
original <- read.csv(file.choose())   # cửa sổ chọn file mở ra: chọn clinical.csv ở root của pack
extract_pattern(original, output_csv = "pattern/dataset_pattern.csv")
```

(Trong demo, `clinical.csv` ở root pack đóng vai "dữ liệu thật nằm ngoài project". Với dữ liệu thật của học viên: file nằm bất kỳ đâu trên máy, ngoài folder pack.)

**Điểm giảng quan trọng nhất của demo**: mở `pattern/dataset_pattern.csv` chiếu lên màn hình. Chỉ cho học viên thấy: không có số dòng, không có mean/min/max, chỉ có tên biến + kiểu + levels + % missing. Đây là toàn bộ những gì AI được biết về dữ liệu thật. Xác nhận review với agent.

Sau khi agent viết `scripts/synthesize_data.R`, chạy tiếp:

```r
source("scripts/synthesize_data.R")
original <- read.csv(file.choose())   # chọn lại clinical.csv
synthesize_data(pattern_csv = "pattern/dataset_pattern.csv", data = original,
                output_csv = "data_synthetic/synthetic_dataset.csv", n = 200, seed = 2026)
```

> Điểm giảng: mở synthetic_dataset.csv cạnh dữ liệu thật — cùng cấu trúc, khác toàn bộ giá trị, 200 dòng thay vì n thật.

### Giai đoạn D1-D2

```text
Use dr-01-understand-dataset. Create the analysis plan and confirm the track.
```

(Track: medical. QA sau mỗi bước: `Use dr-output-qa-gate to check the current stage.`)

```text
Use dr-02-descriptive-analysis. Propose Table 1 variables and grouping first.
Default grouping: treatment. No p-values.
```

Agent viết `scripts/desc.R` và **tự chạy** `Rscript scripts/desc.R` — cho học viên xem `outputs_synthetic/table1.csv` sinh ra từ dữ liệu giả.

> Điểm giảng: Descriptive analysis trả lời "tôi đã nghiên cứu trên ai?". Số trong bảng này là số GIẢ — chỉ để chứng minh code chạy.

### Giai đoạn D3-D4

```text
Use dr-03-inferential-analysis. Confirm the crude plan before writing code.
Expected: mortality_30day ~ treatment, crude logistic regression, OR + 95% CI + p-value.
```

```text
Use dr-04-confounding-adjustment. Keep the D3 model. Proposed covariates:
age, sex, bmi, diabetes, hypertension, smoking, egfr, hba1c, crp.
Ask me to confirm before coding.
```

> Điểm giảng: Analyze để trả lời câu hỏi, không phải để săn p-value. Adjust để so sánh công bằng hơn, không phải để p đẹp hơn.

### Giai đoạn E

Bạn chạy trong RStudio, sửa 2 dòng settings đầu file:

```r
# trong scripts/desc.R và scripts/infer.R, sửa 2 dòng settings đầu file thành:
input_csv  <- file.choose()   # cửa sổ mở ra: chọn file dữ liệu thật
output_dir <- "results_real"
```

Chạy cả hai file, paste console output (hoặc nội dung `results_real/infer_crude_vs_adjusted.csv`) cho agent:

```text
Use dr-05-present-results. Đây là output thật từ RStudio:
[paste]
Create traceable manuscript-ready outputs. Do not invent numbers.
```

> Điểm giảng: cùng một file code — đổi 2 dòng — chạy trên dữ liệu thật. Publication-ready nghĩa là trace được từng con số.

## Phần 2: Demo Survey (SEM Track)

Câu hỏi nghiên cứu:

```text
Burnout và job satisfaction có liên quan tới turnover intent không?
Outcome: turnover_intent.
Constructs: Job satisfaction (js_q1..js_q5), Burnout (bo_q1..bo_q5).
Observed covariates: work_mode, age, gender, income, work_hours, tenure_years, wlb.
```

Trình tự giống Phần 1 cho A-C và D1-D2 (project: `example-survey-sem`; khi synthesize dùng `n = 300` cho lavaan thoải mái; track: sem).

### D3: Measurement Model

```text
Use dr-sem-01-measurement-model.
Constructs: Job satisfaction: js_q1..js_q5; Burnout: bo_q1..bo_q5. Response range 1-5, no reverse coding.
```

Agent viết `scripts/sem_measurement.R` (alpha bằng base R + CFA bằng lavaan) và tự verify.

> Điểm giảng: survey có thêm measurement layer. Fit indices chạy trên dữ liệu giả là VÔ NGHĨA (các item được sinh độc lập) — chỉ khi chạy trên dữ liệu thật mới đọc được alpha/CFI/RMSEA. Đây là minh hoạ sống động nhất cho nguyên tắc "synthetic chỉ để test code".

### D4: Structural Model

```text
Use dr-sem-02-structural-model.
Proposed paths: turnover_intent ~ burnout + jobsat + work_mode.
Show me the full lavaan syntax and ask me to confirm every path.
```

### E: Present Results

Chạy `sem_measurement.R` rồi `sem_structural.R` trên dữ liệu thật trong RStudio (đổi 2 dòng settings), paste output, gọi `dr-05-present-results`.

> Điểm giảng: bảng SEM báo fit trước, path estimates sau. Path là giả thuyết có hướng, không phải chứng minh nhân quả.

## Timing Gợi Ý Cho Live Demo 90 Phút

```text
0-15:  Privacy gate clinical (điểm nhấn: chiếu pattern file + review gate)
15-30: D1 + D2 clinical (agent tự chạy Rscript — chiếu terminal)
30-45: D3 + D4 clinical
45-55: Stage E clinical với output thật
55-75: Survey: privacy gate nhanh + measurement model (điểm nhấn: fit giả vô nghĩa)
75-85: Structural model + Stage E survey bản ngắn
85-90: So sánh 2 track, tổng kết nguyên tắc
```

## Cần Nhấn Mạnh Khi Giảng

- Cùng một workflow, hai track phân tích khác nhau.
- AI chưa bao giờ thấy dữ liệu thật — chỉ thấy pattern bạn đã duyệt và dữ liệu giả.
- Code chạy được trên dữ liệu giả thì chạy được trên dữ liệu thật (cùng tên biến, cùng kiểu, cùng levels).
- Mọi con số cuối cùng đều trace về output RStudio của chính bạn.
- Track Medical: 0 package. Track SEM: đúng 1 package (lavaan).

## Artifact Cuối Cùng Kỳ Vọng

Clinical (`projects/example-clinical/`): `pattern/dataset_pattern.csv`, `data_synthetic/synthetic_dataset.csv`, `plans/analysis_plan.yaml`, `plans/inferential_analysis_plan.yaml`, `plans/confounding_adjustment_plan.yaml`, `scripts/desc.R`, `scripts/infer.R`, `results_real/present_results.md`.

Survey (`projects/example-survey-sem/`): như trên nhưng với `plans/sem_measurement_plan.yaml`, `plans/sem_structural_plan.yaml`, `scripts/sem_measurement.R`, `scripts/sem_structural.R`.
