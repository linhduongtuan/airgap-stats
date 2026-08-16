# DR Workflow - Stage B2 (opt-in): correlated synthetic dataset generation
#
# Runs LOCALLY in RStudio. Base R only -- eigen(), chol(), qnorm(), pnorm(),
# and quantile() are all in the `stats`/`base` packages already loaded by
# default, no install.packages() needed. Python equivalent:
# py-scripts/synthesize_data_correlated.py (this file mirrors it exactly,
# including its comments where the reasoning is identical).
#
# WHY THIS SCRIPT EXISTS
# synthesize_data.R generates every column *independently* -- by design, so
# no real relationship between variables can ever leak into the synthetic
# file. The cost: an AI agent's code can only be checked for "does it run"
# on that file, never "does the model actually converge under realistic
# correlation" -- which is exactly why every SEM/logistic script in this
# pack documents that non-convergence or degenerate fit indices on the
# default synthetic data are *expected*, not a bug.
#
# This script trades a little of that safety margin for a much more useful
# test bed: it preserves the *approximate pairwise correlation structure*
# of the real data (via a Gaussian copula) while still generating every
# row from scratch -- no real row is ever copied, ever. Use it when you
# want to verify a regression/SEM script actually converges before
# touching real data, not just that it runs.
#
# PRIVACY DESIGN (same contract as synthesize_data.R, extended)
# - Every value is freshly generated. No real row is ever copied.
# - `data` (the real data.frame) is REQUIRED here -- unlike the independent
#   synthesizer, there is no correlation structure to preserve without it.
# - The correlation matrix, empirical quantiles, and level proportions used
#   to parameterize generation are computed LOCALLY, AT RUNTIME, and are
#   NEVER written to any file. Only the fabricated synthetic rows are
#   written -- identical in kind to how synthesize_data.R reads numeric
#   ranges locally without persisting them, just extended to a full
#   correlation matrix instead of per-column min/max.
# - REVIEW the synthetic output yourself before sharing it, same as the
#   pattern file. A correlated synthetic dataset reveals *more* about your
#   real data's structure than the independent one (e.g. "these two
#   variables move together") even though no individual value is real --
#   that is the deliberate trade this script makes. Prefer
#   synthesize_data.R's default independent synthesis unless you
#   specifically need the AI agent to validate model convergence.

# Self-contained, like every other R script in this pack (no source()
# dependency on scripts/synthesize_data.R -- a copy already in a project's
# scripts/ folder may predate this file and lack these exact helper names,
# so duplicating the ~20 lines below is more robust than a cross-file
# dependency that could silently drift). Kept identical in behavior to
# synthesize_data.R's own get_levels()/gen_column()/inject_missing(),
# which are exposed as reusable top-level functions there for the same
# reason if you're editing both together.

get_levels <- function(s) {
  if (is.na(s) || s == "") character(0) else strsplit(s, "|", fixed = TRUE)[[1]]
}

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

inject_missing <- function(v, missing_pct, type, n) {
  if (!is.na(missing_pct) && missing_pct > 0 && type != "id_like") {
    n_miss <- min(n - 1, round(n * missing_pct / 100))
    if (n_miss > 0) v[sample(n, n_miss)] <- NA
  }
  v
}

CORRELATABLE_TYPES <- c("numeric", "integer", "integer_scale", "binary")

# Clip negative eigenvalues and renormalize to unit diagonal -- a small,
# standard fix for a correlation matrix that drifted slightly off
# positive-semi-definite due to pairwise-complete-observations deletion.
nearest_psd_correlation <- function(r, eps = 1e-8) {
  eig <- eigen(r, symmetric = TRUE)
  eigvals_clipped <- pmax(eig$values, eps)
  r_psd <- eig$vectors %*% diag(eigvals_clipped, nrow = length(eigvals_clipped)) %*% t(eig$vectors)
  d <- sqrt(diag(r_psd))
  r_psd <- r_psd / outer(d, d)
  diag(r_psd) <- 1.0
  r_psd
}

# A numeric, rank-correlatable version of a column. Already-numeric columns
# pass through unchanged; a binary/ordinal column stored as strings (e.g.
# "M"/"F", "Nữ"/"Nam") is rank-encoded by sorted label order so Spearman
# correlation (which only needs ranks) is still well-defined. This encoding
# is derived from the real data locally and is never written anywhere.
numeric_proxy <- function(col) {
  if (is.numeric(col)) return(col)
  f <- factor(col)
  levels(f) <- sort(levels(f))
  as.numeric(factor(col, levels = sort(unique(as.character(col)))))
}

# Spearman rank correlation among `cols`, computed locally, projected to
# the nearest valid (positive-semi-definite) correlation matrix. Never
# written to any file by this function -- callers must not persist it.
local_correlation_matrix <- function(data, cols) {
  numeric_df <- as.data.frame(lapply(cols, function(c) numeric_proxy(data[[c]])))
  names(numeric_df) <- cols
  r <- suppressWarnings(cor(numeric_df, method = "spearman", use = "pairwise.complete.obs"))
  r[is.na(r)] <- 0
  diag(r) <- 1.0
  nearest_psd_correlation(r)
}

# n x p matrix of Gaussian-copula uniform(0,1) variates with rank
# correlation approximately `corr`.
copula_uniforms <- function(n, corr) {
  p <- nrow(corr)
  L <- tryCatch(t(chol(corr)), error = function(e) {
    # Should not happen after nearest_psd_correlation, but fall back to an
    # eigen-decomposition square root just in case.
    eig <- eigen(corr, symmetric = TRUE)
    eig$vectors %*% diag(sqrt(pmax(eig$values, 0)), nrow = p)
  })
  z <- matrix(rnorm(n * p), nrow = n, ncol = p) %*% t(L)
  pnorm(z)
}

