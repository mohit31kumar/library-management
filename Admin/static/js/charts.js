    // Chart Loader with fixed bar size
    async function loadChart(api, ctxId, label, fieldX, fieldY) {
  const res = await fetch(`${API_BASE}${api}`);
  const data = await res.json();

  const labels = data.map(d => d[fieldX]);
  const values = data.map(d => d[fieldY]);

  if (charts[ctxId]) {
    charts[ctxId].data.labels = labels;
    charts[ctxId].data.datasets[0].data = values;
    charts[ctxId].update();
  } else {
    const ctx = document.getElementById(ctxId).getContext("2d");
    charts[ctxId] = new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{
          label: label,
          data: values,
          backgroundColor: "#4f46e5",
          barThickness: 30  // fixed width bars
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,  // prevents stretching
        scales: {
          x: {
            ticks: { autoSkip: false, maxRotation: 45, minRotation: 0 }
          },
          y: {
            beginAtZero: true
          }
        }
      }
    });
  }
}

  // Export Graphs as PDF 
  async function exportPDF() {
    const { jsPDF } = window.jspdf;
    const pdf = new jsPDF("p", "mm", "a4");

    const charts = [
      { id: "peakChart", title: " Peak Hours (This Week)" },
      { id: "dailyChart", title: " Daily Entries (Past 7 Days)" },
      { id: "weeklyChart", title: " Weekly Entries (Past 30 Days)" },
      { id: "monthlyChart", title: " Monthly Entries (Past 12 Months)" }
    ];

    let chartIndex = 0;

    for (const chart of charts) {
      // Calculate position (top or bottom half of page)
      const isTop = chartIndex % 2 === 0;
      let y = isTop ? 20 : 150; // 20mm from top for first chart, 150mm for second chart

      // Add chart title
      pdf.setFontSize(14);
      pdf.setFont("helvetica", "bold");
      pdf.text(chart.title, 105, y, { align: "center" });
      y += 8;

      // Capture chart as image
      const canvas = document.getElementById(chart.id);
      const img = await html2canvas(canvas);
      const imgData = img.toDataURL("image/png");

      // Add chart image
      pdf.addImage(imgData, "PNG", 15, y, 180, 100);

      // If bottom half is filled, add new page
      if (!isTop) {
        pdf.addPage();
      }

      chartIndex++;
    }

    pdf.save("graphs.pdf");
  }
