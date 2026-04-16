document.addEventListener('DOMContentLoaded', () => {
    console.log("✅ Скрипт сторінки обладнання завантажено (v3.0 - AJAX)");

    const elements = {
        searchInput: document.getElementById('eqSearchInput'),
        clearSearchBtn: document.getElementById('clearEqSearchBtn'),
        tabs: document.querySelectorAll('#eqTabs .nav-link'),
        tabContents: document.querySelectorAll('.tab-pane'),
        tabsContentContainer: document.getElementById('eqTabsContent'),
    };

    let state = {
        activeTab: 'lamps',
        searchQuery: '',
        currentPage: 1,
        sort: {
            lamps: { by: 'status', dir: 'desc' },
            sensors: { by: 'status', dir: 'desc' },
            repeaters: { by: 'status', dir: 'desc' },
        },
        isLoading: false,
    };

    let searchTimeout;

    async function fetchEquipment() {
        if (state.isLoading) return;
        state.isLoading = true;

        const currentTabPane = document.getElementById(state.activeTab);
        const tableBody = currentTabPane.querySelector('tbody');
        const paginationContainer = currentTabPane.querySelector('.pagination-container');

        tableBody.innerHTML = `<tr><td colspan="6" class="text-center py-5"><i class="fas fa-spinner fa-spin fa-2x text-primary"></i></td></tr>`;
        if (paginationContainer) paginationContainer.innerHTML = '';

        const params = new URLSearchParams({
            tab: state.activeTab,
            q: state.searchQuery,
            page: state.currentPage,
            sort: state.sort[state.activeTab].by,
            dir: state.sort[state.activeTab].dir,
        });

        try {
            const response = await fetch(`/diploma/api/equipment-list/?${params.toString()}`);
            if (!response.ok) throw new Error('Network response was not ok');

            const data = await response.json();
            tableBody.innerHTML = data.html;

            // Встановлюємо початкову ширину для індикаторів батареї
            tableBody.querySelectorAll('.tech-row').forEach(row => {
                const batteryLevelEl = row.querySelector('.battery-level');
                if (batteryLevelEl) {
                    batteryLevelEl.style.width = (row.dataset.battery || '0') + '%';
                }
            });

            if (paginationContainer) {
                renderPagination(paginationContainer, data);
            }

        } catch (error) {
            console.error("Fetch error:", error);
            tableBody.innerHTML = `<tr><td colspan="6" class="text-center py-5 text-danger"><i class="fas fa-exclamation-triangle me-2"></i> Помилка завантаження даних</td></tr>`;
        } finally {
            state.isLoading = false;
        }
    }

    function renderPagination(container, data) {
        const { total_pages, current_page } = data;
        if (total_pages <= 1) {
            container.innerHTML = '';
            return;
        }

        let html = '<ul class="pagination custom-pagination">';
        html += `<li class="page-item ${current_page === 1 ? 'disabled' : ''}"><a class="page-link" href="#" data-page="${current_page - 1}">«</a></li>`;

        const pagesToShow = 5;
        let startPage = Math.max(1, current_page - Math.floor(pagesToShow / 2));
        let endPage = Math.min(total_pages, startPage + pagesToShow - 1);

        if (endPage - startPage + 1 < pagesToShow) {
            startPage = Math.max(1, endPage - pagesToShow + 1);
        }

        if (startPage > 1) {
            html += `<li class="page-item"><a class="page-link" href="#" data-page="1">1</a></li>`;
            if (startPage > 2) html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }

        for (let i = startPage; i <= endPage; i++) {
            html += `<li class="page-item ${i === current_page ? 'active' : ''}"><a class="page-link" href="#" data-page="${i}">${i}</a></li>`;
        }

        if (endPage < total_pages) {
            if (endPage < total_pages - 1) html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            html += `<li class="page-item"><a class="page-link" href="#" data-page="${total_pages}">${total_pages}</a></li>`;
        }

        html += `<li class="page-item ${current_page === total_pages ? 'disabled' : ''}"><a class="page-link" href="#" data-page="${current_page + 1}">»</a></li>`;
        html += '</ul>';
        container.innerHTML = html;
    }

    function setupEventListeners() {
        elements.searchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            elements.clearSearchBtn.classList.toggle('visible', elements.searchInput.value.length > 0);
            searchTimeout = setTimeout(() => {
                state.searchQuery = elements.searchInput.value;
                state.currentPage = 1;
                fetchEquipment();
            }, 350);
        });

        elements.clearSearchBtn.addEventListener('click', () => {
            elements.searchInput.value = '';
            elements.clearSearchBtn.classList.remove('visible');
            state.searchQuery = '';
            state.currentPage = 1;
            fetchEquipment();
            elements.searchInput.focus();
        });

        elements.tabs.forEach(tab => {
            tab.addEventListener('show.bs.tab', event => {
                state.activeTab = event.target.dataset.bsTarget.replace('#', '');
                state.currentPage = 1;
                state.searchQuery = '';
                elements.searchInput.value = '';
                elements.clearSearchBtn.classList.remove('visible');
                updateSortHeaders();
                fetchEquipment();
            });
        });

        document.querySelectorAll('.sortable').forEach(header => {
            header.addEventListener('click', () => {
                const sortBy = header.dataset.sortBy;
                const currentSort = state.sort[state.activeTab];

                if (currentSort.by === sortBy) {
                    currentSort.dir = currentSort.dir === 'desc' ? 'asc' : 'desc';
                } else {
                    currentSort.by = sortBy;
                    currentSort.dir = 'desc';
                }
                state.currentPage = 1;
                updateSortHeaders();
                fetchEquipment();
            });
        });

        elements.tabsContentContainer.addEventListener('click', e => {
            const link = e.target.closest('.page-link');
            if (!link) return;
            e.preventDefault();
            const page = link.dataset.page;
            if (page && !link.parentElement.classList.contains('disabled') && !link.parentElement.classList.contains('active')) {
                state.currentPage = parseInt(page);
                fetchEquipment();
            }
        });
    }
    
    function updateSortHeaders() {
        document.querySelectorAll('.sortable').forEach(header => {
            header.classList.remove('sort-asc', 'sort-desc');
            const sortBy = header.dataset.sortBy;
            const currentSort = state.sort[state.activeTab];
            if (currentSort.by === sortBy) {
                header.classList.add(currentSort.dir === 'asc' ? 'sort-asc' : 'sort-desc');
            }
        });
    }

    function startRealTelemetryUpdates() {
        const updateTelemetry = async () => {
            try {
                const response = await fetch('/diploma/api/equipment-telemetry/');
                if (!response.ok) return;
                
                const data = await response.json();
                
                document.querySelectorAll('.tech-row').forEach(row => {
                    const mac = row.dataset.mac;
                    const uid = row.dataset.uid;
                    const deviceData = mac ? data.devices?.[mac] : data.repeaters?.[uid];
                    const isNowActive = !!deviceData;

                    row.classList.toggle('offline-device', !isNowActive);

                    if (isNowActive) {
                        if (mac) { // Lamps and Sensors
                            const batteryLevelEl = row.querySelector('.battery-level');
                            if (batteryLevelEl) {
                                const level = deviceData.battery;
                                batteryLevelEl.style.width = level + '%';
                                batteryLevelEl.parentElement.title = `Рівень заряду: ${level}%`;
                                batteryLevelEl.className = 'battery-level';
                                if (level >= 50) batteryLevelEl.classList.add('bat-high');
                                else if (level >= 20) batteryLevelEl.classList.add('bat-med');
                                else batteryLevelEl.classList.add('bat-low');
                            }
                            const gasSpan = row.querySelector('.sim-gas');
                            if (gasSpan) gasSpan.textContent = deviceData.gas;
                            const tempSpan = row.querySelector('.sim-temp');
                            if (tempSpan) tempSpan.textContent = deviceData.temp !== null ? deviceData.temp : '--';
                        }
                        if (uid) { // Repeaters
                            const clientsSpan = row.querySelector('.sim-clients');
                            if (clientsSpan) clientsSpan.textContent = deviceData.clients;
                            const clientsWrapper = row.querySelector('.clients-wrapper');
                            if (clientsWrapper) clientsWrapper.title = deviceData.clients > 0 ? `Підключені:\n${deviceData.clients_list}` : 'Немає підключень';
                        }
                    }
                });
            } catch (error) {
                // Ignore fetch errors
            } finally {
                setTimeout(updateTelemetry, 5000);
            }
        };
        setTimeout(updateTelemetry, 5000);
    }

    function init() {
        setupEventListeners();
        updateSortHeaders();
        fetchEquipment();
        startRealTelemetryUpdates();
    }

    init();
});