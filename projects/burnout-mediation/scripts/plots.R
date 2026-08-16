# DR Stage D2b (SEM): Visual exploration of scale items
# Base R only (no lavaan needed here). Run from the project folder.
#
# PRIVACY NOTE -------------------------------------------------------------
# These figures are drawn from row-level data: every point is one respondent.
# On a real run the figures are written NEXT TO YOUR REAL DATASET, outside
# this repo, so nothing derived from real data can ever be committed to git.
# Never paste a figure made from real data into an AI chat. Aggregate numbers
# (alpha, CFA fit, path estimates) are fine to paste; pictures of raw rows
# are not.
# --------------------------------------------------------------------------

# === USER SETTINGS ==========================================================
# Runs on the synthetic dataset as delivered:
input_csv  <- "data_synthetic/synthetic_dataset.csv"
output_dir <- "outputs_synthetic/figures"
# To run on REAL data in RStudio, comment the two lines above and uncomment these:
# input_csv  <- file.choose()                                  # select your real dataset
# output_dir <- file.path(dirname(input_csv), "dr_figures")    # figures stay outside the repo
# ============================================================================

# Show individual data points and boxplot outliers (see note in Figure 2).
show_individual_points <- TRUE

dat <- read.csv(input_csv, stringsAsFactors = FALSE, fileEncoding = "UTF-8")
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

# --- Constructs from plans/sem_measurement_plan.yaml ---
# Item order matters: items of the same construct must sit next to each other,
# otherwise the block structure cannot appear on the heatmap.
constructs <- list(
  "Job Satisfaction" = c("js_q1", "js_q2", "js_q3", "js_q4", "js_q5"),
  "Burnout"          = c("bo_q1", "bo_q2", "bo_q3", "bo_q4", "bo_q5"),
  "Turnover"         = c("turnover_intent")
)
items <- unlist(constructs, use.names = FALSE)

stopifnot(all(items %in% names(dat)))

usable <- items[sapply(items, function(v) {
  x <- dat[[v]][!is.na(dat[[v]])]
  length(unique(x)) > 1
})]
dropped <- setdiff(items, usable)
if (length(dropped) > 0) {
  cat("Skipped (no variation or all missing):", paste(dropped, collapse = ", "), "\n")
}
stopifnot(length(usable) >= 2)

# Construct membership of each usable item, kept in display order
item_construct <- rep(names(constructs), sapply(constructs, length))
names(item_construct) <- items
item_construct <- item_construct[usable]

construct_cols <- c("#4393C3", "#D6604D", "#7FBC7F", "#C7B0D9")
names(construct_cols) <- c(names(constructs), rep("extra", 4))[seq_along(construct_cols)]

# === FIGURE 1: ITEM CORRELATION HEATMAP =====================================
M <- cor(dat[usable], use = "pairwise.complete.obs")
p <- ncol(M)

pal <- colorRampPalette(c("#2166AC", "#4393C3", "#F7F7F7", "#D6604D", "#B2182B"))(201)

png(file.path(output_dir, "fig1_item_correlation_heatmap.png"),
    width = 1500, height = 1300, res = 150, type = "cairo")

layout(matrix(c(1, 2), nrow = 1), widths = c(6, 1))
par(mar = c(7, 7, 4.5, 1))

image(1:p, 1:p, M[, p:1], zlim = c(-1, 1), col = pal,
      axes = FALSE, xlab = "", ylab = "")
axis(1, at = 1:p, labels = colnames(M), las = 2, cex.axis = 0.9, tick = FALSE)
axis(2, at = 1:p, labels = rev(colnames(M)), las = 1, cex.axis = 0.9, tick = FALSE)
abline(h = 0.5 + 0:p, v = 0.5 + 0:p, col = "white", lwd = 1.5)

