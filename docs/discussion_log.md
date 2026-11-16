# Discussion log

Required by the project report (section 4). One entry per substantive discussion:
date, participants, question, evidence, decision, and resulting action. Add new entries
as the project continues.

---

### 1. How to combine the drought and wildfire data
- **Date:** 2026-09-26 · **Participants:** Team
- **Question:** How do we combine the two datasets for easy sharing and comparison, and
  what should "severity" be?
- **Decision:** Match drought and wildfire records by date first (a drought row must
  fall inside the fire's discovery-to-containment range), then by location using
  lat/long ranges. If several matches exist, use the closest date. Add a spread-rate
  column: acres (`FIRE_SIZE`) divided by days burning.
- **Action:** Plan written in `docs/wildfire_drought_merge_plan.md`.

### 2. Location matching: pgeocode won't work
- **Date:** 2026-10-26 · **Participants:** Arlim Macaldo, Jack Greene
- **Question:** Can pgeocode turn postal codes into lat/long for matching?
- **Evidence:** The drought data has no postal codes, only county FIPS codes. The
  wildfire database already has `FIPS_CODE`, but 38% of natural fires (125,772 of
  327,319) are missing it. Every fire has a lat/long.
- **Decision:** Get county center points from the Census 2020 county Gazetteer instead
  of pgeocode. Lat/long ranges stay the main method, with FIPS as the backup.
- **Action:** Gazetteer added as `county_centroids`; merge plan updated.

### 3. How to compute spread rate
- **Date:** 2026-10-26 · **Participants:** Team
- **Question:** Is `CONT_DOY - DISCOVERY_DOY` a safe way to count days?
- **Evidence:** 154,204 fires were contained the day they were discovered (0 days, so
  dividing gives an error), 18 fires cross New Year (negative days), and 49,109 have no
  containment date.
- **Decision:** `DURATION_DAYS = CONT_DATE - DISCOVERY_DATE + 1` using full dates;
  `SPREAD_RATE = FIRE_SIZE / DURATION_DAYS` (acres/day). Empty when there's no
  containment date. Hours were considered but rejected, since some fires have no
  times recorded.
- **Action:** Added to `scripts/process_wildfire_data.py`.

### 4. Fires matched to the wrong county (changed the experiment twice)
- **Date:** 2026-10-26 · **Participants:** Team
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

### 5. Shared prediction target
- **Date:** 2026-10-26 · **Participants:** Team
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
  because the dataset is skewed. (c) was rejected because the formula would be hard to justify.
- **Action:** Features limited to what's known at discovery (location, date, that day's
  weather, drought score). Columns known only after the fire are excluded (leakage).

### 6. Separate datasets per fire lifetime (rejected)
- **Date:** 2026-11-01 · **Participants:** Jack Greene, Arlim Macaldo
- **Proposal:** Build five datasets (current; lifetime ≤ 2, 3–30, 31–90, ≥ 91 days) and
  find the best model for each.
- **Evidence:** Lifetime is only known after containment, so no model could be chosen
  at prediction time (leakage), and it is part of the target (spread = acres ÷ days).
  The ≥ 91-day group has only 300 training and 38 test fires.
- **Decision:** Rejected. Instead, every model trains on the full data, and test errors
  are broken down by lifetime group in the error analysis.

### 7. Add FPA FOD-Attributes features (changed the dataset)
- **Date:** 2026-11-03 to 2026-11-04 · **Participants:** Team (approved 2026-11-04)
- **Question:** Error analysis showed all models fail in the same places (fast fires,
  certain states) and rely heavily on latitude/longitude. Would fuel, terrain, and
  on-site weather help?
- **Evidence:** FPA FOD-Attributes (Pourmohamad et al., 2024) matched 99,975 of our
  100,000 fires by `FOD_ID`. Adding 35 of its columns, same fires and split, each model's
  existing settings, improved every model on every validation metric: MAE −0.026
  (LightGBM), −0.035 (random forest), −0.028 (KNN); R² +0.06 to +0.10. Leaky columns
  were excluded (MTBS and ICS-209 IDs exist mostly for large fires; 5-day weather
  windows include days after discovery).
- **Decision:** Adopt the new columns. Split files rebuilt with the same fires and split,
  and compressed (`.csv.gz`). Every model must be retuned and retrained.

### 8. Which feature groups to keep
- **Date:** 2026-11-04 · **Participants:** Team
- **Evidence (validation, removing one group at a time):** removing land owner and
  reporting agency made every model worse (MAE +0.003 to +0.010). Removing our 18 county
  weather columns made every model's MAE equal or better (−0.002 to −0.009), since the
  point weather replaces them.
- **Decision:** Keep owner and agency; drop the county weather from the features (still
  in the files). Final set: 42 features.

### 9. Removing implausible long-duration small fires (rejected)
- **Date:** 2026-11-04 · **Participants:** Team
- **Hypothesis:** 2.2% of fires under 10 acres are recorded as lasting over 2 weeks
  (likely late paperwork, not burning). Removing them from training might help.
- **Evidence:** Removing them (two rules tested) made all four models slightly worse on
  validation. These records turned out to be easy cases (near-zero spread, predicted as
  near zero), not the source of the large errors on long fires.
- **Decision:** Keep the training data as is; report the records as a data-quality
  finding.

### 10. Training goal: median vs mean
- **Date:** 2026-11-04 · **Participants:** Team
- **Evidence (validation):** Switching random forest, KNN, and linear regression to
  median-aiming versions cut MAE by 14–18%, but worsened R², fastest-10% error, and
  fast-fire PR-AUC. LightGBM already aims at the median (`l1`).
- **Decision:** Aim every model at the **median**, because the target is skewed (about
  62% of fires spread 0.25 acres/day or less) and the primary metric is MAE. This keeps
  the comparison fair: all models aim at the same thing. The cost, shown in the evidence,
  is worse R², fastest-10% error, and fast-fire PR-AUC, which the report must state.
  Reported by Arlim Macaldo; agreed by the team on 2026-11-04.
- **Action:** Random forest (`absolute_error` criterion), KNN (median of neighbors), and
  LightGBM (`l1`) aim at the median. Huber regression is closer to median than mean
  regression but is not a pure median model; its README says so.
