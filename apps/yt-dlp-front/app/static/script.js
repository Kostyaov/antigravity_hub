document.addEventListener('DOMContentLoaded', () => {
    const videoUrlInput = document.getElementById('videoUrl');
    const downloadBtn = document.getElementById('downloadBtn');
    const updateBtn = document.getElementById('updateBtn');

    const progressContainer = document.getElementById('progressContainer');
    const speedTxt = document.getElementById('speedTxt');
    const etaTxt = document.getElementById('etaTxt');
    const progressBar = document.getElementById('progressBar');
    const progressTxt = document.getElementById('progressTxt');

    const consoleOutput = document.getElementById('consoleOutput');
    const downloadLinkContainer = document.getElementById('downloadLinkContainer');
    const formatSelect = document.getElementById('formatSelect');
    const includeAudio = document.getElementById('includeAudio');
    const audioOption = document.getElementById('audioOption');
    const includeSubtitles = document.getElementById('includeSubtitles');

    const replaceAudioBtn = document.getElementById('replaceAudioBtn');
    const refreshFilesBtn = document.getElementById('refreshFilesBtn');
    const openFolderBtn = document.getElementById('openFolderBtn');

    let ws;

    function initWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('WebSocket connection established');
        };

        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            handleWebSocketMessage(msg);
        };

        ws.onclose = () => {
            console.log('WebSocket connection closed, attempting to reconnect...');
            setTimeout(initWebSocket, 2000); // Перепідключення через 2 секунди
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    function handleWebSocketMessage(msg) {
        if (msg.type === 'log') {
            appendLog(msg.data.message);
        } else if (msg.type === 'progress') {
            updateProgress(msg.data);
        } else if (msg.type === 'finished') {
            appendLog(msg.data.message);
            showDownloadLink();
            resetUIState();
            loadFiles(); // Автоматично оновлюємо списки файлів після завантаження
        } else if (msg.type === 'error') {
            appendLog(`❌ ${msg.data.message}`);
            resetUIState();
        }
    }

    function appendLog(message) {
        const div = document.createElement('div');
        div.className = 'log-line';
        div.textContent = `> ${message}`;
        consoleOutput.appendChild(div);
        // Автоматична прокрутка донизу
        consoleOutput.scrollTop = consoleOutput.scrollHeight;
    }

    function updateProgress(data) {
        let percent = data.percent;
        // Очищення ANSI escape-кодів, які іноді передає yt-dlp
        percent = percent.replace(/\x1b\[.*?m/g, '').trim();

        // Видалення знаку % для зручного встановлення ширини CSS
        const numPercent = parseFloat(percent.replace('%', ''));

        if (!isNaN(numPercent)) {
            progressBar.style.width = `${numPercent}%`;
            progressTxt.textContent = `${numPercent.toFixed(1)}%`;
        } else {
            // Можливо це мітка часу від FFMPEG (напр. 00:00:10.50)
            progressBar.style.width = '100%';
            progressTxt.textContent = percent;
        }

        speedTxt.textContent = `Speed: ${data.speed.replace(/\x1b\[.*?m/g, '').trim()}`;
        etaTxt.textContent = `ETA: ${data.eta.replace(/\x1b\[.*?m/g, '').trim()}`;

        if (progressContainer.classList.contains('hidden')) {
            progressContainer.classList.remove('hidden');
        }
    }

    function showDownloadLink() {
        downloadLinkContainer.classList.remove('hidden');
    }

    function resetUIState() {
        downloadBtn.disabled = false;
        downloadBtn.textContent = 'Download';
        videoUrlInput.disabled = false;
    }

    downloadBtn.addEventListener('click', async () => {
        const url = videoUrlInput.value.trim();
        if (!url) {
            alert('Please enter a valid YouTube URL');
            return;
        }

        // Скидання UI
        consoleOutput.innerHTML = '';
        progressContainer.classList.add('hidden');
        downloadLinkContainer.classList.add('hidden');
        progressBar.style.width = '0%';
        progressTxt.textContent = '0%';

        downloadBtn.disabled = true;
        downloadBtn.textContent = 'Downloading...';
        videoUrlInput.disabled = true;

        try {
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: url,
                    format: formatSelect.value,
                    include_audio: includeAudio.checked,
                    include_subtitles: includeSubtitles.checked
                })
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Download failed to start');
            }

            appendLog(`Request sent for URL: ${url}`);
        } catch (error) {
            appendLog(`Error: ${error.message}`);
            resetUIState();
        }
    });

    updateBtn.addEventListener('click', async () => {
        try {
            consoleOutput.innerHTML = '';
            appendLog('Sending update request...');
            updateBtn.disabled = true;

            const response = await fetch('/api/update', {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error('Update request failed');
            }
        } catch (error) {
            appendLog(`Error: ${error.message}`);
        } finally {
            // Ми не вмикаємо кнопку автоматично тут, оскільки процес оновлення потребує часу
            // Ми вмикаємо її після короткої затримки
            setTimeout(() => { updateBtn.disabled = false; }, 10000);
        }
    });

    formatSelect.addEventListener('change', () => {
        if (formatSelect.value === 'mp3' || formatSelect.value === 'original_audio') {
            audioOption.classList.add('hidden');
        } else {
            audioOption.classList.remove('hidden');
        }
    });

    // FFMPEG Editor Logic

    async function loadFiles() {
        try {
            const response = await fetch('/api/files_list');
            const data = await response.json();
            
            const optionsHtml = '<option value="">Select file from Downloads...</option>' + 
                data.files.map(f => `<option value="${f}">${f}</option>`).join('');
                
            filePicker1.innerHTML = optionsHtml;
            filePicker2.innerHTML = optionsHtml;
        } catch (e) {
            console.error('Failed to load files:', e);
        }
    }
    
    refreshFilesBtn.addEventListener('click', loadFiles);

    openFolderBtn.addEventListener('click', async () => {
        try {
            await fetch('/api/open_folder');
        } catch (error) {
            console.error('Failed to open folder:', error);
        }
    });

    replaceAudioBtn.addEventListener('click', async () => {
        const video = filePicker1.value;
        const audio = filePicker2.value;
        if (!video || !audio) {
            alert('Please select both File 1 (Video) and File 2 (Audio)');
            return;
        }
        
        consoleOutput.innerHTML = '';
        appendLog(`Requesting Audio Replace for: ${video} + ${audio}`);
        
        try {
            const response = await fetch('/api/ffmpeg/replace', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    video_path: video,
                    audio_path: audio
                })
            });
            if (!response.ok) throw new Error('Failed to start FFMPEG Replace Audio');
        } catch (error) {
            appendLog(`Error: ${error.message}`);
        }
    });

    // Ініціалізація
    loadFiles();
    initWebSocket();
});
