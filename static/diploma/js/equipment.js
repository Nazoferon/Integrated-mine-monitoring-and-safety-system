// Супер-швидкий скрипт пошуку по всіх таблицях
document.addEventListener('DOMContentLoaded', function() {
    console.log("✅ Скрипт пошуку обладнання завантажено");
    
    const searchInput = document.getElementById('eqSearchInput');
    
    // Перевіряємо чи є інпут на сторінці, щоб не було помилок
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            const term = e.target.value.toLowerCase().trim();
            const rows = document.querySelectorAll('.data-row');
            
            rows.forEach(row => {
                // Шукаємо текст тільки в ячейках з класом search-target
                const textData = Array.from(row.querySelectorAll('.search-target'))
                                      .map(td => td.textContent.toLowerCase())
                                      .join(' ');
                
                if (textData.includes(term)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }
});