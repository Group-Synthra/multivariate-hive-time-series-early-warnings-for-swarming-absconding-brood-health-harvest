import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceArea,
  ReferenceDot
} from "recharts";
import {
  TrendingUp,
  Scale,
  Activity,
  CalendarDays,
  ShieldCheck,
  Droplets
} from "lucide-react";
import "./HarvestingModule.css";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

const sections = [
  {
    id: "eda",
    label: "1. Exploratory Analysis",
  },
  {
    id: "comparison",
    label: "2. Model Comparison",
  },
  {
    id: "prediction",
    label: "3. HUI Prediction",
  },
];

function MetricCard({ title, value, description }) {
  return (
    <div className="metric-card">
      <p className="metric-title">{title}</p>
      <h3>{value ?? "N/A"}</h3>
      {description && <p className="metric-description">{description}</p>}
    </div>
  );
}

function LoadingMessage({ text }) {
  return <div className="message-card">{text}</div>;
}

function ErrorMessage({ message }) {
  return (
    <div className="error-card">
      <strong>Error:</strong> {message}
    </div>
  );
}

function HarvestingModule() {
  const [activeSection, setActiveSection] = useState("eda");

  const [edaSummary, setEdaSummary] = useState(null);
  const [edaImages, setEdaImages] = useState([]);
  const [modelResults, setModelResults] = useState(null);

  const [sampleInput, setSampleInput] = useState(null);
  const [formValues, setFormValues] = useState({});
  const [prediction, setPrediction] = useState(null);

  const [loadingEda, setLoadingEda] = useState(true);
  const [loadingModels, setLoadingModels] = useState(true);
  const [loadingPrediction, setLoadingPrediction] = useState(false);

  const [edaError, setEdaError] = useState("");
  const [modelError, setModelError] = useState("");
  const [predictionError, setPredictionError] = useState("");

  const [hiveAnalysis, setHiveAnalysis] = useState(null);
  const [selectedHive, setSelectedHive] = useState("");
  const [hiveAnalysisError, setHiveAnalysisError] = useState("");

  useEffect(() => {
    loadHarvestEda();
    loadModelResults();
    loadSampleInput();
    loadHiveAnalysis();
  }, []);

  async function loadHarvestEda() {
    setLoadingEda(true);
    setEdaError("");

    try {
      const [summaryResponse, imagesResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/api/harvest/eda-summary`),
        fetch(`${API_BASE_URL}/api/harvest/images`),
      ]);

      if (!summaryResponse.ok) {
        const errorData = await summaryResponse.json();
        throw new Error(
          errorData.error || "Failed to load harvesting EDA summary."
        );
      }

      if (!imagesResponse.ok) {
        const errorData = await imagesResponse.json();
        throw new Error(
          errorData.error || "Failed to load harvesting EDA images."
        );
      }

      const summaryData = await summaryResponse.json();
      const imageData = await imagesResponse.json();

      setEdaSummary(summaryData);
      setEdaImages(imageData);
    } catch (error) {
      setEdaError(error.message);
    } finally {
      setLoadingEda(false);
    }
  }

  async function loadModelResults() {
    setLoadingModels(true);
    setModelError("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/harvest/model-results`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "Failed to load model comparison results."
        );
      }

      setModelResults(data);
    } catch (error) {
      setModelError(error.message);
    } finally {
      setLoadingModels(false);
    }
  }

  async function loadSampleInput() {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/harvest/sample`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "Failed to load sample model input."
        );
      }

      setSampleInput(data);
      setFormValues(data);
    } catch (error) {
      setPredictionError(error.message);
    }
  }

  function handleInputChange(event) {
    const { name, value } = event.target;

    setFormValues((previousValues) => ({
      ...previousValues,
      [name]: value === "" ? "" : Number(value),
    }));
  }

  async function loadHiveAnalysis() {
  setHiveAnalysisError("");

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/harvest/hive-analysis`
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.error || "Failed to load hive analysis."
      );
    }

    setHiveAnalysis(data);

    if (data.hives?.length > 0) {
      setSelectedHive(data.hives[0].hive);
    }
  } catch (error) {
    setHiveAnalysisError(error.message);
  }
}

  async function handlePrediction(event) {
    event.preventDefault();

    setLoadingPrediction(true);
    setPredictionError("");
    setPrediction(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/harvest/predict`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(formValues),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        const missingText = Array.isArray(data.missing_columns)
          ? ` Missing: ${data.missing_columns.join(", ")}`
          : "";

        throw new Error(
          `${data.error || "Prediction failed."}${missingText}`
        );
      }

      setPrediction(data);
    } catch (error) {
      setPredictionError(error.message);
    } finally {
      setLoadingPrediction(false);
    }
  }

  function goToNextSection() {
    if (activeSection === "eda") {
      setActiveSection("comparison");
      return;
    }

    if (activeSection === "comparison") {
      setActiveSection("prediction");
    }
  }

  function renderEdaSection() {
    if (loadingEda) {
      return <LoadingMessage text="Loading harvesting EDA..." />;
    }

    if (edaError) {
      return <ErrorMessage message={edaError} />;
    }

    const summary = edaSummary || {};

    const selectedHiveData =
      hiveAnalysis?.hives?.find((item) => item.hive === selectedHive) || null;

    const weightChartData =
      selectedHiveData?.chart_data?.map((item) => ({
        ...item,
        displayTime: new Date(item.timestamp).toLocaleString(),
      })) || [];

    return (
      <section className="content-section">
        <div className="section-heading">
          <div>
            <p className="section-kicker">Step 1</p>
            <h2>Exploratory Data Analysis</h2>
            <p>
              Understand the harvest dataset, generated HUI target,
              distributions and important patterns before model training.
            </p>
          </div>
        </div>

        <div className="metric-grid">
          <MetricCard
            title="Dataset Rows"
            value={
              summary.rows ??
              summary.total_rows ??
              summary.dataset_rows ??
              "N/A"
            }
            description="Hourly hive observations used in harvesting analysis."
          />

          <MetricCard
            title="Dataset Columns"
            value={
              summary.columns ??
              summary.total_columns ??
              summary.dataset_columns ??
              "N/A"
            }
            description="Sensor, weather, seasonal and derived variables."
          />

          <MetricCard
            title="Number of Hives"
            value={summary.hives ?? "N/A"}
            description="Unique bee hives included in the analysis."
          />

          <MetricCard
            title="HUI Mean"
            value={
              summary.hui?.mean !== undefined
                ? Number(summary.hui.mean).toFixed(2)
                : "N/A"
            }
            description="Average generated Harvest Urgency Index."
          />
        </div>

        <div className="analysis-note">
          <h3>HUI generation</h3>
          <p>
            The Harvest Urgency Index is an expert rule proxy target generated
            from hive weight, weight change, stability, nectar-flow conditions,
            brood health, temperature, humidity, CO₂, rainfall, wind, dearth and
            honey flow factors.
          </p>
        </div>

        <div className="image-grid">
          {edaImages.length === 0 ? (
            <div className="message-card">
              No harvesting EDA images are currently available.
            </div>
          ) : (
            edaImages.map((imageName) => (
              <article className="plot-card" key={imageName}>
                <h3>{formatImageTitle(imageName)}</h3>

                <img
                  src={`${API_BASE_URL}/api/harvest/images/${imageName}`}
                  alt={formatImageTitle(imageName)}
                />
              </article>
            ))
          )}
        </div>

                {hiveAnalysisError && (
          <ErrorMessage message={hiveAnalysisError} />
        )}

        {hiveAnalysis && (
          <>
            <div className="harvest-overview-grid">
              <div className="harvest-overview-card">
                <CalendarDays size={22} />

                <div>
                  <span>Total Hives </span>
                  <strong>{hiveAnalysis.total_hives} </strong>
                  <small>
                      included in harvesting analysis
                  </small>
                </div>
              </div>

              <div className="harvest-overview-card">
                <ShieldCheck size={22} />

                <div>
                  <span>Ready Hives </span>
                  <strong>{hiveAnalysis.ready_hives} </strong>
                  <small>
                    Ready or optimal harvesting status
                  </small>
                </div>
              </div>

              <div className="harvest-overview-card">
                <Activity size={22} />

                <div>
                  <span>Plateau Hives </span>
                  <strong>{hiveAnalysis.plateau_hives} </strong>
                  <small>
                     with stable high-weight periods
                  </small>
                </div>
              </div>
            </div>

            <div className="hive-selector-row">
              <div>
                <h3>Per-Hive Harvesting Analysis</h3>
                <p>
                  Select a hive to inspect weight accumulation,
                  plateau behaviour and possible extraction events.
                </p>
              </div>

              <select
                value={selectedHive}
                onChange={(event) =>
                  setSelectedHive(event.target.value)
                }
              >
                {hiveAnalysis.hives.map((hive) => (
                  <option
                    key={hive.hive}
                    value={hive.hive}
                  >
                    {hive.hive.toUpperCase()}
                  </option>
                ))}
              </select>
            </div>

            {selectedHiveData && (
              <>
                <div className="selected-hive-metrics">
                  <div className="hive-metric-card">
                    <Scale size={20} />

                    <span>Current Weight</span>

                    <strong>
                      {selectedHiveData.current_weight} kg
                    </strong>

                    <small>
                      Latest recorded hive weight
                    </small>
                  </div>

                  <div className="hive-metric-card">
                    <TrendingUp size={20} />

                    <span>Peak Weight</span>

                    <strong>
                      {selectedHiveData.maximum_weight} kg
                    </strong>

                    <small>
                      Maximum observed hive weight
                    </small>
                  </div>

                  <div className="hive-metric-card">
                    <Activity size={20} />

                    <span>24-Hour Change</span>

                    <strong>
                      {selectedHiveData.weight_change_24h} kg
                    </strong>

                    <small>
                      Recent weight gain or loss
                    </small>
                  </div>

                  <div className="hive-metric-card">
                    <Droplets size={20} />

                    <span>Current HUI</span>

                    <strong>
                      {selectedHiveData.current_hui ?? "N/A"}
                    </strong>

                    <small>
                      {selectedHiveData.status}
                    </small>
                  </div>
                </div>

                <div className="harvest-chart-and-board">
                  <div className="harvest-weight-chart-card">
                    <div className="chart-section-heading">
                      <h3>
                        Hive Weight Curve and Harvest Signals
                      </h3>

                      <p>
                        The chart shows honey accumulation, stable
                        high-weight periods and possible extraction
                        events for {selectedHive.toUpperCase()}.
                      </p>
                    </div>

                    <div className="harvest-chart-container">
                      <ResponsiveContainer
                        width="100%"
                        height={390}
                      >
                        <LineChart
                          data={weightChartData}
                          margin={{
                            top: 20,
                            right: 25,
                            left: 5,
                            bottom: 10,
                          }}
                        >
                          <CartesianGrid
                            strokeDasharray="3 3"
                          />

                          <XAxis
                            dataKey="displayTime"
                            minTickGap={90}
                            tick={{ fontSize: 11 }}
                          />

                          <YAxis
                            unit=" kg"
                            domain={[
                              "dataMin - 3",
                              "dataMax + 3",
                            ]}
                          />

                          <Tooltip />
                          <Legend />

                          {selectedHiveData.plateau_start &&
                            selectedHiveData.plateau_end && (
                              <ReferenceArea
                                x1={new Date(
                                  selectedHiveData.plateau_start
                                ).toLocaleString()}
                                x2={new Date(
                                  selectedHiveData.plateau_end
                                ).toLocaleString()}
                                label="Detected weight plateau"
                              />
                            )}

                          {weightChartData
                            .filter(
                              (item) =>
                                item.harvest_drop_detected
                            )
                            .map((item) => (
                              <ReferenceDot
                                key={item.timestamp}
                                x={item.displayTime}
                                y={item.weight}
                                r={5}
                                label="Possible harvest"
                              />
                            ))}

                          <Line
                            type="monotone"
                            dataKey="weight"
                            name="Hive Weight"
                            strokeWidth={2}
                            dot={false}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>

                    <div className="chart-interpretation">
                      <strong></strong>

                      <span>
                        Rising weight indicates continuing nectar or
                        honey accumulation.
                      </span>

                      <span>
                        A stable high weight plateau may indicate that
                        accumulation is slowing and a harvest window is
                        approaching.
                      </span>

                      <span>
                        A sudden decrease of 10 kg or more is marked as
                        a possible historical extraction event.
                      </span>
                    </div>
                  </div>

                  <div className="apiary-board-card">
                    <h3>Apiary Harvest Board</h3>

                    <p>
                      Hives are ordered using their latest Harvest
                      Urgency Index.
                    </p>

                    <div className="apiary-table-wrapper">
                      <table>
                        <thead>
                          <tr>
                            <th>Hive</th>
                            <th>Weight</th>
                            <th>HUI</th>
                            <th>Status</th>
                          </tr>
                        </thead>

                        <tbody>
                          {hiveAnalysis.hives.map((hive) => (
                            <tr
                              key={hive.hive}
                              onClick={() =>
                                setSelectedHive(hive.hive)
                              }
                              className={
                                hive.hive === selectedHive
                                  ? "selected-hive-row"
                                  : ""
                              }
                            >
                              <td>
                                {hive.hive.toUpperCase()}
                              </td>

                              <td>
                                {hive.current_weight} kg
                              </td>

                              <td>
                                {hive.current_hui ?? "N/A"}
                              </td>

                              <td>
                                <span
                                  className={`harvest-status-badge ${getStatusClass(
                                    hive.status
                                  )}`}
                                >
                                  {hive.status}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <div className="harvest-advice-panel">
                      <h4>
                        Selected Hive Interpretation
                      </h4>

                      <p>
                        {getSelectedHiveAdvice(
                          selectedHiveData
                        )}
                      </p>

                      <small>
                        Possible historical extraction events:{" "}
                        {
                          selectedHiveData
                            .historical_harvest_count
                        }
                      </small>
                    </div>
                  </div>
                </div>
              </>
            )}
          </>
        )}

        <div className="findings-card">
          <h3>Key EDA observations</h3>

          <ul>
            <li>HUI is treated as a continuous target between 0 and 100.</li>
            <li>
              Hive-weight behaviour is an important harvest-readiness indicator.
            </li>
            <li>
              Environmental conditions can increase or reduce harvesting
              suitability.
            </li>
            <li>
              The current HUI is a proxy label and requires future
              beekeeper-confirmed validation.
            </li>
          </ul>
        </div>

        <div className="section-actions">
          <button
            className="primary-button"
            type="button"
            onClick={goToNextSection}
          >
            Continue to Model Comparison
          </button>
        </div>
      </section>
    );
  }

  function renderModelComparisonSection() {
    if (loadingModels) {
      return <LoadingMessage text="Loading model comparison..." />;
    }

    if (modelError) {
      return <ErrorMessage message={modelError} />;
    }

    const results =
      modelResults?.results ||
      modelResults?.models ||
      modelResults?.comparison ||
      [];

    const bestModel =
      modelResults?.best_model ||
      modelResults?.bestModel ||
      "Not selected";

    return (
      <section className="content-section">
        <div className="section-heading">
          <div>
            <p className="section-kicker">Step 2</p>
            <h2>Model Comparison</h2>
            <p>
              Compare Random Forest, XGBoost and LightGBM using the
              same testing period and regression metrics.
            </p>
          </div>
        </div>

        <div className="best-model-banner">
          <div>
            <span>Selected best model</span>
            <h3>{bestModel}</h3>
          </div>

          <p>
            Selection is based primarily on lowest RMSE, supported by
            MAE and R².
          </p>
        </div>

        <div className="comparison-table-wrapper">
          <table className="comparison-table">
            <thead>
              <tr>
                <th>Model</th>
                <th>MAE</th>
                <th>RMSE</th>
                <th>R² Score</th>
                <th>Result</th>
              </tr>
            </thead>

            <tbody>
              {results.map((result, index) => {
                const modelName =
                  result.model ||
                  result.Model ||
                  result.name ||
                  `Model ${index + 1}`;

                const mae = result.mae ?? result.MAE;
                const rmse = result.rmse ?? result.RMSE;
                const r2 =
                  result.r2 ??
                  result["R2 Score"] ??
                  result.r2_score;

                const isBest =
                  String(modelName).toLowerCase() ===
                  String(bestModel).toLowerCase();

                return (
                  <tr
                    key={modelName}
                    className={isBest ? "best-model-row" : ""}
                  >
                    <td>{modelName}</td>
                    <td>{formatMetric(mae)}</td>
                    <td>{formatMetric(rmse)}</td>
                    <td>{formatMetric(r2)}</td>
                    <td>
                      {isBest ? (
                        <span className="best-badge">Best Model</span>
                      ) : (
                        <span className="normal-badge">Compared</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="metric-explanation-grid">
          <div className="explanation-card">
            <h3>MAE</h3>
            <p>
              Average absolute difference between actual and predicted
              HUI. Lower is better.
            </p>
          </div>

          <div className="explanation-card">
            <h3>RMSE</h3>
            <p>
              Gives greater penalty to large prediction errors. Lower is
              better.
            </p>
          </div>

          <div className="explanation-card">
            <h3>R²</h3>
            <p>
              Shows how much variation in HUI is explained by the model.
              Higher is better.
            </p>
          </div>
        </div>

        <div className="section-actions split-actions">
          <button
            className="secondary-button"
            type="button"
            onClick={() => setActiveSection("eda")}
          >
            Back to EDA
          </button>

          <button
            className="primary-button"
            type="button"
            onClick={goToNextSection}
          >
            Continue to HUI Prediction
          </button>
        </div>
      </section>
    );
  }

  function renderPredictionSection() {
    const visibleFields = [
      {
        key: "internal_temperature_c",
        label: "Internal Temperature (°C)",
      },
      {
        key: "internal_humidity_pct",
        label: "Internal Humidity (%)",
      },
      {
        key: "co2_ppm",
        label: "CO₂ (ppm)",
      },
      {
        key: "hive_weight_kg",
        label: "Hive Weight (kg)",
      },
      {
        key: "external_temperature_c",
        label: "External Temperature (°C)",
      },
      {
        key: "external_humidity_pct",
        label: "External Humidity (%)",
      },
      {
        key: "rainfall_mm_hour",
        label: "Rainfall (mm/hour)",
      },
      {
        key: "wind_speed_mps",
        label: "Wind Speed (m/s)",
      },
      {
        key: "brood_health_score_0_100",
        label: "Brood Health Score",
      },
      {
        key: "nectar_flow_season_proxy",
        label: "Nectar Flow Indicator",
      },
    ];

    return (
      <section className="content-section">
        <div className="section-heading">
          <div>
            <p className="section-kicker">Step 3</p>
            <h2>Harvest Urgency Prediction</h2>
            <p>
              Enter hive and environmental conditions to predict the HUI,
              harvest status and recommendation.
            </p>
          </div>
        </div>

        {!sampleInput ? (
          <LoadingMessage text="Loading model input template..." />
        ) : (
          <form
            className="prediction-layout"
            onSubmit={handlePrediction}
          >
            <div className="prediction-form-card">
              <h3>Hive and environmental inputs</h3>

              <div className="form-grid">
                {visibleFields
                  .filter((field) =>
                    Object.prototype.hasOwnProperty.call(
                      formValues,
                      field.key
                    )
                  )
                  .map((field) => (
                    <label className="form-field" key={field.key}>
                      <span>{field.label}</span>

                      <input
                        type="number"
                        step="any"
                        name={field.key}
                        value={formValues[field.key] ?? ""}
                        onChange={handleInputChange}
                        required
                      />
                    </label>
                  ))}
              </div>

              <button
                className="primary-button prediction-button"
                type="submit"
                disabled={loadingPrediction}
              >
                {loadingPrediction
                  ? "Predicting..."
                  : "Predict Harvest Urgency"}
              </button>
            </div>

            <div className="prediction-result-card">
              <h3>Prediction result</h3>

              {predictionError && (
                <ErrorMessage message={predictionError} />
              )}

              {!prediction && !predictionError && (
                <p className="empty-result">
                  Enter values and run the model to view the result.
                </p>
              )}

              {prediction && (
                <>
                  <div className="hui-score">
                    <span>Predicted HUI</span>
                    <strong>{prediction.predicted_hui}</strong>
                    <small>out of 100</small>
                  </div>

                  <div className="status-result">
                    <span>Harvest Status</span>
                    <strong>{prediction.harvest_status}</strong>
                  </div>

                  <div className="recommendation-box">
                    <h4>Recommendation</h4>
                    <p>{prediction.recommendation}</p>
                  </div>

                  <p className="disclaimer">
                    {prediction.disclaimer}
                  </p>
                </>
              )}
            </div>
          </form>
        )}

        <div className="section-actions">
          <button
            className="secondary-button"
            type="button"
            onClick={() => setActiveSection("comparison")}
          >
            Back to Model Comparison
          </button>
        </div>
      </section>
    );
  }

  return (
    <div className="harvest-page">
      <header className="harvest-header">
        <div>
          <p className="page-kicker">Honey Harvesting Module</p>
          <h1>Harvest Urgency Analysis and Prediction</h1>
          <p>
            Explore the data, compare regression models and use the
            selected model to predict harvest urgency.
          </p>
        </div>
      </header>

      <nav className="harvest-step-navigation">
        {sections.map((section) => (
          <button
            key={section.id}
            type="button"
            className={
              activeSection === section.id
                ? "step-button active"
                : "step-button"
            }
            onClick={() => setActiveSection(section.id)}
          >
            {section.label}
          </button>
        ))}
      </nav>

      {activeSection === "eda" && renderEdaSection()}
      {activeSection === "comparison" &&
        renderModelComparisonSection()}
      {activeSection === "prediction" &&
        renderPredictionSection()}
    </div>
  );
}

function formatMetric(value) {
  if (value === null || value === undefined) {
    return "N/A";
  }

  const numberValue = Number(value);

  if (Number.isNaN(numberValue)) {
    return String(value);
  }

  return numberValue.toFixed(4);
}

function formatImageTitle(fileName) {
  return fileName
    .replace(/\.[^/.]+$/, "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}
function getStatusClass(status) {
  if (status === "Optimal/Emergency") {
    return "status-optimal";
  }

  if (status === "Ready") {
    return "status-ready";
  }

  if (status === "Approaching") {
    return "status-approaching";
  }

  return "status-not-ready";
}

function getSelectedHiveAdvice(hive) {
  if (!hive) {
    return "No hive is currently selected.";
  }

  if (hive.status === "Optimal/Emergency") {
    return (
      "The hive has a high harvest urgency score. Confirm capped " +
      "honey, weather conditions and colony health before harvesting."
    );
  }

  if (hive.status === "Ready") {
    return (
      "The hive appears ready. Arrange a beekeeper inspection and " +
      "consider harvesting within the next few days."
    );
  }

  if (hive.plateau_detected) {
    return (
      "A stable high-weight period was detected. Continue close " +
      "monitoring because a suitable harvest window may be approaching."
    );
  }

  if (hive.weight_change_24h > 0) {
    return (
      "Hive weight is still increasing. Nectar or honey accumulation " +
      "may still be continuing, so harvesting may be premature."
    );
  }

  return (
    "Current indicators do not show strong harvest readiness. " +
    "Continue monitoring hive weight, humidity and weather conditions."
  );
}

export default HarvestingModule;



