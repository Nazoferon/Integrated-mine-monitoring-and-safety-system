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
}

document.addEventListener('DOMContentLoaded', () => {
    new EquipmentPage();
});