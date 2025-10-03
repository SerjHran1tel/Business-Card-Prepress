// static/js/pdfGenerator.js
class PDFGenerator {
    constructor() {
        this.isGenerating = false;
    }

    async generatePDF(parties, config) {
        if (this.isGenerating) {
            app.showNotification('PDF уже генерируется...', 'warning');
            return;
        }

        if (!parties || parties.length === 0) {
            app.showNotification('Нет партий для генерации PDF', 'warning');
            return;
        }

        this.isGenerating = true;
        app.showLoading('Генерация PDF...');

        try {
            const request = {
                parties: parties,
                config: config,
                output_filename: `business_cards_${Date.now()}.pdf`
            };

            const response = await fetch('/api/v1/generate-pdf', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(request)
            });

            const result = await response.json();

            if (result.success) {
                // Скачиваем файл
                this.downloadFile(result.download_url, request.output_filename);

                app.showNotification(
                    `PDF успешно создан! Листов: ${result.total_sheets}, Визиток: ${result.total_cards}`,
                    'success'
                );

                return result;
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            app.showNotification(`Ошибка генерации PDF: ${error.message}`, 'error');
            throw error;
        } finally {
            this.isGenerating = false;
            app.hideLoading();
        }
    }

    downloadFile(url, filename) {
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    async validateBeforeGeneration(parties, config) {
        const errors = [];

        if (!parties || parties.length === 0) {
            errors.push('Нет добавленных партий');
        }

        // Проверяем, что все файлы существуют (в реальном приложении)
        let totalCards = 0;
        parties.forEach(party => {
            totalCards += party.front_images.length * party.quantity;

            if (party.front_images.length === 0) {
                errors.push('В одной из партий нет лицевых сторон');
            }

            if (config.matching_scheme === '1:1' && party.back_images.length !== party.front_images.length) {
                errors.push('Для схемы 1:1 количество лицевых и оборотных сторон должно совпадать');
            }
        });

        if (totalCards === 0) {
            errors.push('Общее количество визиток должно быть больше 0');
        }

        // Проверяем параметры печати
        if (config.card_width <= 0 || config.card_height <= 0) {
            errors.push('Размер визитки должен быть положительным числом');
        }

        if (config.sheet_width <= config.card_width || config.sheet_height <= config.card_height) {
            errors.push('Размер визитки не может быть больше размера листа');
        }

        if (config.margin < 0 || config.bleed < 0) {
            errors.push('Поля и вылеты не могут быть отрицательными');
        }

        return {
            isValid: errors.length === 0,
            errors: errors,
            totalCards: totalCards
        };
    }

    async generateWithValidation(parties, config) {
        const validation = await this.validateBeforeGeneration(parties, config);

        if (!validation.isValid) {
            const errorMessage = validation.errors.join('\n');
            app.showNotification(`Ошибки валидации:\n${errorMessage}`, 'error');
            return null;
        }

        return await this.generatePDF(parties, config);
    }

    getPDFSettings() {
        return {
            quality: 'high', // high, medium, low
            includeCropMarks: true,
            includeBleed: true,
            colorMode: 'rgb',
            compression: true
        };
    }

    async estimateFileSize(parties, config) {
        // Базовая оценка размера файла
        const cardsPerSheet = await this.calculateCardsPerSheet(config);
        const totalSheets = Math.ceil(
            parties.reduce((sum, party) => sum + (party.front_images.length * party.quantity), 0) / cardsPerSheet
        ) * (config.back_files && config.back_files.length > 0 ? 2 : 1);

        // Примерная оценка: 100KB на страницу + 50KB на изображение
        const baseSize = totalSheets * 100 * 1024; // 100KB per page
        const imageSize = parties.reduce((sum, party) => {
            return sum + (party.front_images.length + party.back_images.length) * 50 * 1024; // 50KB per image
        }, 0);

        return baseSize + imageSize;
    }

    async calculateCardsPerSheet(config) {
        try {
            const layoutCalc = new LayoutCalculator();
            const layout = await layoutCalc.calculateLayout(config);
            return layout ? layout.cards_total : 0;
        } catch {
            return 0;
        }
    }
}