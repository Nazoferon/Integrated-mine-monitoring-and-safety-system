# Integrated Mine Monitoring and Safety System

![Project Poster](./poster.png)

## 📖 Опис

**Integrated Mine Monitoring and Safety System** — програмно-апаратний комплекс моніторингу параметрів безпеки шахти.  
Система поєднує IoT-модулі на базі ESP32, серверну обробку телеметрії, кешування, диспетчерський веб-інтерфейс та інтерактивну візуалізацію стану персоналу й інфраструктури в реальному часі.

Проєкт орієнтований на:
- безперервний моніторинг критичних параметрів;
- відмовостійкість (offline-черги на пристроях);
- відкриту модульну архітектуру без vendor lock-in;
- готовність до розгортання як у хмарі, так і на локальному сервері підприємства.

---

## 🏗️ Архітектура системи

### Back-end
- **Django (Python)** — бізнес-логіка, API, веб-рівень
- **Gunicorn** — WSGI-сервер для production
- **PostgreSQL** — основна реляційна БД
- **Redis** — кешування (через `REDIS_URL`, опційно)
- **Management Commands / Cron** — Data Lifecycle Management (очистка/архівація)
- **ReportLab** — генерація офіційних PDF-звітів

### Front-end
- **Django Templates + HTML/CSS**
- **Vanilla JavaScript** (частковий SPA-підхід)
- **Canvas API (2D Context)** — інтерактивна 2D-карта шахти (власна реалізація з плавним масштабуванням та панорамуванням, без сторонніх бібліотек)
- **Chart.js** — аналітичні графіки

### Симуляція та Картографія
- **MineCAD (PyQt6)** — десктопна програма на Python для малювання карти штреків та симуляції руху гірників (навантажувальне тестування).

### IoT-рівень
- **ESP32** — збір телеметрії та передача на сервер
- **Wi-Fi roaming** — безшовне перемикання між AP
- **Offline queue** — локальне буферування даних при втраті зв'язку

---

## ✅ Реалізовані можливості

- Аутентифікація та ролі користувачів
- CRUD для співробітників та обладнання
- Інтерактивна 2D-карта шахти
- Моніторинг телеметрії (метан, температура, тощо)
- Розумна система тривог (автоматичне групування "Аварій інфраструктури", захист від помилкових SOS)
- Логіка розумного завершення зміни (тільки в Ламповій)
- Звіти та аналітика (з автоматичною генерацією PDF-документів)
- Data Lifecycle Management (авто-архівація старих даних у CSV.gz)
- OTA-оновлення прошивок (staged rollout)
- Кешування гарячих API-запитів через Redis (за наявності `REDIS_URL`)
- Інтелектуальний захист від ботів та брутфорсу (Cloudflare Turnstile)
- Корпоративні email-сповіщення (вхід з нового пристрою, привітання, скидання пароля)
- Посилена політика безпеки паролів (перевірка по базі витоків Have I Been Pwned)
- Оптимізація продуктивності (усунення N+1 запитів, стиснення GZip)

---

## 👥 Ролі користувачів

- **Admin** — повні права керування системою
- **Dispatcher** — моніторинг персоналу, карти, тривог
- **Engineer** — управління обладнанням і техобслуговуванням
- **Observer** — режим перегляду

---

## ⚙️ Конфігурація середовища

Проєкт використовує змінні середовища з `.env`.

### Обов'язкові ключі (мінімум)
- `SECRET_KEY`
- `DEBUG`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `ESP32_API_KEY`
- `EMAIL_PASSWORD` — пароль додатка Gmail для надсилання сповіщень та листів

### Опційні
- `REDIS_URL` — якщо задано, вмикається Redis cache backend; якщо не задано — використовується file-based cache fallback.
- `TURNSTILE_SITE_KEY` та `TURNSTILE_SECRET_KEY` — ключі Cloudflare Turnstile для захисту форм (за замовчуванням увімкнений тестовий режим).

---

## 🧪 Локальний запуск (без Docker)

```bash
git clone https://github.com/Nazoferon/Integrated-mine-monitoring-and-safety-system.git
cd Integrated-mine-monitoring-and-safety-system

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# відредагуйте .env

python manage.py migrate
python manage.py runserver
```

Веб-інтерфейс: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 🐳 Docker-розгортання

У проєкті підготовлено Docker deployment pack:
- `Dockerfile`
- `docker-compose.yml`
- `docker/entrypoint.sh`
- `.env.example`
- `.dockerignore`

Повна інструкція: **[`DEPLOYMENT_DOCKER.md`](./DEPLOYMENT_DOCKER.md)**

Коротко:
```bash
cp .env.example .env
# заповнити змінні
docker compose up -d --build
docker compose logs -f web
```

---

## 🔐 Безпека (рекомендації)

- Не комітьте реальний `.env` у репозиторій
- Відкривайте назовні лише `22`, `80`, `443`
- Не відкривайте назовні `5432` (PostgreSQL) і `6379` (Redis)
- Для API пристроїв використовуйте унікальний `ESP32_API_KEY`
- У production використовуйте HTTPS та ротацію секретів

---

## 📊 Діаграма архітектури
```mermaid
graph TB
    subgraph "Шахта (IoT-рівень)"
        ESP[ESP32 модулі]
        AP[Wi-Fi AP / Репітери]
        ESP --> AP
    end
    subgraph "Сервер"
        API[Django + Gunicorn]
        DB[(PostgreSQL)]
        REDIS[(Redis Cache)]
    end
    subgraph "Диспетчер"
        WEB[Web Dashboard]
    end
    AP --> API
    API --> DB
    API --> REDIS
    WEB <--> API
```
**Рис. 1. Архітектура компонентів та логічна структура взаємодії модулів системи моніторингу.**

```mermaid
sequenceDiagram
    participant ESP as ESP32
    participant API as Django API
    participant DB as PostgreSQL
    participant CACHE as Redis
    participant WEB as Web Client

    ESP->>API: POST телеметрія
    API->>CACHE: Оновлення/читання кешу
    API->>DB: Запис телеметрії
    WEB->>API: Запит стану/історії
    API->>CACHE: Швидкі дані дашборду
    API->>DB: Історичні дані
    API-->>WEB: JSON/HTML відповідь

```
**Рис. 2. Потік даних**

---

## 🚀 Подальший розвиток

- Розширення аналітики та прогнозування інцидентів
- Інтеграція з промисловими сертифікованими пристроями (ATEX)
- Розширення модулів диспетчеризації
- Резервування сервісів для підвищення відмовостійкості

---

## 📜 Ліцензія

Проєкт поширюється під ліцензією [MIT](LICENSE).

---

## 👤 Автор

**Nazoferon**  
Проєкт розроблено в межах дослідження системи моніторингу параметрів безпеки шахти.
