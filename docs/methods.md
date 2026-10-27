# Scientific calculations and source alignment

[Overview](../README.md) · [Architecture](architecture.md) · [Validation](validation.md)

## Sample and measurement representation

The UI separates sample-level ages from analytical spots. A sample holds geographic, stratigraphic, mineral/system/technique and reference fields. Spots retain isotope ratios, ratio uncertainties, isotope-specific ages and their errors. The original conversion script flattens nested `{value, err_1s}` measurements into `_val` and `_err` fields; it can derive an illustrative concordance percentage from two age values.

The representation supports inspection and re-selection of analytical inputs. It does not by itself establish that a sample age, measurement uncertainty, table column and source text have been bound correctly by upstream extraction.

## Preserved numerical utilities

[`spotCalc.ts`](../frontend/src/utils/spotCalc.ts) implements the following calculations. [`main.py`](../backend/main.py) separately implements weighted means for its in-memory grain API.

|Calculation|Implementation|Scientific scope|
|---|---|---|
|Inverse-variance weighted mean|`w_i = 1 / sigma_i²`; mean `sum(w_i age_i) / sum(w_i)`; mean error `sqrt(1 / sum(w_i))`; MSWD from weighted residuals over `n−1`.|Uses supplied uncertainties and treats measurements according to that formula. No random-effects age model or external uncertainty inflation is implemented.|
|KDE peak|Gaussian kernel sum over a 201-point grid with a Silverman-style/data-spread bandwidth rule.|A descriptive distribution peak; not automatic identification of a geological event.|
|Minimum apparent age|Chooses the youngest age among 90–110% concordant records; if none meet that interval, falls back to all usable ages.|An implemented selection heuristic. It is not a multi-grain maximum-depositional-age estimator.|
|Wetherill concordia|`exp(lambda238 × t) − 1` versus `exp(lambda235 × t) − 1`, with the constants stored in `concordia.ts`.|Plots a reference curve and points. It does not fit a concordia age with analytical covariance or error ellipses.|
|Timeline and stratigraphic reference|Interactive age-axis placement and a built-in table labeled ICS 2023.|A versioned display reference, not a claim to implement the latest official stratigraphic standard or a measured sedimentary section.|

Callers filter excluded spots before calculation. Inputs need finite ages and strictly positive uncertainties. The preserved routines do not uniformly validate every degenerate case; zero errors and very small sample sets need upstream handling before scientific use. This preparation keeps those algorithms unchanged and checks controlled valid inputs.

For the six synthetic `DEMO01` spots, ages `(100,102,104,106,108,110)` Ma and errors `(1,1,2,2,2,2)` Ma yield **103.0 ± 0.5774 Ma**, MSWD **6.2**, with the current rounding. Their symmetric illustrative distribution gives a KDE peak of **105 Ma**. These values are demonstration calculations, not research observations.

## Source-text alignment

The original [provenance mapper](../scripts/provenance_mapper.py) links extracted context to PDF text. It normalizes text, tries sufficiently informative keyword matches, preselects candidate pages by character-trigram overlap, and performs LCS-based fuzzy alignment with coverage/density criteria. Character positions map back to PDF word boxes; a union bounding box and matched text are returned. A longest-common-substring fallback handles some unmatched spans.

[`compare_hybrid.py`](../scripts/compare_hybrid.py) explores exact substring candidates followed by windowed LCS, comparing them with saved earlier alignments. [`provenance_mineru.py`](../scripts/provenance_mineru.py) adapts span/word data from MinerU. [`provenance_v3.py`](../scripts/provenance_v3.py) converts a v3 Excel batch into the mapper's record format. These are implemented exploratory processing routes; no independently scored provenance-accuracy result was found in the selected GeoViz source snapshot.

## Viewer coordinate contract

Each displayed field carries a record identity, label/value, page index, matched text and `bbox_norm = [x0,y0,x1,y1]` in page-relative coordinates. The React viewer scales those normalized coordinates to the rendered page image. The generated demo page contains explicitly defined boxes. Its fixture alignment demonstrates navigation/highlighting; the separate backend check exercises the preserved PDF matcher on a newly generated PDF with controlled text.

Successful alignment shows where a string was located. It does not verify sample identity, extraction completeness, uncertainty interpretation or the correctness of a geological conclusion.
