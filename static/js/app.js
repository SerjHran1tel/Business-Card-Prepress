/**
 * Основной JavaScript для приложения импозиции визиток
 */

let sessionId = null;
let downloadUrl = null;
let fileQuantities = { front: {}, back: {} };

// Инициализация событий после загрузки DOM
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
});

function initializeEventListeners() {
    // Обработчики для загрузки файлов
    document.getElementById('frontFiles').addEventListener('change', function(e) {
        displayFileList(e.target.files, 'frontFilesList', 'front');
    });

    document.getElementById('backFiles').addEventListener('change', function(e) {
        displayFileList(e.target.files, 'backFilesList', 'back');
    });

    // Обработчики для переключения custom полей
    document.getElementById('pageFormat').addEventListener('change', toggleCustomPage);
    document.getElementById('cardSize').addEventListener('change', toggleCustomCard);
}

function displayFileList(files, containerId, side) {
    const container = document.getElementById(containerId);
    if (files.length > 0) {
        container.classList.remove('hidden');
        container.innerHTML = '';
        for (let file of files) {
            const div = document.createElement('div');
            div.className = 'file-item';

            const info = document.createElement('div');
            info.className = 'file-item-info';
            info.textContent = `📄 ${file.name} (${(file.size / 1024).toFixed(2)} KB)`;

            const quantityGroup = document.createElement('div');
            quantityGroup.className = 'file-item-quantity';

            const label = document.createElement('label');
            label.textContent = 'Количество:';

            const input = document.createElement('input');
            input.type = 'number';
            input.min = '1';
            input.value = fileQuantities[side][file.name] || 1;
            input.addEventListener('change', function() {
                fileQuantities[side][file.name] = parseInt(this.value) || 1;
            });

            quantityGroup.appendChild(label);
            quantityGroup.appendChild(input);

            div.appendChild(info);
            div.appendChild(quantityGroup);
            container.appendChild(div);

            // Инициализируем количество
            if (!fileQuantities[side][file.name]) {
                fileQuantities[side][file.name] = 1;
            }
        }
    } else {
        container.classList.add('hidden');
    }
}

function toggleCustomPage() {
    const select = document.getElementById('pageFormat');
    const group = document.getElementById('customPageGroup');
    group.classList.toggle('hidden', select.value !== 'custom');
}

function toggleCustomCard() {
    const select = document.getElementById('cardSize');
    const group = document.getElementById('customCardGroup');
    group.classList.toggle('hidden', select.value !== 'custom');
}

function showMessage(message, type = 'info') {
    const messagesDiv = document.getElementById('messages');
    const box = document.createElement('div');
    box.className = `${type}-box`;
    box.innerHTML = message;
    messagesDiv.innerHTML = '';
    messagesDiv.appendChild(box);

    setTimeout(() => {
        box.style.transition = 'opacity 0.5s';
        box.style.opacity = '0';
        setTimeout(() => box.remove(), 500);
    }, 10000);
}

function safeShowMessage(validationReport, type = 'success') {
    let message = '';

    if (validationReport && typeof validationReport === 'string') {
        message = validationReport.replace(/\n/g, '<br>');
    } else {
        message = 'PDF успешно создан!';
    }

    showMessage(`
        <strong>✅ PDF успешно создан!</strong><br>
        ${message}
    `, type);
}

function showLoader(show) {
    document.getElementById('loader').style.display = show ? 'block' : 'none';
    document.getElementById('processBtn').disabled = show;
}

function updateProgress(progress, message) {
    const progressContainer = document.getElementById('progressContainer');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');

    progressContainer.classList.remove('hidden');
    progressFill.style.width = `${progress}%`;
    progressText.textContent = `${message} (${progress}%)`;
}

