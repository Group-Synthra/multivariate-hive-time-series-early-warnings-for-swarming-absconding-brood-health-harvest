import React from "react";

export default function PipelineCard() {
    // Compact box style
    const boxStyle = {
        background: "#1e293b",
        padding: "10px 18px",
        borderRadius: "8px",
        textAlign: "center",
        minWidth: "140px",
        color: "#e2e8f0",
        fontSize: "13px",
        fontWeight: "500",
        border: "1px solid #334155",
    };

    // Model box styles (subtle color borders only)
    const modelRF = {
        ...boxStyle,
        borderColor: "#3b82f6",
    };

    const modelXGB = {
        ...boxStyle,
        borderColor: "#f59e0b",
    };

    const modelLSTM = {
        ...boxStyle,
        borderColor: "#8b5cf6",
    };

    const bestBox = {
        ...boxStyle,
        borderColor: "#22c55e",
        background: "#0a2a1a",
        color: "#22c55e",
    };

    const predBox = {
        ...boxStyle,
        borderColor: "#f472b6",
        background: "#2a1020",
        color: "#f472b6",
    };

    const arrowStyle = {
        color: "#475569",
        fontSize: "18px",
        margin: "2px 0",
    };

    const rowStyle = {
        display: "flex",
        gap: "12px",
        flexWrap: "wrap",
        justifyContent: "center",
    };

    return (
        <div
            style={{
                background: "#172554",
                padding: "16px 20px",
                borderRadius: "12px",
                marginBottom: "20px",
                border: "1px solid #1e3a5f",
            }}
        >
            {/* Title - Smaller */}
            <h3
                style={{
                    color: "#38bdf8",
                    fontSize: "16px",
                    fontWeight: "600",
                    margin: "0 0 12px 0",
                    textAlign: "center",
                }}
            >
                🔄 Hybrid Prediction Framework
            </h3>

            <div
                style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: "2px",
                }}
            >
                {/* Step 1 */}
                <div style={boxStyle}>
                    <span style={{ marginRight: "6px" }}>📡</span> Sensor Data
                </div>
                <div style={arrowStyle}>↓</div>

                {/* Step 2 */}
                <div style={boxStyle}>
                    <span style={{ marginRight: "6px" }}>🔎</span> PELT Detection
                </div>
                <div style={arrowStyle}>↓</div>

                {/* Step 3 */}
                <div style={boxStyle}>
                    <span style={{ marginRight: "6px" }}>⚙️</span> Feature Engineering
                </div>
                <div style={arrowStyle}>↓</div>

                {/* Step 4 - Models Row */}
                <div style={rowStyle}>
                    <div style={modelRF}>🌳 RF</div>
                    <div style={modelXGB}>⚡ XGB</div>
                    <div style={modelLSTM}>🧠 LSTM</div>
                </div>
                <div style={arrowStyle}>↓</div>

                {/* Step 5 */}
                <div style={bestBox}>🏆 Best Model</div>
                <div style={arrowStyle}>↓</div>

                {/* Step 6 */}
                <div style={predBox}>🐝 Swarming Prediction</div>
            </div>
        </div>
    );
}