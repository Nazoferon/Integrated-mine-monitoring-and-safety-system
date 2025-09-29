class DashboardApp {
    constructor() {
        this.config = {
            mobileBreakpoint: 768,
            animationDuration: 300,
            realTimeUpdateInterval: 30000,
            notificationTimeout: 5000
        };

        this.state = {
            isMobileMenuOpen: false,
            isMobileView: false,
            notifications: [],
            realTimeData: {},
            isOnline: true
        };

        this.elements = {};
        this.observers = [];
        
        this.init();
    }

    /**
     * Ініціалізація додатку
     */
    async init() {
        try {
            console.log('🚀 Ініціалізація системи Глибина 4.0...');
            
            this.cacheElements();
            this.setupEventListeners();
            this.setupObservers();
            this.checkViewport();
            this.setupServiceWorker();
            
            await this.loadInitialData();
            this.startRealTimeUpdates();
            
            this.updateSystemStatus();
            this.setupErrorHandling();
            
            document.body.classList.add('app-loaded');
            console.log('✅ Система успішно ініціалізована');
            
        } catch (error) {
            console.error('❌ Помилка ініціалізації:', error);
            this.showFatalError('Помилка завантаження системи');
        }
    }

    
    /**
     * Кешування DOM елементів
     */
    cacheElements() {
        this.elements = {
            // Навігація
            menuToggle: document.getElementById('menu-toggle'),
            sidebar: document.getElementById('sidebar'),
            sidebarOverlay: document.getElementById('sidebar-overlay'),
            navLinks: document.querySelectorAll('.nav-link'),
            
            // Контент
            statusCards: document.querySelectorAll('.status-card'),
            alertItems: document.querySelectorAll('.alert-item'),
            viewAllBtn: document.querySelector('.btn-view-all'),
            
            // Модальні вікна
            logoutModal: document.getElementById('logoutModal'),
            
            // Системні елементи
            mainContent: document.querySelector('.dashboard-main'),
            footer: document.querySelector('.dashboard-footer')
        };

        // Валідація обов'язкових елементів
        if (!this.elements.sidebar || !this.elements.menuToggle) {
            throw new Error('Не знайдено обовʼязкові елементи DOM');
        }
    }

    /**
     * Налаштування обробників подій
     */
    setupEventListeners() {
        // Навігація
        this.elements.menuToggle?.addEventListener('click', (e) => 
            this.handleMenuToggle(e));
        
        this.elements.sidebarOverlay?.addEventListener('click', () => 
            this.closeMobileMenu());
        
        // Навігація по меню
        this.elements.navLinks.forEach(link => {
            link.addEventListener('click', (e) => this.handleNavigation(e));
        });

        // Інтерактивні елементи
        this.elements.statusCards.forEach(card => {
            card.addEventListener('click', (e) => this.handleStatusCardClick(e));
        });

        this.elements.alertItems.forEach(alert => {
            alert.addEventListener('click', (e) => this.handleAlertClick(e));
        });

        this.elements.viewAllBtn?.addEventListener('click', () => 
            this.showAllStaff());

        // Глобальні події
        window.addEventListener('resize', () => this.handleResize());
        window.addEventListener('orientationchange', () => 
            this.handleOrientationChange());
        
        document.addEventListener('keydown', (e) => this.handleKeydown(e));
        document.addEventListener('click', (e) => this.handleGlobalClick(e));

        // Online/offline події
        window.addEventListener('online', () => this.handleOnlineStatus(true));
        window.addEventListener('offline', () => this.handleOnlineStatus(false));
    }

    /**
     * Налаштування Intersection Observer для анімацій
     */
    setupObservers() {
        const animationObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in');
                    animationObserver.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });

        // Спостереження за елементами для анімації
        document.querySelectorAll('.card, .status-card, .alert-item').forEach(el => {
            animationObserver.observe(el);
        });

        this.observers.push(animationObserver);
    }

    /**
     * Обробка перемикання мобільного меню
     */
    handleMenuToggle(e) {
        e.stopPropagation();
        
        if (this.state.isMobileMenuOpen) {
            this.closeMobileMenu();
        } else {
            this.openMobileMenu();
        }
    }

    /**
     * Відкриття мобільного меню
     */
    openMobileMenu() {
        this.state.isMobileMenuOpen = true;
        
        this.elements.menuToggle.classList.add('active');
        this.elements.sidebar.classList.add('active');
        
        if (this.elements.sidebarOverlay) {
            this.elements.sidebarOverlay.style.display = 'block';
            setTimeout(() => {
                this.elements.sidebarOverlay.style.opacity = '1';
            }, 10);
        }

        this.disableBodyScroll();
        this.dispatchEvent('mobileMenu:open');
    }

    /**
     * Закриття мобільного меню
     */
    closeMobileMenu() {
        if (!this.state.isMobileMenuOpen) return;
        
        this.state.isMobileMenuOpen = false;
        
        this.elements.menuToggle.classList.remove('active');
        this.elements.sidebar.classList.remove('active');
        
        if (this.elements.sidebarOverlay) {
            this.elements.sidebarOverlay.style.opacity = '0';
            setTimeout(() => {
                this.elements.sidebarOverlay.style.display = 'none';
            }, this.config.animationDuration);
        }

        this.enableBodyScroll();
        this.dispatchEvent('mobileMenu:close');
    }

    /**
     * Обробка навігації
     */
    handleNavigation(e) {
        //e.preventDefault();
        
        const target = e.currentTarget;
        const navText = target.querySelector('span')?.textContent || 'Невідома сторінка';
        
        // Оновлення активної сторінки
        this.updateActiveNavigation(target);
        
        // Анімація переходу
        this.animatePageTransition();
        
        // Закриття мобільного меню
        if (this.state.isMobileView) {
            this.closeMobileMenu();
        }

        console.log('📍 Навігація до:', navText);
        this.dispatchEvent('navigation:change', { page: navText });
    }

    /**
     * Оновлення активної навігації
     */
    updateActiveNavigation(activeLink) {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        activeLink.closest('.nav-item').classList.add('active');
    }

    /**
     * Обробка кліку на картку статусу
     */
    handleStatusCardClick(e) {
        const card = e.currentTarget;
        const statusType = this.getStatusType(card);
        
        // Візуальний фідбек
        this.animateElementClick(card);
        
        // Показати деталі статусу
        this.showStatusDetails(statusType);
        
        this.dispatchEvent('statusCard:click', { type: statusType });
    }

    /**
     * Обробка кліку на сповіщення
     */
    handleAlertClick(e) {
        const alertItem = e.currentTarget;
        const alertType = this.getAlertType(alertItem);
        const title = alertItem.querySelector('h4')?.textContent || 'Невідоме сповіщення';
        
        // Візуальний фідбек
        this.animateElementClick(alertItem);
        
        // Показати деталі сповіщення
        this.showAlertDetails(alertItem, alertType);
        
        this.dispatchEvent('alert:click', { type: alertType, title });
    }

    /**
     * Визначення типу статусу
     */
    getStatusType(cardElement) {
        const classList = Array.from(cardElement.classList);
        
        if (classList.includes('critical')) return 'critical';
        if (classList.includes('warning')) return 'warning';
        if (classList.includes('normal')) return 'normal';
        if (classList.includes('online')) return 'online';
        
        return 'normal';
    }

    /**
     * Визначення типу сповіщення
     */
    getAlertType(alertElement) {
        const classList = Array.from(alertElement.classList);
        
        if (classList.includes('critical')) return 'critical';
        if (classList.includes('warning')) return 'warning';
        if (classList.includes('info')) return 'info';
        
        return 'info';
    }

    /**
     * Анімація кліку на елементі
     */
    animateElementClick(element) {
        element.style.transform = 'scale(0.98)';
        
        setTimeout(() => {
            element.style.transform = '';
        }, 150);
    }

    /**
     * Анімація переходу сторінки
     */
    animatePageTransition() {
        if (!this.elements.mainContent) return;
        
        this.elements.mainContent.style.opacity = '0.7';
        
        setTimeout(() => {
            if (this.elements.mainContent) {
                this.elements.mainContent.style.opacity = '1';
            }
        }, this.config.animationDuration);
    }

    /**
     * Показати деталі статусу
     */
    showStatusDetails(type) {
        const statusMap = {
            'critical': 'Критичні події',
            'warning': 'Попередження',
            'normal': 'Нормальний стан',
            'online': 'Онлайн статус'
        };
        
        const statusName = statusMap[type] || type;
        console.log('📊 Перегляд статусу:', statusName);
        
        this.showNotification(`Перегляд: ${statusName}`, 'info');
    }

    /**
     * Показати деталі сповіщення
     */
    showAlertDetails(alertElement, type) {
        const title = alertElement.querySelector('h4')?.textContent || 'Невідоме сповіщення';
        const message = alertElement.querySelector('p')?.textContent || '';
        
        console.log(`🔔 Деталі сповіщення [${type}]:`, title, '-', message);
        
        // Тут можна реалізувати відкриття модального вікна з деталями
        this.showNotification(`Перегляд сповіщення: ${title}`, 'info');
    }

    /**
     * Показати всіх співробітників
     */
    showAllStaff() {
        console.log('👥 Перегляд всіх співробітників');
        this.showNotification('Завантаження списку співробітників...', 'info');
        
        // Симуляція завантаження даних
        setTimeout(() => {
            this.showNotification('Список співробітників завантажено', 'success');
        }, 1000);
    }

    /**
     * Перевірка viewport та адаптація
     */
    checkViewport() {
        const wasMobile = this.state.isMobileView;
        this.state.isMobileView = window.innerWidth <= this.config.mobileBreakpoint;
        
        // Якщо статус змінився
        if (wasMobile !== this.state.isMobileView) {
            this.handleViewportChange();
        }
    }

    /**
     * Обробка зміни viewport
     */
    handleViewportChange() {
        if (!this.state.isMobileView && this.state.isMobileMenuOpen) {
            this.closeMobileMenu();
        }
        
        this.dispatchEvent('viewport:change', { 
            isMobile: this.state.isMobileView 
        });
    }

    /**
     * Обробка зміни розміру вікна
     */
    handleResize() {
        this.debounce(() => {
            this.checkViewport();
        }, 250)();
    }

    /**
     * Обробка зміни орієнтації
     */
    handleOrientationChange() {
        setTimeout(() => {
            this.checkViewport();
            this.closeMobileMenu();
        }, 300);
    }

    /**
     * Обробка глобальних кліків
     */
    handleGlobalClick(e) {
        // Закриття мобільного меню при кліку поза ним
        if (this.state.isMobileMenuOpen && 
            !this.elements.sidebar.contains(e.target) && 
            !this.elements.menuToggle.contains(e.target)) {
            this.closeMobileMenu();
        }
    }

    /**
     * Обробка клавіатури
     */
    handleKeydown(e) {
        // ESC - закриття мобільного меню
        if (e.key === 'Escape' && this.state.isMobileMenuOpen) {
            this.closeMobileMenu();
        }
        
        // M - перемикання меню (для тесту)
        if (e.key === 'm' && e.ctrlKey) {
            e.preventDefault();
            this.handleMenuToggle(e);
        }
    }

    /**
     * Обробка зміни онлайн статусу
     */
    handleOnlineStatus(isOnline) {
        this.state.isOnline = isOnline;
        
        if (isOnline) {
            this.showNotification('Зʼєднання відновлено', 'success');
            this.restartRealTimeUpdates();
        } else {
            this.showNotification('Втрачено зʼєднання з інтернетом', 'warning');
            this.stopRealTimeUpdates();
        }
        
        this.updateSystemStatus();
        this.dispatchEvent('network:change', { isOnline });
    }

    /**
     * Завантаження початкових даних
     */
    async loadInitialData() {
        try {
            // Симуляція завантаження даних
            await this.delay(1000);
            
            this.state.realTimeData = {
                temperature: 25.5,
                humidity: 60,
                methane: 0.8,
                oxygen: 98.2,
                onlineStaff: 24,
                activeAlerts: 3
            };
            
            this.updateDashboardData();
            this.dispatchEvent('data:loaded');
            
        } catch (error) {
            console.error('Помилка завантаження даних:', error);
            this.showNotification('Помилка завантаження даних', 'error');
        }
    }

    /**
     * Оновлення даних на дашборді
     */
    updateDashboardData() {
        // Оновлення метрик
        this.updateMetrics();
        
        // Оновлення статусних карток
        this.updateStatusCards();
    }

    /**
     * Оновлення метрик
     */
    updateMetrics() {
        const metrics = document.querySelectorAll('.metric-value');
        
        metrics.forEach(metric => {
            const currentValue = parseFloat(metric.textContent);
            const randomChange = (Math.random() - 0.5) * 0.3;
            const newValue = Math.max(0, currentValue + randomChange);
            
            metric.textContent = newValue.toFixed(1) + 
                (metric.textContent.includes('%') ? '%' : '°C');
        });
    }

    /**
     * Оновлення статусних карток
     */
    updateStatusCards() {
        // Тут можна оновити дані статусних карток
        console.log('🔄 Оновлення статусних карток...');
    }

    /**
     * Запуск реальних оновлень
     */
    startRealTimeUpdates() {
        if (!this.state.isOnline) return;
        
        this.realTimeInterval = setInterval(() => {
            this.updateRealTimeData();
        }, this.config.realTimeUpdateInterval);
        
        console.log('🔄 Запущено реальні оновлення');
    }

    /**
     * Зупинка реальних оновлень
     */
    stopRealTimeUpdates() {
        if (this.realTimeInterval) {
            clearInterval(this.realTimeInterval);
            this.realTimeInterval = null;
            console.log('⏹️ Зупинено реальні оновлення');
        }
    }

    /**
     * Перезапуск реальних оновлень
     */
    restartRealTimeUpdates() {
        this.stopRealTimeUpdates();
        this.startRealTimeUpdates();
    }

    /**
     * Оновлення реальних даних
     */
    updateRealTimeData() {
        if (!this.state.isOnline) return;
        
        this.updateMetrics();
        this.simulateNewNotifications();
        this.dispatchEvent('data:updated');
    }

    /**
     * Симуляція нових сповіщень
     */
    simulateNewNotifications() {
        if (Math.random() < 0.2) { // 20% ймовірність нового сповіщення
            const types = ['info', 'warning', 'critical'];
            const type = types[Math.floor(Math.random() * types.length)];
            
            this.addNewNotification(type);
        }
    }

    /**
     * Додавання нового сповіщення
     */
    addNewNotification(type) {
        const notifications = {
            info: [
                'Планове оновлення системи',
                'Нові дані доступні для аналізу',
                'Система працює у штатному режимі'
            ],
            warning: [
                'Підвищений рівень пилу в секторі 2',
                'Зниження типу в системі вентиляції',
                'Необхідна перевірка обладнання'
            ],
            critical: [
                'Критичний рівень метану!',
                'Аварійне відключення живлення',
                'Евакуація персоналу!'
            ]
        };
        
        const messages = notifications[type];
        const message = messages[Math.floor(Math.random() * messages.length)];
        
        this.showNotification(message, type);
        this.dispatchEvent('notification:new', { type, message });
    }

    /**
     * Показати сповіщення
     */
    showNotification(message, type = 'info') {
        const notification = this.createNotificationElement(message, type);
        document.body.appendChild(notification);
        
        // Анімація появи
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        // Автоматичне закриття
        const timeout = setTimeout(() => {
            this.removeNotification(notification);
        }, this.config.notificationTimeout);
        
        // Збереження для можливості ручного закриття
        notification._timeout = timeout;
        this.state.notifications.push(notification);
    }

    /**
     * Створення елементу сповіщення
     */
    createNotificationElement(message, type) {
        const notification = document.createElement('div');
        notification.className = `notification-toast ${type}`;
        
        notification.innerHTML = `
            <div class="notification-icon">
                <i class="fas fa-${this.getNotificationIcon(type)}"></i>
            </div>
            <div class="notification-content">
                <p>${message}</p>
                <span>щойно</span>
            </div>
            <button class="notification-close">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        // Стилізація
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
            transition: 'all 0.3s ease'
        });
        
        // Обробник закриття
        const closeBtn = notification.querySelector('.notification-close');
        closeBtn.addEventListener('click', () => {
            this.removeNotification(notification);
        });
        
        return notification;
    }

    /**
     * Видалення сповіщення
     */
    removeNotification(notification) {
        if (notification._timeout) {
            clearTimeout(notification._timeout);
        }
        
        notification.style.transform = 'translateX(100%)';
        notification.style.opacity = '0';
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
            
            // Видалення з масиву
            this.state.notifications = this.state.notifications.filter(
                n => n !== notification
            );
        }, 300);
    }

    /**
     * Отримання іконки для сповіщення
     */
    getNotificationIcon(type) {
        const icons = {
            'critical': 'skull-crossbones',
            'warning': 'exclamation-triangle',
            'info': 'info-circle',
            'success': 'check-circle'
        };
        
        return icons[type] || 'info-circle';
    }

    /**
     * Отримання кольору для сповіщення
     */
    getNotificationColor(type) {
        const colors = {
            'critical': '#ef4444',
            'warning': '#f59e0b',
            'info': '#4dabf7',
            'success': '#22c55e'
        };
        
        return colors[type] || '#4dabf7';
    }

    /**
     * Оновлення статусу системи
     */
    updateSystemStatus() {
        const statusIndicator = document.querySelector('.status-indicator');
        const statusText = document.querySelector('.footer-status span');
        
        if (statusIndicator && statusText) {
            if (this.state.isOnline) {
                statusIndicator.style.background = '#22c55e';
                statusText.textContent = 'Система активна';
            } else {
                statusIndicator.style.background = '#ef4444';
                statusText.textContent = 'Зʼєднання втрачено';
            }
        }
    }

    /**
     * Налаштування Service Worker (якщо потрібно)
     */
    async setupServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
                // await navigator.serviceWorker.register('/sw.js');
                console.log('🔧 Service Worker підтримується');
            } catch (error) {
                console.log('⚠️ Service Worker не зареєстровано:', error);
            }
        }
    }

    /**
     * Налаштування обробки помилок
     */
    setupErrorHandling() {
        window.addEventListener('error', (e) => {
            console.error('🚨 Глобальна помилка:', e.error);
            this.showNotification('Сталася помилка в системі', 'critical');
        });
        
        window.addEventListener('unhandledrejection', (e) => {
            console.error('🚨 Необроблена проміс-помилка:', e.reason);
            e.preventDefault();
        });
    }

    /**
     * Показати фатальну помилку
     */
    showFatalError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            padding: 20px;
            text-align: center;
            font-family: Arial, sans-serif;
        `;
        
        errorDiv.innerHTML = `
            <div style="font-size: 48px; margin-bottom: 20px;">⚠️</div>
            <h2 style="color: #ef4444; margin-bottom: 10px;">Помилка системи</h2>
            <p style="margin-bottom: 20px; font-size: 16px;">${message}</p>
            <button onclick="location.reload()" style="
                background: #4dabf7;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 14px;
            ">Перезавантажити</button>
        `;
        
        document.body.appendChild(errorDiv);
    }

    /**
     * Допоміжні функції
     */
    
    // Debounce для оптимізації
    debounce(func, wait) {
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

    // Затримка
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Відключення скролу body
    disableBodyScroll() {
        document.body.style.overflow = 'hidden';
    }

    // Включення скролу body
    enableBodyScroll() {
        document.body.style.overflow = '';
    }

    // Відправка кастомних подій
    dispatchEvent(name, detail = {}) {
        const event = new CustomEvent(name, { detail });
        document.dispatchEvent(event);
    }

    /**
     * Очищення ресурсів
     */
    destroy() {
        this.stopRealTimeUpdates();
        
        this.observers.forEach(observer => {
            observer.disconnect();
        });
        
        this.state.notifications.forEach(notification => {
            this.removeNotification(notification);
        });
        
        console.log('🧹 Ресурси додатку очищено');
    }
}

