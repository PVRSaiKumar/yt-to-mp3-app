const API_URL = window.location.origin + '/api';
let currentTaskId = null;

function startDownload() {
    const urlInput = document.getElementById('playlistUrl');
    const url = urlInput.value.trim();

    if (!url) {
        showError('Please enter a YouTube URL');
        return;
    }

    if (!isValidYouTubeUrl(url)) {
        showError('Please enter a valid YouTube video URL');
        return;
    }

    hideError();
    hideFiles();
    showStatus('Downloading... This may take 10-30 seconds.', 50);
    setButtonLoading(true);

    fetch(`${API_URL}/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
    })
    .then(res => res.json().then(d => ({ ok: res.ok, data: d })))
    .then(({ ok, data }) => {
        if (!ok || data.error) {
            throw new Error(data.error || 'Server error');
        }

        currentTaskId = data.task_id;
        showStatus('Download complete!', 100);
        showFiles(data.files);
        setButtonLoading(false);
    })
    .catch(err => {
        showError(err.message || 'Failed to download');
        setButtonLoading(false);
        hideStatus();
    });
}

function showFiles(files) {
    const section = document.getElementById('filesSection');
    const list = document.getElementById('filesList');
    list.innerHTML = '';

    files.forEach(file => {
        const item = document.createElement('div');
        item.className = 'file-item';
        item.innerHTML = `
            <span class="file-name">${file.name.replace(/\.[^.]+$/, '')}</span>
            <span class="file-size">${formatSize(file.size)}</span>
            <button class="file-download" onclick="downloadFile('${file.name}')">Download</button>
        `;
        list.appendChild(item);
    });

    section.classList.remove('hidden');
}

function downloadFile(filename) {
    window.open(`${API_URL}/file/${currentTaskId}/${encodeURIComponent(filename)}`, '_blank');
}

function isValidYouTubeUrl(url) {
    const patterns = [
        /(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=[a-zA-Z0-9_-]{11}/,
        /(?:https?:\/\/)?youtu\.be\/[a-zA-Z0-9_-]{11}/,
        /(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/[a-zA-Z0-9_-]{11}/,
    ];
    return patterns.some(p => p.test(url));
}

function showStatus(text, progress) {
    const status = document.getElementById('status');
    const statusText = document.getElementById('statusText');
    const progressFill = document.getElementById('progressFill');
    status.classList.remove('hidden');
    statusText.textContent = text;
    progressFill.style.width = `${progress}%`;
}

function hideStatus() {
    document.getElementById('status').classList.add('hidden');
}

function showError(message) {
    const error = document.getElementById('error');
    error.textContent = message;
    error.classList.remove('hidden');
}

function hideError() {
    document.getElementById('error').classList.add('hidden');
}

function hideFiles() {
    document.getElementById('filesSection').classList.add('hidden');
}

function setButtonLoading(loading) {
    const btn = document.getElementById('downloadBtn');
    const text = btn.querySelector('.btn-text');
    const loader = btn.querySelector('.btn-loader');
    btn.disabled = loading;
    text.textContent = loading ? 'Processing...' : 'Download';
    loader.classList.toggle('hidden', !loading);
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

document.getElementById('playlistUrl').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') startDownload();
});