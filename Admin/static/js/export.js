// Export daily logs
function exportDailyLogs() {
  window.location.href = "/export/daily";
}

  // Pre-fill dailyDate with today
  document.addEventListener('DOMContentLoaded', () => {
    const today = new Date().toISOString().slice(0, 10);
    const dailyInput = document.getElementById('dailyDate');
    if (dailyInput) dailyInput.value = today;
  });

  function exportDailyLogs() {
    const date = document.getElementById('dailyDate').value;
    if (!date) {
      alert('Please select a date for the daily export.');
      return;
    }
    // trigger browser download
    window.location.href = `/export/daily?date=${encodeURIComponent(date)}`;
  }

  function exportRangeLogs() {
    const start = document.getElementById('startDateRange').value;
    const end = document.getElementById('endDateRange').value;
    if (!start || !end) {
      alert('Please select both start and end dates for the range export.');
      return;
    }
    if (start > end) {
      alert('Start date must be earlier than or equal to end date.');
      return;
    }
    window.location.href = `/export/range?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`;
  }
