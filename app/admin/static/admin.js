/**
 * Admin Console - JavaScript
 * Runs-based Records table (source: /admin/api/runs)
 */

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadRuns();

    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) refreshBtn.addEventListener('click', loadRuns);
});

async function loadRuns() {
    const listContainer = document.getElementById('edr-list');
    if (!listContainer) return;

    listContainer.innerHTML = '<p class="loading">Loading...</p>';

    try {
        const res = await fetch('/admin/api/runs', { cache: 'no-store' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const runs = await res.json();

        if (!Array.isArray(runs) || runs.length === 0) {
            listContainer.innerHTML = '<p class="empty">No records found.</p>';
            return;
        }

        renderRunsTable(runs);
    } catch (err) {
        console.error('Failed to load records:', err);
        listContainer.innerHTML = '<p class="error">Failed to load records.</p>';
    }
}

function renderRunsTable(runs) {
    const listContainer = document.getElementById('edr-list');
    listContainer.innerHTML = '';

    // Header row
    const header = document.createElement('div');
    header.className = 'edr-item';
    header.innerHTML = `
        <div class="edr-item-header" style="display:grid;grid-template-columns:140px 220px 1fr 1fr 80px;gap:12px;align-items:center;">
            <strong>Status</strong>
            <strong>Created</strong>
            <strong>Name</strong>
            <strong>Email</strong>
            <strong>Chat Log</strong>
        </div>
    `;
    listContainer.appendChild(header);

    // Data rows
    runs.forEach((run) => {
        const row = document.createElement('div');
        row.className = 'edr-item';

        const status = (run.eligibility_status || 'unknown');
        const statusClass = `status-${String(status).replace('_', '-')}`;

        const created = run.created_at ? new Date(run.created_at).toLocaleString() : '—';
        const fullName = run.full_name || '—';
        const email = run.email || '—';

        const pdfCell = run.pdf_url
            ? `<a href="${run.pdf_url}" target="_blank" rel="noopener noreferrer">View</a>`
            : '—';

        row.innerHTML = `
            <div class="edr-item-header" style="display:grid;grid-template-columns:140px 220px 1fr 1fr 80px;gap:12px;align-items:center;">
                <span class="badge ${statusClass}">${status}</span>
                <span>${created}</span>
                <span>${escapeHtml(fullName)}</span>
                <span>${escapeHtml(email)}</span>
                <span>${pdfCell}</span>
            </div>
        `;

        // CLICK → load chat history
        row.addEventListener('click', async () => {
            console.log("ROW CLICKED", run);
            try {
                const id = run.id || run.run_id;
                const res = await fetch(`/admin/api/runs/${id}`);
                const data = await res.json();

                console.log('CHAT LOG:', data.chat_log);
                alert('Check console for chat history');
            } catch (e) {
                console.error('Failed to load run detail', e);
            }
        });

        listContainer.appendChild(row);
    });
}

function escapeHtml(value) {
    return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}
