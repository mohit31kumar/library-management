// Generic pagination renderer
function renderTableWithPagination(data, tableId, paginationId, rowsPerPage = 10) {
  let currentPage = 1;
  const tableBody = document.querySelector(`#${tableId} tbody`);
  const paginationDiv = document.getElementById(paginationId);

  function renderPage() {
    tableBody.innerHTML = "";
    let start = (currentPage - 1) * rowsPerPage;
    let end = start + rowsPerPage;
    let paginatedItems = data.slice(start, end);

    // Render table rows
    paginatedItems.forEach(row => {
      let tr = document.createElement("tr");
      tr.innerHTML = Object.values(row).map(v => `<td>${v ?? ""}</td>`).join("");
      tableBody.appendChild(tr);
    });

    // Render pagination
    paginationDiv.innerHTML = "";
    let totalPages = Math.ceil(data.length / rowsPerPage);

    let prevBtn = document.createElement("button");
    prevBtn.innerText = "Prev";
    prevBtn.disabled = currentPage === 1;
    prevBtn.onclick = () => { currentPage--; renderPage(); };

    let nextBtn = document.createElement("button");
    nextBtn.innerText = "Next";
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.onclick = () => { currentPage++; renderPage(); };

    paginationDiv.appendChild(prevBtn);
    paginationDiv.appendChild(document.createTextNode(` Page ${currentPage} of ${totalPages} `));
    paginationDiv.appendChild(nextBtn);
  }

  renderPage();
}

// Fetch Active Users
function fetchActiveUsers() {
  fetch("/api/active_users")
    .then(res => res.json())
    .then(data => {
      renderTableWithPagination(data, "activeUsersTable", "activeUsersPagination", 10);
    })
    .catch(err => console.error("Error fetching active users:", err));
}



// Fetch User History
function fetchUserHistory() {
  let regNo = document.getElementById("regNoInput").value.trim();
  if (!regNo) return;

  fetch(`/api/user_history/${regNo}`)
    .then(res => res.json())
    .then(data => {
      renderTableWithPagination(data, "historyTable", "historyPagination", 10);
    })
    .catch(err => console.error("Error fetching user history:", err));
}

// Auto load active users on page load
document.addEventListener("DOMContentLoaded", fetchActiveUsers);
