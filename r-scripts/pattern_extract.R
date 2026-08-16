# DR Workflow - Stage A: pattern extraction
#
# Runs LOCALLY in RStudio on the real dataset. Base R only, no packages.
#
# Purpose:
# Describe the STRUCTURE of a dataset (variable names, types, categorical
# levels, missingness) so an AI agent can later write analysis and synthesis
# code without ever seeing the real data.
#
# Privacy design:
# - This script uploads nothing. It only writes a local CSV file.
# - The pattern file contains NO row-level values, NO row counts,
#   NO means/medians/min/max, NO summary statistics of any kind.
# - Categorical level labels ARE included, because generated analysis code
#   needs exact labels (e.g. factor levels) to run on the real data.
#   Rare levels are masked as "Other" so uncommon (potentially identifying)
#   categories never appear in the pattern file.
# - REVIEW dataset_pattern.csv YOURSELF before sharing it with any AI.
#   If any level label is sensitive, edit or remove it first.

extract_pattern <- function(data,
                            output_csv = "dataset_pattern.csv",
                            max_levels = 15,
                            min_level_count = 5,
                            id_unique_ratio = 0.9) {
  if (!is.data.frame(data)) stop("`data` must be a data.frame or tibble.")
  data <- as.data.frame(data, stringsAsFactors = FALSE)
  if (nrow(data) == 0) stop("`data` has 0 rows.")
  if (any(names(data) == "")) stop("All columns must have non-empty names.")

  rows <- list()
  for (nm in names(data)) {
    x <- data[[nm]]
    miss_pct <- round(100 * mean(is.na(x)), 1)
    xs <- x[!is.na(x)]
    n_distinct <- length(unique(xs))
    type <- "unsupported"
    levels_str <- ""
    note <- ""

    if (inherits(x, "Date") || inherits(x, "POSIXt")) {
      type <- "date"
    } else if (is.logical(x)) {
      type <- "binary"
      levels_str <- "TRUE|FALSE"
    } else if (is.numeric(x)) {
      if (n_distinct <= 2 && all(xs %in% c(0, 1))) {
        type <- "binary"
        levels_str <- "0|1"
      } else if (length(xs) > 0 && all(xs == round(xs)) && n_distinct <= 10) {
        type <- "integer_scale"
        levels_str <- paste(sort(unique(xs)), collapse = "|")
        note <- "small set of integer values; possibly a Likert/score item"
      } else if (length(xs) > 0 && all(xs == round(xs))) {
        type <- "integer"
      } else {
        type <- "numeric"
      }
    } else if (is.character(x) || is.factor(x)) {
      ch <- as.character(xs)
      if (length(ch) > 0 && n_distinct / length(ch) >= id_unique_ratio) {
        type <- "id_like"
        note <- "high-cardinality; treated as identifier; levels not exported"
      } else {
        tab <- sort(table(ch), decreasing = TRUE)
        keep <- names(tab)[tab >= min_level_count]
        keep <- utils::head(keep, max_levels)
        if (length(keep) < length(tab)) {
          levels_str <- paste(c(keep, "Other"), collapse = "|")
          note <- "rare levels masked as Other"
        } else {
          levels_str <- paste(keep, collapse = "|")
        }
        type <- if (length(keep) <= 2 && length(keep) == length(tab)) "binary" else "categorical"
      }
    } else {
      note <- "unsupported column class; excluded from synthesis"
    }

    # n_distinct is exported only where it is a count of categories.
    # For id_like it would equal the real row count, and for continuous
    # variables it would bound the real n - both must stay unknown.
    n_distinct_out <- if (type %in% c("binary", "categorical", "integer_scale")) {
      n_distinct
    } else {
      NA_integer_
    }

    rows[[nm]] <- data.frame(
      variable = nm,
      type = type,
      levels = levels_str,
      n_distinct = n_distinct_out,
      missing_pct = miss_pct,
      note = note,
      stringsAsFactors = FALSE
    )
  }

  pattern <- do.call(rbind, rows)
  rownames(pattern) <- NULL
  utils::write.csv(pattern, output_csv, row.names = FALSE, fileEncoding = "UTF-8")

  cat("\n=== dataset_pattern written to:", normalizePath(output_csv, winslash = "/", mustWork = FALSE), "===\n\n")
  print(pattern)
  cat("\n--- REVIEW BEFORE SHARING WITH ANY AI ---\n")
  cat("1. No row counts, no statistics, no raw values are in this file.\n")
  cat("2. Check every entry in the `levels` column. If a label is sensitive\n")
  cat("   (rare disease, small clinic name, job title...), edit or remove it.\n")
  cat("3. Only after your review, give dataset_pattern.csv to the agent.\n\n")

  invisible(pattern)
}


source("r-scripts/pattern_extract.R")
original <- read.csv(file.choose())   # chọn file dữ liệu thật của bạn
extract_pattern(original, output_csv = "pattern/dataset_pattern.csv")



source("r-scripts/synthesize_data.R")
original <- read.csv(file.choose())   # chọn lại file dữ liệu thật
synthesize_data(
  pattern_csv = "pattern/dataset_pattern.csv",
  data = original,
  output_csv = "data_synthetic/synthetic_dataset.csv",
  n = 200,
  seed = 2026
)


# Mở RStudio, set working directory vào thư mục projects/crp-mortality/
source("r-scripts/desc.R")


# Set working directory vào thư mục projects/crp-mortality/
source("scripts/infer.R")


# Trong RStudio, working directory = projects/crp-mortality/
source("r-scripts/infer.R")
