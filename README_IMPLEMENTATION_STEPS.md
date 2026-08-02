# Honey-Harvest Probability Integration

This setup changes the live dashboard from a manually weighted proxy-HUI
regression model to a probability-calibrated classifier:

`P(actual harvest occurs within the next 72 hours)`

The historical event-labelled dataset is used for training. The Sri Lankan
PostgreSQL IoT table is used only for live inference.

## Important prerequisite

The historical dataset must contain:

- `timestamp`
- `hive_id`
- `harvest`
- the sensor columns used by the live hive

The implementation assumes:

`harvest = 1` means an actual harvesting event at that timestamp.

If `harvest=1` means only "ready" across a broad period, stop and redefine the
target before training.

---

## 1. Back up current files

From the project root:

```powershell
Copy-Item backend\routes\harvest_routes.py backend\routes\harvest_routes.backup.py
Copy-Item backend\services\live_harvest_service.py backend\services\live_harvest_service.backup.py
Copy-Item backend\harvest\live_feature_engineering.py backend\harvest\live_feature_engineering.backup.py
```

`backend/app.py` remains unchanged.

---

## 2. Copy package files

Copy these replacement files:

```text
backend/harvest/live_feature_engineering.py
backend/services/live_harvest_service.py
backend/routes/harvest_routes.py
```

Copy these new files:

```text
backend/harvest/harvest_target.py
backend/tools/check_harvest_labels.py
backend/ml/train_harvest_classifier.py
backend/services/harvest_prediction_history_service.py
backend/test_harvest_probability_pipeline.py
requirements_harvest_classifier.txt
```

Keep your already working file unchanged:

```text
backend/services/iot_data_service.py
```

Keep your existing application unchanged:

```text
backend/app.py
```

---

## 3. Update `.env`

Append the settings from `.env.additions.example`.

For the UK dataset, use:

```env
HISTORICAL_TIMESTAMPS_ARE_UTC=false
HISTORICAL_SOURCE_TIMEZONE=Europe/London
HISTORICAL_FEATURE_TIMEZONE=Europe/London
```

The live IoT sensor features are generated in:

```env
IOT_FEATURE_TIMEZONE=Asia/Colombo
```

Do not commit `.env`.

---

## 4. Install dependencies

```powershell
pip install -r requirements_harvest_classifier.txt
```

---

## 5. Verify historical labels

```powershell
python backend/tools/check_harvest_labels.py
```

Check:

- both 0 and 1 exist;
- positive rows occur at actual harvest timestamps;
- several hives and time periods contain harvest events.

Do not proceed when the positive class is absent or the meaning is different.

---

## 6. Train the classifier

```powershell
python backend/ml/train_harvest_classifier.py
```

Faster trial:

```powershell
python backend/ml/train_harvest_classifier.py --sample 100000
```

The script performs:

1. Historical timestamp normalization.
2. Hourly resampling.
3. Shared live-compatible feature engineering.
4. Future 72-hour target generation.
5. Post-harvest row exclusion.
6. Chronological 70/15/15 splitting with purge gaps.
7. Logistic Regression, Random Forest, XGBoost and LightGBM training.
8. Probability calibration.
9. Validation-based decision-threshold selection.
10. Final test evaluation.

Expected model files:

```text
backend/models/calibrated_harvest_classifier.joblib
backend/models/best_harvest_base_model.joblib
backend/models/harvest_classifier_ensemble.joblib
backend/models/harvest_classifier_features.joblib
backend/models/harvest_classifier_metadata.json
```

Expected research outputs:

```text
backend/outputs/harvest/harvest_classifier_dataset.csv
backend/outputs/harvest/harvest_classifier_comparison.csv
backend/outputs/harvest/harvest_classifier_comparison.json
backend/outputs/harvest/harvest_confusion_matrix.png
backend/outputs/harvest/harvest_precision_recall_curve.png
backend/outputs/harvest/harvest_roc_curve.png
backend/outputs/harvest/harvest_calibration_curve.png
backend/outputs/harvest/harvest_feature_importance.png
backend/outputs/harvest/actual_vs_predicted_harvest_timeline.csv
backend/outputs/harvest/actual_vs_predicted_harvest_timeline.png
```

