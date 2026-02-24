document.addEventListener('DOMContentLoaded', function () {
    console.log("✅ Скрипт diploma_home.js успішно завантажено!");

    // ==========================================
    // 1. СИСТЕМА ТРИВОГ
    // ==========================================
    function updateAlerts() {
        fetch('/diploma/api/active-alerts/')
            .then(response => response.json())
            .then(data => {
                const container = document.querySelector('.card.alert-card .card-body');
                const badge = document.querySelector('.badge-critical');
                const staffContainer = document.querySelector('.staff-list');

                if (data.count > 0) document.title = `🚨 (${data.count}) Тривога! - Глибина 4.0`;
                else document.title = "Головна панель - Глибина 4.0";

                if (badge) {
                    badge.textContent = data.count > 0 ? `${data.count} критичних` : 'Все спокійно';
                    badge.classList.toggle('badge-danger', data.count > 0);
                    badge.classList.toggle('badge-safe', data.count === 0);
                }

                if (staffContainer && data.staff) {
                    let staffHtml = '';
                    data.staff.forEach(emp => {
                        let statusHtml = '';
                        if (emp.status === 'OK') statusHtml = '<span class="staff-status online">Норма</span>';
                        else if (emp.status === 'WARNING') statusHtml = '<span class="staff-status status-warning">Увага</span>';
                        else if (emp.status === 'SOS') statusHtml = '<span class="staff-status status-sos">ТРИВОГА</span>';

                        const avatarHtml = emp.photo_url
                            ? `<img src="${emp.photo_url}" class="staff-avatar-img" alt="avatar">`
                            : `<i class="fas fa-hard-hat"></i>`;

                        staffHtml += `<div class="staff-item"><div class="staff-avatar">${avatarHtml}</div><div class="staff-info"><h4>${emp.full_name}</h4><p>${emp.position}</p>${statusHtml}</div></div>`;
                    });
                    staffContainer.innerHTML = staffHtml;
                }

                if (container) {
                    if (data.count > 0) {
                        let html = '';
                        data.alerts.forEach(alert => {
                            const alertClass = alert.is_critical ? 'critical' : 'warning';
                            const icon = alert.is_critical ? 'fa-skull-crossbones' : 'fa-exclamation-circle';
                            html += `<a href="/diploma/alert/${alert.id}/" class="alert-link-wrapper">
                                <div class="alert-item ${alertClass}">
                                    <div class="alert-icon"><i class="fas ${icon}"></i></div>
                                    <div class="alert-content">
                                        <h4>${alert.reason}</h4><p>${alert.location} - Працівник: ${alert.employee}</p><span class="alert-time">${alert.time}</span>
                                    </div>
                                    <div class="alert-action"><i class="fas fa-chevron-right"></i></div>
                                </div></a>`;
                        });
                        container.innerHTML = html;
                    } else {
                        container.innerHTML = `<div class="text-center py-4 text-muted"><i class="fas fa-check-circle fa-3x mb-3 icon-success"></i><p>Наразі активних інцидентів немає.</p></div>`;
                    }
                }
            })
            .catch(err => console.error("Помилка оновлення тривог:", err));
    }

    updateAlerts();
    setInterval(updateAlerts, 5000);


    // ==========================================
    // 2. ІНТЕРАКТИВНА КАРТА
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
});