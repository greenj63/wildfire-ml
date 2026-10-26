# Discussion log

Required by the project report (section 4). One entry per substantive discussion:
date, participants, question, evidence, decision, and resulting action. Add teammates'
names where it says `[add]`, and add new entries as the project continues.

Entries marked "Claude Code" were worked through with an AI assistant. The report's
generative-AI disclosure should cover them (tool, purpose, affected work, how the
output was checked).

---

### 1. How to combine the drought and wildfire data
- **Date:** `[add]` · **Participants:** team `[add names]`
- **Question:** How do we combine the two datasets for easy sharing and comparison, and
  what should "severity" be?
- **Decision:** Match drought and wildfire records by date first (a drought row must
  fall inside the fire's discovery-to-containment range), then by location using
  lat/long ranges. If several matches exist, use the closest date. Add a spread-rate
  column: acres (`FIRE_SIZE`) divided by days burning.
- **Action:** Plan written in `docs/wildfire_drought_merge_plan.md`.

### 2. Location matching: pgeocode won't work
- **Date:** 2026-10-26 · **Participants:** Arlim Macaldo, Claude Code
- **Question:** Can pgeocode turn postal codes into lat/long for matching?
- **Evidence:** The drought data has no postal codes, only county FIPS codes. The
  wildfire database already has `FIPS_CODE`, but 38% of natural fires (125,772 of
  327,319) are missing it. Every fire has a lat/long.
- **Decision:** Get county center points from the Census 2020 county Gazetteer instead
  of pgeocode. Lat/long ranges stay the main method, with FIPS as the backup.
- **Action:** Gazetteer added as `county_centroids`; merge plan updated.

### 3. How to compute spread rate
- **Date:** 2026-10-26 · **Participants:** Arlim Macaldo, Claude Code
- **Question:** Is `CONT_DOY - DISCOVERY_DOY` a safe way to count days?
- **Evidence:** 154,204 fires were contained the day they were discovered (0 days, so
  dividing gives an error), 18 fires cross New Year (negative days), and 49,109 have no
  containment date.
- **Decision:** `DURATION_DAYS = CONT_DATE - DISCOVERY_DATE + 1` using full dates;
  `SPREAD_RATE = FIRE_SIZE / DURATION_DAYS` (acres/day). Empty when there's no
  containment date. Hours were considered but rejected, since some fires have no
  times recorded.
- **Action:** Added to `scripts/process_wildfire_data.py`.

### 4. Matching settings and dataset size
- **Date:** 2026-10-26 · **Participants:** Arlim Macaldo, Claude Code
- **Questions and decisions:**
  - Box margin around each county: 25 km beyond the county's own size.
  - The drought score is weekly, so a short fire usually has none inside its dates.
    Decision: take the latest score from up to 7 days before discovery.
  - Fires with no drought match: first "keep with empty columns", then changed to
    **drop them**, so the limited rows go to fires that have drought data.
  - Size: the combined dataset is capped at 100,000 rows, sampled with a fixed seed
    and stratified by `FIRE_SIZE_CLASS`.
- **Action:** Built in `scripts/process_wildfire_drought_data.py`.

### 5. Fires matched to the wrong county (changed the experiment twice)
- **Date:** 2026-10-26 · **Participants:** Arlim Macaldo, Claude Code
- **Question:** Are fires matched to the right county?
- **Evidence (round 1):** After the first build, 5% of fires with a FIPS code were
  matched to a neighboring county. These fires sit far from the center of a long county,
  outside its lat/long box.
- **Decision:** Always add a fire's own FIPS county as a candidate.
- **Evidence (round 2):** That created 90 matches over 300 km away (one 1,394 km). Some
  FIPS codes in the source data are wrong, e.g. a fire near Las Vegas labeled Washoe
  County, 631 km away.
- **Decision:** Add the own county only if the fire is within 2× the county's box
  half-width of its center.
- **Result:** 99.5% of fires with a FIPS code match their own county, and no match is
  over 300 km.

### 6. Shared prediction target
- **Date:** 2026-10-26 · **Participants:** Arlim Macaldo, Claude Code
- **Question:** The proposal says "severity score" but names no column. What does every
  model predict?
- **Framing:** The data only has fires that happened, so we predict severity at the
  moment a fire is reported, not whether a fire will start.
- **Options considered:** (a) `FIRE_SIZE_CLASS` grouped into 3 levels
  (classification), (b) `log(1 + SPREAD_RATE)` (regression), (c) a custom combined
  score.
- **Evidence:** Spread rate is very skewed (median 0.1 acres/day, max about 65,000) and
  missing for fires with no containment date.
- **Decision:** (b) `log(1 + SPREAD_RATE)`. Claude recommended (a); the team chose (b)
  because `[add reason]`. (c) was rejected because the formula would be hard to justify.
- **Action:** Features limited to what's known at discovery (location, date, that day's
  weather, drought score). Columns known only after the fire are excluded (leakage).

### 7. Metric and baseline
- **Date:** 2026-10-26 · **Participants:** Arlim Macaldo, Claude Code
- **Evidence:** 62% of fires spread 0.25 acres/day or less, so a model that always
  predicts "small" looks good on average error.
- **Decision:** Primary metric: MAE on the log scale. Supporting: RMSE, R², and MAE on
  the 10% fastest-spreading fires. Baseline: always predict the training median.
- **Action:** `evaluate_spread_rate()` in `shared/evaluation.py`.

### 8. Rows without a target
- **Date:** 2026-10-26 · **Participants:** Arlim Macaldo, Claude Code
- **Evidence:** Only 85,896 of the 100,000 rows had a spread rate.
- **Decision:** Drop fires without a spread rate before sampling, so all 100,000 rows
  are usable.
- **Action:** Merge script updated and re-run.

### 9. Train/validation/test split (changed)
- **Date:** 2026-10-26 · **Participants:** Arlim Macaldo, Claude Code
- **First decision:** Split by year (train 2000–2014, validation 2015–2017, test
  2018–2020).
- **Change requested:** One script that writes train, validation, and test files with a
  fixed seed, like scikit-learn's `train_test_split`.
- **Evidence:** 12,916 county-days have more than one fire with identical weather. A
  plain random split would put some in train and some in test (leakage).
- **Decision:** Random split with `GroupShuffleSplit` (seed 42), grouping by county +
  discovery date. About 80/10/10: 79,961 / 10,026 / 10,013 rows. Plain
  `train_test_split` was rejected because of the leakage.
- **Action:** `scripts/make_split.py`; tests check that no county-day is in two splits.

### 10. Sharing the data and dividing the work
- **Date:** 2026-10-26 · **Participants:** Arlim Macaldo, Claude Code
- **Decisions:**
  - Only `train.csv`, `validation.csv`, and `test.csv` are committed to Git, so members
    just pull them and don't need to download raw data or run scripts.
  - Each member implements, tunes, and documents their own model from the template.
    Claude Code built only shared code (data scripts, split, features, preprocessing,
    metrics, template, comparison script) and implemented no models.

---

## Open items (to discuss as a team)

| Item | Decision | Owner |
|---|---|---|
| Who builds the baseline (training median) | `[add]` | `[add]` |
| Which algorithm each member takes, and what each comparison shows | `[add]` | everyone |
| One person trains every model at the end to make the final `results/comparison.csv` (recommended), or each member commits only their own results | `[add]` | `[add]` |
| Use `FIRE_YEAR` as a feature? (excluded for now; allowed now that the split is random) | `[add]` | `[add]` |
| Check the Kaggle drought dataset's license allows sharing derived data in the repo | `[add]` | `[add]` |
