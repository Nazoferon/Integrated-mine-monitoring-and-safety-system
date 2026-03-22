// mine_map.js — 2D карта шахти (Canvas API)
// Дані mapData передаються через window.MINE_MAP_DATA з HTML-шаблону

(function () {
    // --- ЗМІННІ ---
    const canvas = document.getElementById('map-canvas');
    const ctx = canvas.getContext('2d');
    const popup = document.getElementById('map-popup');
    const mapArea = document.getElementById('map-area');

    // Дані з Django-шаблону (передаються через json_script фільтр)
    const rawData = document.getElementById('mine-map-data');
    let mapData;
    try {
        mapData = rawData ? JSON.parse(rawData.textContent) : { tunnels: [], yards: [], devices: [] };
    } catch(e) {
        mapData = { tunnels: [], yards: [], devices: [] };
    }
    let scale = 1.0;
    let offsetX = 0, offsetY = 0;
    let isDragging = false, startX, startY;

    let hoveredObject = null;
    let selectedObject = null;

    // --- ІНІЦІАЛІЗАЦІЯ ---
    function initMap() {
        if (window.dashboardApp) window.dashboardApp.showLoader('Побудова карти шахти...');
        
        if (!canvas || !ctx || !mapArea) {
            if (window.dashboardApp) window.dashboardApp.hideLoader();
            return;
        }

        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);

        canvas.addEventListener('mousedown', e => {
            if (hoveredObject) {
                selectObject(hoveredObject.type, hoveredObject.data);
                isDragging = false;
            } else {
                selectObject(null, null);
                isDragging = true;
                startX = e.clientX - offsetX;
                startY = e.clientY - offsetY;
                canvas.style.cursor = 'grabbing';
            }
            draw();
        });

        canvas.addEventListener('mousemove', e => {
            const rect = canvas.getBoundingClientRect();
            const mx = e.clientX - rect.left;
            const my = e.clientY - rect.top;

            if (isDragging) {
                offsetX = e.clientX - startX;
                offsetY = e.clientY - startY;
                updatePopupPosition();
                draw();
            } else {
                checkHover(mx, my);
                draw();
            }
        });

        canvas.addEventListener('mouseup', () => {
            isDragging = false;
            canvas.style.cursor = 'grab';
        });

        // Зум до курсора
        canvas.addEventListener('wheel', e => {
            e.preventDefault();
            const zoomSpeed = 0.1;
            const delta = e.deltaY < 0 ? 1 : -1;
            const rect = canvas.getBoundingClientRect();
            const mx = e.clientX - rect.left;
            const my = e.clientY - rect.top;
            zoomAtPoint(mx, my, delta * zoomSpeed);
        }, { passive: false });

        buildHierarchyTree();

        // Кнопка згортання панелі
        const toggleBtn = document.querySelector('.panel-toggle');
        if (toggleBtn) toggleBtn.addEventListener('click', toggleSidebar);

        // Кнопка скидання виду
        const resetBtn = document.querySelector('[data-action="reset-view"]');
        if (resetBtn) resetBtn.addEventListener('click', () => window.resetView());

        // Автоцентрування з невеликою затримкою, щоб CSS та Flexbox 
        // встигли сформувати правильні розміри canvas.width перед прорахунком
        setTimeout(() => {
            window.resetView();
            if (window.dashboardApp) window.dashboardApp.hideLoader();
        }, 150); // Трохи збільшена затримка для надійного рендеру
    }

    function resizeCanvas() {
        canvas.width = mapArea.clientWidth;
        canvas.height = mapArea.clientHeight;
        draw();
    }

    function zoomAtPoint(x, y, amount) {
        const wx = (x - offsetX) / scale;
        const wy = (y - offsetY) / scale;
        let newScale = scale * (1 + amount);
        newScale = Math.max(0.1, Math.min(10.0, newScale));
        offsetX = x - wx * newScale;
        offsetY = y - wy * newScale;
        scale = newScale;
        updatePopupPosition();
        draw();
    }

    // --- МАЛЮВАННЯ ---
    function draw() {
        ctx.fillStyle = '#0f0f0f';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        drawGrid();

        ctx.save();
        ctx.translate(offsetX, offsetY);
        ctx.scale(scale, scale);

        // 1. РУДДВОРИ
        if (mapData.yards) {
            mapData.yards.forEach(y => {
                const x = y.x * 10, yPos = y.y * 10, w = y.w * 10, h = y.h * 10;
                ctx.fillStyle = '#222';
                ctx.fillRect(x - w / 2, yPos - h / 2, w, h);
                ctx.strokeStyle = '#444';
                ctx.lineWidth = 2;
                ctx.strokeRect(x - w / 2, yPos - h / 2, w, h);

                if (scale > 0.3) {
                    ctx.fillStyle = '#666';
                    ctx.font = '14px Arial';
                    ctx.textAlign = 'center';
                    ctx.fillText(y.name || 'Руддвір', x, yPos);
                }
            });
        }

        // 2. ШТРЕКИ
        if (mapData.tunnels) {
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            mapData.tunnels.forEach(t => {
                const isHovered = (hoveredObject && hoveredObject.data === t);
                const isSelected = (selectedObject && selectedObject.data === t);
                const x1 = t.x1 * 10, y1 = t.y1 * 10, x2 = t.x2 * 10, y2 = t.y2 * 10;

                // Підсвітка
                if (isSelected || isHovered) {
                    ctx.lineWidth = 16;
                    ctx.strokeStyle = isSelected ? '#4dabf7' : '#333';
                    ctx.beginPath();
                    ctx.moveTo(x1, y1);
                    ctx.lineTo(x2, y2);
                    ctx.stroke();
                } else {
                    ctx.lineWidth = 12;
                    ctx.strokeStyle = '#222';
                    ctx.beginPath();
                    ctx.moveTo(x1, y1);
                    ctx.lineTo(x2, y2);
                    ctx.stroke();
                }

                // Внутрішня частина
                ctx.lineWidth = 6;
                ctx.strokeStyle = '#5a4d41';
                ctx.stroke();

                // Назва
                if (scale > 0.4 || isSelected) {
                    ctx.fillStyle = isSelected ? '#4dabf7' : '#888';
                    ctx.font = '10px Arial';
                    ctx.textAlign = 'center';
                    ctx.fillText(t.name, (x1 + x2) / 2, (y1 + y2) / 2 - 10);
                }

                // Пристрої штреку
                if (t.devices) t.devices.forEach(d => drawDevice(d.x * 10, d.y * 10, d));
            });
        }

        // 3. ОКРЕМІ ПРИСТРОЇ
        if (mapData.devices) mapData.devices.forEach(d => drawDevice(d.x * 10, d.y * 10, d));

        ctx.restore();
    }

    function drawDevice(x, y, d) {
        const isHovered = (hoveredObject && hoveredObject.data === d);
        const isSelected = (selectedObject && selectedObject.data === d);

        if (isSelected || isHovered) {
            ctx.beginPath();
            ctx.arc(x, y, 14, 0, Math.PI * 2);
            ctx.fillStyle = isSelected ? 'rgba(77, 171, 247, 0.4)' : 'rgba(255,255,255,0.2)';
            ctx.fill();
            if (isSelected) {
                ctx.strokeStyle = '#4dabf7';
                ctx.lineWidth = 2;
                ctx.stroke();
            }
        }

        ctx.beginPath();
        ctx.arc(x, y, 6, 0, Math.PI * 2);
        ctx.fillStyle = '#00ffff';
        ctx.fill();
        ctx.strokeStyle = 'black';
        ctx.lineWidth = 1;
        ctx.stroke();

        if (scale > 0.6 || isSelected) {
            ctx.fillStyle = isSelected ? '#4dabf7' : '#fff';
            ctx.font = 'bold 11px monospace';
            ctx.textAlign = 'center';
            ctx.fillText(d.id, x, y - 12);
        }
    }

    function drawGrid() {
        const step = 50 * scale;
        if (step < 10) return;
        ctx.beginPath();
        ctx.strokeStyle = '#1a1a1a';
        ctx.lineWidth = 1;
        const sx = (offsetX % step) - step, sy = (offsetY % step) - step;
        for (let x = sx; x < canvas.width; x += step) { ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); }
        for (let y = sy; y < canvas.height; y += step) { ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); }
        ctx.stroke();
    }

    // --- ХОВЕР ---
    function checkHover(mx, my) {
        const wx = (mx - offsetX) / scale;
        const wy = (my - offsetY) / scale;
        hoveredObject = null;
        canvas.style.cursor = 'grab';

        const checkDevs = (list) => {
            list.forEach(d => {
                const dist = Math.hypot(d.x * 10 - wx, d.y * 10 - wy);
                if (dist < 15 / scale + 5) {
                    hoveredObject = { type: 'device', data: d };
                    canvas.style.cursor = 'pointer';
                }
            });
        };
        if (mapData.tunnels) mapData.tunnels.forEach(t => { if (t.devices) checkDevs(t.devices); });
        if (mapData.devices) checkDevs(mapData.devices);

        if (hoveredObject) return;

        if (mapData.tunnels) {
            mapData.tunnels.forEach(t => {
                const dist = distToSegment(wx, wy, t.x1 * 10, t.y1 * 10, t.x2 * 10, t.y2 * 10);
                if (dist < 10) {
                    hoveredObject = { type: 'tunnel', data: t };
                    canvas.style.cursor = 'pointer';
                }
            });
        }
    }

    function distToSegment(px, py, x1, y1, x2, y2) {
        const l2 = (x1 - x2) ** 2 + (y1 - y2) ** 2;
        if (l2 === 0) return Math.hypot(px - x1, py - y1);
        let t = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / l2;
        t = Math.max(0, Math.min(1, t));
        return Math.hypot(px - (x1 + t * (x2 - x1)), py - (y1 + t * (y2 - y1)));
    }

    // --- ВИБІР + POPUP ---
    function selectObject(type, data) {
        selectedObject = (type && data) ? { type, data } : null;

        document.querySelectorAll('.list-tunnel-item, .list-device-item').forEach(el => el.classList.remove('selected'));

        if (selectedObject) {
            if (type === 'tunnel') {
                const idx = mapData.tunnels.indexOf(data);
                if (idx >= 0) document.getElementById(`tree-tunnel-${idx}`).classList.add('selected');
            } else if (type === 'device') {
                mapData.tunnels.forEach((t, tIdx) => {
                    if (t.devices) {
                        const dIdx = t.devices.indexOf(data);
                        if (dIdx >= 0) {
                            document.getElementById(`tree-tunnel-${tIdx}`).classList.add('expanded');
                            document.getElementById(`tree-dev-${tIdx}-${dIdx}`).classList.add('selected');
                        }
                    }
                });
            }
            showPopup();
        } else {
            popup.style.display = 'none';
        }
        draw();
    }

    function showPopup() {
        if (!selectedObject) return;

        let html = '';
        if (selectedObject.type === 'device') {
            const d = selectedObject.data;
            html = `<div class="popup-title"><i class="fas fa-wifi"></i> ${d.id}</div>
                    <div class="popup-row"><span class="popup-label">Тип:</span> WiFi Repeater</div>
                    <div class="popup-row"><span class="popup-label">Статус:</span> <span class="status-online">Online</span></div>
                    <div class="popup-row"><span class="popup-label">Коорд:</span> ${d.x}, ${d.y}</div>`;
        } else if (selectedObject.type === 'tunnel') {
            const t = selectedObject.data;
            const len = Math.hypot(t.x2 - t.x1, t.y2 - t.y1).toFixed(1);
            html = `<div class="popup-title"><i class="fas fa-road"></i> ${t.name}</div>
                    <div class="popup-row"><span class="popup-label">Довжина:</span> ${len} м</div>
                    <div class="popup-row"><span class="popup-label">Пристроїв:</span> ${t.devices ? t.devices.length : 0}</div>`;
        }
        popup.innerHTML = html;
        popup.style.display = 'block';
        updatePopupPosition();
    }

    function updatePopupPosition() {
        if (!selectedObject) return;

        let wx, wy;
        if (selectedObject.type === 'device') {
            wx = selectedObject.data.x * 10;
            wy = selectedObject.data.y * 10;
        } else {
            const t = selectedObject.data;
            wx = (t.x1 + t.x2) / 2 * 10;
            wy = (t.y1 + t.y2) / 2 * 10;
        }

        popup.style.left = (wx * scale + offsetX) + 'px';
        popup.style.top = (wy * scale + offsetY) + 'px';
    }

    // --- UI ДЕРЕВО ---
    function buildHierarchyTree() {
        const container = document.getElementById('objects-tree-container');
        container.innerHTML = '';

        let tCount = 0, dCount = 0;

        if (mapData.yards && mapData.yards.length > 0) {
            container.innerHTML += `<div class="obj-group-title">Інфраструктура</div>`;
            mapData.yards.forEach(y => {
                container.innerHTML += `<div class="yard-item">${y.name || 'Руддвір'}</div>`;
            });
        }

        if (mapData.tunnels) {
            container.innerHTML += `<div class="obj-group-title">Штреки та Мережа</div>`;
            mapData.tunnels.forEach((t, idx) => {
                tCount++;
                const hasDevs = t.devices && t.devices.length > 0;

                let html = `
                    <div class="list-tunnel-item" id="tree-tunnel-${idx}">
                        <div class="tunnel-header" data-action="tunnel" data-idx="${idx}">
                            <span><i class="fas fa-road icon-tunnel"></i> ${t.name}</span>
                            ${hasDevs ? `<i class="fas fa-chevron-right icon-chevron"></i>` : ''}
                        </div>
                `;

                if (hasDevs) {
                    html += `<div class="tunnel-devices-list">`;
                    t.devices.forEach((d, dIdx) => {
                        dCount++;
                        html += `
                            <div class="list-device-item" id="tree-dev-${idx}-${dIdx}" data-action="device" data-tidx="${idx}" data-didx="${dIdx}">
                                <span><i class="fas fa-wifi icon-wifi"></i> ${d.id}</span>
                                <span class="status-dot"></span>
                            </div>
                        `;
                    });
                    html += `</div>`;
                }
                html += `</div>`;
                container.innerHTML += html;
            });
        }

        document.getElementById('stat-tunnels').innerText = tCount;
        document.getElementById('stat-devices').innerText = dCount;

        // Делегування подій замість inline onclick
        container.addEventListener('click', e => {
            const deviceEl = e.target.closest('[data-action="device"]');
            if (deviceEl) {
                e.stopPropagation();
                const tIdx = parseInt(deviceEl.dataset.tidx);
                const dIdx = parseInt(deviceEl.dataset.didx);
                const d = mapData.tunnels[tIdx].devices[dIdx];
                selectObject('device', d);
                focusOnPoint(d.x * 10, d.y * 10);
                return;
            }
            const tunnelEl = e.target.closest('[data-action="tunnel"]');
            if (tunnelEl) {
                const idx = parseInt(tunnelEl.dataset.idx);
                const t = mapData.tunnels[idx];
                document.getElementById(`tree-tunnel-${idx}`).classList.toggle('expanded');
                selectObject('tunnel', t);
                focusOnPoint((t.x1 + t.x2) / 2 * 10, (t.y1 + t.y2) / 2 * 10);
            }
        });
    }

    function focusOnPoint(x, y) {
        // Враховуємо ширину лівої панелі (300px), щоб візуально центрувати у видимій області екрану
        const sidebar = document.getElementById('sidebar-panel');
        let sidebarOffset = 0;
        if (sidebar && !sidebar.classList.contains('collapsed')) {
            sidebarOffset = 300;
        }

        offsetX = (canvas.width + sidebarOffset) / 2 - x * scale;
        offsetY = canvas.height / 2 - y * scale;
        updatePopupPosition();
        draw();
    }

    window.resetView = function () {
        let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
        let hasData = false;

        if (mapData.yards && mapData.yards.length > 0) {
            mapData.yards.forEach(y => {
                const hw = (y.w || 0) / 2;
                const hh = (y.h || 0) / 2;
                minX = Math.min(minX, y.x - hw);
                maxX = Math.max(maxX, y.x + hw);
                minY = Math.min(minY, y.y - hh);
                maxY = Math.max(maxY, y.y + hh);
                hasData = true;
            });
        }

        if (mapData.tunnels && mapData.tunnels.length > 0) {
            mapData.tunnels.forEach(t => {
                minX = Math.min(minX, t.x1, t.x2);
                maxX = Math.max(maxX, t.x1, t.x2);
                minY = Math.min(minY, t.y1, t.y2);
                maxY = Math.max(maxY, t.y1, t.y2);
                hasData = true;
            });
        }
        
        if (mapData.devices && mapData.devices.length > 0) {
            mapData.devices.forEach(d => {
                minX = Math.min(minX, d.x);
                maxX = Math.max(maxX, d.x);
                minY = Math.min(minY, d.y);
                maxY = Math.max(maxY, d.y);
                hasData = true;
            });
        }

        if (hasData) {
            const centerX = (minX + maxX) / 2;
            const centerY = (minY + maxY) / 2;
            const rangeX = maxX - minX;
            const rangeY = maxY - minY;
            
            // Враховуємо ширину бокової панелі для розрахунку масштабу
            const sidebar = document.getElementById('sidebar-panel');
            const sidebarOffset = (sidebar && !sidebar.classList.contains('collapsed')) ? 300 : 0;
            const visibleWidth = canvas.width - sidebarOffset;
            
            const scaleX = visibleWidth / (rangeX * 10 + 200);
            const scaleY = canvas.height / (rangeY * 10 + 200);
            scale = (rangeX === 0 && rangeY === 0) ? 1.0 : Math.min(scaleX, scaleY, 2.0);
            
            focusOnPoint(centerX * 10, centerY * 10);
        } else {
            scale = 1.0;
            const sidebar = document.getElementById('sidebar-panel');
            const sidebarOffset = (sidebar && !sidebar.classList.contains('collapsed')) ? 300 : 0;
            offsetX = (canvas.width + sidebarOffset) / 2;
            offsetY = canvas.height / 2;
            updatePopupPosition();
            draw();
        }
    };

    // Sidebar toggle — підключається через addEventListener в initMap
    function toggleSidebar() {
        const p = document.getElementById('sidebar-panel');
        const i = document.getElementById('toggle-icon');
        p.classList.toggle('collapsed');
        i.className = p.classList.contains('collapsed') ? 'fas fa-chevron-right' : 'fas fa-chevron-left';
    }

    // --- СТАРТ ---
    initMap();
})();