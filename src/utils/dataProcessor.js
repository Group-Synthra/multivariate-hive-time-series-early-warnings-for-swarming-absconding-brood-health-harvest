// Data Processor Utility for Hive EDA Dashboard
// Processes raw data arrays to generate statistical summaries, outlier ranges, correlation matrices,
// multi-hive comparisons, temporal patterns, and module-specific metrics.

export function processHiveData(data) {
  if (!data || data.length === 0) return null;

  const sensors = ['co2', 'temp', 'humidity', 'weight'];
  const sensorNames = {
    co2: 'CO2 (ppm)',
    temp: 'Temperature (°C)',
    humidity: 'Humidity (%)',
    weight: 'Weight (kg)'
  };

  // 1. Helper Stats Functions
  const getMean = arr => arr.reduce((a, b) => a + b, 0) / arr.length;
  const getStdDev = (arr, mean) => {
    const variance = arr.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / (arr.length - 1);
    return Math.sqrt(variance);
  };
  const getPercentile = (sortedArr, p) => {
    const pos = (sortedArr.length - 1) * p;
    const base = Math.floor(pos);
    const rest = pos - base;
    if (sortedArr[base + 1] !== undefined) {
      return sortedArr[base] + rest * (sortedArr[base + 1] - sortedArr[base]);
    } else {
      return sortedArr[base];
    }
  };

  // Extract valid numerical values for each sensor
  const sensorValues = {};
  sensors.forEach(sensor => {
    sensorValues[sensor] = data
      .map(d => parseFloat(d[sensor]))
      .filter(val => !isNaN(val));
  });

  // 2. Outlier Analysis and Overall Statistics
  const outlierResults = {};
  const overallStats = {};

  sensors.forEach(sensor => {
    const vals = [...sensorValues[sensor]].sort((a, b) => a - b);
    const n = vals.length;
    
    if (n === 0) return;

    const min = vals[0];
    const max = vals[n - 1];
    const mean = getMean(vals);
    const std = getStdDev(vals, mean) || 0;
    
    const Q1 = getPercentile(vals, 0.25);
    const Q3 = getPercentile(vals, 0.75);
    const median = getPercentile(vals, 0.5);
    const IQR = Q3 - Q1;
    const lowerBound = Q1 - 1.5 * IQR;
    const upperBound = Q3 + 1.5 * IQR;

    // Identify outliers
    const outliers = vals.filter(v => v < lowerBound || v > upperBound);
    const outlierCount = outliers.length;
    const outlierPercent = (outlierCount / n) * 100;

    outlierResults[sensor] = {
      sensor,
      displayName: sensorNames[sensor],
      Q1: Math.round(Q1 * 100) / 100,
      Q3: Math.round(Q3 * 100) / 100,
      IQR: Math.round(IQR * 100) / 100,
      lowerBound: Math.round(lowerBound * 100) / 100,
      upperBound: Math.round(upperBound * 100) / 100,
      outlierCount,
      outlierPercent: Math.round(outlierPercent * 100) / 100
    };

    overallStats[sensor] = {
      sensor,
      displayName: sensorNames[sensor],
      mean: Math.round(mean * 100) / 100,
      std: Math.round(std * 100) / 100,
      min: Math.round(min * 100) / 100,
      q1: Math.round(Q1 * 100) / 100,
      median: Math.round(median * 100) / 100,
      q3: Math.round(Q3 * 100) / 100,
      max: Math.round(max * 100) / 100
    };
  });

  // 3. Correlation Matrix
  const correlationFeatures = ['co2', 'temp', 'humidity', 'weight', 'co2_trend', 'temp_trend', 'weight_change'];
  const validFeatures = correlationFeatures.filter(feat => data.some(d => d[feat] !== undefined && !isNaN(parseFloat(d[feat]))));
  
  const corrMatrix = {};
  validFeatures.forEach(feat1 => {
    corrMatrix[feat1] = {};
    validFeatures.forEach(feat2 => {
      const pairs = data
        .map(d => [parseFloat(d[feat1]), parseFloat(d[feat2])])
        .filter(p => !isNaN(p[0]) && !isNaN(p[1]));

      if (pairs.length < 2) {
        corrMatrix[feat1][feat2] = 0;
        return;
      }

      const mean1 = getMean(pairs.map(p => p[0]));
      const mean2 = getMean(pairs.map(p => p[1]));

      let num = 0;
      let den1 = 0;
      let den2 = 0;

      pairs.forEach(p => {
        const diff1 = p[0] - mean1;
        const diff2 = p[1] - mean2;
        num += diff1 * diff2;
        den1 += diff1 * diff1;
        den2 += diff2 * diff2;
      });

      const denom = Math.sqrt(den1 * den2);
      corrMatrix[feat1][feat2] = denom === 0 ? 0 : Math.round((num / denom) * 100) / 100;
    });
  });

  // 4. Multi-Hive Comparison
  const hives = [...new Set(data.map(d => d.hive).filter(Boolean))];
  const hiveComparison = hives.map(hive => {
    const hiveRows = data.filter(d => d.hive === hive);
    const summary = { hive };
    
    sensors.forEach(sensor => {
      const vals = hiveRows.map(d => parseFloat(d[sensor])).filter(v => !isNaN(v));
      if (vals.length > 0) {
        vals.sort((a, b) => a - b);
        summary[sensor] = {
          mean: Math.round(getMean(vals) * 100) / 100,
          median: Math.round(getPercentile(vals, 0.5) * 100) / 100,
          min: Math.round(vals[0] * 100) / 100,
          max: Math.round(vals[vals.length - 1] * 100) / 100,
          q1: Math.round(getPercentile(vals, 0.25) * 100) / 100,
          q3: Math.round(getPercentile(vals, 0.75) * 100) / 100
        };
      }
    });
    return summary;
  });

  // 5. Temporal Patterns
  const temporalData = {
    hourly: Array.from({ length: 24 }, (_, hour) => ({ hour, co2: [], temp: [], humidity: [], weight: [] })),
    dayOfWeek: Array.from({ length: 7 }, (_, dow) => ({ dow, co2: [], temp: [], humidity: [], weight: [] }))
  };

  data.forEach(d => {
    if (!d.timestamp) return;
    const date = new Date(d.timestamp);
    if (isNaN(date.getTime())) return;
    
    const hour = date.getHours();
    const dow = date.getDay(); // 0 is Sunday, 1 is Monday...

    sensors.forEach(sensor => {
      const val = parseFloat(d[sensor]);
      if (!isNaN(val)) {
        temporalData.hourly[hour][sensor].push(val);
        temporalData.dayOfWeek[dow][sensor].push(val);
      }
    });
  });

  // Post-process temporal patterns into averages
  const hourlyPatterns = temporalData.hourly.map((h, i) => {
    const result = { hour: i };
    sensors.forEach(sensor => {
      result[sensor] = h[sensor].length > 0 ? Math.round(getMean(h[sensor]) * 100) / 100 : 0;
    });
    return result;
  });

  const dailyPatterns = temporalData.dayOfWeek.map((d, i) => {
    const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const result = { day: dayNames[i], dayIndex: i };
    sensors.forEach(sensor => {
      result[sensor] = d[sensor].length > 0 ? Math.round(getMean(d[sensor]) * 100) / 100 : 0;
    });
    return result;
  });

  // 6. Anomalies & Warnings
  // Flag temp deviations (>1C deviation from optimal 35C), weight drops (<-0.5kg), CO2 spikes (>1000ppm trend)
  const anomalies = data
    .map((d, idx) => {
      const tempDev = Math.abs(parseFloat(d.temp) - 35);
      const weightChange = parseFloat(d.weight_change) || 0;
      const co2Trend = parseFloat(d.co2_trend) || 0;
      const isCo2Spike = co2Trend > 1000 || parseFloat(d.co2) > 1800;
      const isWeightDrop = weightChange < -0.5;
      const isTempAnomaly = tempDev > 1.5;

      if (isCo2Spike || isWeightDrop || isTempAnomaly) {
        return {
          timestamp: d.timestamp,
          hive: d.hive,
          co2: d.co2,
          temp: d.temp,
          humidity: d.humidity,
          weight: d.weight,
          co2Trend,
          weightChange,
          tempDev,
          flags: {
            co2Spike: isCo2Spike,
            weightDrop: isWeightDrop,
            tempAnomaly: isTempAnomaly
          }
        };
      }
      return null;
    })
    .filter(Boolean);

  // 7. Module-Specific Calculations
  
  // MODULE 1: Brood Health
  // Calculate percentage of time each hive is in optimal range (temp: 34-36C, humidity: 50-65%)
  const broodHealth = hives.map(hive => {
    const hiveRows = data.filter(d => d.hive === hive);
    const total = hiveRows.length;
    
    const optimalTempCount = hiveRows.filter(d => {
      const t = parseFloat(d.temp);
      return t >= 34 && t <= 36;
    }).length;

    const optimalHumidityCount = hiveRows.filter(d => {
      const h = parseFloat(d.humidity);
      return h >= 50 && h <= 65;
    }).length;

    const optimalBothCount = hiveRows.filter(d => {
      const t = parseFloat(d.temp);
      const h = parseFloat(d.humidity);
      return t >= 34 && t <= 36 && h >= 50 && h <= 65;
    }).length;

    return {
      hive,
      optimalTempPct: total > 0 ? Math.round((optimalTempCount / total) * 100) : 0,
      optimalHumidityPct: total > 0 ? Math.round((optimalHumidityCount / total) * 100) : 0,
      optimalBothPct: total > 0 ? Math.round((optimalBothCount / total) * 100) : 0,
      avgTemp: total > 0 ? Math.round(getMean(hiveRows.map(d => parseFloat(d.temp)).filter(v => !isNaN(v))) * 10) / 10 : 0,
      avgHumidity: total > 0 ? Math.round(getMean(hiveRows.map(d => parseFloat(d.humidity)).filter(v => !isNaN(v))) * 10) / 10 : 0,
      status: (optimalBothCount / total) > 0.8 ? 'Excellent' : (optimalBothCount / total) > 0.5 ? 'Good' : 'Needs Attention'
    };
  });

  // MODULE 2: Colony Swarming Prediction
  // Look for sudden weight drops (<-0.5kg) followed/co-occurring with CO2 spikes
const swarmingEvents = anomalies.filter(anom => anom.flags.weightDrop && (anom.flags.co2Spike || anom.flags.tempAnomaly));

  // MODULE 3: Absconding Behavior Prediction
  // Look for steady decline in weight over a window of several days, along with decreasing CO2
  const abscondingAnalysis = hives.map(hive => {
    const hiveRows = data.filter(d => d.hive === hive).sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    
    // Check weight slope in last 20% of data
    const len = hiveRows.length;
    const checkLen = Math.floor(len * 0.2); // last 20%
    if (checkLen < 10) return { hive, slope: 0, status: 'Normal' };

    const startIdx = len - checkLen;
    const endIdx = len - 1;
    
    const weightStart = parseFloat(hiveRows[startIdx].weight);
    const weightEnd = parseFloat(hiveRows[endIdx].weight);
    const weightDiff = weightEnd - weightStart;
    
    const co2Start = parseFloat(hiveRows[startIdx].co2);
    const co2End = parseFloat(hiveRows[endIdx].co2);
    const co2Diff = co2End - co2Start;

    let status = 'Normal';
    if (weightDiff < -2.0 && co2Diff < -100) {
      status = 'High Risk - Hive Depopulating';
    } else if (weightDiff < -1.0) {
      status = 'Warning - Moderate Weight Decline';
    }

    return {
      hive,
      weightChangePeriod: Math.round(weightDiff * 100) / 100,
      co2ChangePeriod: Math.round(co2Diff),
      status
    };
  });

  // MODULE 4: Honey Harvesting
  // Look for weight plateauing and sudden harvest drops
  const harvestingAnalysis = hives.map(hive => {
    const hiveRows = data.filter(d => d.hive === hive).sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    const weights = hiveRows.map(d => parseFloat(d.weight)).filter(w => !isNaN(w));
    
    if (weights.length < 5) return { hive, currentWeight: 0, status: 'N/A' };

    const maxWeight = Math.max(...weights);
    const currentWeight = weights[weights.length - 1];
    
    // Look for harvest event: single weight drop of > 8 kg
    let harvestCount = 0;
    let lastHarvestDate = null;
    
    for (let i = 1; i < hiveRows.length; i++) {
      const prevW = parseFloat(hiveRows[i-1].weight);
      const currW = parseFloat(hiveRows[i].weight);
      if (!isNaN(prevW) && !isNaN(currW) && (currW - prevW) < -8.0) {
        // Double check it wasn't a sudden single anomaly (i.e. if it stays low)
        const nextW = hiveRows[i+3] ? parseFloat(hiveRows[i+3].weight) : currW;
        if (!isNaN(nextW) && nextW < prevW - 5.0) {
          harvestCount++;
          lastHarvestDate = hiveRows[i].timestamp;
        }
      }
    }

    // Determine if weight is plateauing (ready for harvest)
    // Weight is high (say > 80% of max weight) and change in last 5 days is very small (abs change < 0.2kg)
    const last5Days = hiveRows.slice(-120); // roughly 5 days if hourly
    const weights5 = last5Days.map(d => parseFloat(d.weight)).filter(w => !isNaN(w));
    let isPlateauing = false;
    let harvestReadiness = 'Not Ready';

    if (weights5.length > 24) {
      const minW5 = Math.min(...weights5);
      const maxW5 = Math.max(...weights5);
      const range5 = maxW5 - minW5;
      
      // If weight is stable and near maximum
      if (range5 < 0.5 && currentWeight > 25) {
        isPlateauing = true;
        harvestReadiness = 'Optimal Harvest Window';
      } else if (currentWeight > 35) {
        harvestReadiness = 'Nearing Capacity';
      }
    }

    return {
      hive,
      currentWeight: Math.round(currentWeight * 10) / 10,
      maxWeight: Math.round(maxWeight * 10) / 10,
      harvestCount,
      lastHarvestDate: lastHarvestDate ? new Date(lastHarvestDate).toLocaleDateString() : 'None',
      status: harvestReadiness,
      isPlateauing
    };
  });

  return {
    rawLength: data.length,
    hives,
    outliers: outlierResults,
    overallStats,
    correlation: corrMatrix,
    hiveComparison,
    temporal: {
      hourly: hourlyPatterns,
      daily: dailyPatterns
    },
    anomalies: anomalies.slice(0, 100), // cap at 100
    broodHealth,
    swarmingEvents,
    abscondingAnalysis,
    harvestingAnalysis
  };
}