---

## 7. Test the complete backend pipeline

```powershell
python backend/test_harvest_probability_pipeline.py
```

It checks:

- PostgreSQL connectivity;
- classifier artifact availability;
- device list;
- one live prediction.

---

## 8. Start the existing Flask app

No `app.py` change is required.

```powershell
python backend/app.py
```

Test:

```text
GET http://localhost:5000/api/harvest/live/health
GET http://localhost:5000/api/harvest/live/devices
GET http://localhost:5000/api/harvest/live/latest/DEVICE_ID
GET http://localhost:5000/api/harvest/live/history/DEVICE_ID?hours=168
GET http://localhost:5000/api/harvest/live/predict/DEVICE_ID?hours=168
GET http://localhost:5000/api/harvest/live/predict-all?hours=168
GET http://localhost:5000/api/harvest/classifier-results
```

---

## 9. Dashboard mapping

Use these response fields:

```text
harvest_readiness_percent
status
prediction_horizon
recommendation
recommended_harvest_window
confidence.level
environmental_suitability.status
main_reasons
current_sensor_values
derived_values
trend.previous_7_day_predictions
colony_risks
data_quality
warnings
```

Example cards:

```text
Harvest readiness: 82%
Status: Ready
Prediction horizon: Harvest within the next 3 days
Confidence: High
Environmental suitability: Suitable
```

Use `operational_decision.ready_for_action` for alerts. It uses the
validation-selected threshold. Do not hard-code 70% for the alert.

---

## 10. Prediction history and harvest window

Every live prediction is written to:

```text
backend/outputs/harvest/harvest_prediction_history.sqlite3
```

A recommended window becomes available only after the probability has remained
above the validated threshold with sufficient hourly prediction coverage for
approximately 24 hours.

During testing, call `/live/predict/DEVICE_ID` periodically. The frontend can
refresh once every 60 minutes. Calling every minute creates unnecessary
duplicate history.

---

## 11. React refresh recommendation

For the final system, request a live prediction every 60 minutes:

```javascript
useEffect(() => {
  fetchPrediction();

  const timer = setInterval(
    fetchPrediction,
    60 * 60 * 1000
  );

  return () => clearInterval(timer);
}, [deviceId]);
```

During development, use a shorter interval such as 60 seconds.

---

## 12. What the model can and cannot claim

Supported:

- Probability of an observed harvest event within 72 hours.
- Readiness status.
- Validation-selected operational threshold.
- Recommendation.
- Confidence based on model agreement and data quality.
- Environmental similarity to historical pre-harvest conditions.
- A sustained-probability harvest window after sufficient prediction history.

Not yet supported:

- Exact days until harvest.
- Estimated harvestable honey quantity.
- Proven local accuracy in Sri Lanka.
- Brood/swarming/absconding values until those modules are connected.

---

## 13. Common errors

### No positive class after target generation

Confirm `harvest=1` is an actual event timestamp and that the dataset has enough
future coverage after each event.

### One class in validation or test

The events are too concentrated in time. Use more data or modify the split
boundaries carefully. Do not use a random split to hide this issue.

### Complete live feature row cannot be produced

Ensure at least 72 hours of data exist. For the seven-day maximum feature,
168 hours is recommended.

### High historical accuracy but poor Sri Lankan predictions

This is domain shift. Record actual Sri Lankan harvest events and retrain or
calibrate the model locally.

---

## Final project flow

```text
Historical UK event-labelled data
→ common hourly preprocessing
→ common sensor feature engineering
→ future 72-hour target
→ calibrated classifier
→ saved model

Sri Lankan PostgreSQL live readings
→ same hourly preprocessing
→ same sensor feature engineering
→ predicted probability
→ HUI/status/action/confidence/explanation
→ dashboard
```
