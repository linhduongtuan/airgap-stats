# DR Stage D2b: Visual exploration (correlation heatmap + boxplot series)
# Base R only. Run from the project folder.
#
# PRIVACY NOTE -------------------------------------------------------------
# These figures are drawn from row-level data: every point is one participant.
# On a real run the figures are written NEXT TO YOUR REAL DATASET, outside
# this repo, so nothing derived from real data can ever be committed to git.
# Never paste a figure made from real data into an AI chat. Aggregate numbers
# (Table 1, model estimates) are fine to paste; pictures of raw rows are not.
# --------------------------------------------------------------------------

# === USER SETTINGS ==========================================================
# Runs on the synthetic dataset as delivered:
input_csv  <- "data_synthetic/synthetic_dataset.csv"
output_dir <- "outputs_synthetic/figures"
# To run on REAL data in RStudio, comment the two lines above and uncomment these:
# input_csv  <- file.choose()                                  # select your real dataset
# output_dir <- file.path(dirname(input_csv), "dr_figures")    # figures stay outside the repo
# ============================================================================

# Show individual data points and boxplot outliers.
# TRUE is correct for your own analysis: outliers carry real clinical meaning.
# Set to FALSE only if you intend to show this figure outside your own machine.
show_individual_points <- TRUE

dat <- read.csv(input_csv, stringsAsFactors = FALSE, fileEncoding = "UTF-8")
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

# --- Variables from plans/analysis_plan.yaml ---
group_var    <- "mortality_30day"
group_labels <- c("Sống", "Tử vong")     # for values 0 and 1
numeric_vars <- c("age", "bmi", "sbp", "dbp", "egfr", "hba1c", "crp", "length_of_stay")

stopifnot(all(c(numeric_vars, group_var) %in% names(dat)))

# Keep only variables that actually vary; a constant column breaks cor()
usable <- numeric_vars[sapply(numeric_vars, function(v) {
  x <- dat[[v]][!is.na(dat[[v]])]
  length(unique(x)) > 1
})]
dropped <- setdiff(numeric_vars, usable)
if (length(dropped) > 0) {
  cat("Skipped (no variation or all missing):", paste(dropped, collapse = ", "), "\n")
}
stopifnot(length(usable) >= 2)

# === FIGURE 1: CORRELATION HEATMAP ==========================================
M <- cor(dat[usable], use = "pairwise.complete.obs")
p <- ncol(M)

pal <- colorRampPalette(c("#2166AC", "#4393C3", "#F7F7F7", "#D6604D", "#B2182B"))(201)

png(file.path(output_dir, "fig1_correlation_heatmap.png"),
    width = 1500, height = 1250, res = 150, type = "cairo")

layout(matrix(c(1, 2), nrow = 1), widths = c(6, 1))
par(mar = c(7, 7, 4, 1))

# image() draws y bottom-up; reverse the columns so row 1 sits at the top
image(1:p, 1:p, M[, p:1], zlim = c(-1, 1), col = pal,
      axes = FALSE, xlab = "", ylab = "")
axis(1, at = 1:p, labels = colnames(M), las = 2, cex.axis = 0.9, tick = FALSE)
axis(2, at = 1:p, labels = rev(colnames(M)), las = 1, cex.axis = 0.9, tick = FALSE)

# Grid lines between cells
abline(h = 0.5 + 0:p, v = 0.5 + 0:p, col = "white", lwd = 2)

# Overlay the coefficients; light text on dark cells
for (i in 1:p) {
  for (j in 1:p) {
    r <- M[i, j]
    text(i, p + 1 - j, sprintf("%.2f", r), cex = 0.75,
         col = if (abs(r) > 0.55) "white" else "grey15")
  }
}
title(main = "Tương quan giữa các biến liên tục (Pearson)", cex.main = 1.2, adj = 0)
mtext("pairwise complete observations", side = 3, adj = 0, line = 0.2,
      cex = 0.8, col = "grey40")

# Colour bar
par(mar = c(7, 1, 4, 4))
bar_vals <- seq(-1, 1, length.out = 201)
image(1, bar_vals, matrix(bar_vals, nrow = 1), col = pal, zlim = c(-1, 1),
      axes = FALSE, xlab = "", ylab = "")
axis(4, at = seq(-1, 1, 0.5), las = 1, cex.axis = 0.85)
box(col = "grey70")

dev.off()
cat("Figure 1 written:", file.path(output_dir, "fig1_correlation_heatmap.png"), "\n")

# === FIGURE 2: BOXPLOT SERIES BY OUTCOME ====================================
g <- dat[[group_var]]
keep <- !is.na(g)
g_vals <- sort(unique(g[keep]))

if (length(g_vals) < 2) {
  cat("Skipping Figure 2: grouping variable has fewer than 2 observed levels.\n")
} else {
  # Small-cell guard: a group of 2-3 people yields a meaningless box and
  # exposes those individuals. Standard disclosure control threshold is 5.
  g_n <- sapply(g_vals, function(v) sum(g == v, na.rm = TRUE))
  too_small <- g_vals[g_n < 5]
  if (length(too_small) > 0) {
    cat("WARNING: group(s)", paste(too_small, collapse = ", "),
        "have fewer than 5 observations. Figure 2 skipped.\n")
  } else {
    labs <- if (length(g_vals) == length(group_labels)) group_labels else as.character(g_vals)
    box_cols <- c("#92C5DE", "#F4A582", "#B8E186", "#C7B0D9")[seq_along(g_vals)]

    n_panel <- length(usable)
    n_col <- min(4, n_panel)
    n_row <- ceiling(n_panel / n_col)

    png(file.path(output_dir, "fig2_boxplot_series.png"),
        width = 400 * n_col, height = 420 * n_row + 90, res = 150, type = "cairo")

    par(mfrow = c(n_row, n_col), mar = c(3.5, 4, 3.5, 1),
        oma = c(0, 0, 3.5, 0), mgp = c(2.4, 0.7, 0))

    for (v in usable) {
      groups <- lapply(g_vals, function(val) dat[[v]][keep & g == val])
      names(groups) <- labs

      boxplot(groups, col = box_cols, border = "grey25",
              outline = show_individual_points, outpch = 21, outcex = 0.7,
              outbg = "grey60", main = v, ylab = "", cex.main = 1.15,
              cex.axis = 0.95, boxwex = 0.55, staplewex = 0.4)

      if (show_individual_points) {
        for (k in seq_along(groups)) {
          y <- groups[[k]][!is.na(groups[[k]])]
          points(jitter(rep(k, length(y)), amount = 0.13), y,
                 pch = 16, cex = 0.45, col = adjustcolor("grey20", alpha.f = 0.35))
        }
      }
      grp_n <- sapply(groups, function(x) sum(!is.na(x)))
      mtext(paste0("n = ", paste(grp_n, collapse = " / ")), side = 3,
            line = 0.15, cex = 0.7, col = "grey40")
    }

    mtext(paste0("Phân bố biến liên tục theo ", group_var),
          outer = TRUE, side = 3, line = 0.8, cex = 1.1, font = 2)

    dev.off()
    cat("Figure 2 written:", file.path(output_dir, "fig2_boxplot_series.png"), "\n")
  }
}

cat("\nVisual exploration complete. Figures in:", output_dir, "\n")
cat("These figures describe distributions and associations only.\n")
cat("They are not statistical tests and prove nothing on their own.\n")
