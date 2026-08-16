# DR Stage D2: Descriptive analysis / Table 1
# Base R only. Run from the project folder.
#
# Group-comparison tests (Phase 1 of the statistical-methods roadmap): each
# variable's test is auto-selected at runtime -- Shapiro-Wilk decides
# t-test/Welch-ANOVA vs. Mann-Whitney/Kruskal-Wallis for continuous
# variables, and the minimum expected cell count decides chi-squared vs.
# Fisher's exact for categorical ones. Nobody has seen the real data's
# distribution, so this branches at runtime, never fixed in advance (see
# plans/sap.md Section G). Python equivalent: tools/diagnostics/group_tests.py
# -- kept numerically in parity (cross-validated F/chi2/p-values match).

# === USER SETTINGS ==========================================================
# Runs on the synthetic dataset as delivered:
input_csv  <- "data_synthetic/synthetic_dataset.csv"
output_dir <- "outputs_synthetic"
# To run on REAL data in RStudio, comment the two lines above and uncomment these:
# input_csv  <- file.choose()   # a file-picker opens: select your real dataset
# output_dir <- "results_real"
# ============================================================================

dat <- read.csv(input_csv, stringsAsFactors = FALSE, fileEncoding = "UTF-8")

# --- Variables from plans/analysis_plan.yaml ---
group_var       <- "mortality_30day"
continuous_vars <- c("age", "bmi", "sbp", "egfr", "hba1c", "crp")
categorical_vars <- c("sex", "treatment", "diabetes", "hypertension", "smoking", "complication")

stopifnot(all(c(continuous_vars, categorical_vars, group_var) %in% names(dat)))

# --- Helper: summarize one continuous variable ---
summ_cont <- function(x) {
  sprintf("%.1f (%.1f)", mean(x, na.rm = TRUE), sd(x, na.rm = TRUE))
}

# --- Phase 1: group-comparison test helpers -------------------------------

# Shapiro-Wilk: too few points or a constant sample can't be tested
# meaningfully -- treated as "not confirmed normal" (the conservative
# branch), not as an error.
shapiro_normal <- function(x) {
  x <- x[!is.na(x)]
  if (length(x) < 3 || length(unique(x)) < 2) return(list(normal = FALSE, p = NA_real_))
  p <- tryCatch(shapiro.test(x)$p.value, error = function(e) NA_real_)
  list(normal = !is.na(p) && p >= 0.05, p = p)
}

# Compare a continuous variable across the levels of group_var.
# 2 groups: Welch's t-test (normal) / Mann-Whitney U (not normal).
# >2 groups: Welch's one-way ANOVA (normal) / Kruskal-Wallis (not normal).
# oneway.test()'s default (var.equal = FALSE) already implements Welch
# (1951), matching tools/diagnostics/group_tests.py's hand-rolled Welch-ANOVA
# (cross-validated: identical F-statistic and p-value on the same data).
compare_continuous <- function(d, var, group_var) {
  sub <- d[!is.na(d[[var]]) & !is.na(d[[group_var]]), ]
  groups <- sort(unique(sub[[group_var]]))
  k <- length(groups)
  if (k < 2) return(list(test = "none", p_value = NA_real_,
                         reason = "fewer than 2 groups with data -- no test possible"))

  samples <- lapply(groups, function(g) sub[[var]][sub[[group_var]] == g])
  all_normal <- all(sapply(samples, function(s) shapiro_normal(s)$normal))

  if (k == 2) {
    if (all_normal) {
      res <- t.test(samples[[1]], samples[[2]])
      list(test = "welch_t_test", p_value = res$p.value,
           reason = "both groups pass Shapiro-Wilk (p>=0.05) -> two-sample t-test (Welch)")
    } else {
      res <- suppressWarnings(wilcox.test(samples[[1]], samples[[2]]))
      list(test = "mann_whitney_u", p_value = res$p.value,
           reason = "at least one group fails Shapiro-Wilk (p<0.05) -> Mann-Whitney U")
    }
  } else {
    if (all_normal) {
      res <- oneway.test(sub[[var]] ~ as.factor(sub[[group_var]]), var.equal = FALSE)
      list(test = "welch_anova", p_value = res$p.value,
           reason = sprintf("%d groups, all pass Shapiro-Wilk -> Welch's one-way ANOVA (unequal variances)", k))
    } else {
      res <- kruskal.test(sub[[var]], as.factor(sub[[group_var]]))
      list(test = "kruskal_wallis", p_value = res$p.value,
           reason = sprintf("%d groups, at least one fails Shapiro-Wilk -> Kruskal-Wallis", k))
    }
  }
}