for (i in 1:p) {
  for (j in 1:p) {
    r <- M[i, j]
    text(i, p + 1 - j, sprintf("%.2f", r), cex = 0.7,
         col = if (abs(r) > 0.55) "white" else "grey15")
  }
}

# Outline the expected construct blocks along the diagonal
bounds <- cumsum(rle(as.vector(item_construct))$lengths)
starts <- c(1, head(bounds, -1) + 1)
for (b in seq_along(bounds)) {
  a <- starts[b]; z <- bounds[b]
  rect(a - 0.5, p + 1 - z - 0.5, z + 0.5, p + 1 - a + 0.5,
       border = "grey10", lwd = 3)
}

title(main = "Tương quan giữa các item, nhóm theo construct",
      cex.main = 1.2, adj = 0)
mtext("Khối đậm trên đường chéo = các item cùng một nhân tố tiềm ẩn",
      side = 3, adj = 0, line = 0.2, cex = 0.8, col = "grey40")

par(mar = c(7, 1, 4.5, 4))
bar_vals <- seq(-1, 1, length.out = 201)
image(1, bar_vals, matrix(bar_vals, nrow = 1), col = pal, zlim = c(-1, 1),
      axes = FALSE, xlab = "", ylab = "")
axis(4, at = seq(-1, 1, 0.5), las = 1, cex.axis = 0.85)
box(col = "grey70")

dev.off()
cat("Figure 1 written:", file.path(output_dir, "fig1_item_correlation_heatmap.png"), "\n")

# === FIGURE 2: ITEM DISTRIBUTION SERIES =====================================
n_ok <- sapply(usable, function(v) sum(!is.na(dat[[v]])))
if (any(n_ok < 5)) {
  cat("WARNING: item(s) with fewer than 5 observations; Figure 2 skipped.\n")
} else {
  png(file.path(output_dir, "fig2_item_boxplot_series.png"),
      width = 1600, height = 950, res = 150, type = "cairo")

  par(mar = c(6, 4.5, 4.5, 1), mgp = c(2.8, 0.7, 0))

  groups <- lapply(usable, function(v) dat[[v]][!is.na(dat[[v]])])
  names(groups) <- usable
  box_fill <- construct_cols[item_construct]

  boxplot(groups, col = adjustcolor(box_fill, alpha.f = 0.65), border = "grey25",
          outline = show_individual_points, outpch = 21, outcex = 0.7,
          outbg = "grey60", las = 2, ylab = "Điểm trả lời",
          cex.axis = 0.95, boxwex = 0.6, staplewex = 0.4)

  if (show_individual_points) {
    for (k in seq_along(groups)) {
      y <- groups[[k]]
      points(jitter(rep(k, length(y)), amount = 0.16), jitter(y, amount = 0.12),
             pch = 16, cex = 0.4, col = adjustcolor("grey20", alpha.f = 0.3))
    }
  }

  # Separate the constructs visually
  bounds2 <- cumsum(rle(as.vector(item_construct))$lengths)
  abline(v = head(bounds2, -1) + 0.5, col = "grey55", lty = 2)

  title(main = "Phân bố từng item theo construct", cex.main = 1.25, adj = 0)
  mtext("Kiểm tra hiệu ứng trần/sàn và item lệch trước khi chạy CFA",
        side = 3, adj = 0, line = 0.2, cex = 0.8, col = "grey40")

  legend("topright", legend = names(constructs),
         fill = adjustcolor(construct_cols[names(constructs)], alpha.f = 0.65),
         border = "grey25", bty = "n", cex = 0.9)

  dev.off()
  cat("Figure 2 written:", file.path(output_dir, "fig2_item_boxplot_series.png"), "\n")
}

cat("\nVisual exploration complete. Figures in:", output_dir, "\n")
cat("NOTE: on the synthetic dataset the items are simulated independently,\n")
cat("so no block structure will appear on the heatmap. That is expected and\n")
cat("only proves the code runs. The blocks appear on your real data.\n")
