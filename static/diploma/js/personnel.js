document.addEventListener('DOMContentLoaded', function() {
    console.log("✅ Скрипт керування персоналом завантажено");

    // --- 1. ЛОГІКА ПОШУКУ ---
    const searchInput = document.getElementById('searchInput');
    const cards = document.querySelectorAll('.employee-card');
    const noResultsMsg = document.getElementById('noResultsMsg');

    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase().trim();
            let visibleCards = 0;

            cards.forEach(card => {
                const name = card.querySelector('.emp-name').textContent.toLowerCase();
                const badge = card.querySelector('.detail-value').textContent.toLowerCase();
                const position = card.querySelector('.emp-position').textContent.toLowerCase();
                
                const column = card.closest('.personnel-col');

                if (name.includes(searchTerm) || badge.includes(searchTerm) || position.includes(searchTerm)) {
                    if (column) column.style.display = '';
                    visibleCards++;
                } else {
                    if (column) column.style.display = 'none';
                }
            });

            if (noResultsMsg) {
                noResultsMsg.style.display = (visibleCards === 0 && cards.length > 0) ? 'block' : 'none';
            }
        });
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
});