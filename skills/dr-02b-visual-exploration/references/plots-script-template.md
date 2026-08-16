# plots.R Script Template

Structure for `scripts/plots.R`. Base R graphics only. Two worked examples exist in the repo:

- Medical: `projects/crp-mortality/scripts/plots.R`
- SEM: `projects/burnout-mediation/scripts/plots.R`

## 1. Header and privacy note

Open with a short comment block stating that the figures are row-level, that real-run figures land outside the repo, and that figures from real data must never be pasted into an AI chat.

## 2. Settings block

Delivered in **synthetic mode**, so the user can open the file and hit Run without editing anything:

```r
# === USER SETTINGS ==========================================================
# Runs on the synthetic dataset as delivered:
input_csv  <- "data_synthetic/synthetic_dataset.csv"
output_dir <- "outputs_synthetic/figures"
# To run on REAL data in RStudio, comment the two lines above and uncomment these:
# input_csv  <- file.choose()                                  # select your real dataset
# output_dir <- file.path(dirname(input_csv), "dr_figures")    # figures stay outside the repo
# ============================================================================

show_individual_points <- TRUE
```

Switching to real data must be a one-line comment swap, never an edit the user has to make before their first run.

```r
dat <- read.csv(input_csv, stringsAsFactors = FALSE, fileEncoding = "UTF-8")
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)
```

## 3. Variable block and guards

Declare variables from `analysis_plan.yaml`, `stopifnot` they exist, then drop columns with no variation — a constant column makes `cor()` return `NA` and produces an unreadable figure:

```r
usable <- numeric_vars[sapply(numeric_vars, function(v) {
  x <- dat[[v]][!is.na(dat[[v]])]
  length(unique(x)) > 1
})]
stopifnot(length(usable) >= 2)
```

Report anything dropped with `cat()`.

## 4. Figure 1 — correlation heatmap

```r
M <- cor(dat[usable], use = "pairwise.complete.obs")
p <- ncol(M)
pal <- colorRampPalette(c("#2166AC", "#4393C3", "#F7F7F7", "#D6604D", "#B2182B"))(201)

png(file.path(output_dir, "fig1_correlation_heatmap.png"),
    width = 1500, height = 1250, res = 150, type = "cairo")
layout(matrix(c(1, 2), nrow = 1), widths = c(6, 1))
par(mar = c(7, 7, 4, 1))
```

**Orientation.** `image()` draws the y axis bottom-up, so a raw `image(M)` prints the matrix upside down. Pass `M[, p:1]` and label the y axis with `rev(colnames(M))`; cell `M[i, j]` then sits at `(i, p + 1 - j)`:

```r
image(1:p, 1:p, M[, p:1], zlim = c(-1, 1), col = pal, axes = FALSE, xlab = "", ylab = "")
axis(1, at = 1:p, labels = colnames(M), las = 2, cex.axis = 0.9, tick = FALSE)
axis(2, at = 1:p, labels = rev(colnames(M)), las = 1, cex.axis = 0.9, tick = FALSE)
abline(h = 0.5 + 0:p, v = 0.5 + 0:p, col = "white", lwd = 2)

for (i in 1:p) for (j in 1:p) {
  r <- M[i, j]
  text(i, p + 1 - j, sprintf("%.2f", r), cex = 0.75,
       col = if (abs(r) > 0.55) "white" else "grey15")
}
```

Always fix `zlim = c(-1, 1)` so white is exactly zero and colours mean the same thing across projects.

Colour bar in the second layout panel:

```r
par(mar = c(7, 1, 4, 4))
bar_vals <- seq(-1, 1, length.out = 201)
image(1, bar_vals, matrix(bar_vals, nrow = 1), col = pal, zlim = c(-1, 1),
      axes = FALSE, xlab = "", ylab = "")
axis(4, at = seq(-1, 1, 0.5), las = 1, cex.axis = 0.85)
box(col = "grey70")
dev.off()
```

**SEM variant.** Order items by construct, then outline each block on the diagonal so the expected factor structure is visible:

```r
bounds <- cumsum(rle(as.vector(item_construct))$lengths)
starts <- c(1, head(bounds, -1) + 1)
for (b in seq_along(bounds)) {
  a <- starts[b]; z <- bounds[b]
  rect(a - 0.5, p + 1 - z - 0.5, z + 0.5, p + 1 - a + 0.5, border = "grey10", lwd = 3)
}
```

## 5. Figure 2 — boxplot series

Apply the small-cell guard before drawing:

```r
g_n <- sapply(g_vals, function(v) sum(g == v, na.rm = TRUE))
if (any(g_n < 5)) { cat("WARNING: group with n < 5; Figure 2 skipped.\n") }
```

Medical variant: one panel per numeric variable, split by the grouping variable.

```r
par(mfrow = c(n_row, n_col), mar = c(3.5, 4, 3.5, 1),
    oma = c(0, 0, 3.5, 0), mgp = c(2.4, 0.7, 0))

boxplot(groups, col = box_cols, border = "grey25",
        outline = show_individual_points, outpch = 21, outcex = 0.7,
        outbg = "grey60", main = v, cex.main = 1.15, boxwex = 0.55)

if (show_individual_points) {
  for (k in seq_along(groups)) {
    y <- groups[[k]][!is.na(groups[[k]])]
    points(jitter(rep(k, length(y)), amount = 0.13), y,
           pch = 16, cex = 0.45, col = adjustcolor("grey20", alpha.f = 0.35))
  }
}
```

Print the per-group n with `mtext()` above each panel.

SEM variant: one box per item in a single panel, filled by construct, with dashed separators between constructs and a legend. Jitter both x and y, since Likert values are discrete and would otherwise stack into solid lines.

## 6. Closing output

`cat()` the files written and a one-line reminder that figures describe distributions only and are not tests.

For the SEM track add the honest note: on synthetic data the items are simulated independently, so **no block structure will appear**. That is expected and proves only that the code runs. The blocks appear on real data.

## Verification checklist

1. `Rscript scripts/plots.R` from the project folder, exit code 0. If you have no R, hand this command to the user instead and say plainly that you did not run it.
2. Look at each PNG: diagonal is 1.00, off-diagonal is symmetric, labels are not clipped, text is legible. Without R, put this checklist in the notes file for the user.
3. Leave the settings block in synthetic mode.
