document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('profileForm');
    const fileInput = document.querySelector('input[type="file"]');
    const profileImg = document.querySelector('.profile-avatar');
    const maxFileSize = 5 * 1024 * 1024; // 5 МБ
    const allowedFormats = ['image/png', 'image/jpeg', 'image/jpg'];

    // Клієнтська валідація файлу
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // Перевірка розміру
                if (file.size > maxFileSize) {
                    showMessage('Файл занадто великий! Максимум 5 МБ.', 'error');
                    e.target.value = ''; // Очистити поле
                    return;
                }
                // Перевірка формату
                if (!allowedFormats.includes(file.type)) {
                    showMessage('Непідтримуваний формат! Дозволено: PNG, JPG, JPEG.', 'error');
                    e.target.value = '';
                    return;
                }
                // Попередній перегляд
                if (window.dashboardApp) window.dashboardApp.showLoader('Обробка фото...');
                const reader = new FileReader();
                reader.onload = function(e) {
                    if (profileImg) {
                        profileImg.src = e.target.result;
                    }
                    showMessage('Фото оновлено! 📸', 'success');
                    if (window.dashboardApp) window.dashboardApp.hideLoader();
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // Повідомлення після відправки форми
    if (form) {
        form.addEventListener('submit', function(e) {
            // Якщо є помилки, вони відобразяться через {{ form.errors }}
            if (window.dashboardApp) window.dashboardApp.showLoader('Збереження змін...');
            showMessage('Зміни збережено! ✅', 'success');
        });
    }

    // Функція для показу повідомлень
    function showMessage(text, type = 'success') {
        if (window.dashboardApp && typeof window.dashboardApp.showNotification === 'function') {
            window.dashboardApp.showNotification(text, type);
        } else {
            alert(text);
        }
    }

    // Підсвічування активних полів
    const inputs = document.querySelectorAll('#profileForm input, #profileForm textarea');
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.style.transform = 'translateY(-2px)';
            this.parentElement.style.boxShadow = '0 2px 8px rgba(77, 171, 247, 0.3)';
        });
        input.addEventListener('blur', function() {
            this.parentElement.style.transform = 'translateY(0)';
            this.parentElement.style.boxShadow = 'none';
        });
    });
});