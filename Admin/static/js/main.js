document.addEventListener("DOMContentLoaded", () => {
   // Init Dashboard
    loadLiveStats();
    loadActiveUsers();
    loadChart('/api/peak_hours_week', 'peakChart', 'Entries', 'hour', 'entries'); // weekly peak
    loadChart('/api/daily_entries', 'dailyChart', 'Entries', 'date', 'entries');
    loadChart('/api/weekly_entries', 'weeklyChart', 'Entries', 'week', 'entries');
    loadChart('/api/monthly_entries', 'monthlyChart', 'Entries', 'month', 'entries');

    // Refresh every 30s
    setInterval(() => {
      loadLiveStats();
      loadActiveUsers();
      loadChart('/api/peak_hours_week', 'peakChart', 'Entries', 'hour', 'entries');
      loadChart('/api/daily_entries', 'dailyChart', 'Entries', 'date', 'entries');
      loadChart('/api/weekly_entries', 'weeklyChart', 'Entries', 'week', 'entries');
      loadChart('/api/monthly_entries', 'monthlyChart', 'Entries', 'month', 'entries');
    }, 30000);
});