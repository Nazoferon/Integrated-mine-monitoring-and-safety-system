// Супер-швидкий скрипт пошуку по всіх таблицях
document.addEventListener('DOMContentLoaded', function() {
    console.log("✅ Скрипт пошуку обладнання завантажено");
    
    const searchInput = document.getElementById('eqSearchInput');
    const clearSearchBtn = document.getElementById('clearEqSearchBtn');
    
    // Функція фільтрації
    function filterEquipment() {
        const term = searchInput.value.toLowerCase().trim();
        const rows = document.querySelectorAll('.data-row');
        
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
    
    // Додатково: додамо лічильник видимих рядків (опціонально)
    function updateResultsCount() {
        const visibleRows = document.querySelectorAll('.data-row[style="display: ""]').length;
        const totalRows = document.querySelectorAll('.data-row').length;
        const resultsInfo = document.getElementById('resultsCount');
        
        if (resultsInfo) {
            resultsInfo.textContent = `Показано: ${visibleRows} з ${totalRows}`;
        }
    }
});