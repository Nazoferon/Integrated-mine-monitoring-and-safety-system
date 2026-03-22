document.addEventListener('DOMContentLoaded', function() {
    console.log("✅ Скрипт звітів та графіків завантажено");

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
            labels: ['01 Березня', '04 Березня', '08 Березня', '12 Березня', '16 Березня', '20 Березня', 'Сьогодні'],
            datasets: [{
                label: 'Кількість інцидентів',
                data: [3, 1, 5, 2, 0, 4, 1],
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
            plugins: {
                legend: { display: false }
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
            labels: ['Кнопка SOS', 'Падіння (Man Down)', 'Низький заряд', 'Газ (CO)'],
            datasets: [{
                data: [40, 15, 25, 20],
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
    const generateBtn = document.getElementById('generateBtn');
    if (generateBtn) {
        generateBtn.addEventListener('click', async function() {
            // Запобігання подвійним клікам та накладанням запитів
            if (this.disabled) return;

            const icon = generateBtn.querySelector('i');
            
            try {
                if (icon) icon.classList.add('fa-spin');
                generateBtn.disabled = true;
                
                if (window.dashboardApp && typeof window.dashboardApp.showLoader === 'function') {
                    window.dashboardApp.showLoader('Отримання даних з БД...');
                }
                
                const reportType = document.getElementById('reportType').value;
                const startDate = document.getElementById('startDate').value;
                const endDate = document.getElementById('endDate').value;
                
                // Додаємо таймаут 10 секунд на випадок, якщо мережа зависла (через розширення браузера)
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 10000);

                const response = await fetch(`/diploma/api/reports-data/?type=${reportType}&start_date=${startDate}&end_date=${endDate}`, {
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
                // Спочатку парсимо JSON, щоб отримати текст помилки з бекенду (якщо є)
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.error || 'Помилка отримання даних з сервера');
                }
                
                if (data.chart_main) {
                    mainChart.data.labels = data.chart_main.labels || [];
                    mainChart.data.datasets[0].data = data.chart_main.values || [];
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
                
                const tbody = document.getElementById('reportTableBody');
                if (tbody) {
                    tbody.innerHTML = '';
                    if (!data.table_rows || data.table_rows.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted" style="padding: 20px;">За обраний період даних не знайдено</td></tr>';
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
                generateBtn.disabled = false;
                if (window.dashboardApp && typeof window.dashboardApp.hideLoader === 'function') window.dashboardApp.hideLoader();
            }
        });
    }

    // --- Автоматичне оновлення при зміні параметрів ---
    ['reportType', 'startDate', 'endDate'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', () => generateBtn.click());
        }
    });

    // Завантажуємо дані за замовчуванням при відкритті сторінки
    generateBtn.click();

    // --- Допоміжна функція для отримання вибраних колонок таблиці ---
    function getExportData() {
        const colCheckboxes = document.querySelectorAll('.col-toggle');
        const selectedIndices = Array.from(colCheckboxes)
            .filter(cb => cb.checked)
            .map(cb => parseInt(cb.value));
            
        if (selectedIndices.length === 0) {
            alert('Будь ласка, оберіть хоча б одну колонку для експорту.');
            return null;
        }

        const headers = Array.from(document.querySelectorAll('.tech-table thead th'))
            .filter((_, index) => selectedIndices.includes(index))
            .map(th => th.innerText.trim());

        const rows = [];
        document.querySelectorAll('.tech-table tbody tr').forEach(row => {
            const cells = Array.from(row.querySelectorAll('td'));
            // Пропускаємо рядок "Даних не знайдено", якщо в ньому менше колонок
            if (cells.length < selectedIndices.length) return; 
            
            const rowData = selectedIndices.map(index => cells[index].innerText.trim().replace(/\n/g, ' '));
            rows.push(rowData);
        });

        return { headers, rows };
    }

    // --- 4. Експорт у CSV (Дані для Excel) ---
    const exportCsvBtn = document.getElementById('exportCsvBtn');
    if (exportCsvBtn) {
        exportCsvBtn.addEventListener('click', function() {
            const data = getExportData();
            if (!data) return;

            let csvContent = "\uFEFF"; // BOM для підтримки кирилиці в Excel
            
            const reportSelect = document.getElementById('reportType');
            const reportType = reportSelect.options[reportSelect.selectedIndex].text;
            const startDate = document.getElementById('startDate').value;
            const endDate = document.getElementById('endDate').value;
            
            csvContent += `Звіт: ${reportType}\n`;
            csvContent += `Період: ${startDate} — ${endDate}\n`;
            csvContent += `Створено: ${new Date().toLocaleString('uk-UA')}\n\n`;

            // Заголовки таблиці
            csvContent += data.headers.map(h => `"${h}"`).join(";") + "\n";

            // Рядки таблиці
            data.rows.forEach(row => {
                csvContent += row.map(cell => `"${cell.replace(/"/g, '""')}"`).join(";") + "\n";
            });

            // Завантаження файлу
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.setAttribute("href", url);
            link.setAttribute("download", `Glybina4.0_Data_${new Date().toISOString().slice(0,10)}.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            if (window.dashboardApp && typeof window.dashboardApp.showNotification === 'function') {
                window.dashboardApp.showNotification('CSV файл з даними завантажено!', 'success');
            }
        });
    }

    // --- 5. Друк та Експорт у PDF ---
    const handlePrintAndPdf = function() {
        // Заповнюємо дані для шапки друку
        const reportSelect = document.getElementById('reportType');
        const reportType = reportSelect ? reportSelect.options[reportSelect.selectedIndex].text : 'Звіт';
        const startDate = document.getElementById('startDate') ? document.getElementById('startDate').value : '';
        const endDate = document.getElementById('endDate') ? document.getElementById('endDate').value : '';
        
        const printTitle = document.getElementById('printReportTitle');
        if (printTitle) {
            printTitle.innerHTML = `<strong>${reportType}</strong><br><small class="text-muted">Період аналізу: з ${startDate} по ${endDate}</small>`;
        }

        // Викликаємо нативний діалог друку/збереження PDF браузера
        window.print();
    };

    const exportPdfBtn = document.getElementById('exportPdfBtn');
    if (exportPdfBtn) exportPdfBtn.addEventListener('click', handlePrintAndPdf);
});