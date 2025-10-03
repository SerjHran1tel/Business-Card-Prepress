// static/js/layoutCalculator.js
class LayoutCalculator {
    constructor() {
        this.currentLayout = null;
    }

    async calculateLayout(config) {
        try {
            const request = {
                sheet_width: config.sheet_width,
                sheet_height: config.sheet_height,
                card_width: config.card_width,
                card_height: config.card_height,
                margin: config.margin,
                bleed: config.bleed,
                gutter: config.gutter,
                rotate: config.rotate_cards
            };

            const response = await fetch('/api/v1/calculate-layout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(request)
            });

            const result = await response.json();

            if (result.success) {
                this.currentLayout = result.layout;
                return result.layout;
            } else {
                throw new Error(result.error || 'Ошибка расчета раскладки');
            }
        } catch (error) {
            console.error('Layout calculation error:', error);
            throw error;
        }
    }

    getSheetsNeeded(totalCards, cardsPerSheet) {
        if (!cardsPerSheet || cardsPerSheet === 0) return 0;
        return Math.ceil(totalCards / cardsPerSheet);
    }

    calculateEfficiency(layout, sheetWidth, sheetHeight, cardWidth, cardHeight) {
        if (!layout || layout.cards_total === 0) return 0;

        const totalCardArea = layout.cards_total * cardWidth * cardHeight;
        const sheetArea = sheetWidth * sheetHeight;

        return (totalCardArea / sheetArea) * 100;
    }

    validateLayout(layout, sheetWidth, sheetHeight, margin) {
        const warnings = [];

        if (!layout || layout.cards_total === 0) {
            warnings.push('Невозможно разместить визитки на листе с текущими параметрами');
            return warnings;
        }

        // Проверка эффективности
        if (layout.efficiency < 60) {
            warnings.push(`Низкая эффективность использования площади: ${layout.efficiency.toFixed(1)}%`);
        }

        // Проверка границ
        layout.positions.forEach((pos, index) => {
            if (pos.x < margin - 1) {
                warnings.push(`Визитка ${index + 1} слишком близко к левому краю`);
            }
            if (pos.x + pos.width > sheetWidth - margin + 1) {
                warnings.push(`Визитка ${index + 1} слишком близко к правому краю`);
            }
            if (pos.y < margin - 1) {
                warnings.push(`Визитка ${index + 1} слишком близко к верхнему краю`);
            }
            if (pos.y + pos.height > sheetHeight - margin + 1) {
                warnings.push(`Визитка ${index + 1} слишком близко к нижнему краю`);
            }
        });

        return warnings;
    }

    getLayoutInfo(layout, sheetWidth, sheetHeight, cardWidth, cardHeight) {
        if (!layout || layout.cards_total === 0) {
            return {
                cardsPerSheet: 0,
                efficiency: 0,
                rotation: false,
                warnings: ['Нет данных о раскладке']
            };
        }

        const warnings = this.validateLayout(layout, sheetWidth, sheetHeight, 5); // margin 5mm

        return {
            cardsPerSheet: layout.cards_total,
            efficiency: layout.efficiency,
            rotation: layout.rotated,
            warnings: warnings
        };
    }

    async updateLayoutInfo(config) {
        try {
            const layout = await this.calculateLayout(config);
            const info = this.getLayoutInfo(
                layout,
                config.sheet_width,
                config.sheet_height,
                config.card_width,
                config.card_height
            );

            this.updateLayoutUI(info);
            return layout;
        } catch (error) {
            this.updateLayoutUI({
                cardsPerSheet: 0,
                efficiency: 0,
                rotation: false,
                warnings: [error.message]
            });
            return null;
        }
    }

    updateLayoutUI(info) {
        const infoContent = document.getElementById('layoutInfoContent');
        if (!infoContent) return;

        let html = '';

        if (info.cardsPerSheet > 0) {
            html += `
                <div class="layout-stats">
                    <div class="stat">
                        <span class="stat-label">Визиток на листе:</span>
                        <span class="stat-value">${info.cardsPerSheet}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Эффективность:</span>
                        <span class="stat-value">${info.efficiency.toFixed(1)}%</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Поворот:</span>
                        <span class="stat-value">${info.rotation ? 'Да' : 'Нет'}</span>
                    </div>
                </div>
            `;
        } else {
            html += '<p>Невозможно рассчитать раскладку с текущими параметрами</p>';
        }

        if (info.warnings && info.warnings.length > 0) {
            html += '<div class="alert alert-warning">';
            html += '<strong>Предупреждения:</strong>';
            html += '<ul>';
            info.warnings.forEach(warning => {
                html += `<li>${warning}</li>`;
            });
            html += '</ul>';
            html += '</div>';
        }

        infoContent.innerHTML = html;
    }

    getCurrentLayout() {
        return this.currentLayout;
    }
}