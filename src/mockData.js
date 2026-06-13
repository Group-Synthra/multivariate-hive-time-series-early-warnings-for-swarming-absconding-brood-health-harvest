// Mock Data Generator for Hive EDA Dashboard
// Generates realistic telemetry for 5 hives over a 30-day period with 1-hour intervals.

export function generateMockData() {
  const hives = ['hive41', 'hive42', 'hive43', 'hive44', 'hive45'];
  const sensors = ['co2', 'temp', 'humidity', 'weight'];
  
  const data = [];
  const startDate = new Date(2026, 5, 1); // June 1, 2026
  
  // Create a 30-day hourly time series
  const totalHours = 30 * 24;
  
  hives.forEach((hive, hiveIdx) => {
    let currentWeight = 30 + hiveIdx * 5; // Starting weight around 30-50 kg
    let weightTrend = 0.02; // General weight gain from honey collection
    let abscondingTimer = -1;
    let swarmingHour = 12 + Math.floor(Math.random() * 12); // Swarming day 15 hour
    const swarmingDay = 14 + hiveIdx * 3; // Swarming day spread across hives
    
    // Some hives have anomalies, some don't
    const isAbscondingHive = hive === 'hive45';
    const isSwarmingHive = hive === 'hive41' || hive === 'hive43';
    const isUnstableHive = hive === 'hive44'; // poor brood temp regulation
    
    for (let h = 0; h < totalHours; h++) {
      const timestamp = new Date(startDate.getTime() + h * 60 * 60 * 1000);
      const day = Math.floor(h / 24);
      const hour = h % 24;
      
      // Diurnal profiles
      const timeOfDayFactor = Math.sin((hour - 6) / 24 * 2 * Math.PI); // Peak at 12pm, trough at 12am
      const tempDiurnal = 34.5 + 1.2 * timeOfDayFactor; // standard interior hive temp oscillates slightly
      const humidityDiurnal = 58 - 5 * timeOfDayFactor; // humidity inversely related to temp
      const co2Diurnal = 600 + 150 * timeOfDayFactor; // CO2 slightly higher during peak activity
      
      // Base values
      let temp = tempDiurnal;
      let humidity = humidityDiurnal;
      let co2 = co2Diurnal;
      
      // Weight logic (gradual increase, then possible harvest or swarm drops)
      if (isAbscondingHive && day >= 20) {
        // Absconding behavior: gradual decline in weight (bees leaving), fluctuating temperature
        if (abscondingTimer === -1) abscondingTimer = h;
        currentWeight -= 0.05 + 0.02 * Math.random();
        temp = 34.5 + 3.0 * Math.sin(h / 6) + (Math.random() - 0.5) * 1.5; // highly unstable temp
        humidity = 58 + 15 * Math.sin(h / 8) + (Math.random() - 0.5) * 5;
        co2 = Math.max(300, co2 - 5 * (h - abscondingTimer)); // dropping CO2 levels
      } else if (isSwarmingHive && day === swarmingDay && hour === swarmingHour) {
        // Swarming event: sudden weight drop (-3kg), CO2 spike (+1200ppm), Temp spike (+1.5C)
        currentWeight -= 3.2;
        co2 += 1400;
        temp += 1.8;
        humidity -= 8;
      } else if (day === 25 && hour === 8 && hive === 'hive42') {
        // Honey Harvest Event: sudden massive weight drop of 15kg (honey supers removed)
        currentWeight -= 15.0;
        co2 += 200; // brief spike due to beekeeper disturbance
        temp -= 1.5; // hive opened, temp dropped
      } else {
        // Normal weight gain
        currentWeight += weightTrend + (Math.random() - 0.45) * 0.03;
      }
      
      // Add random sensor noise and outliers
      // CO2 outliers (5% probability of spike/noise)
      if (Math.random() < 0.03) {
        co2 += (Math.random() > 0.5 ? 800 : -300);
      }
      
      // Temp outliers (10% outliers due to sensor noise or opening hive)
      if (isUnstableHive) {
        temp += (Math.random() - 0.5) * 2.5; // hive 44 is poorly regulated
      } else {
        if (Math.random() < 0.05) {
          temp += (Math.random() > 0.5 ? 4.5 : -5.0);
        }
      }
      
      // Humidity outliers (10% outliers)
      if (Math.random() < 0.06) {
        humidity += (Math.random() > 0.5 ? 20 : -22);
      }
      
      // Keep weight within reasonable bounds and limit weight outliers (<1%)
      if (Math.random() < 0.005) {
        currentWeight += (Math.random() > 0.5 ? 2.5 : -2.5); // small weight spikes (e.g. landing board crowd)
      }
      
      // Bound checking
      co2 = Math.round(Math.max(200, Math.min(4000, co2)));
      temp = Math.round(Math.min(45, Math.max(15, temp)) * 10) / 10;
      humidity = Math.round(Math.min(100, Math.max(10, humidity)) * 10) / 10;
      currentWeight = Math.round(Math.max(10, currentWeight) * 100) / 100;
      
      data.push({
        timestamp: timestamp.toISOString(),
        hive,
        co2,
        temp,
        humidity,
        weight: currentWeight,
        co2_trend: Math.round((co2 * 0.9 + 500 * 0.1) * 10) / 10,
        temp_trend: Math.round(temp * 10) / 10,
        weight_change: h > 0 && data[data.length - 1]?.hive === hive 
          ? Math.round((currentWeight - data[data.length - 1].weight) * 100) / 100
          : 0,
        temp_deviation: Math.round((temp - 35) * 10) / 10
      });
    }
  });
  
  return data;
}
