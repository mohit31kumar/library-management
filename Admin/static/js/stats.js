const API_BASE = 'http://'+location.hostname+':5001';
    const charts = {}; // store chart instances

    // Load Live Stats
    async function loadLiveStats() {
      const res = await fetch(`${API_BASE}/api/live_stats`);
      const data = await res.json();
      document.getElementById('insideCount').innerText = data.inside;
      document.getElementById('todayEntries').innerText = data.today_entries;
    }
