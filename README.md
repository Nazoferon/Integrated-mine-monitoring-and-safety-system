# Integrated Mine Monitoring and Safety System

![](./poster.png)

## 📖 Опис
**Integrated Mine Monitoring and Safety System** — дипломний проєкт, який реалізує комплексну систему моніторингу та безпеки шахт. Вона поєднує збір даних від ESP32 модулів, управління співробітниками та обладнанням, інтерактивний конструктор карти шахти й систему сповіщень для підвищення рівня безпеки.

---

## 🎯 MVP (Minimum Viable Product)

### Критично важливі функції (Phase 1)
- [x] Базовий веб-інтерфейс з аутентифікацією та ролями
- [x] Управління співробітниками (CRUD)
- [x] 2D візуалізація карти шахти та репітерів
- [x] ESP32 симулятор у Wokwi та прошивка для реального заліза
- [x] Позиціювання персоналу та моніторинг безпеки
- [x] Адаптивний темний дизайн (Глибина 4.0)

### Важливі функції (Phase 2)
- [x] Управління парком обладнання (коногонки, датчики)
- [x] Моніторинг показників середовища (Метан, Температура)
- [x] Система сповіщень та обробки інцидентів (SOS)
- [x] Генерація звітів з експортом у PDF та CSV
- [x] **Data Lifecycle Management**: Автоматична архівація застарілої телеметрії у GZIP
- [x] **OTA Updates**: Повітряне оновлення прошивок ESP32 через веб-інтерфейс

### Додатково (за наявності часу)
- 3D візуалізація шахти
- Розширена аналітика + ML

---

## 🏗️ Архітектура системи

### Backend
- Django (Python) — основний сервер та REST API
- PostgreSQL — основна реляційна база даних
- Redis — кешування та черги
- Gunicorn — WSGI сервер для Production
- Docker & Docker Compose — контейнеризація для легкого розгортання

### Frontend
- Django Templates + HTML5/CSS3 — серверний рендеринг сторінок
- Vanilla JavaScript — динаміка та взаємодія з API (Fetch)
- Chart.js — побудова аналітичних графіків
- Konva.js — рендеринг 2D карти шахти (Canvas)
- Bootstrap Grid — адаптивна сітка

### ESP32
- WiFi + HTTP POST/GET для зв'язку з сервером
- JSON протокол передачі даних
- **Offline-стійкість**: вбудована черга збереження телеметрії при втраті зв'язку

---

## 👥 Ролі користувачів
- **Admin** — повні права, управління всіма ресурсами
- **Dispatcher** — моніторинг карти, співробітників, тривог
- **Engineer** — управління обладнанням, техобслуговування
- **Observer** — тільки перегляд

---

## 🗄️ Структура БД
- **User / Role / Session** — користувачі та права доступу
- **Employee / ESPModule / Assignment** — співробітники та модулі
- **MineMap / MineZone** — карта шахти
- **EmployeePosition / EnvironmentalData / EmergencySignal** — позиціювання, середовище, аварійні сигнали
- **EquipmentType / EquipmentUnit / MaintenanceLog** — обладнання та його обслуговування
- **SystemLog** — логування дій користувачів

---

## 📱 Веб-форми
- Додавання співробітників
- Призначення ESP модулів
- Додавання обладнання
- Редагування карти шахти

---

## 🔄 Робота ESP32
Модуль зчитує дані (сенсори, WiFi, SOS кнопка), формує JSON пакет і надсилає його на сервер кожні 5 секунд. Сервер відповідає статусом і може надсилати команди.

---

## 📊 Діаграми
### Архітектура
```mermaid
graph TB
    subgraph "Шахта"
        ESP[ESP32 Modules] --> AP[WiFi APs]
    end
    subgraph "VPS Server"
        API[Django Backend / Gunicorn]
        DB[(PostgreSQL)]
        REDIS[(Redis)]
    end
    subgraph "Client"
        WEB[Web Dashboard]
    end
    AP --> API
    API --> DB
    API --> REDIS
    API --> WEB
```

### Потік даних
```mermaid
sequenceDiagram
    ESP->>VPS: Sensor + Position Data
    VPS->>DB: Save data
    VPS->>WEB: Real-time update
    WEB->>VPS: Request history
    VPS->>DB: Query data
    DB->>VPS: Return results
    VPS->>WEB: Send response
```

---

## ✅ План реалізації MVP
- **Тиждень 1-2**: VPS, Docker, базовий Django + React, моделі БД
- **Тиждень 3-4**: CRUD для співробітників та ESP модулів, ролі
- **Тиждень 5-6**: 2D карта, симуляція ESP32, позиціювання
- **Тиждень 7-8**: Система алертів, дашборд, логування
- **Тиждень 9-10**: Тестування, оптимізація, документація

---

## 🛠️ Встановлення
```bash
git clone https://github.com/Nazoferon/Integrated-mine-monitoring-and-safety-system.git
cd Integrated-mine-monitoring-and-safety-system
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
Веб-інтерфейс: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 📌 Подальший розвиток
- Машинне навчання для прогнозування аварій
- Інтеграція з реальними сенсорами
- Мобільний застосунок
- Розширені аналітичні інструменти

---

## 📜 Ліцензія
Проєкт поширюється під ліцензією [MIT](LICENSE).

---

## 👤 Автор
**Nazoferon** — дипломний проєкт із розробки системи моніторингу шахт.
