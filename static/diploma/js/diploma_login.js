/**
 * Скрипт для сторінки логіну - Глибина 4.0
 * Версія 2.1 - Виправлено показ пароля, підтримка обох шаблонів
 */

class LoginApp {
    constructor() {
        this.config = {
            animationDuration: 300,
            notificationTimeout: 4000,
            minUsernameLength: 3,
            minPasswordLength: 6
        };

        this.elements = {};
        this.state = {
            notifications: [],
            isLoading: false
        };

        this.init();
    }

    /**
     * Ініціалізація додатку
     */
    init() {
        try {
            console.log('🚀 Ініціалізація скрипту логіну...');

            this.cacheElements();
            if (!this.elements.loginForm || !this.elements.passwordInput) {
                console.warn('⚠️ Не знайдено елементи форми. Скрипт пропущено.');
                return;
            }

            this.setupEventListeners();
            this.setupThemeToggle();
            if (this.elements.errorMessage && this.elements.errorMessage.style.display !== 'none') {
                this.showNotification('Невірний логін або пароль', 'error');
            }

            console.log('✅ Скрипт логіну ініціалізовано');
        } catch (error) {
            console.error('❌ Помилка ініціалізації:', error);
            this.showNotification('Помилка завантаження форми', 'error');
        }
    }

    /**
     * Кешування DOM елементів
     */
    cacheElements() {
        this.elements = {
            usernameInput: document.querySelector('input[name="username"]') || document.querySelector('#id_username') || document.querySelector('#username'),
            passwordInput: document.querySelector('input[name="password"]') || document.querySelector('#id_password') || document.querySelector('#password'),
            showPasswordCheckbox: document.querySelector('#showPassword'),
            passwordToggle: document.querySelector('#passwordToggle'),
            loginForm: document.querySelector('.auth-form') || document.querySelector('form'),
            errorMessage: document.querySelector('.error-message') || document.querySelector('.alert-danger'),
            submitButton: document.querySelector('.btn-login-submit') || document.querySelector('button[type="submit"]'),
            loginContainer: document.querySelector('.login-container')
        };

        // Дебаг-логування для перевірки елементів
        console.log('🛠️ Знайдені елементи:', {
            usernameInput: !!this.elements.usernameInput,
            passwordInput: !!this.elements.passwordInput,
            showPasswordCheckbox: !!this.elements.showPasswordCheckbox,
            passwordToggle: !!this.elements.passwordToggle,
            loginForm: !!this.elements.loginForm
        });
    }

    /**
     * Налаштування обробників подій
     */
    setupEventListeners() {
        // Показ/приховування пароля (кнопка)
        if (this.elements.passwordToggle && this.elements.passwordInput) {
            console.log('🛠️ Налаштовано обробник для passwordToggle');
            this.elements.passwordToggle.addEventListener('click', () => {
                const isText = this.elements.passwordInput.type === 'text';
                this.elements.passwordInput.type = isText ? 'password' : 'text';
                const icon = this.elements.passwordToggle.querySelector('i');
                if (icon) {
                    icon.classList.toggle('fa-eye', isText);
                    icon.classList.toggle('fa-eye-slash', !isText);
                }
                this.animateElement(this.elements.passwordToggle, 'pulse 0.2s');
            });
        }

        // Показ/приховування пароля (чекбокс)
        if (this.elements.showPasswordCheckbox && this.elements.passwordInput) {
            console.log('🛠️ Налаштовано обробник для showPasswordCheckbox');
            this.elements.showPasswordCheckbox.addEventListener('change', () => {
                this.elements.passwordInput.type = this.elements.showPasswordCheckbox.checked ? 'text' : 'password';
                this.animateElement(this.elements.showPasswordCheckbox, 'pulse 0.2s');
            });
        }

        // Валідація форми
        if (this.elements.loginForm) {
            this.elements.loginForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }

        // Анімація фокусу на полях
        [this.elements.usernameInput, this.elements.passwordInput].forEach(input => {
            if (input) {
                input.addEventListener('focus', () => this.animateElement(input, 'scale 0.98'));
                input.addEventListener('blur', () => input.style.transform = '');
            }
        });

        // Обробка клавіатури
        document.addEventListener('keydown', (e) => this.handleKeydown(e));

        // Анімація кнопки при натисканні
        if (this.elements.submitButton) {
            this.elements.submitButton.addEventListener('click', () => {
                if (!this.state.isLoading) {
                    this.animateElement(this.elements.submitButton, 'scale 0.95');
                }
            });
        }
    }

    /**
     * Налаштування перемикання теми
     */
    setupThemeToggle() {
        const themeToggle = document.createElement('button');
        themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
        themeToggle.className = 'theme-toggle';
        themeToggle.setAttribute('aria-label', 'Перемкнути тему');
        if (this.elements.loginContainer) {
            this.elements.loginContainer.appendChild(themeToggle);
        }

        themeToggle.addEventListener('click', () => {
            document.body.classList.toggle('light-theme');
            const isLight = document.body.classList.contains('light-theme');
            themeToggle.innerHTML = `<i class="fas fa-${isLight ? 'sun' : 'moon'}"></i>`;
            this.showNotification(`Тема змінена на ${isLight ? 'світлу' : 'темну'}`, 'info');
        });
    }

