# Hướng Dẫn Cài Đặt & Sử Dụng AirGap Stats

AirGap Stats là bộ công cụ phân tích dữ liệu bằng AI agent mà **dữ liệu thật không bao giờ rời khỏi máy của bạn** — đúng như tên gọi "air-gapped" (cách ly khỏi mạng): AI bị cách ly hoàn toàn khỏi dữ liệu thật ở mọi giai đoạn. AI chỉ biết những gì bạn chủ động khai báo và duyệt.

# License: PROPRIETARY AND CONFIDENTIAL

Copyright © 2026. All Rights Reserved.

This material is licensed to one registered user only. It may not be copied, modified, shared, redistributed, sublicensed, published, sold, uploaded to a shared workspace, or provided to any third party, whether for commercial or non-commercial purposes.

Bản quyền © 2026. Bảo lưu mọi quyền.

Tài liệu này chỉ được cấp phép cho một người dùng đã đăng ký.

Người được cấp phép không được sao chép, sửa đổi, chia sẻ, phân phối lại, cấp phép lại, công bố, bán, đăng tải lên không gian làm việc dùng chung hoặc cung cấp tài liệu cho bất kỳ bên thứ ba nào, dù vì mục đích thương mại hay phi thương mại.

Người dùng được phép sử dụng tài liệu này để phục vụ công việc cá nhân nhưng không được chia sẻ, bán hoặc phân phối chính tài liệu, kỹ năng, hay prompt hay workflow được cung cấp.

## Yêu Cầu Môi Trường

- **R + RStudio** (bản R 4.x bất kỳ). Track Medical chạy 100% base R — không cần cài package nào.
- Track SEM cần đúng 1 package: chạy `install.packages("lavaan")` một lần trong RStudio.
- Một AI coding agent chạy local tại folder này: **Claude Code** (khuyến nghị), **Codex**, hoặc **OpenCode**.

## Cài Đặt

1. Giải nén file zip sản phẩm vào một folder, ví dụ `D:\projects\airgap-stats\`.
2. Khởi động agent (`claude`, `codex`, hoặc `opencode`) và trở project của agent vào folder trên
3. Xong. Skills đã nằm sẵn trong repo:
   - Claude Code tự nhận `.claude/skills/` và đọc `CLAUDE.md`.
   - Codex đọc `AGENTS.md` (trỏ đến `skills/`).
   - OpenCode tự nhận `.opencode/skill/`.

Kiểm tra bằng câu hỏi:

```text
Use dr-workflow-orchestrator. Tôi muốn bắt đầu một dự án phân tích mới. Quy trình gồm những bước nào?
```

## QUAN TRỌNG NHẤT: Dữ Liệu Thật Của Bạn Để Ở Đâu?

**QUY TẮC VÀNG: KHÔNG BAO GIỜ copy file dữ liệu thật vào folder AirGap Stats này.** Cứ để nó ở nơi bạn vẫn lưu — ví dụ `Documents\du-lieu-nghien-cuu\` hay USB. AI agent chỉ hoạt động bên trong folder pack, nên dữ liệu nằm ngoài folder = nằm ngoài tầm với của AI.

Vậy khi script cần đọc dữ liệu thật thì sao? Mỗi khi cần, script sẽ dùng lệnh `file.choose()` — R sẽ **mở một cửa sổ chọn file giống hệt khi bạn mở file Word/Excel**. Bạn chỉ việc trỏ tới file dữ liệu của mình và bấm Open. Không cần gõ đường dẫn, không cần biết lập trình.

### Từng bước cụ thể (làm đúng 5 bước này mỗi lần chạy trên dữ liệu thật)

1. Mở **RStudio**.
2. Vào menu **Session → Set Working Directory → Choose Directory...** rồi chọn folder project của bạn (ví dụ `...\projects\diabetes`). Bước này để R biết "nhà" của project ở đâu.
3. **Copy nguyên khối lệnh** mà agent đưa cho bạn, **dán vào ô Console** (ô có dấu `>` ở góc dưới bên trái RStudio), nhấn **Enter**.
4. Khi thấy R như "đứng im" — đó là lúc **cửa sổ chọn file đã mở** (đôi khi nó nấp sau cửa sổ RStudio, hãy nhìn thanh taskbar dưới màn hình). Tìm đến file dữ liệu thật của bạn → bấm **Open**.
5. Chờ chữ chạy xong trong Console, rồi quay lại làm theo hướng dẫn tiếp theo của agent.

### Vì sao cách này an toàn tuyệt đối?

- Đường dẫn tới file thật **chỉ tồn tại trong phiên RStudio của bạn** — không được ghi vào bất kỳ file nào trong folder pack. AI thậm chí không biết dữ liệu thật nằm ở đâu, tên là gì.
- Nhờ vậy, **toàn bộ folder project của bạn an toàn để zip gửi cho người khác** (nhờ giảng viên xem giúp, backup, sync cloud) — trong đó không hề có dữ liệu thật.

### Một lưu ý khi paste kết quả cho AI (bước E)

Nếu trong phần kết quả bạn copy từ Console có hiện **đường dẫn hoặc tên file dữ liệu thật** (ví dụ `D:\benh-vien\HIV_2024.csv`), hãy **xoá dòng đó trước khi paste** — vì đôi khi chính tên file cũng là thông tin nhạy cảm.

## Vì Sao An Toàn? (kiến trúc 5 giai đoạn)

```text
A. Agent viết pattern_extract.R -> BẠN chạy trong RStudio, chọn file thật
   qua cửa sổ file.choose()
   -> ra file pattern/dataset_pattern.csv (chỉ có: tên biến, kiểu biến,
      levels của biến phân loại, % missing — KHÔNG có giá trị thật,
      KHÔNG có thống kê, KHÔNG có số dòng, KHÔNG có đường dẫn file)
   -> BẠN mở file này duyệt từng dòng trước khi đưa cho agent (review gate)

