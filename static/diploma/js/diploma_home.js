document.addEventListener('DOMContentLoaded', function () {
    console.log("✅ Скрипт diploma_home.js успішно завантажено!");

    // ==========================================
    // 1. ІНТЕРАКТИВНА КАРТА
    // ==========================================
    const rawData = document.getElementById('mine-map-data');
    let mapData = { tunnels: [], yards: [], devices: [] };

    if (rawData) {
        try {
            mapData = JSON.parse(rawData.textContent);
        } catch (e) {
            console.error("Помилка розпізнавання даних карти:", e);
        }
    }

    const canvas = document.getElementById('homeMapCanvas');

    if (canvas && (mapData.tunnels || mapData.yards)) {
        const ctx = canvas.getContext('2d');

        function drawPreviewMap() {
            canvas.width = canvas.offsetWidth;
            canvas.height = canvas.offsetHeight;
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
            const points = [];
            if (mapData.tunnels) mapData.tunnels.forEach(t => { points.push({ x: t.x1 * 10, y: t.y1 * 10 }, { x: t.x2 * 10, y: t.y2 * 10 }); });
            if (mapData.yards) mapData.yards.forEach(y => { points.push({ x: (y.x - y.w / 2) * 10, y: (y.y - y.h / 2) * 10 }, { x: (y.x + y.w / 2) * 10, y: (y.y + y.h / 2) * 10 }); });

            if (points.length === 0) return;

            points.forEach(p => {
                if (p.x < minX) minX = p.x;
                if (p.x > maxX) maxX = p.x;
                if (p.y < minY) minY = p.y;
                if (p.y > maxY) maxY = p.y;
            });

            const mapWidth = maxX - minX;
            const mapHeight = maxY - minY;
            const padding = Math.max(mapWidth, mapHeight) * 0.2;
            const scaleX = (canvas.width - padding) / mapWidth;
            const scaleY = (canvas.height - padding) / mapHeight;
            const scale = Math.min(scaleX, scaleY);

            ctx.save();
            ctx.translate(canvas.width / 2, canvas.height / 2);
            ctx.scale(scale, scale);
            ctx.translate(-(minX + maxX) / 2, -(minY + maxY) / 2);

            if (mapData.yards) {
                ctx.fillStyle = '#1a1a1a'; ctx.strokeStyle = '#333'; ctx.lineWidth = 2;
                mapData.yards.forEach(y => {
                    const x = y.x * 10, yPos = y.y * 10, w = y.w * 10, h = y.h * 10;
                    ctx.fillRect(x - w / 2, yPos - h / 2, w, h); ctx.strokeRect(x - w / 2, yPos - h / 2, w, h);
                });
            }

            if (mapData.tunnels) {
                ctx.lineCap = 'round'; ctx.lineJoin = 'round';
                mapData.tunnels.forEach(t => {
                    const x1 = t.x1 * 10, y1 = t.y1 * 10, x2 = t.x2 * 10, y2 = t.y2 * 10;
                    ctx.lineWidth = 12; ctx.strokeStyle = '#222';
                    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
                    ctx.lineWidth = 4; ctx.strokeStyle = '#5a4d41';
                    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
                    if (t.devices) {
                        t.devices.forEach(d => {
                            ctx.beginPath(); ctx.arc(d.x * 10, d.y * 10, 4, 0, Math.PI * 2);
                            ctx.fillStyle = '#00ffff'; ctx.shadowBlur = 5; ctx.shadowColor = '#00ffff'; ctx.fill(); ctx.shadowBlur = 0;
                        });
                    }
                });
            }
            ctx.restore();
        }

        drawPreviewMap();
        window.addEventListener('resize', drawPreviewMap);
    }

    // ==========================================
    // 2. АВТОМАТИЧНЕ ОНОВЛЕННЯ ДАШБОРДУ
    // ==========================================
    function updateDashboardStats() {
        fetch('/diploma/api/dashboard-stats/')
            .then(res => {
                if (!res.ok) throw new Error('Помилка мережі');
                return res.json();
            })
            .then(data => {
                // 1. Оновлення списку "Персонал у Шахті"
                const staffList = document.querySelector('.staff-list');
                if (staffList && data.recent_staff) {
                    let html = '';
                    if (data.recent_staff.length === 0) {
                        html = '<p class="text-muted text-center py-3">Наразі в шахті немає працівників.</p>';
                    } else {
                        data.recent_staff.forEach(emp => {
                            let statusHtml = '';
                            if (emp.status === 'OK') statusHtml = '<span class="staff-status online">Норма</span>';
                            else if (emp.status === 'WARNING') statusHtml = '<span class="staff-status status-warning">Увага</span>';
                            else if (emp.status === 'SOS') statusHtml = '<span class="staff-status status-sos">ТРИВОГА</span>';
                            else statusHtml = '<span class="staff-status offline">Офлайн</span>';
                            
                            let avatarHtml = emp.photo_url 
                                ? `<img src="${emp.photo_url}" alt="Avatar" class="staff-avatar-img">`
                                : `<i class="fas fa-hard-hat"></i>`;
                            
                            let locationHtml = emp.location
                            ? ` | <span class="text-info staff-location-text"><i class="fas fa-map-marker-alt"></i> ${emp.location}</span>`
                            : '';
                                html += `
                            <a href="/diploma/mine_map/?focus_ap=${emp.location || ''}" class="staff-item">
                                <div class="staff-avatar">${avatarHtml}</div>
                                <div class="staff-info">
                                    <h4>${emp.first_name} ${emp.last_name}</h4>
                                    <p>${emp.position}${locationHtml}</p>
                                    ${statusHtml}
                                </div>
                            </div>`;
                        });
                    }
                    staffList.innerHTML = html;
                }

                // 2. Оновлення лічильників онлайн
                const onlineIndicators = document.querySelectorAll('.online-indicator');
                onlineIndicators.forEach(el => el.textContent = data.online_count + ' онлайн');
                
                const topOnlineCount = document.querySelector('.status-card.online h3');
                if (topOnlineCount) topOnlineCount.textContent = data.online_count;

                // 3. Оновлення Температури, Вологості та кількості Тривог
                const tempEl = document.querySelector('.status-card .fa-thermometer-half')?.closest('.status-card')?.querySelector('h3');
                if (tempEl && data.avg_temp !== undefined) tempEl.textContent = data.avg_temp.toFixed(1) + '°C';
                
                const humEl = document.querySelector('.status-card .fa-tint')?.closest('.status-card')?.querySelector('h3');
                if (humEl && data.avg_hum !== undefined) humEl.textContent = data.avg_hum.toFixed(0) + '%';
                
                const warnEl = document.querySelector('.status-card .fa-exclamation-triangle')?.closest('.status-card')?.querySelector('h3');
                if (warnEl && data.warning_count !== undefined) {
                    warnEl.textContent = data.warning_count;
                    const warnCard = warnEl.closest('.status-card');
                    if (warnCard) warnCard.className = `status-card ${data.warning_count > 0 ? 'warning' : 'normal'}`;
                }

                // 4. Оновлення списку інцидентів
                const alertsContainer = document.getElementById('active-alerts-container');
                if (alertsContainer && data.alerts_html !== undefined) alertsContainer.innerHTML = data.alerts_html;

                const alertBadge = document.querySelector('.alert-card .card-header .badge');
                if (alertBadge && data.warning_count !== undefined) {
                    if (data.warning_count > 0) {
                        alertBadge.className = 'badge badge-critical';
                        alertBadge.textContent = data.warning_count + ' критичних';
                    } else {
                        alertBadge.className = 'badge badge-safe';
                        alertBadge.textContent = 'Все спокійно';
                    }
                }

                // 5. Оновлення графіка "Показники Середовища"
                const envCards = document.querySelectorAll('.environment-card .metric-item');
                if (envCards.length >= 3) {
                    envCards[0].querySelector('.metric-value').textContent = data.avg_temp.toFixed(1) + '°C';
                    envCards[1].querySelector('.metric-value').textContent = data.avg_hum.toFixed(0) + '%';
                    envCards[2].querySelector('.metric-value').textContent = data.gas_level;
                    
                    const gasTrend = envCards[2].querySelector('.metric-trend');
                    if (gasTrend) {
                        if (data.gas_level > 250) {
                            gasTrend.className = 'metric-trend up';
                            gasTrend.innerHTML = '<i class="fas fa-arrow-up icon-danger"></i>';
                        } else {
                            gasTrend.className = 'metric-trend stable';
                            gasTrend.innerHTML = '<i class="fas fa-minus"></i>';
                        }
                    }
                }
            })
            .catch(err => console.error("Помилка оновлення дашборду:", err));
    }

    // Запускаємо оновлення дашборду кожні 5 секунд
    setInterval(updateDashboardStats, 5000);
});