# Inverse-transform one column of copula uniforms through the variable's
# empirical marginal (computed locally from `real_col`, never persisted).
map_uniform_to_marginal <- function(u, col_type, real_col, levs) {
  real_col <- real_col[!is.na(real_col)]

  if (col_type == "numeric") {
    return(round(quantile(as.numeric(real_col), probs = u, names = FALSE, type = 7), 2))
  }

  if (col_type == "integer") {
    return(as.integer(round(quantile(as.numeric(real_col), probs = u, names = FALSE, type = 7))))
  }

  if (col_type %in% c("integer_scale", "binary")) {
    # Ordinal/binary: map through the LOCAL empirical level proportions
    # (never written to file), via cumulative thresholds -- the same idea
    # as an ordinal probit/copula threshold model.
    vals <- if (length(levs) > 0) levs else sort(unique(as.character(real_col)))
    counts <- table(factor(as.character(real_col), levels = vals))
    probs <- as.numeric(counts)
    if (sum(probs) <= 0) probs <- rep(1, length(vals))
    probs <- probs / sum(probs)
    cum <- cumsum(probs)
    idx <- pmin(findInterval(u, cum, left.open = FALSE) + 1L, length(vals))
    picked <- vals[idx]
    if (col_type == "binary") {
      as_num <- suppressWarnings(as.numeric(picked))
      if (!anyNA(as_num)) return(as_num)
      return(picked)
    }
    as_int <- suppressWarnings(as.integer(picked))
    if (!anyNA(as_int)) return(as_int)
    return(picked)
  }

  stop("map_uniform_to_marginal does not support column type: ", col_type)
}

synthesize_correlated <- function(pattern_csv = "dataset_pattern.csv",
                                  data = NULL,
                                  output_csv = "synthetic_dataset_correlated.csv",
                                  n = 200,
                                  seed = 2026) {
  if (is.null(data)) {
    stop("synthesize_correlated requires `data` (the real data.frame, used only ",
         "locally at runtime) -- there is no correlation structure to preserve without it. ",
         "Use synthesize_data.R's independent synthesizer if you don't have local access ",
         "to the real data right now.")
  }
  if (!file.exists(pattern_csv)) stop("Pattern file not found: ", pattern_csv)
  if (!is.numeric(n) || length(n) != 1 || is.na(n) || n < 10) stop("`n` must be a single number >= 10.")

  pat <- utils::read.csv(pattern_csv, stringsAsFactors = FALSE, fileEncoding = "UTF-8")
  needed <- c("variable", "type", "levels", "missing_pct")
  if (!all(needed %in% names(pat))) stop("Pattern file must contain columns: ", paste(needed, collapse = ", "))

  set.seed(seed)

  correlatable <- Filter(function(nm) {
    row <- pat[pat$variable == nm, ]
    nrow(row) == 1 && row$type[1] %in% CORRELATABLE_TYPES && nm %in% names(data)
  }, pat$variable)
  # A constant column breaks cor() -- drop columns with < 2 unique non-NA values.
  correlatable <- Filter(function(nm) length(unique(stats::na.omit(data[[nm]]))) > 1, correlatable)

  out <- list()
  actually_correlated <- character(0)

  if (length(correlatable) >= 2) {
    actually_correlated <- correlatable
    corr <- local_correlation_matrix(data, correlatable)  # local only; never written
    u <- copula_uniforms(n, corr)  # n x length(correlatable)
    for (j in seq_along(correlatable)) {
      nm <- correlatable[j]
      row <- pat[pat$variable == nm, ][1, ]
      col_type <- row$type
      levs <- get_levels(row$levels)
      v <- map_uniform_to_marginal(u[, j], col_type, data[[nm]], levs)
      out[[nm]] <- inject_missing(v, row$missing_pct, col_type, n)
    }
  } else if (length(correlatable) == 1) {
    cat(sprintf("Only one correlatable column (%s); nothing to correlate it with. ", correlatable[1]))
    cat("Falling back to independent generation for it.\n")
  }

  # Every other column (categorical with >2 levels, id_like, date,
  # unsupported, or a lone correlatable column) -- same independent
  # generation as synthesize_data.R.
  for (i in seq_len(nrow(pat))) {
    nm <- pat$variable[i]
    if (nm %in% names(out)) next
    col_type <- pat$type[i]
    levs <- get_levels(pat$levels[i])
    v <- gen_column(col_type, levs, nm, n, data)
    if (is.null(v)) next
    out[[nm]] <- inject_missing(v, pat$missing_pct[i], col_type, n)
  }

  synthetic <- as.data.frame(out, check.names = FALSE, stringsAsFactors = FALSE)
  utils::write.csv(synthetic, output_csv, row.names = FALSE, na = "", fileEncoding = "UTF-8")

  cat(sprintf("\n=== correlated synthetic dataset written to: %s ===\n",
              normalizePath(output_csv, winslash = "/", mustWork = FALSE)))
  cat("Rows:", nrow(synthetic), "| Columns:", ncol(synthetic), "\n")
  cat(sprintf("Correlation-preserving columns (%d): %s\n", length(actually_correlated),
              if (length(actually_correlated) > 0) paste(actually_correlated, collapse = ", ") else "none"))
  cat("All values are simulated. No real row was copied.\n")
  cat("This file preserves approximate pairwise correlations from your real data -- ")
  cat("review it yourself before sharing, the same as the pattern file, and prefer ")
  cat("the independent synthesizer (synthesize_data.R) unless you specifically need ")
  cat("convergence-testing fidelity.\n\n")

  invisible(synthetic)
}
