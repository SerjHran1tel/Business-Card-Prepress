// static/js/utils.js
class Utils {
    static formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    static getFileIcon(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const icons = {
            'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️',
            'tiff': '🖼️', 'bmp': '🖼️', 'webp': '🖼️',
            'pdf': '📄', 'svg': '📐', 'tif': '🖼️'
        };
        return icons[ext] || '📄';
    }

    static sanitizeFilename(filename) {
        const invalidChars = '<>:"/\\|?*';
        let sanitized = filename;
        for (let char of invalidChars) {
            sanitized = sanitized.replace(new RegExp('\\' + char, 'g'), '_');
        }
        return sanitized;
    }

    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    static generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }

    static async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (err) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            try {
                document.execCommand('copy');
                return true;
            } catch (err) {
                return false;
            } finally {
                document.body.removeChild(textArea);
            }
        }
    }

    static showToast(message, type = 'info') {
        // Implementation would go here
        console.log(`[${type}] ${message}`);
    }

    static validateEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }

    static formatDate(date) {
        return new Date(date).toLocaleDateString('ru-RU');
    }

    static formatDateTime(date) {
        return new Date(date).toLocaleString('ru-RU');
    }

    static parseJSON(str, fallback = {}) {
        try {
            return JSON.parse(str);
        } catch {
            return fallback;
        }
    }

    static escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
}

// Event bus for component communication
class EventBus {
    constructor() {
        this.events = {};
    }

    on(event, callback) {
        if (!this.events[event]) {
            this.events[event] = [];
        }
        this.events[event].push(callback);
    }

    off(event, callback) {
        if (!this.events[event]) return;
        this.events[event] = this.events[event].filter(cb => cb !== callback);
    }

    emit(event, data) {
        if (!this.events[event]) return;
        this.events[event].forEach(callback => callback(data));
    }
}

// Storage helper
class Storage {
    static set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (e) {
            console.error('LocalStorage set error:', e);
            return false;
        }
    }

    static get(key, fallback = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : fallback;
        } catch (e) {
            console.error('LocalStorage get error:', e);
            return fallback;
        }
    }

    static remove(key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (e) {
            console.error('LocalStorage remove error:', e);
            return false;
        }
    }

    static clear() {
        try {
            localStorage.clear();
            return true;
        } catch (e) {
            console.error('LocalStorage clear error:', e);
            return false;
        }
    }
}