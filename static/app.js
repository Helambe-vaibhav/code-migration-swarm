// RefactorSwarm Dashboard Interactive Engine
document.addEventListener('DOMContentLoaded', () => {
  let pollingInterval = null;
  let currentFileCache = {};
  let selectedFile = null;
  let activeTab = 'diff';

  // DOM Elements
  const btnLaunch = document.getElementById('btnLaunchSwarm');
  const globalStatusPill = document.getElementById('globalStatusPill');
  const globalStatusText = document.getElementById('globalStatusText');
  const logStream = document.getElementById('logStream');
  const modulesTableBody = document.getElementById('modulesTableBody');
  const codeDisplayArea = document.getElementById('codeDisplayArea');
  const diffViewerTitle = document.getElementById('diffViewerTitle');
  const prContentArea = document.getElementById('prContentArea');
  const hitlCard = document.getElementById('hitlCard');
  const btnHitlApprove = document.getElementById('btnHitlApprove');
  const btnHitlReject = document.getElementById('btnHitlReject');
  const tabButtons = document.querySelectorAll('.tab-btn');

  // Launch Swarm Event
  btnLaunch.addEventListener('click', async () => {
    const targetDir = document.getElementById('inputTargetDir').value.trim();
    const provider = document.getElementById('selectProvider').value;
    const maxRetries = parseInt(document.getElementById('inputMaxRetries').value, 10);
    const stack = document.getElementById('selectStack').value;

    btnLaunch.disabled = true;
    btnLaunch.innerHTML = '<span class="btn-icon">⏳</span> Launching...';

    try {
      const resp = await fetch('/api/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_dir: targetDir,
          provider: provider,
          max_retries: maxRetries,
          target_stack: stack
        })
      });
      const data = await resp.json();
      if (!resp.ok) {
        alert(data.message || 'Failed to start migration');
        btnLaunch.disabled = false;
        btnLaunch.innerHTML = '<span class="btn-icon">▶</span> Launch Autonomous Swarm';
        return;
      }

      startPolling();
    } catch (err) {
      console.error(err);
      alert('Error connecting to server.');
      btnLaunch.disabled = false;
      btnLaunch.innerHTML = '<span class="btn-icon">▶</span> Launch Autonomous Swarm';
    }
  });

  // HITL Approval Buttons
  btnHitlApprove.addEventListener('click', () => sendApproval(true));
  btnHitlReject.addEventListener('click', () => sendApproval(false));

  async function sendApproval(approved) {
    try {
      const resp = await fetch('/api/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved: approved })
      });
      const data = await resp.json();
      hitlCard.style.display = 'none';
      if (!pollingInterval) startPolling();
    } catch (err) {
      console.error(err);
    }
  }

  // Polling Status Loop
  function startPolling() {
    if (pollingInterval) clearInterval(pollingInterval);
    pollingInterval = setInterval(fetchStatus, 1200);
    fetchStatus();
  }

  async function fetchStatus() {
    try {
      const resp = await fetch('/api/status');
      if (!resp.ok) return;
      const data = await resp.json();

      updateStatusUI(data);
      updateDAGVisualizer(data.active_node);
      updateLogs(data.logs);
      updateModulesTable(data.completed_files);

      if (data.pr_summary) {
        prContentArea.textContent = data.pr_summary;
      }

      if (data.human_review_required) {
        hitlCard.style.display = 'block';
      } else {
        hitlCard.style.display = 'none';
      }

      if (!data.is_running && data.status === 'COMPLETED') {
        btnLaunch.disabled = false;
        btnLaunch.innerHTML = '<span class="btn-icon">✔</span> Migration Complete';
        clearInterval(pollingInterval);
        pollingInterval = null;
      } else if (!data.is_running && data.status === 'ERROR') {
        btnLaunch.disabled = false;
        btnLaunch.innerHTML = '<span class="btn-icon">✖</span> Error Occurred';
        clearInterval(pollingInterval);
        pollingInterval = null;
      }
    } catch (err) {
      console.error('Polling error:', err);
    }
  }

  function updateStatusUI(data) {
    globalStatusText.textContent = `${data.status} (Node: ${data.active_node || 'None'})`;
    if (data.is_running) {
      globalStatusPill.className = 'status-pill running';
    } else {
      globalStatusPill.className = 'status-pill';
    }
  }

  function updateDAGVisualizer(activeNode) {
    document.querySelectorAll('.dag-node').forEach(node => {
      node.classList.remove('active');
    });

    if (activeNode) {
      const activeEl = document.getElementById(`node_${activeNode}`);
      if (activeEl) {
        activeEl.classList.add('active');
      }
    }
  }

  let seenLogCount = 0;
  function updateLogs(logs) {
    if (!logs || logs.length === 0) return;
    if (logs.length === seenLogCount) return;

    logStream.innerHTML = '';
    logs.forEach(log => {
      const div = document.createElement('div');
      div.className = `log-entry ${log.level || 'INFO'}`;
      div.textContent = `[${log.node}] ${log.message}`;
      logStream.appendChild(div);
    });

    seenLogCount = logs.length;
    logStream.scrollTop = logStream.scrollHeight;
  }

  function updateModulesTable(completed) {
    if (!completed || completed.length === 0) {
      modulesTableBody.innerHTML = '<tr><td colspan="4" class="empty-state">No modules migrated yet. Launch the swarm to begin.</td></tr>';
      return;
    }

    modulesTableBody.innerHTML = '';
    completed.forEach((cf, idx) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${cf.file_path}</strong></td>
        <td><span style="color: var(--accent-emerald);">✔ ${cf.tests_passed}</span></td>
        <td>${cf.retries}</td>
        <td><button class="btn-view-diff" data-file="${cf.file_path}">Inspect Diff</button></td>
      `;
      modulesTableBody.appendChild(tr);
    });

    // Auto-select first completed file if none selected
    if (!selectedFile && completed.length > 0) {
      selectFileForDiff(completed[0].file_path);
    }

    // Attach click listeners to inspect diff buttons
    document.querySelectorAll('.btn-view-diff').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const file = e.target.getAttribute('data-file');
        selectFileForDiff(file);
      });
    });
  }

  async function selectFileForDiff(fileName) {
    selectedFile = fileName;
    diffViewerTitle.textContent = `Inspection: ${fileName}`;

    if (!currentFileCache[fileName]) {
      try {
        const resp = await fetch(`/api/diff/${encodeURIComponent(fileName)}`);
        if (resp.ok) {
          currentFileCache[fileName] = await resp.json();
        }
      } catch (err) {
        console.error(err);
      }
    }

    renderActiveTabContent();
  }

  // Tab switching
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      tabButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeTab = btn.getAttribute('data-tab');
      renderActiveTabContent();
    });
  });

  function renderActiveTabContent() {
    if (!selectedFile || !currentFileCache[selectedFile]) {
      codeDisplayArea.textContent = '// Select a completed module above to view details';
      return;
    }

    const fileData = currentFileCache[selectedFile];
    if (activeTab === 'diff') {
      codeDisplayArea.textContent = fileData.diff || '// No diff available';
    } else if (activeTab === 'modern') {
      codeDisplayArea.textContent = fileData.migrated_code || '// No modern code';
    } else if (activeTab === 'tests') {
      codeDisplayArea.textContent = fileData.tests || '// No tests synthesized';
    } else if (activeTab === 'legacy') {
      codeDisplayArea.textContent = fileData.legacy_code || '// No legacy code';
    }
  }

  // Initial status check
  fetchStatus();
});
