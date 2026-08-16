# Present Results — Burnout Mediation

## Research Question
Burnout có làm trung gian mối quan hệ giữa job satisfaction và ý định nghỉ việc không?

## Measurement Model
- Job Satisfaction (js_q1–js_q5): α = 0.890, loadings 0.75–0.82
- Burnout (bo_q1–bo_q5): α = 0.921, loadings 0.82–0.85
- CFA fit: CFI = 0.998, TLI = 0.998, RMSEA = 0.018, SRMR = 0.035

## Structural Model Fit
- CFI = 0.996, TLI = 0.995, RMSEA = 0.016, SRMR = 0.029
- χ²(96) = 104.565, p = 0.258

## Key Findings
| Effect | β (95% CI) | p | Standardized |
|---|---|---|---|
| JS → Burnout (a) | −0.054 (−0.170, 0.062) | 0.359 | −0.054 |
| Burnout → TI (b) | 0.171 (0.129, 0.214) | < 0.001 | 0.381 |
| JS → TI direct (c') | −0.188 (−0.231, −0.144) | < 0.001 | −0.415 |
| Indirect (a × b) | −0.009 (−0.029, 0.011) | 0.358 | −0.021 |
| Total | −0.197 (−0.244, −0.150) | < 0.001 | −0.436 |
- R²(turnover_intent) = 0.349

**Kết luận:** Burnout **không** làm trung gian mối quan hệ giữa Job Satisfaction và Turnover Intention (indirect effect p = 0.358). Job Satisfaction có direct effect mạnh lên Turnover Intention và có tác động tổng thể có ý nghĩa thống kê, nhưng không thông qua Burnout.

## Limitations
1. Cross-sectional data — không thể kết luận quan hệ nhân quả.
2. turnover_intent là biến nhị phân, ước lượng ML có thể chưa tối ưu; DWLS (ordered) có thể cho kết quả chính xác hơn.
3. Các biến không đo lường khác (ví dụ: áp lực công việc, hỗ trợ tổ chức) có thể là confounder chưa được kiểm soát.

## Files
- `results_traceability_check.yaml`
- `manuscript_results_table.md`
- `results_paragraph.md`
