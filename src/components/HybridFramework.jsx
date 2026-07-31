import React from "react";

export default function HybridFramework() {

    const card = {
        background: "#1e293b",
        padding: "18px",
        borderRadius: "12px",
        textAlign: "center",
        minWidth: "150px",
        flex: 1,
        boxShadow: "0 4px 12px rgba(0,0,0,.3)"
    };

    return (

        <div
            style={{
                background: "#0f172a",
                borderRadius: "16px",
                padding: "30px",
                marginTop: "40px"
            }}
        >

            <h2 style={{ color: "#38bdf8" }}>
                Hybrid PELT–LSTM Prediction Framework
            </h2>

            <p style={{ color: "#cbd5e1", marginBottom: "30px" }}>
                Behavioural change points detected by the PELT algorithm are
                transformed into temporal features, which are combined with hive
                sensor measurements and supplied to the machine learning models.
                The LSTM model produced the best predictive performance and was
                selected as the final swarming prediction model.
            </p>

            <div
                style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "15px",
                    flexWrap: "wrap"
                }}
            >

                <div style={card}>
                    <br/><br/>
                    Raw Sensor Data
                </div>

                ➜

                <div style={card}>
                    <br/><br/>
                    PELT Change Detection
                </div>

                ➜

                <div style={card}>
                    <br/><br/>
                    Feature Engineering
                </div>

                ➜

                <div style={card}>
                     RF
                    <br/><br/>
                     XGB
                    <br/><br/>
                     LSTM
                </div>

                ➜

                <div
                    style={{
                        ...card,
                        background:"#123c33",
                        border:"2px solid #22c55e"
                    }}
                >
                    <br/><br/>
                    Best Model
                    <br/><br/>
                    LSTM
                </div>

            </div>

        </div>

    );

}