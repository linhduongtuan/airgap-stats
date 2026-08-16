# DR Workflow - Stage B/C: synthetic dataset generation
#
# Runs LOCALLY in RStudio. Base R only, no packages.
#
# Purpose:
# Generate a fully synthetic dataset from a reviewed dataset_pattern.csv.
# The synthetic dataset exists only so that AI-generated analysis code can be
# tested for "does it run", then re-run unchanged on the real data locally.
#
# Privacy design:
# - Every value is freshly generated. No real row is ever copied.
# - Sample size `n` is chosen by you and is unrelated to the real n.
# - If `data` (the real dataset) is supplied, numeric ranges are read from it
#   AT RUNTIME, LOCALLY, only to make simulated numbers plausible. Those
#   ranges are never written into any shared file. If `data` is NULL,
#   generic default ranges are used instead.
# - Columns are simulated independently: no real correlation structure is
#   reproduced, so results computed on synthetic data are meaningless by
#   design. Only "the code runs" matters here.

# --- Reusable helpers (also used by synthesize_correlated.R for its
# non-correlatable-column fallback -- source() this file to reuse them
# rather than re-deriving the same per-type generation rules twice). ---

get_levels <- function(s) {
  if (is.na(s) || s == "") character(0) else strsplit(s, "|", fixed = TRUE)[[1]]
}

# One column's worth of independently-generated synthetic values for a
# single pattern-file row. `data` (optional) is read locally only to pick
# a plausible numeric/date range; never persisted. Returns NULL for an
# unsupported type (caller should skip that column).
gen_column <- function(type, levs, nm, n, data = NULL) {
  local_range <- function(default_lo, default_hi) {
    if (!is.null(data) && nm %in% names(data) && is.numeric(data[[nm]]) &&
        any(!is.na(data[[nm]]))) {
      range(data[[nm]], na.rm = TRUE)
    } else {
      c(default_lo, default_hi)
    }
  }
  switch(
    type,
    id_like = paste0("id_", seq_len(n)),
    binary = {
      vals <- if (length(levs) > 0) levs else c("0", "1")
      picked <- sample(vals, n, replace = TRUE)
      if (!anyNA(suppressWarnings(as.numeric(vals)))) as.numeric(picked) else picked
    },
    categorical = {
      if (length(levs) == 0) stop("Categorical variable without levels: ", nm)
      sample(levs, n, replace = TRUE)
    },
    integer_scale = {
      vals <- suppressWarnings(as.numeric(levs))
      if (anyNA(vals)) stop("integer_scale levels must be numeric for: ", nm)
      sample(vals, n, replace = TRUE)
    },
    integer = {
      rng <- round(local_range(0, 100))
      sample(seq(rng[1], rng[2]), n, replace = TRUE)
    },
    numeric = {
      rng <- local_range(0, 100)
      round(stats::runif(n, rng[1], rng[2]), 2)
    },
    date = {
      rng <- if (!is.null(data) && nm %in% names(data) &&
                 inherits(data[[nm]], "Date") && any(!is.na(data[[nm]]))) {
        range(data[[nm]], na.rm = TRUE)
      } else {
        as.Date(c("2020-01-01", "2024-12-31"))
      }
      sample(seq(rng[1], rng[2], by = "day"), n, replace = TRUE)
    },
    NULL # unsupported types are skipped
  )
}

# Inject missingness into an already-generated column vector, in place of
# `n * missing_pct/100` random positions (never the id_like column).
inject_missing <- function(v, missing_pct, type, n) {
  if (!is.na(missing_pct) && missing_pct > 0 && type != "id_like") {
    n_miss <- min(n - 1, round(n * missing_pct / 100))
    if (n_miss > 0) v[sample(n, n_miss)] <- NA
  }
  v
}

synthesize_data <- function(pattern_csv = "dataset_pattern.csv",
                            data = NULL,
                            output_csv = "synthetic_dataset.csv",
                            n = 200,
                            seed = 2026) {
  if (!file.exists(pattern_csv)) stop("Pattern file not found: ", pattern_csv)
  if (!is.numeric(n) || length(n) != 1 || is.na(n) || n < 10) {
    stop("`n` must be a single number >= 10.")
  }
  pat <- utils::read.csv(pattern_csv, stringsAsFactors = FALSE, fileEncoding = "UTF-8")
  needed <- c("variable", "type", "levels", "missing_pct")
  if (!all(needed %in% names(pat))) {
    stop("Pattern file must contain columns: ", paste(needed, collapse = ", "))
  }
  set.seed(seed)

  out <- list()
  for (i in seq_len(nrow(pat))) {
    nm <- pat$variable[i]
    type <- pat$type[i]
    levs <- get_levels(pat$levels[i])

    v <- gen_column(type, levs, nm, n, data)
    if (is.null(v)) next

    out[[nm]] <- inject_missing(v, pat$missing_pct[i], type, n)
  }

  synthetic <- as.data.frame(out, check.names = FALSE, stringsAsFactors = FALSE)
  utils::write.csv(synthetic, output_csv, row.names = FALSE, na = "", fileEncoding = "UTF-8")

  cat("\n=== synthetic dataset written to:",
      normalizePath(output_csv, winslash = "/", mustWork = FALSE), "===\n")
  cat("Rows:", nrow(synthetic), "| Columns:", ncol(synthetic), "\n")
  cat("All values are simulated. No real row was copied.\n")
  cat("This file is safe to share with the AI agent (levels come from the\n")
  cat("pattern file you already reviewed).\n\n")

  invisible(synthetic)
}
