document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('.profile-page form');
    const fileInput = document.querySelector('input[type="file"]');
    const profileImg = document.querySelector('.profile-page img');
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
                const reader = new FileReader();
                reader.onload = function(e) {
                    if (profileImg) {
                        profileImg.src = e.target.result;
                    }
                    showMessage('Фото оновлено! 📸', 'success');
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // Повідомлення після відправки форми
    if (form) {
        form.addEventListener('submit', function(e) {
            // Якщо є помилки, вони відобразяться через {{ form.errors }}
            showMessage('Зміни збережено! ✅', 'success');
        });
    }

    // Функція для показу повідомлень
    function showMessage(text, type = 'success') {
        const messagesContainer = document.querySelector('.profile-messages') || document.createElement('div');
        if (!messagesContainer.classList.contains('profile-messages')) {
            messagesContainer.className = 'profile-messages';
            document.body.appendChild(messagesContainer);
        }

        const oldMessages = messagesContainer.querySelectorAll('.profile-message');
        oldMessages.forEach(msg => msg.remove());

        const message = document.createElement('div');
        message.className = `profile-message ${type} show`;
        message.innerHTML = `
            <i class="fas fa-${type === 'error' ? 'exclamation-circle' : 'check-circle'}"></i>
            <span>${text}</span>
        `;
        messagesContainer.appendChild(message);

        setTimeout(() => {
            message.classList.remove('show');
            setTimeout(() => {
                if (message.parentNode) {
                    message.parentNode.removeChild(message);
                }
            }, 300);
        }, 3000);
    }

    // Підсвічування активних полів
    const inputs = document.querySelectorAll('.profile-page input, .profile-page textarea');
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