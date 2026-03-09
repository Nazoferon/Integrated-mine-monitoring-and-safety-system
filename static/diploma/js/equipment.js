// Супер-швидкий скрипт пошуку по всіх таблицях
document.addEventListener('DOMContentLoaded', function() {
    console.log("✅ Скрипт пошуку обладнання завантажено");
    
    const searchInput = document.getElementById('eqSearchInput');
    const clearSearchBtn = document.getElementById('clearEqSearchBtn');
    
    // Функція фільтрації
    function filterEquipment() {
        const term = searchInput.value.toLowerCase().trim();
        const rows = document.querySelectorAll('.tech-row');
        
        // Показуємо/ховаємо кнопку очищення
        if (clearSearchBtn) {
            if (searchInput.value.length > 0) {
                clearSearchBtn.classList.add('visible');
            } else {
                clearSearchBtn.classList.remove('visible');
            }
        }
        
        rows.forEach(row => {
            // Шукаємо текст тільки в ячейках з класом search-target
            const textData = Array.from(row.querySelectorAll('.search-target'))
                                  .map(td => td.textContent.toLowerCase())
                                  .join(' ');
            
            if (textData.includes(term) || term === '') {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }
    
    // Функція очищення
    function clearSearch() {
        if (searchInput) {
            searchInput.value = '';
            filterEquipment();
            searchInput.focus();
        }
    }
    
    // Перевіряємо чи є інпут на сторінці, щоб не було помилок
    if (searchInput) {
        searchInput.addEventListener('input', filterEquipment);
        
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
    
    // --- 3. ЛОГІКА СОРТУВАННЯ ТАБЛИЦІ ПО БАТАРЕЇ ---
    const batteryHeader = document.getElementById('sort-battery');

    if (batteryHeader) {
        let sortDirection = 'none'; // 'none', 'desc', 'asc'

        // Функція для отримання числового значення заряду
        const getBatteryValue = (row) => {
            const levelDiv = row.querySelector('.battery-level');
            if (!levelDiv) return 0;
            if (levelDiv.classList.contains('bat-high')) return 3;
            if (levelDiv.classList.contains('bat-med')) return 2;
            if (levelDiv.classList.contains('bat-low')) return 1;
            return 0;
        };

        batteryHeader.addEventListener('click', () => {
            // Визначаємо напрямок сортування
            if (sortDirection === 'none' || sortDirection === 'asc') {
                sortDirection = 'desc'; // Спочатку сортуємо від більшого до меншого
            } else {
                sortDirection = 'asc';
            }

            // Оновлюємо класи для іконок
            batteryHeader.classList.remove('sort-asc', 'sort-desc');
            if (sortDirection === 'asc') {
                batteryHeader.classList.add('sort-asc');
            } else {
                batteryHeader.classList.add('sort-desc');
            }

            // Отримуємо тіло таблиці та рядки
            const tableBody = document.querySelector('#lamps tbody');
            const rows = Array.from(tableBody.querySelectorAll('tr.tech-row'));

            // Сортуємо масив рядків
            rows.sort((rowA, rowB) => {
                const valueA = getBatteryValue(rowA);
                const valueB = getBatteryValue(rowB);

                return (sortDirection === 'asc') ? valueA - valueB : valueB - valueA;
            });

            // Вставляємо відсортовані рядки назад в таблицю
            rows.forEach(row => tableBody.appendChild(row));
        });
    }
});