B. Agent đọc pattern đã duyệt -> viết scripts/synthesize_data.R

C. BẠN chạy script đó trong RStudio -> ra data_synthetic/synthetic_dataset.csv
   (100% giá trị được sinh mới, không copy dòng nào từ dữ liệu thật)

D. Agent phân tích trên dữ liệu GIẢ: viết desc.R, infer.R (hoặc sem_*.R),
   tự chạy thử bằng Rscript cho đến khi code sạch

E. BẠN chạy các file .R đó trong RStudio trên dữ liệu THẬT (chọn file qua
   cửa sổ file.choose(), sửa output_dir thành "results_real")
   -> paste output cho agent -> agent viết bảng kết quả + đoạn Results
   (agent không được bịa số; mọi con số phải từ output bạn cung cấp)
```

Bốn lớp bảo vệ:

1. **Dữ liệu thật nằm ngoài folder pack** — ngoài tầm hoạt động của AI agent. Đây là lớp quan trọng nhất và áp dụng cho mọi agent (Claude Code, Codex, OpenCode).
2. Lưới an toàn: nếu bạn lỡ copy dữ liệu vào folder `data_real/` nào đó trong pack, `.claude/settings.json` có **deny rule chặn Claude Code đọc folder đó** ở tầng công cụ, và mọi skill đều có lệnh cấm kèm cảnh báo bạn chuyển file ra ngoài.
3. `.gitignore` chặn commit các file dữ liệu (`data_real/`, `.sav`, `.dta`, `.xlsx`).
4. QA gate (`dr-output-qa-gate`) kiểm tra từng giai đoạn: pattern file không chứa thống kê/đường dẫn, bạn đã xác nhận review, không có dữ liệu thật trong repo.

## Cách Dùng: Mỗi Câu Hỏi Nghiên Cứu = 1 Project

Mọi output nằm trong `projects/<tên-project>/`. Bắt đầu dự án mới:

```text
Use dr-workflow-orchestrator.
Tạo project mới tên "diabetes" cho câu hỏi nghiên cứu:
[viết câu hỏi nghiên cứu của bạn]
```

Agent sẽ tạo `projects/diabetes/` từ template. Dữ liệu thật của bạn **giữ nguyên ở chỗ cũ ngoài folder pack** — khi cần, script sẽ mở cửa sổ cho bạn chọn file (xem mục "Dữ Liệu Thật Của Bạn Để Ở Đâu?" phía trên).

Cấu trúc một project:

```text
projects/diabetes/
  dr_workflow_state.yaml   trạng thái workflow (hỏi "tôi đang ở bước nào?" bất kỳ lúc nào)
  pattern/                 dataset_pattern.csv (bạn duyệt trước khi agent đọc)
  data_synthetic/          dữ liệu giả
  plans/                   analysis_plan.yaml và các plan từng bước
  scripts/                 các file .R (chạy được cả trên dữ liệu giả lẫn thật)
  outputs_synthetic/       kết quả chạy thử trên dữ liệu giả (chỉ để kiểm tra code)
  results_real/            output thật bạn paste + bảng kết quả, đoạn Results cuối cùng
```

Hai track phân tích (agent sẽ hỏi bạn xác nhận ở bước D1):

- **Medical**: outcome quan sát được, regression + confounding adjustment (dùng cho nghiên cứu lâm sàng, y sinh).
- **SEM**: thang đo Likert, constructs, CFA + structural model bằng lavaan (dùng cho public health, khoa học xã hội).

## Hai Project Mẫu

- `projects/example-clinical/` — dữ liệu lâm sàng giả lập (treatment vs mortality), track Medical.
- `projects/example-survey-sem/` — dữ liệu khảo sát giả lập (burnout, job satisfaction, turnover intent), track SEM.

Dùng để học và demo trước khi làm với dữ liệu của bạn. Xem kịch bản demo đầy đủ trong `docs/dr-demo-runbook.md`.

## Prompt Bắt Đầu Chuẩn

```text
Use dr-workflow-orchestrator.

