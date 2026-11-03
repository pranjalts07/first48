# Is creation timing associated with 30-day views once early views are
# known? Association only: editors choose when to publish.
#
#   python -m first48.warehouse   # writes data/fct_articles.csv
#   Rscript analysis/timing.R

suppressPackageStartupMessages(library(lme4))

holdout_start <- as.Date("2026-08-20")

articles <- read.csv("data/fct_articles.csv")
articles <- subset(articles, dataset == "backfill" & as.Date(cohort_date) < holdout_start)
articles$log_y <- log1p(articles$views_30d)
articles$log_early <- log1p(articles$views_48h)
articles$creation_hour <- factor(articles$creation_hour)
articles$weekday <- factor(articles$weekday, labels = c("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"))

full <- lmer(log_y ~ log_early + creation_hour + weekday + (1 | article_type),
             data = articles, REML = FALSE)
no_hour <- update(full, . ~ . - creation_hour)
no_weekday <- update(full, . ~ . - weekday)

sink("results/timing_model.txt")
cat("Articles:", nrow(articles), "\n")
cat("Cohorts:", min(articles$cohort_date), "to", max(articles$cohort_date), "\n\n")
print(summary(full)$coefficients[, 1:2], digits = 3)
cat("\nRandom effect (article type):\n")
print(VarCorr(full))
cat("\nLikelihood ratio test, creation hour:\n")
print(anova(no_hour, full))
cat("\nLikelihood ratio test, weekday:\n")
print(anova(no_weekday, full))
cat("\nWald 95% intervals, weekday effects (log scale, vs Monday):\n")
ci <- confint(full, parm = grep("^weekday", names(fixef(full)), value = TRUE), method = "Wald")
print(round(ci, 3))
sink()

cat(readLines("results/timing_model.txt"), sep = "\n")
