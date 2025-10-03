// static/js/fileManager.js
class FileManager {
    constructor() {
        this.currentFiles = {
            front: [],
            back: []
        };
        this.setupEventListeners();
    }

    setupEventListeners() {
        this.setupFileUpload('frontFiles', 'front');
        this.setupFileUpload('backFiles', 'back');
    }

    setupFileUpload(inputId, type) {
        const input = document.getElementById(inputId);
        const area = document.getElementById(`${type}UploadArea`);

        if (!input || !area) return;

        // Клик по области
        area.addEventListener('click', () => input.click());

        // Drag and drop
        area.addEventListener('dragover', (e) => {
            e.preventDefault();
            area.classList.add('dragover');
        });

        area.addEventListener('dragleave', () => {
            area.classList.remove('dragover');
        });

        area.addEventListener('drop', (e) => {
            e.preventDefault();
            area.classList.remove('dragover');
            this.handleFiles(e.dataTransfer.files, type);
        });

        // Выбор файлов
        input.addEventListener('change', (e) => {
            this.handleFiles(e.target.files, type);
        });
    }

    async handleFiles(files, type) {
        if (files.length === 0) return;

        app.showLoading(`Загрузка ${files.length} файлов...`);

        try {
            const formData = new FormData();
            for (let file of files) {
                formData.append(`${type}_files`, file);
            }

            const response = await fetch('/api/v1/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                this.currentFiles[type] = result[`${type}_files`] || [];
                this.updateFileList(type);

                let message = `Загружено ${result.file_count} файлов`;
                if (result.converted_count > 0) {
                    message += ` (${result.converted_count} сконвертировано)`;
                }

                app.showNotification(message, 'success');

                if (result.errors && result.errors.length > 0) {
                    app.showNotification(`Ошибки: ${result.errors.join(', ')}`, 'warning');
                }

                app.updatePreview();
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            app.showNotification(`Ошибка загрузки: ${error.message}`, 'error');
        } finally {
            app.hideLoading();
        }
    }

    updateFileList(type) {
        const container = document.getElementById(`${type}FileList`);
        const files = this.currentFiles[type];

        if (!container) return;

        if (files.length === 0) {
            container.innerHTML = '<div class="empty-state">Файлы не загружены</div>';
            return;
        }

        container.innerHTML = files.map(filePath => {
            const fileName = filePath.split('/').pop();
            const fileSize = 'N/A'; // В реальном приложении можно получить размер файла

            return `
                <div class="file-item">
                    <span class="file-icon">${Utils.getFileIcon(fileName)}</span>
                    <span class="file-name">${fileName}</span>
                    <span class="file-size">${fileSize}</span>
                    <button class="file-remove" onclick="fileManager.removeFile('${type}', '${filePath}')">×</button>
                </div>
            `;
        }).join('');

        this.updateFileCount();
    }

    removeFile(type, filePath) {
        this.currentFiles[type] = this.currentFiles[type].filter(f => f !== filePath);
        this.updateFileList(type);
        app.updatePreview();
    }

    updateFileCount() {
        const total = this.currentFiles.front.length + this.currentFiles.back.length;
        const badge = document.getElementById('fileCount');
        if (badge) badge.textContent = `${total} файлов`;
    }

    getCurrentFiles() {
        return this.currentFiles;
    }

    clearFiles() {
        this.currentFiles = { front: [], back: [] };
        this.updateFileList('front');
        this.updateFileList('back');
        this.updateFileCount();
    }

    async loadDemoFiles() {
        app.showLoading('Создание демо-файлов...');

        try {
            const response = await fetch('/api/v1/demo', {
                method: 'GET'
            });

            const result = await response.json();

            if (result.success) {
                this.currentFiles.front = result.front_files;
                this.currentFiles.back = result.back_files;

                this.updateFileList('front');
                this.updateFileList('back');
                app.updatePreview();

                app.showNotification('Демо-файлы успешно загружены', 'success');
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            app.showNotification(`Ошибка загрузки демо: ${error.message}`, 'error');
        } finally {
            app.hideLoading();
        }
    }
}