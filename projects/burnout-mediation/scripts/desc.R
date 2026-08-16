# DR Stage D2: Descriptive analysis / Table 1
# Base R only. Run from the project folder.
#
# Group-comparison tests (Phase 1 of the statistical-methods roadmap): each
# variable's test is auto-selected at runtime -- see plans/sap.md Section G.
# compare_continuous also covers the ordinal (Likert) variable here: it
# branches on Shapiro-Wilk, and a bounded discrete Likert item almost always
# fails normality, correctly routing to Mann-Whitney U -- the standard test
# for ordinal data anyway. Python equivalent: tools/diagnostics/group_tests.py
# (kept numerically in parity).

# === USER SETTINGS ==========================================================
# Runs on the synthetic dataset as delivered:
input_csv  <- "data_synthetic/synthetic_dataset.csv"
output_dir <- "outputs_synthetic"
# To run on REAL data in RStudio, comment the two lines above and uncomment these:
# input_csv  <- file.choose()   # a file-picker opens: select your real dataset
# output_dir <- "results_real"
# ============================================================================

dat <- read.csv(input_csv, stringsAsFactors = FALSE, fileEncoding = "UTF-8")

# --- Variables ---
group_var       <- "turnover_intent"
continuous_vars <- c("age", "tenure_years", "job_satisfaction", "burnout_score")
categorical_vars <- c("gender", "education")
ordinal_vars    <- c("wlb", "js_q1", "js_q2", "js_q3", "js_q4", "js_q5",
                     "bo_q1", "bo_q2", "bo_q3", "bo_q4", "bo_q5")

all_vars <- c(continuous_vars, categorical_vars, ordinal_vars, group_var)
missing_cols <- all_vars[!all_vars %in% names(dat)]
if (length(missing_cols) > 0) {
  stop("Missing columns in data: ", paste(missing_cols, collapse = ", "))
}

# --- Helper: summarize continuous ---
summ_cont <- function(x) {
  m <- mean(x, na.rm = TRUE)
  s <- sd(x, na.rm = TRUE)
  sprintf("%.1f (%.1f)", m, s)
}

# --- Helper: summarize ordinal as median (IQR) ---
summ_ord <- function(x) {
  md <- median(x, na.rm = TRUE)
  q1 <- quantile(x, 0.25, na.rm = TRUE)
  q3 <- quantile(x, 0.75, na.rm = TRUE)
  sprintf("%.0f (%.0f-%.0f)", md, q1, q3)
}

# --- Helper: summarize categorical ---
summ_cat <- function(x) {
  tab <- table(x, useNA = "no")
  data.frame(level = names(tab),
             value = sprintf("%d (%.1f%%)", as.integer(tab),
                             100 * as.integer(tab) / sum(tab)),
             stringsAsFactors = FALSE)
}

