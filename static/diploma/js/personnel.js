document.addEventListener('DOMContentLoaded', function() {
    console.log("✅ Скрипт керування персоналом завантажено");

    // --- 1. ЛОГІКА ПОШУКУ ---
    const searchInput = document.getElementById('searchInput');
    const clearSearchBtn = document.getElementById('clearSearchBtn');
    const cards = document.querySelectorAll('.employee-card');
    const personnelCols = document.querySelectorAll('.personnel-col'); // Отримуємо колонки для сортування
    const noResultsMsg = document.getElementById('noResultsMsg');

    function filterEmployees() {
        const searchTerm = searchInput.value.toLowerCase().trim();
        let visibleCards = 0;

        // Скидаємо будь-які активні сортування при пошуку
        resetSortButtons();

        // Показуємо/ховаємо кнопку очищення
        if (clearSearchBtn) {
            if (searchInput.value.length > 0) {
                clearSearchBtn.classList.add('visible');
            } else {
                clearSearchBtn.classList.remove('visible');
            }
        }

        cards.forEach(card => {
            const name = card.querySelector('.emp-name').textContent.toLowerCase();
            const badge = card.querySelector('.detail-value').textContent.toLowerCase();
            const position = card.querySelector('.emp-position').textContent.toLowerCase(); // Посада
            const device = card.querySelector('.device-status span')?.textContent.toLowerCase() || ''; // Пристрій
            const column = card.closest('.personnel-col'); // Отримуємо батьківську колонку

            if (name.includes(searchTerm) || badge.includes(searchTerm) || position.includes(searchTerm) || device.includes(searchTerm)) {
                if (column) column.style.display = ''; // Показуємо колонку
                visibleCards++;
            } else {
                if (column) column.style.display = 'none'; // Ховаємо колонку
            }
        });

        if (noResultsMsg) {
            noResultsMsg.style.display = (visibleCards === 0 && cards.length > 0) ? 'block' : 'none';
        }
    }

    // Функція очищення пошуку
    function clearSearch() {
        if (searchInput) {
            searchInput.value = '';
            searchInput.focus();
            filterEmployees();
        }
    }

    if (searchInput) {
        searchInput.addEventListener('input', filterEmployees);
        
        // Очищення при натисканні Escape
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                clearSearch();
            }
        });
    }

    // Обробник для кнопки очищення
    if (clearSearchBtn) {
        clearSearchBtn.addEventListener('click', clearSearch);
    }

    // --- 2. ЛОГІКА ПЕРЕМИКАННЯ ВИГЛЯДУ (СІТКА / СПИСОК) ---
    const gridBtn = document.getElementById('btnGrid');
    const listBtn = document.getElementById('btnList');
    const gridContainer = document.getElementById('personnelGrid');

    function setView(viewType) {
        if (!gridContainer || !listBtn || !gridBtn) return;

        if (viewType === 'list') {
            gridContainer.classList.add('list-view');
            listBtn.classList.add('active');
            gridBtn.classList.remove('active');
        } else {
            gridContainer.classList.remove('list-view');
            gridBtn.classList.add('active');
            listBtn.classList.remove('active');
        }
        localStorage.setItem('personnelViewStyle', viewType);
    }

    if (gridBtn && listBtn) {
        gridBtn.addEventListener('click', () => setView('grid'));
        listBtn.addEventListener('click', () => setView('list'));

        const savedView = localStorage.getItem('personnelViewStyle') || 'grid';
        setView(savedView);
    }

    // --- 3. ЛОГІКА СОРТУВАННЯ ---
    const sortAlphaBtn = document.getElementById('btnSortAlpha');
    const sortStatusBtn = document.getElementById('btnSortStatus'); // Нова кнопка сортування за статусом
    const personnelGrid = document.getElementById('personnelGrid');
    let currentSort = {
        field: null, // 'name' або 'status'
        order: 'asc' // 'asc' або 'desc'
    };

    // Скидання активних класів з кнопок сортування
    function resetSortButtons() {
        [sortAlphaBtn, sortStatusBtn].forEach(btn => {
            if (btn) btn.classList.remove('active');
        });
    }

    // Функція сортування
    function sortPersonnel(field) {
        resetSortButtons(); // Скидаємо інші кнопки

        const isCurrentField = currentSort.field === field;
        if (isCurrentField) {
            currentSort.order = currentSort.order === 'asc' ? 'desc' : 'asc';
        } else {
            currentSort.field = field;
            // ЗАВЖДИ починаємо з 'asc' при першому кліку на нове поле,
            // оскільки 'desc' для статусу є сортуванням за замовчуванням.
            // Це дасть миттєвий візуальний відгук.
            currentSort.order = 'asc';
        }

        const sortedCards = Array.from(personnelCols).sort((a, b) => {
            let valA, valB;

            if (field === 'name') {
                valA = a.querySelector('.emp-name').textContent.trim();
                valB = b.querySelector('.emp-name').textContent.trim();
                return currentSort.order === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
            } else if (field === 'status') {
                // Сортування за рівнем безпеки (SOS найвищий пріоритет)
                const getStatusWeight = (cardEl) => {
                    const badge = cardEl.querySelector('.emp-status .badge');
                    if (!badge) return 0;
                    if (badge.classList.contains('bg-danger')) return 4; // SOS
                    if (badge.classList.contains('bg-warning')) return 3; // WARNING
                    if (badge.classList.contains('bg-success')) return 2; // OK
                    if (badge.classList.contains('bg-secondary')) return 1; // Не на зміні
                    return 0; // Дефолт (Без пристрою, якщо немає інших класів)
                };
                
                valA = getStatusWeight(a);
                valB = getStatusWeight(b);

                // Якщо ваги однакові, сортуємо за прізвищем як допоміжний критерій
                if (valA === valB) {
                    const nameA = a.querySelector('.emp-name').textContent.trim();
                    const nameB = b.querySelector('.emp-name').textContent.trim();
                    return nameA.localeCompare(nameB); // Завжди asc для допоміжного
                }

                return currentSort.order === 'asc' ? valA - valB : valB - valA;
            }
            return 0;
        });

        // Додаємо відсортовані картки назад в DOM
        sortedCards.forEach(col => personnelGrid.appendChild(col));

        // Оновлюємо іконку та активний клас для поточної кнопки сортування
        const currentBtn = field === 'name' ? sortAlphaBtn : sortStatusBtn;
        if (currentBtn) {
            currentBtn.classList.add('active');
            const icon = currentBtn.querySelector('i');
            if (icon) {
                if (field === 'name') {
                    icon.className = currentSort.order === 'asc' ? 'fas fa-sort-alpha-down me-2' : 'fas fa-sort-alpha-up-alt me-2';
                } else if (field === 'status') {
                    // Використовуємо правильні іконки для висхідного/низхідного сортування
                    icon.className = currentSort.order === 'asc' ? 'fas fa-sort-amount-up me-2' : 'fas fa-sort-amount-down me-2';
                }
            }
        }
    }

    // Обробники для кнопок сортування
    if (sortAlphaBtn) {
        sortAlphaBtn.addEventListener('click', () => sortPersonnel('name'));
    }
    if (sortStatusBtn) {
        sortStatusBtn.addEventListener('click', () => sortPersonnel('status'));
    }

    // --- 4. АВТОМАТИЧНЕ ОНОВЛЕННЯ СТАТУСІВ ---
    const API_URL = '/diploma/personnel-status-api/';
    const UPDATE_INTERVAL = 7000; // Оновлюємо кожні 7 секунд

    async function updateDeviceStatuses() {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 6000);
            
            const response = await fetch(API_URL, {
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                // Не виводимо помилку в консоль, щоб не засмічувати її при обриві з'єднання
                return;
            }
            const data = await response.json();
            const statuses = data.device_statuses;

            if (!statuses) return;

            // Проходимо по всіх картках співробітників, які мають MAC
            document.querySelectorAll('.employee-card[data-mac-address]').forEach(card => {
                const mac = card.dataset.macAddress;
                const statusInfo = statuses[mac];
                
                if (!statusInfo) return; // Немає даних для цього MAC

                const statusDiv = card.querySelector('.device-status');
                const statusSpan = statusDiv.querySelector('span');
                const statusDot = statusDiv.querySelector('.status-dot');

                const isCurrentlyActive = statusDiv.classList.contains('status-active');
                const shouldBeActive = statusInfo.is_active;

                const locationValue = card.querySelector('.location-value');
                const currentLocationStr = locationValue ? locationValue.textContent.trim() : '';
                const newLocationUID = statusInfo.location || 'Невідомо';
                
                const locationChanged = shouldBeActive && (!currentLocationStr.includes(newLocationUID));

                // Оновлюємо якщо змінився статус або локація
                if (isCurrentlyActive !== shouldBeActive || locationChanged) {
                    statusDiv.classList.add('updating'); // Додаємо клас для анімації

                    // Через невеликий проміжок часу оновлюємо класи та текст
                    setTimeout(() => {
                        if (shouldBeActive) {
                            statusDiv.className = 'device-status status-active';
                            statusDot.className = 'status-dot dot-active';
                            statusSpan.textContent = statusInfo.inventory_number;
                            statusDiv.title = '';
                            
                            if (locationValue) {
                                locationValue.innerHTML = statusInfo.location ? 
                                    `<a href="/diploma/mine_map/?focus_ap=${statusInfo.location}" class="location-link" title="Показати на карті"><i class="fas fa-map-marker-alt text-danger"></i> ${statusInfo.location}</a>` : 
                                    '<span class="text-muted">Невідомо</span>';
                            }
                        } else {
                            statusDiv.className = 'device-status status-device-inactive';
                            statusDot.className = 'status-dot dot-device-inactive';
                            statusSpan.textContent = `${statusInfo.inventory_number} (Неактивний)`;
                            statusDiv.title = 'Пристрій неактивний';
                            
                            if (locationValue) {
                                locationValue.innerHTML = '<span class="text-muted">Невідомо</span>';
                            }
                        }
                        statusDiv.classList.remove('updating');
                    }, 500);
                }
            });

        } catch (error) {
            // Ігноруємо помилки fetch, щоб не засмічувати консоль при обриві з'єднання
        } finally {
            // Рекурсивний виклик тільки після завершення поточного запиту
            setTimeout(updateDeviceStatuses, UPDATE_INTERVAL);
        }
    }

    // Запускаємо перше оновлення
    setTimeout(updateDeviceStatuses, UPDATE_INTERVAL);
});