document.addEventListener('DOMContentLoaded', function() {
    console.log("✅ Скрипт керування персоналом завантажено (v2.0 - AJAX)");

    // --- 1. ГЛОБАЛЬНІ ЗМІННІ ТА СТАН ---
    const elements = {
        searchInput: document.getElementById('searchInput'),
        clearSearchBtn: document.getElementById('clearSearchBtn'),
        gridContainer: document.getElementById('personnelGrid'),
        noResultsMsg: document.getElementById('noResultsMsg'),
        paginationContainer: document.getElementById('pagination-container'),
        personnelCounter: document.getElementById('personnel-counter'),
        sortButtons: document.querySelectorAll('#btnSortStatus, #btnSortAlpha'),
        viewGridBtn: document.getElementById('btnGrid'),
        viewListBtn: document.getElementById('btnList'),
    };

    let state = {
        currentPage: 1,
        searchQuery: '',
        sortBy: 'status', // 'status' or 'name'
        isLoading: false,
        viewMode: localStorage.getItem('personnelViewStyle') || 'grid',
    };

    let searchTimeout;

    // --- 2. ОСНОВНА ФУНКЦІЯ ОТРИМАННЯ ДАНИХ ---
    async function fetchPersonnel() {
        if (state.isLoading) return;
        state.isLoading = true;
        
        // Показуємо лоадер
        elements.gridContainer.innerHTML = `
            <div class="personnel-loader text-center py-5 w-100">
                <i class="fas fa-spinner fa-spin fa-3x text-primary"></i>
            </div>`;
        elements.noResultsMsg.style.display = 'none';
        elements.paginationContainer.innerHTML = '';

        const params = new URLSearchParams({
            page: state.currentPage,
            q: state.searchQuery,
            sort: state.sortBy,
        });

        try {
            const response = await fetch(`/diploma/api/personnel-list/?${params.toString()}`);
            if (!response.ok) throw new Error('Network response was not ok');
            
            const data = await response.json();
            
            // Оновлюємо DOM
            elements.gridContainer.innerHTML = data.html || '';
            
            // Оновлюємо лічильник
            elements.personnelCounter.textContent = `Знайдено співробітників: ${data.total_results}`;

            // Показуємо повідомлення, якщо нічого не знайдено
            if (data.total_results === 0) {
                elements.noResultsMsg.style.display = 'block';
            }

            // Рендеримо пагінацію
            renderPagination(data.total_pages, data.current_page);

        } catch (error) {
            console.error("Fetch error:", error);
            elements.gridContainer.innerHTML = `
                <div class="personnel-loader text-center py-5 w-100">
                    <i class="fas fa-exclamation-triangle fa-3x text-danger"></i>
                    <h4 class="mt-3 text-muted">Помилка завантаження даних</h4>
                </div>`;
        } finally {
            state.isLoading = false;
        }
    }

    // --- 3. РЕНДЕРИНГ ПАГІНАЦІЇ ---
    function renderPagination(totalPages, currentPage) {
        if (totalPages <= 1) {
            elements.paginationContainer.innerHTML = '';
            return;
        }

        let html = '<ul class="pagination custom-pagination">';
        
        // Кнопка "Назад"
        html += `<li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                    <a class="page-link" href="#" data-page="${currentPage - 1}">«</a>
                 </li>`;
        
        // Генеруємо номери сторінок
        const pagesToShow = 5;
        let startPage = Math.max(1, currentPage - Math.floor(pagesToShow / 2));
        let endPage = Math.min(totalPages, startPage + pagesToShow - 1);

        if (endPage - startPage + 1 < pagesToShow) {
            startPage = Math.max(1, endPage - pagesToShow + 1);
        }

        if (startPage > 1) {
            html += `<li class="page-item"><a class="page-link" href="#" data-page="1">1</a></li>`;
            if (startPage > 2) html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }

        for (let i = startPage; i <= endPage; i++) {
            html += `<li class="page-item ${i === currentPage ? 'active' : ''}">
                        <a class="page-link" href="#" data-page="${i}">${i}</a>
                     </li>`;
        }

        if (endPage < totalPages) {
            if (endPage < totalPages - 1) html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            html += `<li class="page-item"><a class="page-link" href="#" data-page="${totalPages}">${totalPages}</a></li>`;
        }

        // Кнопка "Вперед"
        html += `<li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
                    <a class="page-link" href="#" data-page="${currentPage + 1}">»</a>
                 </li>`;

        html += '</ul>';
        elements.paginationContainer.innerHTML = html;
    }

    // --- 4. ОБРОБНИКИ ПОДІЙ ---
    function setupEventListeners() {
        // Пошук
        elements.searchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            elements.clearSearchBtn.classList.toggle('visible', elements.searchInput.value.length > 0);
            searchTimeout = setTimeout(() => {
                state.searchQuery = elements.searchInput.value;
                state.currentPage = 1;
                fetchPersonnel();
            }, 300); // Затримка для уникнення зайвих запитів
        });

        elements.clearSearchBtn.addEventListener('click', () => {
            elements.searchInput.value = '';
            elements.clearSearchBtn.classList.remove('visible');
            state.searchQuery = '';
            state.currentPage = 1;
            fetchPersonnel();
            elements.searchInput.focus();
        });

        // Сортування
        elements.sortButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const sortBy = btn.dataset.sort;
                if (state.sortBy !== sortBy) {
                    state.sortBy = sortBy;
                    state.currentPage = 1;
                    updateSortButtons();
                    fetchPersonnel();
                }
            });
        });

        // Пагінація (делегування подій)
        elements.paginationContainer.addEventListener('click', e => {
            e.preventDefault();
            const target = e.target.closest('a');
            if (!target || target.parentElement.classList.contains('disabled') || target.parentElement.classList.contains('active')) {
                return;
            }
            state.currentPage = parseInt(target.dataset.page);
            fetchPersonnel();
        });

        // Перемикання вигляду
        elements.viewGridBtn.addEventListener('click', () => setView('grid'));
        elements.viewListBtn.addEventListener('click', () => setView('list'));
    }

    // --- 5. ДОПОМІЖНІ ФУНКЦІЇ UI ---
    function updateSortButtons() {
        elements.sortButtons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.sort === state.sortBy);
        });
    }

    function setView(viewType) {
        state.viewMode = viewType;
        if (viewType === 'list') {
            elements.gridContainer.classList.add('list-view');
            elements.viewListBtn.classList.add('active');
            elements.viewGridBtn.classList.remove('active');
        } else {
            elements.gridContainer.classList.remove('list-view');
            elements.viewGridBtn.classList.add('active');
            elements.viewListBtn.classList.remove('active');
        }
        localStorage.setItem('personnelViewStyle', viewType);
    }

    // --- 6. ІНІЦІАЛІЗАЦІЯ ---
    function init() {
        setupEventListeners();
        updateSortButtons();
        setView(state.viewMode);
        fetchPersonnel(); // Перше завантаження даних
        
        // Старий функціонал оновлення статусів можна залишити, він працює незалежно
        startStatusUpdater();
    }
    
    // --- 7. ОНОВЛЕННЯ СТАТУСІВ (старий код, адаптований) ---
    function startStatusUpdater() {
        const API_URL = '/diploma/personnel-status-api/';
        const UPDATE_INTERVAL = 7000;

        async function updateDeviceStatuses() {
            try {
                const response = await fetch(API_URL);
                if (!response.ok) return;
                
                const data = await response.json();
                const statuses = data.device_statuses;
                if (!statuses) return;

                document.querySelectorAll('.employee-card[data-mac-address]').forEach(card => {
                    const mac = card.dataset.macAddress;
                    const statusInfo = statuses[mac];
                    if (!statusInfo) return;

                    const statusDiv = card.querySelector('.device-status');
                    const statusSpan = statusDiv.querySelector('span');
                    const statusDot = statusDiv.querySelector('.status-dot');
                    const locationValue = card.querySelector('.location-value');

                    const isCurrentlyActive = statusDiv.classList.contains('status-active');
                    const shouldBeActive = statusInfo.is_active;

                    if (isCurrentlyActive !== shouldBeActive) {
                        statusDiv.classList.add('updating');
                        setTimeout(() => {
                            if (shouldBeActive) {
                                statusDiv.className = 'device-status status-active';
                                statusDot.className = 'status-dot dot-active';
                                statusSpan.textContent = statusInfo.inventory_number;
                                statusDiv.title = '';
                            } else {
                                statusDiv.className = 'device-status status-device-inactive';
                                statusDot.className = 'status-dot dot-device-inactive';
                                statusSpan.textContent = `${statusInfo.inventory_number} (Неактивний)`;
                                statusDiv.title = 'Пристрій неактивний';
                            }
                            statusDiv.classList.remove('updating');
                        }, 500);
                    }
                    
                    // Оновлення локації
                    if (locationValue) {
                        const newLocationHTML = statusInfo.location ? 
                            `<a href="/diploma/mine_map/?focus_ap=${statusInfo.location}" class="location-link" title="Показати на карті"><i class="fas fa-map-marker-alt text-danger"></i> ${statusInfo.location}</a>` : 
                            '<span class="text-muted">Невідомо</span>';
                        
                        if (locationValue.innerHTML !== newLocationHTML) {
                            locationValue.innerHTML = newLocationHTML;
                        }
                    }
                });
            } catch (error) {
                // ігноруємо помилки
            } finally {
                setTimeout(updateDeviceStatuses, UPDATE_INTERVAL);
            }
        }
        setTimeout(updateDeviceStatuses, UPDATE_INTERVAL);
    }

    init();
});