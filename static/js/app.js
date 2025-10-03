// static/js/app.js
class BusinessCardApp {
    constructor() {
        this.parties = [];
        this.currentConfig = this.getDefaultConfig();
        this.fileManager = new FileManager();
        this.layoutCalculator = new LayoutCalculator();
        this.pdfGenerator = new PDFGenerator();
        this.preview = new Preview();

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadFromStorage();
        this.updateUI();

        // Инициализация предпросмотра после загрузки DOM
        setTimeout(() => {
            this.preview.initCanvas();
            this.updatePreview();
        }, 100);
    }

    setupEventListeners() {
        // Обработчики изменений настроек
        this.setupConfigListeners();

        // Глобальные обработчики
        window.addEventListener('resize', () => {
            this.preview.handleResize();
        });
    }

    setupConfigListeners() {
        const configElements = [
            'sheetSize', 'cardSize', 'margin', 'bleed', 'gutter', 'dpi',
            'matchingScheme', 'customSheetWidth', 'customSheetHeight',
            'customCardWidth', 'customCardHeight', 'markLength', 'markThickness'
        ];

        configElements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('change', () => this.onConfigChange());
            }
        });

        // Чекбоксы
        const checkboxes = ['rotateCards', 'addCropMarks', 'fitProportions', 'matchByName'];
        checkboxes.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('change', () => this.onConfigChange());
            }
        });
    }

    onConfigChange() {
        this.updateConfigFromUI();
        this.updatePreview();
        this.saveToStorage();
    }

    updateConfigFromUI() {
        const config = this.currentConfig;

        // Основные настройки
        config.sheet_size = document.getElementById('sheetSize').value;
        config.card_size = document.getElementById('cardSize').value;
        config.margin = parseInt(document.getElementById('margin').value) || 5;
        config.bleed = parseInt(document.getElementById('bleed').value) || 3;
        config.gutter = parseInt(document.getElementById('gutter').value) || 2;
        config.dpi = parseInt(document.getElementById('dpi').value) || 300;
        config.matching_scheme = document.getElementById('matchingScheme').value;

        // Произвольные размеры
        config.custom_sheet_width = parseInt(document.getElementById('customSheetWidth').value) || 210;
        config.custom_sheet_height = parseInt(document.getElementById('customSheetHeight').value) || 297;
        config.custom_card_width = parseInt(document.getElementById('customCardWidth').value) || 90;
        config.custom_card_height = parseInt(document.getElementById('customCardHeight').value) || 50;

        // Чекбоксы
        config.rotate_cards = document.getElementById('rotateCards').checked;
        config.add_crop_marks = document.getElementById('addCropMarks').checked;
        config.fit_proportions = document.getElementById('fitProportions').checked;
        config.match_by_name = document.getElementById('matchByName').checked;

        // Параметры меток
        config.mark_length = parseInt(document.getElementById('markLength').value) || 5;
        config.mark_thickness = parseFloat(document.getElementById('markThickness').value) || 0.3;

        this.updateVisibility();
    }

    updateVisibility() {
        // Произвольный размер листа
        const sheetContainer = document.getElementById('customSheetContainer');
        if (sheetContainer) {
            sheetContainer.style.display = this.currentConfig.sheet_size === 'Произвольный' ? 'grid' : 'none';
        }

        // Произвольный размер визитки
        const cardContainer = document.getElementById('customCardContainer');
        if (cardContainer) {
            cardContainer.style.display = this.currentConfig.card_size === 'Произвольный' ? 'grid' : 'none';
        }
    }

    onSheetSizeChange() {
        this.updateVisibility();
        this.onConfigChange();
    }

    onCardSizeChange() {
        this.updateVisibility();
        this.onConfigChange();
    }

    getCurrentConfig() {
        // Возвращаем конфиг с вычисленными размерами
        const config = { ...this.currentConfig };

        if (config.sheet_size === 'Произвольный') {
            config.sheet_width = config.custom_sheet_width;
            config.sheet_height = config.custom_sheet_height;
        } else {
            const sheetSizes = {
                'A4': [210, 297], 'A3': [297, 420], 'A5': [148, 210],
                'SRA3': [305, 457], 'Letter': [216, 279], 'Legal': [216, 356]
            };
            const size = sheetSizes[config.sheet_size] || [210, 297];
            config.sheet_width = size[0];
            config.sheet_height = size[1];
        }

        if (config.card_size === 'Произвольный') {
            config.card_width = config.custom_card_width;
            config.card_height = config.custom_card_height;
        } else {
            const cardSizes = {
                'Стандартная (90×50)': [90, 50],
                'Евро (85×55)': [85, 55],
                'Квадратная (90×90)': [90, 90],
                'Мини (70×40)': [70, 40]
            };
            const size = cardSizes[config.card_size] || [90, 50];
            config.card_width = size[0];
            config.card_height = size[1];
        }

        return config;
    }

    getDefaultConfig() {
        return {
            sheet_size: 'A4',
            custom_sheet: false,
            custom_sheet_width: 210,
            custom_sheet_height: 297,
            card_size: 'Стандартная (90×50)',
            custom_card_width: 90,
            custom_card_height: 50,
            margin: 5,
            bleed: 3,
            gutter: 2,
            rotate_cards: false,
            add_crop_marks: true,
            mark_length: 5,
            mark_thickness: 0.3,
            matching_scheme: '1:1',
            fit_proportions: true,
            match_by_name: false,
            dpi: 300
        };
    }

    async addCurrentParty() {
        const files = this.fileManager.getCurrentFiles();

        if (files.front.length === 0) {
            this.showNotification('Добавьте лицевые стороны!', 'warning');
            return;
        }

        const quantity = parseInt(document.getElementById('quantity').value) || 1;

        const party = {
            id: Utils.generateId(),
            front_images: [...files.front],
            back_images: [...files.back],
            quantity: quantity,
            name: `Партия ${this.parties.length + 1}`,
            timestamp: new Date().toISOString()
        };

        this.parties.push(party);
        this.updatePartiesList();
        this.updatePreview();
        this.saveToStorage();

        this.showNotification(
            `Партия добавлена: ${party.front_images.length} дизайнов × ${quantity} копий`,
            'success'
        );

        // Очищаем текущие файлы
        this.fileManager.clearFiles();
    }

    updatePartiesList() {
        const container = document.getElementById('partiesList');
        const summary = document.getElementById('partiesSummary');
        const totalCards = document.getElementById('totalCards');

        if (!container) return;

        if (this.parties.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>Партии не добавлены</p>
                    <small>Добавьте файлы и нажмите "Добавить партию"</small>
                </div>
            `;
            if (summary) summary.style.display = 'none';
            return;
        }

        const total = this.parties.reduce((sum, party) => sum + (party.front_images.length * party.quantity), 0);
        if (totalCards) totalCards.textContent = total;
        if (summary) summary.style.display = 'flex';

        container.innerHTML = this.parties.map((party, index) => `
            <div class="party-item">
                <div class="party-info">
                    <strong>${party.name}</strong>
                    <div class="party-details">
                        ${party.front_images.length} дизайнов × ${party.quantity} копий = ${party.front_images.length * party.quantity} визиток
                    </div>
                </div>
                <div class="party-actions">
                    <button class="btn btn-outline btn-sm" onclick="app.removeParty('${party.id}')">Удалить</button>
                </div>
            </div>
        `).join('');
    }

    removeParty(partyId) {
        this.parties = this.parties.filter(party => party.id !== partyId);
        this.updatePartiesList();
        this.updatePreview();
        this.saveToStorage();
        this.showNotification('Партия удалена', 'success');
    }

    clearAllParties() {
        if (this.parties.length === 0) {
            this.showNotification('Нет партий для очистки', 'info');
            return;
        }

        if (confirm('Вы уверены, что хотите удалить все партии?')) {
            this.parties = [];
            this.updatePartiesList();
            this.updatePreview();
            this.saveToStorage();
            this.showNotification('Все партии удалены', 'success');
        }
    }

    async validateCurrentFiles() {
        const files = this.fileManager.getCurrentFiles();

        if (files.front.length === 0 && files.back.length === 0) {
            this.showNotification('Нет файлов для проверки', 'warning');
            return;
        }

        this.showLoading('Проверка качества файлов...');

        try {
            const config = this.getCurrentConfig();
            const request = {
                front_files: files.front,
                back_files: files.back,
                scheme: config.matching_scheme,
                card_width: config.card_width,
                card_height: config.card_height,
                bleed: config.bleed
            };

            const response = await fetch('/api/v1/validate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(request)
            });

            const result = await response.json();

            if (result.success) {
                this.showValidationReport(result.report);
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            this.showNotification(`Ошибка валидации: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    showValidationReport(report) {
        this.showModal('Отчет о проверке качества', `
            <div class="validation-report">${report}</div>
            <div class="modal-actions" style="margin-top: 20px; text-align: right;">
                <button class="btn btn-primary" onclick="app.closeModal()">Закрыть</button>
            </div>
        `);
    }

    async generatePDF() {
        try {
            const config = this.getCurrentConfig();
            await this.pdfGenerator.generateWithValidation(this.parties, config);
        } catch (error) {
            // Ошибка уже обработана в pdfGenerator
            console.error('PDF generation failed:', error);
        }
    }

    async loadDemoFiles() {
        await this.fileManager.loadDemoFiles();
    }

    async updatePreview() {
        const files = this.fileManager.getCurrentFiles();
        const hasData = files.front.length > 0 || this.parties.length > 0;

        if (hasData) {
            this.preview.showPreview();

            try {
                const config = this.getCurrentConfig();
                await this.layoutCalculator.updateLayoutInfo(config);
                await this.preview.render();
            } catch (error) {
                console.error('Preview update error:', error);
            }
        } else {
            this.preview.showPlaceholder();
        }
    }

    // UI методы
    showNotification(message, type = 'info') {
        const container = document.getElementById('notifications');
        if (!container) {
            console.log(`[${type}] ${message}`);
            return;
        }

        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <p>${message}</p>
            </div>
        `;

        container.appendChild(notification);

        // Автоматическое скрытие
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }

    showLoading(message = 'Загрузка...') {
        const statusMessage = document.getElementById('statusMessage');
        const progress = document.getElementById('statusProgress');

        if (statusMessage) statusMessage.textContent = message;
        if (progress) progress.style.display = 'flex';
    }

    hideLoading() {
        const statusMessage = document.getElementById('statusMessage');
        const progress = document.getElementById('statusProgress');

        if (statusMessage) statusMessage.textContent = 'Готов';
        if (progress) progress.style.display = 'none';
    }

    showModal(title, content) {
        const modal = document.getElementById('modalOverlay');
        const modalTitle = document.getElementById('modalTitle');
        const modalContent = document.getElementById('modalContent');

        if (modal && modalTitle && modalContent) {
            modalTitle.textContent = title;
            modalContent.innerHTML = content;
            modal.style.display = 'flex';
        }
    }

    closeModal() {
        const modal = document.getElementById('modalOverlay');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    showHelp() {
        const helpContent = document.getElementById('helpModal').innerHTML;
        this.showModal('Помощь', helpContent);
    }

    showAbout() {
        const aboutContent = document.getElementById('aboutModal').innerHTML;
        this.showModal('О программе', aboutContent);
    }

    updateUI() {
        this.updateConfigUI();
        this.updatePartiesList();
        this.updateVisibility();
    }

    updateConfigUI() {
        const config = this.currentConfig;

        // Устанавливаем значения из конфига
        document.getElementById('sheetSize').value = config.sheet_size;
        document.getElementById('cardSize').value = config.card_size;
        document.getElementById('margin').value = config.margin;
        document.getElementById('bleed').value = config.bleed;
        document.getElementById('gutter').value = config.gutter;
        document.getElementById('dpi').value = config.dpi;
        document.getElementById('matchingScheme').value = config.matching_scheme;

        document.getElementById('customSheetWidth').value = config.custom_sheet_width;
        document.getElementById('customSheetHeight').value = config.custom_sheet_height;
        document.getElementById('customCardWidth').value = config.custom_card_width;
        document.getElementById('customCardHeight').value = config.custom_card_height;

        document.getElementById('markLength').value = config.mark_length;
        document.getElementById('markThickness').value = config.mark_thickness;

        document.getElementById('rotateCards').checked = config.rotate_cards;
        document.getElementById('addCropMarks').checked = config.add_crop_marks;
        document.getElementById('fitProportions').checked = config.fit_proportions;
        document.getElementById('matchByName').checked = config.match_by_name;
    }

    // Работа с localStorage
    saveToStorage() {
        const data = {
            parties: this.parties,
            config: this.currentConfig,
            timestamp: new Date().toISOString()
        };
        Storage.set('businessCardApp', data);
    }

    loadFromStorage() {
        try {
            const data = Storage.get('businessCardApp');
            if (data) {
                this.parties = data.parties || [];
                this.currentConfig = { ...this.getDefaultConfig(), ...data.config };
                this.updateUI();
                this.updatePreview();
            }
        } catch (error) {
            console.warn('Error loading from storage:', error);
        }
    }

    clearStorage() {
        Storage.remove('businessCardApp');
    }
}

// Глобальная инициализация
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new BusinessCardApp();
});