async function generatePreview() {
    const data = collectFormData();
    data.session_id = sessionId;

    try {
        const response = await fetch('/preview', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (response.ok) {
            displayPreview(result);
            showMessage(`
                <strong>Расчет раскладки:</strong><br>
                Визиток на листе: ${result.cols}x${result.rows} = ${result.cards_per_sheet} шт.
            `, 'info');
        } else {
            showMessage(`Ошибка: ${result.error}`, 'error');
        }
    } catch (error) {
        showMessage(`Ошибка: ${error.message}`, 'error');
    }
}

function displayPreview(data) {
    const container = document.getElementById('previewContainer');
    const canvas = document.getElementById('previewCanvas');
    const ctx = canvas.getContext('2d');

    // Устанавливаем размер canvas
    const scale = 2;
    canvas.width = data.page_width * scale;
    canvas.height = data.page_height * scale;
    canvas.style.width = '100%';
    canvas.style.height = 'auto';

    // Очищаем canvas
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Рисуем визитки
    ctx.strokeStyle = '#667eea';
    ctx.lineWidth = 2;

    for (let row = 0; row < data.rows; row++) {
        for (let col = 0; col < data.cols; col++) {
            const x = (data.x_offset + col * (data.card_width + parseFloat(document.getElementById('gap').value))) * scale;
            const y = (data.y_offset + row * (data.card_height + parseFloat(document.getElementById('gap').value))) * scale;
            const w = data.card_width * scale;
            const h = data.card_height * scale;

            ctx.strokeRect(x, y, w, h);

            // Номер визитки
            ctx.fillStyle = '#667eea';
            ctx.font = `${12 * scale}px Arial`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(row * data.cols + col + 1, x + w/2, y + h/2);
        }
    }

    // Показываем статистику
    document.getElementById('previewInfo').innerHTML = `
        <div class="preview-stat">
            <div class="preview-stat-value">${data.cols}×${data.rows}</div>
            <div class="preview-stat-label">Сетка</div>
        </div>
        <div class="preview-stat">
            <div class="preview-stat-value">${data.cards_per_sheet}</div>
            <div class="preview-stat-label">Визиток на листе</div>
        </div>
        <div class="preview-stat">
            <div class="preview-stat-value">${data.card_width}×${data.card_height}</div>
            <div class="preview-stat-label">Размер визитки (мм)</div>
        </div>
        <div class="preview-stat">
            <div class="preview-stat-value">${data.page_width}×${data.page_height}</div>
            <div class="preview-stat-label">Размер листа (мм)</div>
        </div>
    `;

    // Отображаем превью файлов
    displayCardPreviews(data.front_previews, 'frontPreviewGrid');
    displayCardPreviews(data.back_previews, 'backPreviewGrid');

    container.style.display = 'block';
}

function displayCardPreviews(previews, gridId) {
    const grid = document.getElementById(gridId);
    grid.innerHTML = '';

    if (!previews || previews.length === 0) {
        grid.innerHTML = '<p style="text-align: center; color: #6c757d;">Нет файлов</p>';
        return;
    }

    previews.forEach(item => {
        const card = document.createElement('div');
        card.className = 'preview-card';

        if (item.preview) {
            const img = document.createElement('img');
            img.src = item.preview;
            img.alt = item.name;
            card.appendChild(img);
        }

        const label = document.createElement('div');
        label.className = 'preview-card-label';
        label.textContent = item.name;
        card.appendChild(label);

        grid.appendChild(card);
    });
}

function collectFormData() {
    return {
        page_format: document.getElementById('pageFormat').value,
        custom_page_width: document.getElementById('customPageWidth').value,
        custom_page_height: document.getElementById('customPageHeight').value,
        card_size: document.getElementById('cardSize').value,
        custom_card_width: document.getElementById('customCardWidth').value,
        custom_card_height: document.getElementById('customCardHeight').value,
        margin_top: document.getElementById('marginTop').value,
        margin_bottom: document.getElementById('marginBottom').value,
        margin_left: document.getElementById('marginLeft').value,
        margin_right: document.getElementById('marginRight').value,
        bleed: document.getElementById('bleed').value,
        gap: document.getElementById('gap').value,
        dpi: document.getElementById('dpi').value,
        output_dpi: document.getElementById('outputDpi').value,
        color_mode: document.getElementById('colorMode').value,
        crop_marks: document.getElementById('cropMarks').checked,
        matching_mode: document.getElementById('matchingMode').value,
        strict_matching: document.getElementById('strictMatching').checked,
        quantities: fileQuantities
    };
}

async function processFiles() {
    const frontFiles = document.getElementById('frontFiles').files;
    const backFiles = document.getElementById('backFiles').files;

    if (frontFiles.length === 0) {
        showMessage('Пожалуйста, загрузите файлы лицевой стороны!', 'error');
        return;
    }

    showLoader(true);

    try {
        // Загрузка файлов
        const formData = new FormData();
        for (let file of frontFiles) {
            formData.append('front_files', file);
        }
        for (let file of backFiles) {
            formData.append('back_files', file);
        }

        const uploadResponse = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const uploadResult = await uploadResponse.json();

        if (!uploadResponse.ok) {
            throw new Error(uploadResult.error);
        }

        sessionId = uploadResult.session_id;

        // Обработка
        const processData = collectFormData();
        processData.session_id = sessionId;

        const processResponse = await fetch('/process', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(processData)
        });

        const processResult = await processResponse.json();

        if (processResponse.ok) {
            // Запускаем отслеживание прогресса
            trackProgress();
        } else {
            throw new Error(processResult.error + (processResult.details ? '\n' + processResult.details : ''));
        }

    } catch (error) {
        showMessage(`Ошибка: ${error.message}`, 'error');
        showLoader(false);
    }
}

// Новая функция для отслеживания прогресса
function trackProgress() {
    const progressInterval = setInterval(async () => {
        try {
            const response = await fetch(`/progress/${sessionId}`);
            const progressData = await response.json();

            if (progressData.error) {
                clearInterval(progressInterval);
                showMessage(`Ошибка: ${progressData.error}`, 'error');
                showLoader(false);
                document.getElementById('progressContainer').classList.add('hidden');
                return;
            }

            if (progressData.progress) {
                updateProgress(progressData.progress, progressData.message);
            }

            if (progressData.progress === 100) {
                clearInterval(progressInterval);

                safeShowMessage(progressData.validation_report, 'success');

                downloadUrl = progressData.download_url;
                document.getElementById('downloadBtn').classList.remove('hidden');
                document.getElementById('progressContainer').classList.add('hidden');
                showLoader(false);
            }
        } catch (error) {
            clearInterval(progressInterval);
            showMessage(`Ошибка отслеживания прогресса: ${error.message}`, 'error');
            showLoader(false);
            document.getElementById('progressContainer').classList.add('hidden');
        }
    }, 1000); // Проверяем каждую секунду
}

function downloadFile() {
    if (downloadUrl) {
        window.location.href = downloadUrl;
        showMessage('Файл загружается...', 'success');
    }
}

// Экспорт функций для тестирования
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        displayFileList,
        toggleCustomPage,
        toggleCustomCard,
        collectFormData,
        safeShowMessage
    };
}