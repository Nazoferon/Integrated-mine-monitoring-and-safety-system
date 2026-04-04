class EquipmentPage {
    constructor() {
        this.sortState = {
            column: null,
            direction: 'none' // 'asc', 'desc'
        };
        this.elements = {};
        this.init();
    }

    init() {
        console.log("✅ Скрипт сторінки обладнання завантажено (v2.0)");
        this.cacheElements();
        this.setupEventListeners();
        this.buildSearchCache();
        this.setInitialBatteryLevels();
        this.startRealTelemetryUpdates();
    }

    cacheElements() {
        this.elements = {
            searchInput: document.getElementById('eqSearchInput'),
            clearSearchBtn: document.getElementById('clearEqSearchBtn'),
            allRows: document.querySelectorAll('.tech-row'),
            sortableHeaders: document.querySelectorAll('.sortable')
        };
    }

    setupEventListeners() {
        if (this.elements.searchInput) {
            this.elements.searchInput.addEventListener('input', () => this.filterEquipment());
            this.elements.searchInput.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') this.clearSearch();
            });
        }

        if (this.elements.clearSearchBtn) {
            this.elements.clearSearchBtn.addEventListener('click', () => this.clearSearch());
        }

        this.elements.sortableHeaders.forEach(header => {
            header.addEventListener('click', (e) => this.handleSort(e));
        });
    }

    // Створюємо кеш пошукового тексту для кращої продуктивності
    buildSearchCache() {
        this.elements.allRows.forEach(row => {
            row.dataset.searchableText = Array.from(row.querySelectorAll('.search-target'))
                .map(td => td.textContent.toLowerCase())
                .join(' ');
        });
    }

    setInitialBatteryLevels() {
        this.elements.allRows.forEach(row => {
            const batteryLevel = row.querySelector('.battery-level');
            // Застосовуємо точну ширину батареї (з data-battery), якщо пристрій онлайн
            if (batteryLevel && row.dataset.battery !== undefined && !row.classList.contains('offline-device')) {
                batteryLevel.style.width = row.dataset.battery + '%';
            }
        });
    }

    filterEquipment() {
        const term = this.elements.searchInput.value.toLowerCase().trim();
        this.elements.clearSearchBtn.classList.toggle('visible', term.length > 0);

        this.elements.allRows.forEach(row => {
            const isVisible = row.dataset.searchableText.includes(term);
            row.style.display = isVisible ? '' : 'none';
        });
    }

    clearSearch() {
        if (this.elements.searchInput) {
            this.elements.searchInput.value = '';
            this.filterEquipment();
            this.elements.searchInput.focus();
        }
    }

    handleSort(e) {
        const header = e.currentTarget;
        const sortBy = header.dataset.sortBy;
        if (!sortBy) return;

        // Визначаємо напрямок сортування
        if (this.sortState.column === sortBy && this.sortState.direction === 'desc') {
            this.sortState.direction = 'asc';
        } else {
            this.sortState.direction = 'desc';
        }
        this.sortState.column = sortBy;

        // Оновлюємо стилі заголовків
        this.elements.sortableHeaders.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
        header.classList.add(this.sortState.direction === 'asc' ? 'sort-asc' : 'sort-desc');

        // Отримуємо тіло таблиці та рядки
        const tableBody = header.closest('table').querySelector('tbody');
        const rows = Array.from(tableBody.querySelectorAll('tr.tech-row'));

        // Сортуємо
        rows.sort((rowA, rowB) => {
            const valueA = this.getSortValue(rowA, sortBy);
            const valueB = this.getSortValue(rowB, sortBy);

            if (valueA < valueB) return this.sortState.direction === 'asc' ? -1 : 1;
            if (valueA > valueB) return this.sortState.direction === 'asc' ? 1 : -1;
            return 0;
        });

        // Вставляємо відсортовані рядки назад
        rows.forEach(row => tableBody.appendChild(row));
    }

    getSortValue(row, sortBy) {
        const value = row.dataset[sortBy.toLowerCase()] || '';

        // Для прошивки повертаємо рядок, який можна сортувати лексикографічно,
        // перетворивши версію "1.2.10" на "001.002.010" для коректного порівняння.
        if (sortBy === 'firmware' && value) {
            return value.split('.').map(part => part.padStart(3, '0')).join('.');
        }

        // Для інших значень (батарея, статус) пробуємо перетворити на число.
        const numValue = parseFloat(value);
        return isNaN(numValue) ? value : numValue;
    }

    startRealTelemetryUpdates() {
        const updateTelemetry = async () => {
            try {
                const response = await fetch('/diploma/api/equipment-telemetry/');
                if (!response.ok) return;
                
                const data = await response.json();
                let needsResort = false;
                
                this.elements.allRows.forEach(row => {
                    const mac = row.dataset.mac;
                    const uid = row.dataset.uid;
                    const wasOffline = row.classList.contains('offline-device');

                    // Визначаємо чи є цей пристрій в списку активних
                    let isNowActive = false;
                    let deviceData = null;

                    if (mac && data.devices && data.devices[mac]) {
                        isNowActive = true;
                        deviceData = data.devices[mac];
                    } else if (uid && data.repeaters && data.repeaters[uid]) {
                        isNowActive = true;
                        deviceData = data.repeaters[uid];
                    }

                    // --- ВІЗУАЛЬНА ЗМІНА СТАТУСУ ---
                    if (isNowActive && wasOffline) {
                        row.classList.remove('offline-device');
                        row.dataset.status = "1";
                        needsResort = true;
                        
                    } else if (!isNowActive && !wasOffline) {
                        row.classList.add('offline-device');
                        row.dataset.status = "0";
                        row.dataset.battery = "0"; // Скидаємо для правильного сортування
                        needsResort = true;
                    }

                    // --- ОНОВЛЕННЯ ТЕЛЕМЕТРІЇ (ТІЛЬКИ ОНЛАЙН) ---
                    if (isNowActive) {
                        // Оновлення коногонок та датчиків
                        if (mac) {
                            const batteryLevel = row.querySelector('.battery-level');
                            if (batteryLevel) {
                                const level = deviceData.battery;
                                batteryLevel.style.width = level + '%';
                                const wrapper = row.querySelector('.battery-wrapper');
                                if (wrapper) wrapper.title = `Рівень заряду: ${level}%`;
                                
                                batteryLevel.className = 'battery-level';
                                if (level >= 50) batteryLevel.classList.add('bat-high');
                                else if (level >= 20) batteryLevel.classList.add('bat-med');
                                else batteryLevel.classList.add('bat-low');
                                
                                row.dataset.battery = level; // Для сортування
                            }

                            const gasSpan = row.querySelector('.sim-gas');
                            const tempSpan = row.querySelector('.sim-temp');
                            if (gasSpan) gasSpan.textContent = deviceData.gas;
                            if (tempSpan) tempSpan.textContent = deviceData.temp !== null ? deviceData.temp : '--';
                        }

                        // Оновлення репітерів
                        if (uid) {
                            const clientsSpan = row.querySelector('.sim-clients');
                            const clientsWrapper = row.querySelector('.clients-wrapper');
                            if (clientsSpan) {
                                clientsSpan.textContent = deviceData.clients;
                            }
                            if (clientsWrapper) {
                                clientsWrapper.title = deviceData.clients > 0 ? `Підключені:\n${deviceData.clients_list}` : 'Немає підключень';
                            }
                        }
                    }
                });

                // Якщо статус змінився і таблиця відсортована користувачем — пересортовуємо
                if (needsResort && this.sortState.column) {
                    const activeHeader = Array.from(this.elements.sortableHeaders).find(
                        h => h.dataset.sortBy === this.sortState.column
                    );
                    if (activeHeader) {
                        // Тимчасово інвертуємо напрямок, щоб він зберігся після кліку (auto-resort)
                        this.sortState.direction = this.sortState.direction === 'asc' ? 'desc' : 'asc';
                        this.handleSort({ currentTarget: activeHeader });
                    }
                }
            } catch (error) {
                console.error("Помилка оновлення телеметрії:", error);
            } finally {
                setTimeout(updateTelemetry, 5000);
            }
        };

        // Запускаємо перше оновлення
        setTimeout(updateTelemetry, 5000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new EquipmentPage();
});