// Ініціалізація додатку при завантаженні сторінки
document.addEventListener('DOMContentLoaded', () => {
    // Перевірка підтримки необхідних API
    if (!('classList' in document.documentElement)) {
        alert('Ваш браузер застарів. Будь ласка, оновіть його.');
        return;
    }
    
    
    window.dashboardApp = new DashboardApp();
});

// Глобальні функції для відладки
window.showTestNotification = (message = 'Тестове сповіщення', type = 'info') => {
    if (window.dashboardApp) {
        window.dashboardApp.showNotification(message, type);
    }
};

window.toggleMobileMenu = () => {
    if (window.dashboardApp) {
        window.dashboardApp.handleMenuToggle(new Event('click'));
    }
};

// Стилі для анімацій сповіщень
const notificationStyles = document.createElement('style');
notificationStyles.textContent = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    .notification-toast.show {
        transform: translateX(0) !important;
        opacity: 1 !important;
    }
    
    /* Reduced motion support */
    @media (prefers-reduced-motion: reduce) {
        .notification-toast {
            transition: none !important;
        }
    }
`;
document.head.appendChild(notificationStyles);

// Обробка закриття сторінки
window.addEventListener('beforeunload', () => {
    if (window.dashboardApp) {
        window.dashboardApp.destroy();
    }
});

console.log('📄 JavaScript система Глибина 4.0 завантажена');