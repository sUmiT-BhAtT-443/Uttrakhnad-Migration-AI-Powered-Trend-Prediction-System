document.getElementById("predictForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("predictBtn");
  btn.innerText = "🔄 Generating...";
  btn.disabled = true;

  const district = document.getElementById("district").value;
  const years = parseInt(document.getElementById("years").value);

  try {
    const response = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ district, years })
    });

    const data = await response.json();

    if (data.error) {
      alert("Error generating forecast: " + data.error);
      return;
    }

    document.getElementById("results").classList.remove("hidden");
    document.getElementById("inflowVal").textContent = data.inflow_pred;
    document.getElementById("outflowVal").textContent = data.outflow_pred;
    document.getElementById("growthVal").textContent = data.avg_growth + "%";

    // ensure reasons list always shows three items; backend may send fewer/more
    const defaults = ["Employment", "Education", "Climate stress"];
    const incoming = Array.isArray(data.reasons) ? data.reasons : [];
    // create a merged list: keep unique preserving incoming order then append defaults until length 3
    const merged = [];
    incoming.forEach(r => {
      if (merged.length < 3 && typeof r === 'string' && !merged.includes(r)) merged.push(r);
    });
    for (let d of defaults) {
      if (merged.length >= 3) break;
      if (!merged.includes(d)) merged.push(d);
    }

    const reasonList = document.getElementById("reasonList");
    reasonList.innerHTML = "";
    merged.forEach((r) => {
      const li = document.createElement("li");
      li.textContent = "• " + r;
      reasonList.appendChild(li);
    });

    // plotly arrays
    const yearsArr = data.table_data.map((x) => x.year);
    const inflowArr = data.table_data.map((x) => x.inflow);
    const outflowArr = data.table_data.map((x) => x.outflow);

    const traceIn = {
      x: yearsArr,
      y: inflowArr,
      name: "Inflow",
      type: "scatter",
      mode: "lines+markers",
      line: { color: "#b266ff", width: 3 },
      marker: { size: 7 },
      visible: true
    };

    const traceOut = {
      x: yearsArr,
      y: outflowArr,
      name: "Outflow",
      type: "scatter",
      mode: "lines+markers",
      line: { color: "#ff5fc3", width: 3, dash: "dot" },
      marker: { size: 7 },
      visible: true
    };

    const layout = {
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: { color: "#fff", family: "Poppins" },
      title: `Migration Forecast for ${data.district}`,
      titlefont: { size: 20, color: "#d8b4ff" },
      legend: { orientation: "h", x: 0.3, y: -0.2 },
      xaxis: { title: "Years" },
      yaxis: { title: "Migrants (Persons)" },
      transition: { duration: 600, easing: "cubic-in-out" }
    };

    // draw chart (bigger size managed by CSS)
    await Plotly.newPlot("forecastChart", [traceIn, traceOut], layout, { responsive: true });

    // reliable toggle handlers
    const btnIn = document.getElementById("toggleInflow");
    const btnOut = document.getElementById("toggleOutflow");

    function getVisible(index) {
      const gd = document.getElementById("forecastChart");
      if (!gd || !gd.data || !gd.data[index]) return true;
      const v = gd.data[index].visible;
      if (v === undefined || v === true) return true;
      return !(v === 'legendonly' || v === false);
    }
    function setVisible(index, visible) {
      const val = visible ? true : 'legendonly';
      Plotly.restyle("forecastChart", { visible: val }, [index]);
    }

    // init UI
    if (getVisible(0)) btnIn.classList.add('active'); else btnIn.classList.remove('active');
    if (getVisible(1)) btnOut.classList.add('active'); else btnOut.classList.remove('active');

    btnIn.onclick = function () {
      const cur = getVisible(0);
      setVisible(0, !cur);
      if (!cur) btnIn.classList.add('active'); else btnIn.classList.remove('active');
    };
    btnOut.onclick = function () {
      const cur = getVisible(1);
      setVisible(1, !cur);
      if (!cur) btnOut.classList.add('active'); else btnOut.classList.remove('active');
    };

    // populate table
    const tbody = document.querySelector("#forecastTable tbody");
    tbody.innerHTML = "";
    data.table_data.forEach((row) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${row.year}</td>
        <td>${row.inflow}</td>
        <td>${row.outflow}</td>
      `;
      tbody.appendChild(tr);
    });

  } catch (err) {
    alert("Error generating forecast. Try again!");
    console.error(err);
  } finally {
    btn.innerText = "🔮 Generate Forecast";
    btn.disabled = false;
  }
});