# Compare a categorical variable across the levels of group_var.
# chi-squared if every expected cell count >= 5, else Fisher's exact
# (fisher.test handles r x c tables in R, not just 2x2).
compare_categorical <- function(d, var, group_var, min_expected = 5) {
  sub <- d[!is.na(d[[var]]) & !is.na(d[[group_var]]), ]
  tab <- table(sub[[var]], sub[[group_var]])
  if (nrow(tab) < 2 || ncol(tab) < 2) {
    return(list(test = "none", p_value = NA_real_,
                reason = "fewer than 2 levels on one side of the table -- no test possible"))
  }
  chi <- suppressWarnings(chisq.test(tab))
  min_exp <- min(chi$expected)
  if (min_exp >= min_expected) {
    list(test = "chi_squared", p_value = chi$p.value,
         reason = sprintf("min expected cell count %.1f >= %g -> chi-squared", min_exp, min_expected))
  } else {
    ft <- fisher.test(tab)
    list(test = "fisher_exact", p_value = ft$p.value,
         reason = sprintf("min expected cell count %.1f < %g -> Fisher's exact", min_exp, min_expected))
  }
}

# --- Build Table 1 ---
group_vals <- sort(unique(dat[[group_var]]))
group_labels <- paste0("Group_", group_vals)
# Maps label -> actual value for filtering
group_map <- setNames(as.list(group_vals), group_labels)

all_cols <- c("Overall", group_labels, "test", "p_value")

table1 <- data.frame(characteristic = character(),
                     level = character(),
                     stringsAsFactors = FALSE)
for (cname in all_cols) table1[[cname]] <- character()
table1[["p_value"]] <- numeric()

test_log <- character()

# --- N per group ---
n_row <- data.frame(characteristic = "N", level = "-", stringsAsFactors = FALSE)
n_row[["Overall"]] <- nrow(dat)
for (glab in group_labels) {
  n_row[[glab]] <- sum(dat[[group_var]] == group_map[[glab]], na.rm = TRUE)
}
n_row[["test"]] <- "-"
n_row[["p_value"]] <- NA_real_
table1 <- rbind(table1, n_row)

# --- Continuous variables ---
for (var in continuous_vars) {
  result <- compare_continuous(dat, var, group_var)
  test_log <- c(test_log, sprintf("%s: %s", var, result$reason))

  row <- data.frame(characteristic = var, level = "-", stringsAsFactors = FALSE)
  row[["Overall"]] <- if (sum(!is.na(dat[[var]])) > 0) summ_cont(dat[[var]]) else "NA"
  for (glab in group_labels) {
    idx <- dat[[group_var]] == group_map[[glab]]
    x <- dat[[var]][idx & !is.na(idx)]
    row[[glab]] <- if (sum(!is.na(x)) > 0) summ_cont(x) else "NA"
  }
  row[["test"]] <- result$test
  row[["p_value"]] <- result$p_value
  table1 <- rbind(table1, row)
}

# --- Categorical variables ---
for (var in categorical_vars) {
  result <- compare_categorical(dat, var, group_var)
  test_log <- c(test_log, sprintf("%s: %s", var, result$reason))

  levels_tab <- table(dat[[var]], useNA = "no")
  first <- TRUE
  for (lev in names(levels_tab)) {
    row <- data.frame(characteristic = var, level = lev, stringsAsFactors = FALSE)
    # Overall
    n_total <- sum(dat[[var]] == lev, na.rm = TRUE)
    total_n <- sum(!is.na(dat[[var]]))
    row[["Overall"]] <- sprintf("%d (%.1f%%)", n_total, 100 * n_total / max(total_n, 1))
    # Per group
    for (glab in group_labels) {
      idx <- dat[[group_var]] == group_map[[glab]]
      idx[is.na(idx)] <- FALSE
      grp_dat <- dat[[var]][idx]
      n_grp <- sum(grp_dat == lev, na.rm = TRUE)
      grp_total <- sum(!is.na(grp_dat))
      row[[glab]] <- sprintf("%d (%.1f%%)", n_grp, 100 * n_grp / max(grp_total, 1))
    }
    row[["test"]] <- if (first) result$test else ""
    row[["p_value"]] <- if (first) result$p_value else NA_real_
    first <- FALSE
    table1 <- rbind(table1, row)
  }
}

# --- Save outputs ---
dir.create(output_dir, showWarnings = FALSE)
write.csv(table1, file.path(output_dir, "table1.csv"),
          row.names = FALSE, fileEncoding = "UTF-8")
cat("Table 1 written to", file.path(output_dir, "table1.csv"), "\n")
print(table1, row.names = FALSE)

cat("\nGroup comparison tests (auto-selected at runtime, by", group_var, "):\n")
for (line in test_log) cat("  -", line, "\n")
cat("\nNOTE: p-values on this synthetic dataset are meaningless by design\n")
cat("(columns are simulated independently). Only the branch selection logic\n")
cat("is being verified here.\n")
