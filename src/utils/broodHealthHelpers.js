/**
 * Calculate the start index for a given window number (0-based) and window size.
 * @param {number} windowNumber - 0,1,2...
 * @param {number} windowSize - number of records per window
 * @param {number} totalRecords - total number of records in the full array
 * @returns {number} start index for slice()
 */
export function getWindowStart(windowNumber, windowSize, totalRecords) {
  const endIndex = totalRecords - (windowNumber * windowSize);
  let startIndex = endIndex - windowSize;
  if (startIndex < 0) startIndex = 0;
  return startIndex;
}

/**
 * Get the slice of data for the current window.
 * @param {Array} fullData - complete time series array
 * @param {number} windowNumber - 0 = most recent window
 * @param {number} windowSize - records per window
 * @returns {Array} sliced array
 */
export function getWindowData(fullData, windowNumber, windowSize) {
  if (!fullData || fullData.length === 0) return [];
  const total = fullData.length;
  const start = getWindowStart(windowNumber, windowSize, total);
  return fullData.slice(start, start + windowSize);
}

/**
 * Get human-readable window description.
 */
export function getWindowDescription(fullData, windowNumber, windowSize) {
  if (!fullData || fullData.length === 0) return "No data";
  const total = fullData.length;
  const start = getWindowStart(windowNumber, windowSize, total);
  const end = Math.min(start + windowSize, total);
  return `Showing records ${start+1} – ${end} of ${total}`;
}

/**
 * Get total number of windows.
 */
export function getTotalWindows(totalRecords, windowSize) {
  return Math.ceil(totalRecords / windowSize);
}