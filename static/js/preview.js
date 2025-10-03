// static/js/preview.js
class Preview {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.currentTab = 'front';
        this.showSafeZone = true;
        this.showBleed = true;
        this.scale = 1;
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Табы предпросмотра
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Чекбоксы управления
        document.getElementById('showSafeZone')?.addEventListener('change', (e) => {
            this.showSafeZone = e.target.checked;
            this.render();
        });

        document.getElementById('showBleed')?.addEventListener('change', (e) => {
            this.showBleed = e.target.checked;
            this.render();
        });
    }

    initCanvas() {
        const canvas = document.getElementById('previewCanvas');
        if (!canvas) return false;

        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');

        // Устанавливаем размеры canvas
        const container = canvas.parentElement;
        if (container) {
            const rect = container.getBoundingClientRect();
            canvas.width = rect.width - 40; // Отступы
            canvas.height = Math.min(400, rect.width * 0.6);
        }

        return true;
    }

    switchTab(tab) {
        this.currentTab = tab;

        // Обновляем активную кнопку
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });

        this.render();
    }

    async render() {
        if (!this.canvas && !this.initCanvas()) {
            return;
        }

        const config = app.getCurrentConfig();
        const files = fileManager.getCurrentFiles();
        const parties = app.parties;

        // Очищаем canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Если нет данных для отображения
        if ((!files.front.length && !parties.length) || !config) {
            this.showPlaceholder();
            return;
        }

        try {
            // Получаем раскладку
            const layout = await layoutCalculator.calculateLayout(config);
            if (!layout || layout.cards_total === 0) {
                this.showError('Невозможно отобразить раскладку');
                return;
            }

            this.drawLayout(layout, config);
            this.updateStats(layout);

        } catch (error) {
            this.showError('Ошибка отображения предпросмотра');
            console.error('Preview error:', error);
        }
    }

    drawLayout(layout, config) {
        const { ctx, canvas } = this;
        const { sheet_width, sheet_height, margin, bleed, card_width, card_height } = config;

        // Масштабирование
        const scaleX = (canvas.width - 40) / sheet_width;
        const scaleY = (canvas.height - 40) / sheet_height;
        this.scale = Math.min(scaleX, scaleY);

        // Смещение для центрирования
        const offsetX = (canvas.width - sheet_width * this.scale) / 2;
        const offsetY = (canvas.height - sheet_height * this.scale) / 2;

        // Очищаем canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Рисуем лист
        this.drawSheet(offsetX, offsetY, sheet_width, sheet_height);

        // Рисуем рабочую область
        this.drawWorkArea(offsetX, offsetY, sheet_width, sheet_height, margin);

        // Рисуем визитки
        layout.positions.forEach((position, index) => {
            this.drawCard(offsetX, offsetY, position, bleed, card_width, card_height, index);
        });
    }

    drawSheet(offsetX, offsetY, width, height) {
        const { ctx } = this;

        ctx.fillStyle = '#e2e8f0';
        ctx.strokeStyle = '#cbd5e1';
        ctx.lineWidth = 1;

        ctx.fillRect(offsetX, offsetY, width * this.scale, height * this.scale);
        ctx.strokeRect(offsetX, offsetY, width * this.scale, height * this.scale);
    }

    drawWorkArea(offsetX, offsetY, sheetWidth, sheetHeight, margin) {
        const { ctx } = this;

        const workX = offsetX + margin * this.scale;
        const workY = offsetY + margin * this.scale;
        const workWidth = (sheetWidth - 2 * margin) * this.scale;
        const workHeight = (sheetHeight - 2 * margin) * this.scale;

        ctx.fillStyle = 'rgba(59, 130, 246, 0.1)';
        ctx.strokeStyle = '#3b82f6';
        ctx.lineWidth = 1;
        ctx.setLineDash([5, 5]);

        ctx.fillRect(workX, workY, workWidth, workHeight);
        ctx.strokeRect(workX, workY, workWidth, workHeight);

        ctx.setLineDash([]);
    }

    drawCard(offsetX, offsetY, position, bleed, cardWidth, cardHeight, index) {
        const { ctx } = this;

        const x = offsetX + position.x * this.scale;
        const y = offsetY + position.y * this.scale;
        const width = position.width * this.scale;
        const height = position.height * this.scale;

        const innerX = x + bleed * this.scale;
        const innerY = y + bleed * this.scale;
        const innerWidth = cardWidth * this.scale;
        const innerHeight = cardHeight * this.scale;

        // Вылет под обрез
        if (this.showBleed) {
            ctx.fillStyle = 'rgba(34, 197, 94, 0.2)';
            ctx.strokeStyle = '#22c55e';
            ctx.lineWidth = 1;

            ctx.fillRect(x, y, width, height);
            ctx.strokeRect(x, y, width, height);
        }

        // Область визитки
        ctx.fillStyle = '#ffffff';
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 1;

        ctx.fillRect(innerX, innerY, innerWidth, innerHeight);
        ctx.strokeRect(innerX, innerY, innerWidth, innerHeight);

        // Безопасная зона
        if (this.showSafeZone) {
            const safeMargin = 5 * this.scale;
            const safeX = innerX + safeMargin;
            const safeY = innerY + safeMargin;
            const safeWidth = innerWidth - 2 * safeMargin;
            const safeHeight = innerHeight - 2 * safeMargin;

            ctx.strokeStyle = '#ef4444';
            ctx.lineWidth = 1;
            ctx.setLineDash([3, 3]);

            ctx.strokeRect(safeX, safeY, safeWidth, safeHeight);
            ctx.setLineDash([]);
        }

        // Номер визитки
        ctx.fillStyle = '#000000';
        ctx.font = '12px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(
            (index + 1).toString(),
            innerX + innerWidth / 2,
            innerY + innerHeight / 2
        );

        // Обрезные метки
        this.drawCropMarks(innerX, innerY, innerWidth, innerHeight);
    }

    drawCropMarks(x, y, width, height) {
        const { ctx } = this;
        const markLength = 5 * this.scale;

        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 1;
        ctx.setLineDash([]);

        // Верхний левый
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(x, y - markLength);
        ctx.moveTo(x, y);
        ctx.lineTo(x - markLength, y);
        ctx.stroke();

        // Верхний правый
        ctx.beginPath();
        ctx.moveTo(x + width, y);
        ctx.lineTo(x + width, y - markLength);
        ctx.moveTo(x + width, y);
        ctx.lineTo(x + width + markLength, y);
        ctx.stroke();

        // Нижний левый
        ctx.beginPath();
        ctx.moveTo(x, y + height);
        ctx.lineTo(x, y + height + markLength);
        ctx.moveTo(x, y + height);
        ctx.lineTo(x - markLength, y + height);
        ctx.stroke();

        // Нижний правый
        ctx.beginPath();
        ctx.moveTo(x + width, y + height);
        ctx.lineTo(x + width, y + height + markLength);
        ctx.moveTo(x + width, y + height);
        ctx.lineTo(x + width + markLength, y + height);
        ctx.stroke();
    }

    updateStats(layout) {
        document.getElementById('statCardsPerSheet').textContent = layout.cards_total;
        document.getElementById('statEfficiency').textContent = `${(layout.efficiency * 100).toFixed(1)}%`;
        document.getElementById('statRotation').textContent = layout.rotated ? 'Да' : 'Нет';
    }

    showPlaceholder() {
        const placeholder = document.getElementById('previewPlaceholder');
        const content = document.getElementById('previewContent');

        if (placeholder && content) {
            placeholder.style.display = 'block';
            content.style.display = 'none';
        }
    }

    showError(message) {
        const { ctx, canvas } = this;

        if (!ctx || !canvas) return;

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#ef4444';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(message, canvas.width / 2, canvas.height / 2);
    }

    showPreview() {
        const placeholder = document.getElementById('previewPlaceholder');
        const content = document.getElementById('previewContent');

        if (placeholder && content) {
            placeholder.style.display = 'none';
            content.style.display = 'block';
        }
    }

    handleResize() {
        if (this.canvas) {
            this.initCanvas();
            this.render();
        }
    }
}