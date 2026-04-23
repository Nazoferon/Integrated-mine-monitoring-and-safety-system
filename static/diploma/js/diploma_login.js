/**
 * Скрипт для сторінки логіну - Глибина 4.0
 * Версія 2.1 - Виправлено показ пароля, підтримка обох шаблонів
 */

class LoginApp {
    constructor() {
        this.config = {
            animationDuration: 300,
            notificationTimeout: 4000,
            minUsernameLength: 1,
            minPasswordLength: 1
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

            // --- НОВІ ФІЧІ ОПТИМІЗОВАНОГО UX ---
            this.injectOptimizedStyles();
            this.setupFloatingLabels();
            this.setupAutocomplete();
            this.initAmbientDust();

            // Фікс: додаємо відступ справа, щоб довгий пароль не ховався за іконку ока
            if (this.elements.passwordInput && this.elements.passwordToggle) {
                this.elements.passwordInput.style.paddingRight = '45px';
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
            // Встановлюємо правильну початкову іконку (закреслене око, бо пароль приховано)
            const initialIcon = this.elements.passwordToggle.querySelector('i');
            if (initialIcon && this.elements.passwordInput.type === 'password') {
                initialIcon.className = 'fas fa-eye-slash';
            }

            console.log('🛠️ Налаштовано обробник для passwordToggle');
            this.elements.passwordToggle.addEventListener('click', () => {
                const isText = this.elements.passwordInput.type === 'text';
                this.elements.passwordInput.type = isText ? 'password' : 'text';
                const icon = this.elements.passwordToggle.querySelector('i');
                if (icon) {
                    icon.classList.toggle('fa-eye', !isText); // Відкрите око, коли пароль видно
                    icon.classList.toggle('fa-eye-slash', isText); // Закреслене око, коли пароль приховано
                    
                    // Анімуємо лише іконку, щоб не збивати позиціонування (transform: translateY) самої кнопки
                    this.animateElement(icon, 'pulse 0.2s');
                }
                
                // Динамічно змінюємо текст підказки для кращого UX
                this.elements.passwordToggle.title = isText ? 'Показати пароль' : 'Приховати пароль';
                this.elements.passwordToggle.setAttribute('aria-label', isText ? 'Показати пароль' : 'Приховати пароль');
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

        // Перевірка Caps Lock
        if (this.elements.passwordInput) {
            ['keyup', 'keydown', 'mousedown'].forEach(evt => {
                this.elements.passwordInput.addEventListener(evt, (e) => this.checkCapsLock(e));
            });
        }

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
        } else {
            this.state.isLoading = true;
            
            // Анімація звуження кнопки (Morphing)
            const btn = this.elements.submitButton;
            btn.style.width = btn.offsetWidth + 'px'; // Фіксуємо ширину для плавності
            btn.classList.add('btn-morph');
            
            setTimeout(() => {
                btn.classList.add('loading');
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                btn.disabled = true;
            }, 10);
        }
    }

    /**
     * Показ помилки для поля
     */
    showFieldError(input, message) {
        input.classList.add('error');
        input.placeholder = message;
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

    /**
     * Перевірка статусу Caps Lock та показ попередження
     */
    checkCapsLock(e) {
        if (!e.getModifierState) return;

        const isCapsLockOn = e.getModifierState('CapsLock');
        let capsWarning = document.getElementById('caps-lock-warning');

        if (isCapsLockOn) {
            // Динамічний відступ, щоб текст не перекривався
            if (this.elements.passwordInput) {
                this.elements.passwordInput.style.paddingRight = '120px';
            }

            if (!capsWarning) {
                capsWarning = document.createElement('div');
                capsWarning.id = 'caps-lock-warning';
                capsWarning.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Caps Lock';

                // Стилізація попередження
                Object.assign(capsWarning.style, {
                    position: 'absolute',
                    right: '45px', // Розташовуємо зліва від іконки ока
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: '#f59e0b',
                    fontSize: '12px',
                    fontWeight: '600',
                    pointerEvents: 'none', // Щоб не перекривало кліки по полю
                    animation: 'pulse 1s infinite'
                });

                const parent = this.elements.passwordInput.parentElement;
                if (parent) {
                    parent.style.position = 'relative';
                    parent.appendChild(capsWarning);
                }
            }
        } else {
            // Повертаємо стандартний відступ
            if (this.elements.passwordInput) {
                this.elements.passwordInput.style.paddingRight = '45px';
            }

            if (capsWarning) {
                capsWarning.remove();
            }
        }
    }

    // ==========================================
    // ОПТИМІЗОВАНІ UX/UI МЕТОДИ (КЛІЄНТСЬКА ЧАСТИНА)
    // ==========================================

    /**
     * Вбудовування CSS стилів (Без додаткових HTTP-запитів)
     */
    injectOptimizedStyles() {
        if (document.getElementById('login-optimized-styles')) return;
        const style = document.createElement('style');
        style.id = 'login-optimized-styles';
        style.innerHTML = `
            .floating-group { position: relative; margin-bottom: 1rem; width: 100%; }
            .floating-group input { padding: 1.25rem 0.75rem 0.25rem 0.75rem !important; width: 100%; }
            .floating-group label {
                position: absolute; top: 50%; left: 0.75rem; transform: translateY(-50%);
                color: #888; transition: all 0.2s ease-out; pointer-events: none; margin: 0;
            }
            .floating-group input:focus ~ label,
            .floating-group input:not(:placeholder-shown) ~ label,
            .floating-group input:-webkit-autofill ~ label {
                top: 0.35rem; font-size: 0.75rem; color: #4dabf7; transform: none; left: 0.75rem;
            }
            
            /* Модифікатори, якщо знайдено іконку (user, lock) */
            .floating-group.has-icon input { padding-left: 2.5rem !important; }
            .floating-group.has-icon label { left: 2.5rem; }
            .floating-group.has-icon input:focus ~ label,
            .floating-group.has-icon input:not(:placeholder-shown) ~ label,
            .floating-group.has-icon input:-webkit-autofill ~ label { left: 2.5rem; }
            
            .floating-group .input-icon {
                position: absolute; left: 0.85rem; top: 50%; transform: translateY(-50%);
                color: #888; transition: color 0.2s; pointer-events: none; z-index: 5; font-size: 1.1rem;
            }
            .floating-group input:focus ~ .input-icon { color: #4dabf7; }
            
            .btn-morph {
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
                display: flex !important; justify-content: center; align-items: center;
                overflow: hidden; white-space: nowrap;
            }
            .btn-morph.loading {
                width: 48px !important; height: 48px !important; border-radius: 50% !important;
                padding: 0 !important; color: transparent !important; margin: 0 auto;
            }
            .btn-morph.loading i { color: #fff; font-size: 1.2rem; margin: 0; }
            #ambient-dust {
                position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
                pointer-events: none; z-index: -1; opacity: 0.4;
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Менеджери паролів (1Password, Keychain) - миттєве заповнення
     */
    setupAutocomplete() {
        if (this.elements.usernameInput) this.elements.usernameInput.setAttribute('autocomplete', 'username');
        if (this.elements.passwordInput) this.elements.passwordInput.setAttribute('autocomplete', 'current-password');
    }

    /**
     * Динамічне створення Floating Labels без зміни HTML-шаблону
     */
    setupFloatingLabels() {
        [this.elements.usernameInput, this.elements.passwordInput].forEach(input => {
            if (!input || input.type === 'hidden' || input.parentElement.classList.contains('floating-group')) return;

            const placeholderText = input.getAttribute('placeholder') || (input.name === 'username' ? 'Логін' : 'Пароль');
            input.setAttribute('placeholder', ' '); 
            
            const parent = input.parentElement;
            
            // Знаходимо існуючі іконки (FontAwesome), щоб вони не накладались на текст
            let targetIcon = null;
            const icons = parent.querySelectorAll('i.fas, i.far');
            icons.forEach(i => {
                // Ігноруємо функціональні іконки (око, попередження caps lock)
                if (!i.classList.contains('fa-eye') && !i.classList.contains('fa-eye-slash') && !i.classList.contains('fa-exclamation-triangle')) {
                    targetIcon = i;
                }
            });
            
            const wrapper = document.createElement('div');
            wrapper.className = 'floating-group';
            
            input.parentNode.insertBefore(wrapper, input);
            wrapper.appendChild(input);
            
            // Переносимо знайдену іконку всередину нашої обгортки
            if (targetIcon) {
                const oldIconParent = targetIcon.parentElement;
                wrapper.classList.add('has-icon');
                targetIcon.classList.add('input-icon');
                wrapper.appendChild(targetIcon);
                
                // Якщо стара обгортка іконки (наприклад .input-group-text) залишилась пустою — ховаємо її
                if (oldIconParent && oldIconParent !== parent && oldIconParent.innerText.trim() === '' && oldIconParent.children.length === 0) {
                    oldIconParent.style.display = 'none';
                }
            }
            
            const label = document.createElement('label');
            label.textContent = placeholderText;
            wrapper.appendChild(label);

            if (input === this.elements.passwordInput && this.elements.passwordToggle) {
                wrapper.appendChild(this.elements.passwordToggle);
                this.elements.passwordToggle.style.position = 'absolute';
                this.elements.passwordToggle.style.right = '10px';
                this.elements.passwordToggle.style.top = '50%';
                this.elements.passwordToggle.style.transform = 'translateY(-50%)';
            }
        });
    }

    /**
     * Ефект пилу (Оптимізовано: зупиняється на неактивній вкладці)
     */
    initAmbientDust() {
        if (document.getElementById('ambient-dust')) return; 
        
        const canvas = document.createElement('canvas');
        canvas.id = 'ambient-dust';
        document.body.prepend(canvas);
        const ctx = canvas.getContext('2d', { alpha: true }); 
        
        let width, height;
        const particles = [];
        
        const resize = () => { width = canvas.width = window.innerWidth; height = canvas.height = window.innerHeight; };
        window.addEventListener('resize', resize);
        resize();
        
        for(let i = 0; i < 40; i++) {
            particles.push({
                x: Math.random() * width, y: Math.random() * height,
                r: Math.random() * 1.5 + 0.5, dx: (Math.random() - 0.5) * 0.2,
                dy: Math.random() * -0.5 - 0.1, opacity: Math.random() * 0.5 + 0.1
            });
        }
        
        const animate = () => {
            ctx.clearRect(0, 0, width, height);
            particles.forEach(p => {
                p.x += p.dx; p.y += p.dy;
                if (p.y < 0) p.y = height; if (p.x < 0) p.x = width; if (p.x > width) p.x = 0;
                ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(200, 200, 220, ${p.opacity})`; ctx.fill();
            });
            if (document.visibilityState === 'visible') requestAnimationFrame(animate);
        };
        
        document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') animate(); });
        animate();
    }
}

// Ініціалізація
document.addEventListener('DOMContentLoaded', () => {
    window.loginApp = new LoginApp();
});