# --- Helper: get group N label ---
group_N <- function(d, gv) {
  tab <- table(d[[gv]], useNA = "no")
  paste0(names(tab), " (N=", as.integer(tab), ")")
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

# --- Build Table 1 ---
groups <- sort(unique(dat[[group_var]]))
overall_N <- nrow(dat)
group_labels <- group_N(dat, group_var)

table1 <- data.frame(characteristic = character(),
                     level = character(),
                     Overall = character(),
                     stringsAsFactors = FALSE)
for (g in groups) {
  table1[[as.character(g)]] <- character()
}
table1[["test"]] <- character()
table1[["p_value"]] <- numeric()

test_log <- character()

add_continuous <- function(v, label) {
  result <- compare_continuous(dat, v, group_var)
  test_log <<- c(test_log, sprintf("%s: %s", v, result$reason))
  overall <- summ_cont(dat[[v]])
  by_group <- sapply(groups, function(g) summ_cont(dat[[v]][dat[[group_var]] == g]))
  row <- data.frame(characteristic = label, level = "-",
                    Overall = overall, stringsAsFactors = FALSE)
  for (i in seq_along(groups)) row[[as.character(groups[i])]] <- by_group[i]
  row[["test"]] <- result$test
  row[["p_value"]] <- result$p_value
  table1 <<- rbind(table1, row)
}

add_ordinal <- function(v, label) {
  result <- compare_continuous(dat, v, group_var)
  test_log <<- c(test_log, sprintf("%s: %s", v, result$reason))
  overall <- summ_ord(dat[[v]])
  by_group <- sapply(groups, function(g) summ_ord(dat[[v]][dat[[group_var]] == g]))
  row <- data.frame(characteristic = label, level = "-",
                    Overall = overall, stringsAsFactors = FALSE)
  for (i in seq_along(groups)) row[[as.character(groups[i])]] <- by_group[i]
  row[["test"]] <- result$test
  row[["p_value"]] <- result$p_value
  table1 <<- rbind(table1, row)
}

add_categorical <- function(v, label) {
  overall_tab <- summ_cat(dat[[v]])
  if (nrow(overall_tab) == 0) return()
  result <- compare_categorical(dat, v, group_var)
  test_log <<- c(test_log, sprintf("%s: %s", v, result$reason))
  first <- TRUE
  for (i in seq_len(nrow(overall_tab))) {
    lev <- overall_tab$level[i]
    overall_val <- overall_tab$value[i]
    by_group <- sapply(groups, function(g) {
      sub <- dat[[v]][dat[[group_var]] == g]
      sub_tab <- summ_cat(sub)
      match_idx <- which(sub_tab$level == lev)
      if (length(match_idx) > 0) sub_tab$value[match_idx[1]] else "0 (0.0%)"
    })
    row <- data.frame(
      characteristic = if (first) label else "",
      level = lev,
      Overall = overall_val,
      stringsAsFactors = FALSE
    )
    for (j in seq_along(groups)) row[[as.character(groups[j])]] <- by_group[j]
    row[["test"]] <- if (first) result$test else ""
    row[["p_value"]] <- if (first) result$p_value else NA_real_
    table1 <<- rbind(table1, row)
    first <- FALSE
  }
}

add_continuous("age", "Age, years")
add_continuous("tenure_years", "Tenure, years")
add_continuous("job_satisfaction", "Job satisfaction score")
add_continuous("burnout_score", "Burnout score")
add_ordinal("wlb", "Work-life balance")
add_categorical("gender", "Gender")
add_categorical("education", "Education")

names(table1)[names(table1) == "Overall"] <- paste0("Overall (N=", overall_N, ")")
names(table1)[names(table1) %in% as.character(groups)] <- group_labels

# --- Add footnote ---
footnote <- paste(
  "Continuous variables are presented as mean (SD);",
  "ordinal/Likert variables as median (IQR);",
  "categorical variables as n (%)."
)

# --- Save ---
dir.create(output_dir, showWarnings = FALSE)
write.csv(table1, file.path(output_dir, "table1.csv"),
          row.names = FALSE, fileEncoding = "UTF-8")
cat("Table 1 written to", file.path(output_dir, "table1.csv"), "\n\n")
print(table1, row.names = FALSE)
cat("\n", footnote, "\n")

cat("\nGroup comparison tests (auto-selected at runtime, by", group_var, "):\n")
for (line in test_log) cat("  -", line, "\n")
cat("\nNOTE: p-values on this synthetic dataset are meaningless by design\n")
cat("(columns are simulated independently). Only the branch selection logic\n")
cat("is being verified here.\n")

# --- Missing summary ---
miss_rows <- data.frame(variable = all_vars,
                        n_missing = sapply(dat[all_vars], function(x) sum(is.na(x))),
                        pct_missing = sapply(dat[all_vars], function(x) round(100 * mean(is.na(x)), 1)),
                        stringsAsFactors = FALSE)
write.csv(miss_rows, file.path(output_dir, "missing_summary.csv"),
          row.names = FALSE, fileEncoding = "UTF-8")
cat("\nMissing summary written to", file.path(output_dir, "missing_summary.csv"), "\n")