    /**
     * Обробка відправки форми
     */
    handleFormSubmit(e) {
        let isValid = true;

        if (!this.elements.usernameInput.value.trim()) {
            isValid = false;
            this.showFieldError(this.elements.usernameInput, 'Введіть логін або Email');
        } else if (this.elements.usernameInput.value.length < this.config.minUsernameLength) {
            isValid = false;
            this.showFieldError(this.elements.usernameInput, `Логін або Email має бути довше ${this.config.minUsernameLength} символів`);
        }

        if (!this.elements.passwordInput.value.trim()) {
            isValid = false;
            this.showFieldError(this.elements.passwordInput, 'Введіть пароль');
        } else if (this.elements.passwordInput.value.length < this.config.minPasswordLength) {
            isValid = false;
            this.showFieldError(this.elements.passwordInput, `Пароль має бути довше ${this.config.minPasswordLength} символів`);
        }

        if (!isValid) {
            e.preventDefault();
            this.showNotification('Будь ласка, виправте помилки у формі', 'error');
            this.showErrorAnimation();
        } else {
            this.state.isLoading = true;
            this.elements.submitButton.disabled = true;
            this.elements.submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Вхід...';
        }
    }

    /**
     * Показ помилки для поля
     */
    showFieldError(input, message) {
        input.classList.add('error');
        input.placeholder = message;
        this.animateElement(input, 'shake 0.5s');
        setTimeout(() => {
            input.classList.remove('error');
            input.placeholder = '';
        }, 3000);
    }

    /**
     * Показ сповіщення
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification-toast ${type}`;
        notification.innerHTML = `
            <div class="notification-icon">
                <i class="fas fa-${this.getNotificationIcon(type)}"></i>
            </div>
            <div class="notification-content">
                <p>${message}</p>
                <span>Щойно</span>
            </div>
            <button class="notification-close"><i class="fas fa-times"></i></button>
        `;

        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            background: this.getNotificationColor(type),
            color: 'white',
            padding: '15px',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            zIndex: '10000',
            maxWidth: '350px',
            boxShadow: '0 4px 15px rgba(0, 0, 0, 0.3)',
            transform: 'translateX(100%)',
            opacity: '0',
            transition: `all ${this.config.animationDuration}ms ease`
        });

        document.body.appendChild(notification);
        setTimeout(() => notification.classList.add('show'), 100);

        const timeout = setTimeout(() => this.removeNotification(notification), this.config.notificationTimeout);
        notification.querySelector('.notification-close').addEventListener('click', () => this.removeNotification(notification));
        this.state.notifications.push({ element: notification, timeout });
    }

    /**
     * Видалення сповіщення
     */
    removeNotification(notification) {
        const index = this.state.notifications.findIndex(n => n.element === notification);
        if (index !== -1) {
            clearTimeout(this.state.notifications[index].timeout);
            notification.style.transform = 'translateX(100%)';
            notification.style.opacity = '0';
            setTimeout(() => {
                notification.remove();
                this.state.notifications.splice(index, 1);
            }, this.config.animationDuration);
        }
    }

    /**
     * Іконка для сповіщення
     */
    getNotificationIcon(type) {
        const icons = {
            error: 'exclamation-circle',
            info: 'info-circle',
            success: 'check-circle'
        };
        return icons[type] || 'info-circle';
    }

    /**
     * Колір для сповіщення
     */
    getNotificationColor(type) {
        const colors = {
            error: '#ef4444',
            info: '#4dabf7',
            success: '#22c55e'
        };
        return colors[type] || '#4dabf7';
    }

    /**
     * Анімація елемента
     */
    animateElement(element, animation) {
        element.style.animation = animation;
        setTimeout(() => element.style.animation = '', this.config.animationDuration);
    }

    /**
     * Анімація помилки
     */
    showErrorAnimation() {
        if (this.elements.loginForm) {
            this.animateElement(this.elements.loginForm, 'shake 0.5s');
        }
    }

    /**
     * Обробка клавіатури
     */
    handleKeydown(e) {
        if (e.key === 'Enter' && document.activeElement === this.elements.usernameInput) {
            this.elements.passwordInput.focus();
        } else if (e.key === 'Enter' && document.activeElement === this.elements.passwordInput) {
            this.elements.loginForm.submit();
        } else if (e.key === 'Escape' && this.state.notifications.length) {
            this.state.notifications.forEach(n => this.removeNotification(n.element));
        }
    }
}

// Ініціалізація
document.addEventListener('DOMContentLoaded', () => {
    window.loginApp = new LoginApp();
});