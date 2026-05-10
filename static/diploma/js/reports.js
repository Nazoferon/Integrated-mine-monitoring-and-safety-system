document.addEventListener('DOMContentLoaded', function() {
    console.log("✅ Скрипт звітів та графіків завантажено");

    // --- АВТОМАТИЧНЕ ВСТАНОВЛЕННЯ ДАТ (Сьогодні та 30 днів тому) ---
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    
    if (startDateInput && endDateInput) {
        const today = new Date();
        const pastDate = new Date();
        pastDate.setDate(today.getDate() - 30); // За останні 30 днів
        
        const formatDate = (date) => {
            const yyyy = date.getFullYear();
            const mm = String(date.getMonth() + 1).padStart(2, '0');
            const dd = String(date.getDate()).padStart(2, '0');
            return `${yyyy}-${mm}-${dd}`;
        };

        if (!endDateInput.value) endDateInput.value = formatDate(today);
        if (!startDateInput.value) startDateInput.value = formatDate(pastDate);
    }

    // Налаштування кольорів для темної теми Chart.js
    Chart.defaults.color = '#888';
    Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.1)';

    // --- 1. Лінійний графік (Динаміка інцидентів) ---
    const ctxMain = document.getElementById('mainChart').getContext('2d');
    
    // Створюємо градієнт для заповнення графіка
    let gradient = ctxMain.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, 'rgba(77, 171, 247, 0.5)'); // Синій
    gradient.addColorStop(1, 'rgba(77, 171, 247, 0.0)');

    const mainChart = new Chart(ctxMain, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Кількість інцидентів',
                data: [],
                borderColor: '#4dabf7',
                backgroundColor: gradient,
                borderWidth: 2,
                pointBackgroundColor: '#fff',
                pointBorderColor: '#4dabf7',
                pointRadius: 4,
                fill: true,
                tension: 0.4 // Робить лінію плавною (хвилястою)
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(15, 15, 35, 0.9)',
                    titleColor: '#4dabf7',
                    bodyFont: { size: 14 },
                    padding: 12,
                    borderColor: 'rgba(77, 171, 247, 0.3)',
                    borderWidth: 1,
                    displayColors: false
                }
            },
            scales: {
                y: { beginAtZero: true, suggestedMax: 8 }
            }
        }
    });

    // --- 2. Круговий графік (Причини тривог) ---
    const ctxDoughnut = document.getElementById('doughnutChart').getContext('2d');
    const doughnutChart = new Chart(ctxDoughnut, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    '#ff4444', // Червоний (SOS)
                    '#ff9800', // Оранжевий (Падіння)
                    '#ffd700', // Жовтий (Батарея)
                    '#00c851'  // Зелений (Газ)
                ],
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%', // Товщина кільця
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#bbb', padding: 15, font: { size: 11 } }
                }
            }
        }
    });

    // --- 3. Отримання реальних даних при натисканні "Згенерувати" ---
    let isInitialLoad = true;
    let currentReportPage = 1;
    const generateBtn = document.getElementById('generateBtn');

    async function loadReportData(page = 1) {
        if (generateBtn && generateBtn.disabled) return;

        currentReportPage = page;
        const icon = generateBtn ? generateBtn.querySelector('i') : null;
        
        try {
            if (icon) icon.classList.add('fa-spin');
            if (generateBtn) generateBtn.disabled = true;
            
            if (window.dashboardApp && typeof window.dashboardApp.showLoader === 'function') {
                window.dashboardApp.showLoader('Отримання даних з БД...');
            }
            
            const reportType = document.getElementById('reportType').value;
            const startDate = document.getElementById('startDate').value;
            const endDate = document.getElementById('endDate').value;
            
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000);

            // ДОДАЄМО &page=${currentReportPage} ДО URL
            const response = await fetch(`/diploma/api/reports-data/?type=${reportType}&start_date=${startDate}&end_date=${endDate}&page=${currentReportPage}`, {
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            let data;
            try {
                data = await response.json();
            } catch (e) {
                if (!response.ok) {
                    throw new Error(`Помилка сервера: ${response.status} ${response.statusText}`);
                }
                throw new Error('Помилка обробки даних (невірний формат)');
            }
            
            if (!response.ok) {
                throw new Error(data.error || 'Помилка отримання даних з сервера');
            }
            
            const chartTitles = {
                'incidents': { main: 'Динаміка інцидентів (шт)', doughnut: 'Причини тривог' },
                'telemetry': { main: 'Максимальний рівень метану (% LEL)', doughnut: 'Розподіл небезпеки газу' },
                'equipment': { main: 'Події розряду батареї та втрати зв\'язку', doughnut: 'Склад обладнання' },
                'personnel': { main: 'Унікальні працівники в шахті (чол)', doughnut: 'Поточний статус безпеки' }
            };
            
            const mainTitleEl = document.getElementById('mainChartTitle');
            const doughnutTitleEl = document.getElementById('doughnutChartTitle');
            
            if (mainTitleEl && doughnutTitleEl && chartTitles[reportType]) {
                mainTitleEl.innerText = chartTitles[reportType].main;
                doughnutTitleEl.innerText = chartTitles[reportType].doughnut;
                mainChart.data.datasets[0].label = chartTitles[reportType].main;
            }

            if (data.chart_main) {
                mainChart.data.labels = data.chart_main.labels || [];
                mainChart.data.datasets[0].data = data.chart_main.values || [];
                
                if (mainChart.data.datasets[0].data.length === 1) {
                    mainChart.data.datasets[0].pointRadius = 8;
                    mainChart.data.datasets[0].pointBorderWidth = 3;
                } else {
                    mainChart.data.datasets[0].pointRadius = 4;
                    mainChart.data.datasets[0].pointBorderWidth = 1;
                }
                
                mainChart.update();
            }
            
            if (data.chart_doughnut) {
                doughnutChart.data.labels = data.chart_doughnut.labels || [];
                doughnutChart.data.datasets[0].data = data.chart_doughnut.values || [];
                if (data.chart_doughnut.colors) {
                    doughnutChart.data.datasets[0].backgroundColor = data.chart_doughnut.colors;
                }
                doughnutChart.update();
            }
            
            // --- РЕНДЕРИМО КАРТКИ З ПІДСУМКАМИ (SUMMARY CARDS) ---
            const summaryContainer = document.getElementById('summaryCardsContainer');
            if (summaryContainer) {
                if (data.summary_cards && data.summary_cards.length > 0) {
                    summaryContainer.innerHTML = data.summary_cards.map(card => `
                        <div class="col-12 col-md-4 mb-3 mb-md-0">
                            <div class="report-card h-100 d-flex align-items-center p-2 px-3 border-start border-3 border-${card.color}">
                                <div class="rounded-circle bg-${card.color} bg-opacity-10 me-2 d-flex justify-content-center align-items-center summary-icon-wrapper">
                                    <i class="fas ${card.icon} text-${card.color}"></i>
                                </div>
                                <div>
                                    <div class="text-muted text-uppercase fw-bold summary-card-title">${card.title}</div>
                                    <div class="text-white fw-bold fs-5 summary-card-value">${card.value}</div>
                                </div>
                            </div>
                        </div>
                    `).join('');
                } else {
                    summaryContainer.innerHTML = '';
                }
            }

            const tbody = document.getElementById('reportTableBody');
            if (tbody) {
                tbody.innerHTML = '';
                if (!data.table_rows || data.table_rows.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-5">
                    <i class="fas fa-folder-open fa-2x mb-3 opacity-50"></i><br>
                    За обраний період даних не знайдено
                </td></tr>`;
                } else {
                    data.table_rows.forEach(row => {
                        const tr = document.createElement('tr');
                        tr.className = 'tech-row';
                        tr.innerHTML = `
                            <td>${row.date || ''}</td>
                            <td class="${row.event_class || ''}">${row.event_text || ''}</td>
                            <td>${row.location || ''}</td>
                            <td>${row.person || ''}</td>
                            <td>${row.status_html || ''}</td>
                        `;
                        tbody.appendChild(tr);
                    });
                }
            }

            // ВІДМАЛЬОВУЄМО ПАГІНАЦІЮ
            if (data.pagination) {
                renderPagination(data.pagination);
            }
            
            if (!isInitialLoad && window.dashboardApp && typeof window.dashboardApp.showNotification === 'function') {
                window.dashboardApp.showNotification('Дані успішно завантажено!', 'success');
            }
            isInitialLoad = false;
            
        } catch (error) {
            console.error("Помилка генерації звіту:", error);
            const isTimeout = error.name === 'AbortError';
            const msg = isTimeout ? 'Сервер не відповідає. Перевірте з\'єднання.' : (error.message || 'Помилка при генерації звіту');
            
            if (window.dashboardApp && typeof window.dashboardApp.showNotification === 'function') {
                window.dashboardApp.showNotification(msg, 'critical');
            } else {
                alert(msg);
            }
        } finally {
            if (icon) icon.classList.remove('fa-spin');
            if (generateBtn) generateBtn.disabled = false;
            if (window.dashboardApp && typeof window.dashboardApp.hideLoader === 'function') window.dashboardApp.hideLoader();
        }
    }

    if (generateBtn) {
        generateBtn.addEventListener('click', () => loadReportData(1));
    }

    // --- Автоматичне оновлення при зміні параметрів ---
    ['reportType', 'startDate', 'endDate'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', () => loadReportData(1));
        }
    });

    // Завантажуємо дані за замовчуванням при відкритті сторінки
    if (generateBtn) loadReportData(1);

    // --- Рендеринг кнопок сторінок ---
    function renderPagination(pagination) {
        const wrapper = document.getElementById('paginationWrapper');
        const info = document.getElementById('paginationInfo');
        const controls = document.getElementById('paginationControls');
        
        if (!wrapper || !info || !controls) return;
        
        if (!pagination || pagination.total === 0) {
            wrapper.style.setProperty('display', 'none', 'important');
            return;
        }
        
        wrapper.style.setProperty('display', 'flex', 'important');
        
        const startRec = (pagination.current - 1) * pagination.per_page + 1;
        const endRec = Math.min(pagination.current * pagination.per_page, pagination.total);
        info.innerHTML = `Показано <b>${startRec}-${endRec}</b> з <b>${pagination.total}</b>`;
        
        let html = '';
        
        html += `<li class="page-item ${pagination.current === 1 ? 'disabled' : ''}">
                    <a class="page-link" href="#" data-page="${pagination.current - 1}">«</a>
                 </li>`;
                 
        let startPage = Math.max(1, pagination.current - 2);
        let endPage = Math.min(pagination.pages, pagination.current + 2);
        
        if (startPage > 1) {
            html += `<li class="page-item"><a class="page-link" href="#" data-page="1">1</a></li>`;
            if (startPage > 2) html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
        
        for (let i = startPage; i <= endPage; i++) {
            html += `<li class="page-item ${i === pagination.current ? 'active' : ''}">
                        <a class="page-link" href="#" data-page="${i}">${i}</a>
                     </li>`;
        }
        
        if (endPage < pagination.pages) {
            if (endPage < pagination.pages - 1) html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            html += `<li class="page-item"><a class="page-link" href="#" data-page="${pagination.pages}">${pagination.pages}</a></li>`;
        }
        
        html += `<li class="page-item ${pagination.current === pagination.pages ? 'disabled' : ''}">
                    <a class="page-link" href="#" data-page="${pagination.current + 1}">»</a>
                 </li>`;
                 
        controls.innerHTML = html;
        
        controls.querySelectorAll('.page-link').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const parent = this.parentElement;
                if (parent.classList.contains('disabled') || parent.classList.contains('active')) return;
                
                const newPage = parseInt(this.getAttribute('data-page'));
                if (newPage && newPage !== currentReportPage) {
                    loadReportData(newPage); // Завантажуємо нову сторінку
                }
            });
        });
    }

    // --- 4. Експорт у CSV (Дані для Excel) ---
    const exportCsvBtn = document.getElementById('exportCsvBtn');
    if (exportCsvBtn) {
        exportCsvBtn.addEventListener('click', function() {
            const reportSelect = document.getElementById('reportType');
            const reportValue = reportSelect.value;
            const startDate = document.getElementById('startDate').value;
            const endDate = document.getElementById('endDate').value;
            
            const exportUrl = `/diploma/api/reports-data/?type=${reportValue}&start_date=${startDate}&end_date=${endDate}&export=csv`;
            
            const link = document.createElement("a");
            link.href = exportUrl;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            if (window.dashboardApp && typeof window.dashboardApp.showNotification === 'function') {
                window.dashboardApp.showNotification('Формування повного файлу CSV розпочато...', 'info');
            }
        });
    }

    // --- 5. Друк та Експорт у PDF ---
    const handlePrintAndPdf = function() {
        // Заповнюємо дані для шапки друку
        const reportSelect = document.getElementById('reportType');
        const reportType = reportSelect ? reportSelect.options[reportSelect.selectedIndex].text : 'Звіт';
        const reportValue = reportSelect ? reportSelect.value : 'report';
        const startDate = document.getElementById('startDate') ? document.getElementById('startDate').value : '';
        const endDate = document.getElementById('endDate') ? document.getElementById('endDate').value : '';
        
        const printTitle = document.getElementById('printReportTitle');
        if (printTitle) {
            printTitle.innerHTML = `<strong>${reportType}</strong><br><small class="text-muted">Період аналізу: з ${startDate} по ${endDate}</small>`;
        }

        // Тимчасово змінюємо назву документа, щоб браузер зберіг PDF з гарним ім'ям
        const originalTitle = document.title;
        document.title = `Glybina4.0_Summary_${reportValue}_${startDate}_to_${endDate}`;

        // Викликаємо нативний діалог друку/збереження PDF браузера
        window.print();
        
        // Повертаємо оригінальну назву сайту
        setTimeout(() => { document.title = originalTitle; }, 1000);
    };

    const exportPdfBtn = document.getElementById('exportPdfBtn');
    if (exportPdfBtn) {
        exportPdfBtn.addEventListener('click', () => {
            const printDate = document.getElementById('printDateGenerated');
            if (printDate) printDate.innerText = new Date().toLocaleString('uk-UA');
            
            if (window.dashboardApp && typeof window.dashboardApp.showNotification === 'function') {
                window.dashboardApp.showNotification('У вікні друку оберіть "Зберегти як PDF"', 'info');
            }
            
            setTimeout(handlePrintAndPdf, 600);
        });
    }

    // --- АВТОМАТИЧНА ЗМІНА ТЕМИ ГРАФІКІВ ДЛЯ ДРУКУ ---
    window.addEventListener('beforeprint', () => {
        Chart.defaults.color = '#000'; // Чорний текст для PDF
        mainChart.update(); doughnutChart.update();
    });

    window.addEventListener('afterprint', () => {
        Chart.defaults.color = '#888'; // Повертаємо сірий для сайту
        mainChart.update(); doughnutChart.update();
    });
});