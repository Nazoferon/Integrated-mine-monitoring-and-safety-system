document.addEventListener('DOMContentLoaded', () => {
    // Обробка натискання на іконки ока (показ/приховування пароля)
    const toggleIcons = document.querySelectorAll('.password-toggle-icon');
    toggleIcons.forEach(icon => {
        icon.addEventListener('click', function() {
            const input = this.previousElementSibling;
            if (!input || input.tagName !== 'INPUT') return;
            
            const isText = input.type === 'text';
            input.type = isText ? 'password' : 'text';
            
            this.classList.toggle('fa-eye', !isText);
            this.classList.toggle('fa-eye-slash', isText);
            this.style.animation = 'none';
            setTimeout(() => this.style.animation = 'pulse 0.2s', 10);
        });
    });

    const pwdInput = document.querySelector('input[name="new_password1"]');
    const pwdConfirm = document.querySelector('input[name="new_password2"]');
    const strengthContainer = document.getElementById('pwd-strength-container');
    const bars = document.querySelectorAll('.strength-bar');
    const text = document.getElementById('pwd-strength-text');
    const matchText = document.getElementById('password-match-text');

    function updateStrength() {
        const val = pwdInput.value;
        if (!val) { strengthContainer.style.display = 'none'; checkMatch(); return; }
        
        strengthContainer.style.display = 'block';
        let score = 0;
        if (val.length >= 8) score++;
        if (/[a-z]/.test(val) && /[A-Z]/.test(val)) score++;
        if (/[0-9]/.test(val)) score++;
        if (/[^A-Za-z0-9]/.test(val)) score++;
        
        bars.forEach(b => b.style.background = '#374151');
        
        let color, label;
        if (val.length < 8) { color = '#ef4444'; label = 'Закороткий (мінімум 8 символів)'; bars[0].style.background = color; }
        else if (score <= 2) { color = '#f59e0b'; label = 'Слабкий пароль'; bars[0].style.background = color; bars[1].style.background = color; }
        else if (score === 3) { color = '#3b82f6'; label = 'Надійний пароль'; bars[0].style.background = color; bars[1].style.background = color; bars[2].style.background = color; }
        else { color = '#10b981'; label = 'Дуже надійний!'; bars.forEach(b => b.style.background = color); }
        
        text.textContent = label;
        text.style.color = color;
        checkMatch();
    }

    function checkMatch() {
        if (!pwdConfirm.value) { matchText.style.display = 'none'; return; }
        matchText.style.display = 'block';
        if (pwdInput.value === pwdConfirm.value) {
            matchText.textContent = 'Паролі збігаються';
            matchText.style.color = '#10b981';
        } else {
            matchText.textContent = 'Паролі не збігаються';
            matchText.style.color = '#ef4444';
        }
    }

    if (pwdInput) ['input', 'keyup'].forEach(e => pwdInput.addEventListener(e, updateStrength));
    if (pwdConfirm) ['input', 'keyup'].forEach(e => pwdConfirm.addEventListener(e, checkMatch));
});