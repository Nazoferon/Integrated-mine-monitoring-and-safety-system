document.addEventListener('DOMContentLoaded', () => {
    
    // --- 1. Mobile Menu Functionality (Залишили як було, працює добре) ---
    const menuToggle = document.querySelector('.menu-toggle');
    const navLinks = document.querySelector('.nav-links');
    const body = document.body;

    if (menuToggle && navLinks) {
        menuToggle.addEventListener('click', () => {
            menuToggle.classList.toggle('active');
            navLinks.classList.toggle('active');
            
            // Блокування скролу при відкритому меню
            if (navLinks.classList.contains('active')) {
                body.style.overflow = 'hidden';
            } else {
                body.style.overflow = 'auto';
            }
        });

        // Закриття меню при кліку на посилання
        navLinks.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                menuToggle.classList.remove('active');
                navLinks.classList.remove('active');
                body.style.overflow = 'auto';
            });
        });

        // Закриття при кліку поза меню
        document.addEventListener('click', (e) => {
            if (navLinks.classList.contains('active') && 
                !e.target.closest('.nav-links') && 
                !e.target.closest('.menu-toggle')) {
                menuToggle.classList.remove('active');
                navLinks.classList.remove('active');
                body.style.overflow = 'auto';
            }
        });
    }

    // --- 2. NEW Category Filtering (Адаптовано під Django Cards) ---
    const filterButtons = document.querySelectorAll('.filter-btn');
    const projectCards = document.querySelectorAll('.project-card');

    if (filterButtons.length > 0) {
        filterButtons.forEach(button => {
            button.addEventListener('click', () => {
                // Активний клас для кнопок
                filterButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');

                const filterValue = button.getAttribute('data-category');

                projectCards.forEach(card => {
                    const cardCategory = card.getAttribute('data-category');

                    if (filterValue === 'all' || filterValue === cardCategory) {
                        // Показуємо картку
                        card.style.display = 'flex';
                        // Невелика затримка для анімації opacity
                        setTimeout(() => {
                            card.classList.remove('hidden');
                            card.classList.add('visible');
                            card.style.opacity = '1';
                            card.style.transform = 'translateY(0)';
                        }, 10);
                    } else {
                        // Ховаємо картку
                        card.style.opacity = '0';
                        card.style.transform = 'translateY(20px)';
                        card.classList.remove('visible');
                        card.classList.add('hidden');
                        
                        // Чекаємо завершення анімації перед display: none
                        setTimeout(() => {
                            card.style.display = 'none';
                        }, 300);
                    }
                });
            });
        });
    }

    // --- 3. Intersection Observer (Анімація появи при скролі) ---
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                // observer.unobserve(entry.target); // Розкоментуй, якщо хочеш анімацію лише один раз
            }
        });
    }, observerOptions);

    document.querySelectorAll('.project-card, .contact-card, .hero-content').forEach(el => {
        el.classList.add('fade-in'); // Додаємо клас для початкового стану
        observer.observe(el);
    });


    // --- 4. Smooth Scrolling & Header ---
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = anchor.getAttribute('href');
            const targetElement = document.querySelector(targetId);

            if (targetElement) {
                const headerHeight = document.querySelector('header').offsetHeight;
                const targetPosition = targetElement.getBoundingClientRect().top + window.pageYOffset - headerHeight;

                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });

    const header = document.querySelector('header');
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            header.style.background = 'rgba(15, 15, 35, 0.98)';
            header.style.boxShadow = '0 4px 30px rgba(0, 0, 0, 0.1)';
        } else {
            header.style.background = 'rgba(15, 15, 35, 0.95)';
            header.style.boxShadow = 'none';
        }
    });


    // --- 5. Stats Counter Animation ---
    const animateCounter = (element, target) => {
        let count = 0;
        const duration = 2000; // 2 секунди
        const startTime = performance.now();

        const updateCount = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function для плавності
            const easeOutQuad = progress * (2 - progress);
            
            count = Math.floor(easeOutQuad * target);
            element.textContent = count + (target >= 5 ? '+' : ''); // Додаємо плюсик якщо число велике

            if (progress < 1) {
                requestAnimationFrame(updateCount);
            } else {
                element.textContent = target + (target >= 5 ? '+' : '');
            }
        };

        requestAnimationFrame(updateCount);
    };

    const heroStats = document.querySelector('.hero-stats');
    if (heroStats) {
        const statsObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    document.querySelectorAll('.stat-number').forEach(stat => {
                        const target = parseInt(stat.getAttribute('data-target') || stat.textContent);
                        animateCounter(stat, target);
                    });
                    statsObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });
        statsObserver.observe(heroStats);
    }


    // --- 6. Contact Cards Clickable ---
    document.querySelectorAll('.contact-card').forEach(card => {
        card.addEventListener('click', function(e) {
            // Щоб не спрацьовувало двічі якщо клікнули прямо по посиланню
            if (e.target.tagName !== 'A') {
                const link = card.querySelector('a');
                if (link) link.click();
            }
        });
    });


    // --- 7. Password Toggle (З перевіркою існування) ---
    const passwordToggle = document.getElementById('showPassword');
    if (passwordToggle) {
        passwordToggle.addEventListener('change', function() {
            const passwordInput = document.getElementById('password');
            if (passwordInput) {
                passwordInput.type = this.checked ? 'text' : 'password';
            }
        });
    }

    // --- 8. Theme Switcher (Новий функціонал) ---
    // Потрібно додати кнопку з id="theme-toggle" в HTML
    const themeToggleBtn = document.getElementById('theme-toggle');
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
    
    // Перевіряємо збережену тему або налаштування системи
    const currentTheme = localStorage.getItem('theme');
    if (currentTheme == 'light') {
        document.body.setAttribute('data-theme', 'light');
    } else {
        document.body.setAttribute('data-theme', 'dark');
    }

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            let theme = document.body.getAttribute('data-theme');
            if (theme === 'dark') {
                document.body.setAttribute('data-theme', 'light');
                localStorage.setItem('theme', 'light');
            } else {
                document.body.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
            }
        });
    }

    // --- 9. Language Switcher (Простий перекладач) ---
    const langToggleBtn = document.getElementById('lang-toggle');
    const translations = {
        'uk': {
            'role': '• Розробник •',
            'works_title': 'Мої Роботи',
            'works_desc': 'Колекція проєктів, які демонструють мої навички',
            'contact_title': 'Зв\'язатися',
            'contact_desc': 'Готовий до нових проєктів та цікавих викликів',
            'btn_projects': 'Переглянути проєкти',
            'btn_contact': 'Зв\'язатися',
            'status_completed': 'Завершено',
            'status_idea': 'В розробці'
        },
        'en': {
            'role': '• Developer •',
            'works_title': 'My Works',
            'works_desc': 'A collection of projects demonstrating my skills',
            'contact_title': 'Contact Me',
            'contact_desc': 'Ready for new projects and interesting challenges',
            'btn_projects': 'View Projects',
            'btn_contact': 'Contact Me',
            'status_completed': 'Completed',
            'status_idea': 'In Progress'
        }
    };

    let currentLang = 'uk'; // Мова за замовчуванням

    if (langToggleBtn) {
        langToggleBtn.addEventListener('click', () => {
            currentLang = currentLang === 'uk' ? 'en' : 'uk';
            const langText = langToggleBtn.querySelector('.lang-text');
            if(langText) langText.textContent = currentLang.toUpperCase();

            // Знаходимо всі елементи з data-i18n
            document.querySelectorAll('[data-i18n]').forEach(el => {
                const key = el.getAttribute('data-i18n');
                if (translations[currentLang][key]) {
                    // Плавно змінюємо текст
                    el.style.opacity = '0';
                    setTimeout(() => {
                        el.textContent = translations[currentLang][key];
                        el.style.opacity = '1';
                    }, 200);
                }
            });
        });
    }

    // --- 10. Project Modal Functionality ---
    const projectCardsModal = document.querySelectorAll('.project-card');
    const modal = document.getElementById('projectModal');
    
    if (modal && projectCardsModal.length > 0) {
        const modalBackdrop = modal.querySelector('.modal-backdrop');
        const modalCloseBtn = modal.querySelector('.modal-close-btn');
        const modalDetails = modal.querySelector('.modal-project-details');

        const openModal = (card) => {
            const title = card.querySelector('.project-header h4').textContent;
            const techHtml = card.querySelector('.project-tech').innerHTML;
            const fullDescElement = card.querySelector('.full-description');
            const description = fullDescElement ? fullDescElement.innerHTML : card.querySelector('.project-description').innerHTML;
            const linksHtml = card.querySelector('.project-links').innerHTML;
            const imageContainerHtml = card.querySelector('.project-image-container').innerHTML;
            
            modalDetails.innerHTML = `
                <div class="modal-image-container">
                    ${imageContainerHtml}
                </div>
                <div class="modal-info">
                    <h3>${title}</h3>
                    <div class="project-tech">
                        ${techHtml}
                    </div>
                    <div class="project-description">
                        ${description}
                    </div>
                    <div class="project-links">
                        ${linksHtml}
                    </div>
                </div>
            `;
            
            // Визначаємо ширину скроллбара, щоб уникнути стрибка контенту при overflow: hidden
            const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
            document.body.style.paddingRight = `${scrollbarWidth}px`;
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        };

        const closeModal = () => {
            modal.classList.remove('active');
            document.body.style.overflow = 'auto';
            document.body.style.paddingRight = '0px';
        };

        projectCardsModal.forEach(card => {
            card.addEventListener('click', (e) => {
                // Ігноруємо кліки по прямих посиланнях (наприклад, кнопка GitHub)
                if (e.target.closest('.project-link')) {
                    return;
                }
                openModal(card);
            });
            // Вказуємо, що картка клікабельна
            card.style.cursor = 'pointer';
        });

        modalBackdrop.addEventListener('click', closeModal);
        modalCloseBtn.addEventListener('click', closeModal);
        
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal.classList.contains('active')) {
                closeModal();
            }
        });
    }
});