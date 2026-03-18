/**
 * Admin Console - JavaScript
 * Runs-based Records table (source: /admin/api/runs)
 */

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadRuns();

    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) refreshBtn.addEventListener('click', loadRuns);

    // Close modal on backdrop click
    document.getElementById('chat-modal').addEventListener('click', (e) => {
        if (e.target === document.getElementById('chat-modal')) closeModal();
    });

    // Close modal on Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });
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

        row.innerHTML = `
            <div class="edr-item-header" style="display:grid;grid-template-columns:140px 220px 1fr 1fr 80px;gap:12px;align-items:center;">
                <span class="badge ${statusClass}">${status}</span>
                <span>${created}</span>
                <span>${escapeHtml(fullName)}</span>
                <span>${escapeHtml(email)}</span>
                <span><a href="#" class="view-chat-link">View</a></span>
            </div>
        `;

        // View link click -> open chat modal
        row.querySelector('.view-chat-link').addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            await openChatModal(run);
        });

        listContainer.appendChild(row);
    });
}

async function openChatModal(run) {
    const modal = document.getElementById('chat-modal');
    const modalBody = document.getElementById('chat-modal-body');
    const modalTitle = document.getElementById('chat-modal-title');

    modalBody.innerHTML = '<p style="color:#666;padding:20px;">Loading...</p>';
    modal.style.display = 'flex';

    const created = run.created_at ? new Date(run.created_at).toLocaleString() : '—';
    const status = run.eligibility_status || 'unknown';
    modalTitle.textContent = `${run.full_name || 'Anonymous'} — ${created} — ${status}`;

    try {
        const id = run.id || run.run_id;
        const res = await fetch(`/admin/api/runs/${id}`);
        const data = await res.json();

        const routing = data.answers_log || data.chat_log?.input?.routing || {};
        const entries = Object.entries(routing);

        if (entries.length === 0) {
            modalBody.innerHTML = '<p style="color:#666;padding:20px;">No answers recorded for this session.</p>';
            return;
        }

        let html = '<div style="display:flex;flex-direction:column;gap:12px;">';

        entries.forEach(([key, value]) => {
            const label = formatKey(key);
            const answer = Array.isArray(value) ? value.join(', ') : String(value ?? '—');
            html += `
                <div style="border-bottom:1px solid #f0f0f0;padding-bottom:12px;">
                    <div style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">${escapeHtml(label)}</div>
                    <div style="font-size:14px;color:#111;font-weight:500;">${escapeHtml(answer)}</div>
                </div>
            `;
        });

        html += '</div>';
        modalBody.innerHTML = html;

    } catch (e) {
        console.error('Failed to load run detail', e);
        modalBody.innerHTML = '<p style="color:#ef4444;padding:20px;">Failed to load chat log.</p>';
    }
}

function closeModal() {
    document.getElementById('chat-modal').style.display = 'none';
}

function formatKey(key) {
    return String(key)
        .replace(/_/g, ' ')
        .replace(/\./g, ' > ')
        .replace(/\b\w/g, c => c.toUpperCase());
}

function escapeHtml(value) {
    return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}