Project: [tên project]
Câu hỏi nghiên cứu: [câu hỏi của bạn]

Hãy xác định tôi đang ở giai đoạn nào, cập nhật dr_workflow_state.yaml,
và cho tôi biết hành động tiếp theo.
```

## Xử Lý Sự Cố

- **Agent không thấy skill**: hỏi thẳng `Đọc skills/dr-workflow-orchestrator/SKILL.md và làm theo` — mọi agent đọc được file thường.
- **`Rscript` không chạy được khi agent verify (báo "not recognized" / "command not found")**: xem mục riêng bên dưới. **Đây là tuỳ chọn, không bắt buộc.**
- **R báo thiếu lavaan (track SEM)**: `install.packages("lavaan")` trong RStudio, một lần duy nhất.
- **File CSV tiếng Việt bị lỗi font**: các script của pack luôn đọc/ghi UTF-8; nếu tự viết thêm code, thêm `fileEncoding = "UTF-8"`.

## (Tuỳ Chọn) Cho Agent Tự Chạy `Rscript` — Không Bắt Buộc

Ở giai đoạn D, agent có thể **tự chạy thử** code bằng lệnh `Rscript` để kiểm tra code chạy sạch trên dữ liệu giả. Muốn vậy, `Rscript` phải nằm trong PATH của hệ thống.

**Nhưng bước này hoàn toàn tuỳ chọn.** Nếu gõ `Rscript` mà máy báo lỗi "not recognized" (Windows) hoặc "command not found" (macOS), bạn **không cần sửa gì cả**. Cách đơn giản và luôn hoạt động:

> Để agent viết code xong, bạn **copy file `.R` mở trong RStudio và bấm Source** (hoặc chọn hết code rồi Ctrl/Cmd + Enter). RStudio luôn tự biết R nằm đâu, không cần PATH. Chạy xong, **báo kết quả (hoặc lỗi) cho agent** — bước kiểm tra vẫn hoàn tất, chỉ là bạn chạy thay agent.

Nói cách khác: giá trị cốt lõi của pack là **AI viết code, bạn chạy trong RStudio**. Việc agent tự chạy `Rscript` chỉ là tiện ích tăng tốc, không phải điều kiện bắt buộc.

Nếu bạn *muốn* bật tiện ích này:

**Windows**

R không tự thêm mình vào PATH khi cài. Thêm thủ công:

1. Tìm thư mục `bin` của R, thường là `C:\Program Files\R\R-4.x.x\bin` (thay `4.x.x` bằng phiên bản của bạn).
2. Nhấn phím Windows, gõ "environment variables" → mở **Edit the system environment variables**.
3. Bấm **Environment Variables** → ở **User variables**, chọn **Path** → **Edit** → **New** → dán đường dẫn `bin` ở trên → OK hết các cửa sổ.
4. **Đóng hẳn agent/terminal rồi mở lại** (agent đọc PATH lúc khởi động, không khởi động lại sẽ không thấy thay đổi).

Kiểm tra: mở terminal mới, gõ `Rscript --version` — hiện số phiên bản là được.

**macOS**

Khi cài R từ bộ cài chính thức của CRAN (file `.pkg`), macOS **thường đã tự tạo sẵn** liên kết để `Rscript` chạy được trong Terminal — nên phần lớn máy Mac không cần làm gì. Nếu vẫn báo "command not found":

1. R thường nằm ở `/Library/Frameworks/R.framework/Resources/bin`. Kiểm tra nhanh: gõ trong Terminal
   ```bash
   ls /usr/local/bin/Rscript
   ```
   Nếu có kết quả là đã ổn.
2. Nếu chưa, thêm dòng này vào file `~/.zshrc` (macOS mới dùng shell zsh):
   ```bash
   export PATH="/Library/Frameworks/R.framework/Resources/bin:$PATH"
   ```
3. Chạy `source ~/.zshrc` (hoặc mở Terminal mới), rồi **khởi động lại agent**.

Kiểm tra: `Rscript --version`.

## Nhắc Lại Về Bảo Mật

Không bao giờ upload dữ liệu bệnh nhân, dữ liệu định danh, hay dữ liệu khảo sát nhạy cảm cho AI — kể cả "chỉ vài dòng đầu". Toàn bộ workflow này tồn tại để bạn không bao giờ phải làm điều đó:

```text
dữ liệu thật ở RStudio -> pattern đã duyệt -> dữ liệu giả -> AI viết code
-> code chạy trên dữ liệu thật tại máy bạn -> chỉ output bạn chọn mới đưa lại cho AI
```
