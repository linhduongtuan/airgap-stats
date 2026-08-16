# DR Stage D2: Descriptive analysis / Table 1  (example-clinical, medical track)
# Base R only. Run from the project folder.
#
# Group-comparison tests (Phase 1 of the statistical-methods roadmap): each
# variable's test is auto-selected at runtime -- see plans/sap.md Section G.
# Python equivalent: tools/diagnostics/group_tests.py (kept numerically in
# parity; cross-validated F/chi2/p-values match).

# === USER SETTINGS ==========================================================
input_csv  <- "data_synthetic/synthetic_dataset.csv"
output_dir <- "outputs_synthetic"
# To run on REAL data in RStudio, change the two lines above to:
# input_csv  <- file.choose()   # cua so chon file se hien ra: chon file du lieu that cua ban
# output_dir <- "results_real"
# ============================================================================

dat <- read.csv(input_csv, stringsAsFactors = FALSE, fileEncoding = "UTF-8")

group_var        <- "treatment"
continuous_vars  <- c("age", "bmi", "egfr", "hba1c", "crp")
categorical_vars <- c("sex", "diabetes", "hypertension", "smoking", "mortality_30day")

all_vars <- c(group_var, continuous_vars, categorical_vars)
missing_cols <- setdiff(all_vars, names(dat))
if (length(missing_cols) > 0) stop("Missing columns: ", paste(missing_cols, collapse = ", "))

groups <- sort(unique(dat[[group_var]][!is.na(dat[[group_var]])]))

summ_cont <- function(x) sprintf("%.1f (%.1f)", mean(x, na.rm = TRUE), sd(x, na.rm = TRUE))
summ_cat_level <- function(x, lvl) {
  x <- x[!is.na(x)]
  sprintf("%d (%.1f%%)", sum(x == lvl), 100 * mean(x == lvl))
}

# --- Phase 1: group-comparison test helpers -------------------------------

shapiro_normal <- function(x) {
  x <- x[!is.na(x)]
  if (length(x) < 3 || length(unique(x)) < 2) return(list(normal = FALSE, p = NA_real_))
  p <- tryCatch(shapiro.test(x)$p.value, error = function(e) NA_real_)
  list(normal = !is.na(p) && p >= 0.05, p = p)
}

compare_continuous <- function(d, var, group_var) {
  sub <- d[!is.na(d[[var]]) & !is.na(d[[group_var]]), ]
  gs <- sort(unique(sub[[group_var]]))
  k <- length(gs)
  if (k < 2) return(list(test = "none", p_value = NA_real_,
                         reason = "fewer than 2 groups with data -- no test possible"))

  samples <- lapply(gs, function(g) sub[[var]][sub[[group_var]] == g])
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

rows <- list()
test_log <- character()
add_row <- function(char, level, overall, per_group, test = "", p_value = NA_real_) {
  rows[[length(rows) + 1]] <<- data.frame(
    characteristic = char, level = level, Overall = overall,
    setNames(as.list(per_group), paste0(group_var, "=", groups)),
    test = test, p_value = p_value,
    check.names = FALSE, stringsAsFactors = FALSE)
}

for (v in continuous_vars) {
  result <- compare_continuous(dat, v, group_var)
  test_log <- c(test_log, sprintf("%s: %s", v, result$reason))
  add_row(v, "mean (SD)", summ_cont(dat[[v]]),
          vapply(groups, function(g) summ_cont(dat[[v]][dat[[group_var]] == g]), character(1)),
          result$test, result$p_value)
}
for (v in categorical_vars) {
  result <- compare_categorical(dat, v, group_var)
  test_log <- c(test_log, sprintf("%s: %s", v, result$reason))
  first <- TRUE
  for (lvl in sort(unique(dat[[v]][!is.na(dat[[v]])]))) {
    add_row(v, as.character(lvl), summ_cat_level(dat[[v]], lvl),
            vapply(groups, function(g) summ_cat_level(dat[[v]][dat[[group_var]] == g], lvl), character(1)),
            if (first) result$test else "", if (first) result$p_value else NA_real_)
    first <- FALSE
  }
}

table1 <- do.call(rbind, rows)
dir.create(output_dir, showWarnings = FALSE)
write.csv(table1, file.path(output_dir, "table1.csv"), row.names = FALSE, fileEncoding = "UTF-8")
cat("N =", nrow(dat), "| Table 1 written to", file.path(output_dir, "table1.csv"), "\n\n")
print(table1, row.names = FALSE)

cat("\nGroup comparison tests (auto-selected at runtime, by", group_var, "):\n")
for (line in test_log) cat("  -", line, "\n")
cat("\nNOTE: p-values on this synthetic dataset are meaningless by design\n")
cat("(columns are simulated independently). Only the branch selection logic\n")
cat("is being verified here.\n")
