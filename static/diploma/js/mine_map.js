// mine_map.js — 2D карта шахти (Canvas API)
// Дані mapData передаються через window.MINE_MAP_DATA з HTML-шаблону

(function () {
    // --- ЗМІННІ ---
    const canvas = document.getElementById('map-canvas');
    const ctx = canvas.getContext('2d');
    const popup = document.getElementById('map-popup');
    const mapArea = document.getElementById('map-area');

    // При CSS zoom/масштабуванні (body.zoom-*) DOM координати можуть не співпасти з canvas.width/height.
    // Тому мапимо clientX/clientY у координати canvas через співвідношення rect -> canvas.
    function getCanvasPointFromClient(clientX, clientY) {
        const rect = canvas.getBoundingClientRect();
        const scaleX = rect.width ? (canvas.width / rect.width) : 1;
        const scaleY = rect.height ? (canvas.height / rect.height) : 1;
        return {
            x: (clientX - rect.left) * scaleX,
            y: (clientY - rect.top) * scaleY,
        };
    }

    // Дані з Django-шаблону (передаються через json_script фільтр)
    const rawData = document.getElementById('mine-map-data');
    let mapData;
    try {
        mapData = rawData ? JSON.parse(rawData.textContent) : { tunnels: [], yards: [], devices: [] };
    } catch(e) {
        mapData = { tunnels: [], yards: [], devices: [] };
    }

    // --- НОВЕ: Масив працівників у шахті ---
    let activeMiners = [];
    let dangerTunnels = [];
    let clickableMiners = [];

    // Константа масштабу, після якого кластери розпадаються
    const ZOOM_THRESHOLD = 1.5;

    let scale = 1.0;
    let offsetX = 0, offsetY = 0;
    let isDragging = false, startX, startY;

    let hoveredObject = null;
    let selectedObject = null;

    // --- НОВЕ: Плавна кінематична анімація камери (FlyTo) ---
    let flightAnimationId = null;
    
    function flyTo(targetMapX, targetMapY, targetScale = scale, duration = 600) {
        if (flightAnimationId) cancelAnimationFrame(flightAnimationId);
        
        const startScale = scale;
        const startOffsetX = offsetX;
        const startOffsetY = offsetY;
        
        const sidebar = document.getElementById('sidebar-panel');
        const sidebarOffset = (sidebar && !sidebar.classList.contains('collapsed')) ? 300 : 0;
        
        // Рахуємо цільові відступи, щоб центрувати точку targetMapX/Y на екрані
        const targetOffsetX = (canvas.width + sidebarOffset) / 2 - targetMapX * targetScale;
        const targetOffsetY = canvas.height / 2 - targetMapY * targetScale;
        
        const startTime = performance.now();
        
        function animateFrame(now) {
            if (isDragging) return; // Відміна польоту, якщо користувач почав тягнути карту руками
            
            let progress = (now - startTime) / duration;
            if (progress >= 1) progress = 1;
            
            // Функція плавності EaseInOutCubic
            const ease = progress < 0.5 ? 4 * progress * progress * progress : 1 - Math.pow(-2 * progress + 2, 3) / 2;
            
            scale = startScale + (targetScale - startScale) * ease;
            offsetX = startOffsetX + (targetOffsetX - startOffsetX) * ease;
            offsetY = startOffsetY + (targetOffsetY - startOffsetY) * ease;
            
            updatePopupPosition();
            draw();
            
            if (progress < 1) flightAnimationId = requestAnimationFrame(animateFrame);
        }
        flightAnimationId = requestAnimationFrame(animateFrame);
    }

    // --- НОВЕ: Отримання даних з сервера в реальному часі ---
    function fetchActiveMiners() {
        const mapAreaEl = document.getElementById('map-area');
        if (!mapAreaEl || !mapAreaEl.dataset.apiUrl) return;

        const apiUrl = mapAreaEl.dataset.apiUrl;

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 4000);

        fetch(apiUrl, { signal: controller.signal })
            .then(res => {
                clearTimeout(timeoutId);
                return res.json();
            })
            .then(data => {
                if (data.danger_tunnels) {
                    dangerTunnels = data.danger_tunnels;
                } else {
                    dangerTunnels = [];
                }
                if (data.miners) {
                    activeMiners = data.miners; // Оновлюємо глобальний масив

                    // СУПЕР ФІШКА: Якщо у диспетчера зараз відкрито віконце конкретного працівника,
                    // ми оновлюємо дані прямо у відкритому віконці (щоб він бачив падіння заряду онлайн!)
                    if (selectedObject && selectedObject.type === 'miner') {
                        const updatedMiner = activeMiners.find(m => m.id === selectedObject.data.id);
                        if (updatedMiner) {
                            selectedObject.data = updatedMiner;
                            showPopup(); // Перемальовуємо віконце новими даними
                        } else {
                            // Якщо працівника більше немає в шахті - знімаємо виділення
                            selectObject(null, null); 
                        }
                    }

                    draw(); // Перемальовуємо карту з новими координатами/статусами
                    
                    // --- НОВЕ: Запуск анімації мигання, якщо є тривога ---
                    let needsAnimation = activeMiners.some(m => m.status === 'SOS' || m.status === 'WARNING') || dangerTunnels.length > 0;
                    if (needsAnimation && !isAnimating) {
                        animateAlerts();
                    }
                }
            })
                .catch(err => console.error("Помилка завантаження телеметрії:", err))
                .finally(() => setTimeout(fetchActiveMiners, 3000));
    }

    let isAnimating = false;
    function animateAlerts() {
        let needsAnimation = activeMiners.some(m => m.status === 'SOS' || m.status === 'WARNING') || dangerTunnels.length > 0;
        if (needsAnimation) {
            isAnimating = true;
            draw();
            requestAnimationFrame(animateAlerts);
        } else {
            isAnimating = false;
            draw(); // Очищаємо залишки червоної пульсації
        }
    }

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
                if (hoveredObject.type === 'cluster') {
                    // СПАЙДЕРІФАЙ: При кліку на кластер — ховаємо вікно і плавно зумуємо
                    selectObject(null, null); 
                    // Налітаємо камерою, робимо зум трохи більшим за поріг розпаду
                    flyTo(hoveredObject.data.map_x, hoveredObject.data.map_y, ZOOM_THRESHOLD + 0.4);
                } else {
                    selectObject(hoveredObject.type, hoveredObject.data);
                }
                isDragging = false;
            } else {
                selectObject(null, null);
                isDragging = true;
                const p = getCanvasPointFromClient(e.clientX, e.clientY);
                startX = p.x - offsetX;
                startY = p.y - offsetY;
                canvas.style.cursor = 'grabbing';
            }
            draw();
        });

        canvas.addEventListener('mousemove', e => {
            const p = getCanvasPointFromClient(e.clientX, e.clientY);
            const mx = p.x;
            const my = p.y;

            if (isDragging) {
                offsetX = mx - startX;
                offsetY = my - startY;
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

        // --- ДОДАНО: Підтримка сенсорних екранів (Drag & Pinch-to-Zoom) ---
        let initialPinchDistance = null;
        let initialScale = 1;

        canvas.addEventListener('touchstart', e => {
            e.preventDefault(); // Запобігаємо скролу сторінки
            
            if (e.touches.length === 1) {
                const touch = e.touches[0];
                const p = getCanvasPointFromClient(touch.clientX, touch.clientY);
                const mx = p.x;
                const my = p.y;

                checkHover(mx, my); // Перевіряємо, чи не тапнули на об'єкт

                if (hoveredObject) {
                    if (hoveredObject.type === 'cluster') {
                        selectObject(null, null);
                        flyTo(hoveredObject.data.map_x, hoveredObject.data.map_y, ZOOM_THRESHOLD + 0.4);
                    } else {
                        selectObject(hoveredObject.type, hoveredObject.data);
                    }
                    isDragging = false;
                } else {
                    selectObject(null, null);
                    isDragging = true;
                    startX = mx - offsetX;
                    startY = my - offsetY;
                }
                draw();
            } else if (e.touches.length === 2) {
                isDragging = false;
                const t1 = e.touches[0];
                const t2 = e.touches[1];
                initialPinchDistance = Math.hypot(t1.clientX - t2.clientX, t1.clientY - t2.clientY);
                initialScale = scale;
            }
        }, { passive: false });

        canvas.addEventListener('touchmove', e => {
            e.preventDefault();
            
            if (e.touches.length === 1 && isDragging) {
                const touch = e.touches[0];
                const p = getCanvasPointFromClient(touch.clientX, touch.clientY);
                const mx = p.x;
                const my = p.y;
                offsetX = mx - startX;
                offsetY = my - startY;
                updatePopupPosition();
                draw();
            } else if (e.touches.length === 2 && initialPinchDistance) {
                const t1 = e.touches[0];
                const t2 = e.touches[1];
                const currentDistance = Math.hypot(t1.clientX - t2.clientX, t1.clientY - t2.clientY);
                const zoomFactor = currentDistance / initialPinchDistance;

                const centerClientX = (t1.clientX + t2.clientX) / 2;
                const centerClientY = (t1.clientY + t2.clientY) / 2;
                const center = getCanvasPointFromClient(centerClientX, centerClientY);
                const cx = center.x;
                const cy = center.y;
                
                const newScale = Math.max(0.1, Math.min(10.0, initialScale * zoomFactor));
                const wx = (cx - offsetX) / scale;
                const wy = (cy - offsetY) / scale;
                
                scale = newScale;
                offsetX = cx - wx * scale;
                offsetY = cy - wy * scale;
                
                updatePopupPosition();
                draw();
            }
        }, { passive: false });

        canvas.addEventListener('touchend', e => {
            if (e.touches.length < 2) initialPinchDistance = null;
            if (e.touches.length === 0) isDragging = false;
        });

        // Зум до курсора
        canvas.addEventListener('wheel', e => {
            e.preventDefault();
            const zoomSpeed = 0.1;
            const delta = e.deltaY < 0 ? 1 : -1;
            const p = getCanvasPointFromClient(e.clientX, e.clientY);
            const mx = p.x;
            const my = p.y;
            zoomAtPoint(mx, my, delta * zoomSpeed);
        }, { passive: false });

        buildHierarchyTree();

        // Кнопка згортання панелі
        const toggleBtn = document.querySelector('.panel-toggle');
        if (toggleBtn) toggleBtn.addEventListener('click', toggleSidebar);

        // Кнопка скидання виду
        const resetBtn = document.querySelector('[data-action="reset-view"]');
        if (resetBtn) resetBtn.addEventListener('click', () => window.resetView());

        // Кнопки масштабування
        const zoomInBtn = document.querySelector('[data-action="zoom-in"]');
        if (zoomInBtn) zoomInBtn.addEventListener('click', () => zoomAtPoint(canvas.width / 2, canvas.height / 2, 0.2));

        const zoomOutBtn = document.querySelector('[data-action="zoom-out"]');
        if (zoomOutBtn) zoomOutBtn.addEventListener('click', () => zoomAtPoint(canvas.width / 2, canvas.height / 2, -0.2));

        // Кнопка на весь екран
        const fullscreenBtn = document.querySelector('[data-action="fullscreen"]');
        if (fullscreenBtn) fullscreenBtn.addEventListener('click', () => {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen().catch(err => console.log(err));
            } else if (document.exitFullscreen) {
                document.exitFullscreen();
            }
        });

        // --- НОВЕ: Запускаємо цикл реального часу ---
        fetchActiveMiners(); // Перший запит одразу при завантаженні
        
        // Автоцентрування з невеликою затримкою, щоб CSS та Flexbox 
        // встигли сформувати правильні розміри canvas.width перед прорахунком
        setTimeout(() => {
            const urlParams = new URLSearchParams(window.location.search);
            const focusAp = urlParams.get('focus_ap');
            const focusLoc = urlParams.get('focus_loc');
            let focused = false;

            if (focusAp) {
                let targetAp = null;
                if (mapData.devices) targetAp = mapData.devices.find(d => d.id === focusAp);
                if (!targetAp && mapData.tunnels) {
                    for (let t of mapData.tunnels) {
                        if (t.devices) {
                            targetAp = t.devices.find(d => d.id === focusAp);
                            if (targetAp) break;
                        }
                    }
                }

                if (targetAp) {
                    selectObject('device', targetAp);
                    flyTo(targetAp.x * 10, targetAp.y * 10, 2.5, 1000); // Кінематографічний наліт
                    focused = true;
                }
            }
            else if (focusLoc) {
                let targetTunnel = null;
                if (mapData.tunnels) {
                    targetTunnel = mapData.tunnels.find(t => t.name === focusLoc);
                }
                if (targetTunnel) {
                    const tIdx = mapData.tunnels.indexOf(targetTunnel);
                    if (tIdx >= 0) {
                        // Розгортаємо список пристроїв штреку у бічній панелі зліва
                        const treeEl = document.getElementById(`tree-tunnel-${tIdx}`);
                        if (treeEl) treeEl.classList.add('expanded');
                    }
                    selectObject('tunnel', targetTunnel);
                    // Фокусуємось на центрі обраного штреку (зум 2.0)
                    flyTo((targetTunnel.x1 + targetTunnel.x2) / 2 * 10, (targetTunnel.y1 + targetTunnel.y2) / 2 * 10, 2.0, 1000);
                    focused = true;
                }
            }

            if (!focused) {
                window.resetView();
            }
            
            if (window.dashboardApp) window.dashboardApp.hideLoader();
        }, 150); // Трохи збільшена затримка для надійного рендеру
    }

    function resizeCanvas() {
        const rect = mapArea.getBoundingClientRect();
        canvas.width = Math.max(1, Math.round(rect.width));
        canvas.height = Math.max(1, Math.round(rect.height));
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
            const time = Date.now();
            const pulse = (Math.sin(time / 150) + 1) / 2;
            
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            mapData.tunnels.forEach(t => {
                const isHovered = (hoveredObject && hoveredObject.data === t);
                const isSelected = (selectedObject && selectedObject.data === t);
                const isDanger = dangerTunnels.includes(t.name);
                const x1 = t.x1 * 10, y1 = t.y1 * 10, x2 = t.x2 * 10, y2 = t.y2 * 10;

                // Підсвітка
                if (isSelected || isHovered || isDanger) {
                    ctx.lineWidth = isDanger ? 16 + 6 * pulse : 16;
                    if (isDanger) {
                        ctx.strokeStyle = `rgba(255, 68, 68, ${0.4 + 0.4 * pulse})`;
                    } else {
                        ctx.strokeStyle = isSelected ? '#4dabf7' : '#333';
                    }
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
                ctx.strokeStyle = isDanger ? '#ff4444' : '#5a4d41';
                ctx.beginPath();
                ctx.moveTo(x1, y1);
                ctx.lineTo(x2, y2);
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

        // 3. ОКРЕМІ ПРИСТРОЇ (Репітери)
        if (mapData.devices) mapData.devices.forEach(d => drawDevice(d.x * 10, d.y * 10, d));

        // --- НОВЕ: Малюємо працівників (Кластери) ---
        drawMiners();

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
        if (d.id === 'AP-SURFACE') {
            ctx.fillStyle = '#00c851'; // Зелений для Лампової
        } else {
            ctx.fillStyle = d.id === 'AP-MAIN' ? '#ff4444' : '#00ffff';
        }
        ctx.fill();
        ctx.strokeStyle = 'black';
        ctx.lineWidth = 1;
        ctx.stroke();

        if (scale > 0.6 || isSelected) {
            let textColor = '#fff';
            if (d.id === 'AP-SURFACE') textColor = '#00c851';
            else if (d.id === 'AP-MAIN') textColor = '#ff4444';
            ctx.fillStyle = isSelected ? '#4dabf7' : textColor;
            ctx.font = 'bold 11px monospace';
            ctx.textAlign = 'center';
            ctx.fillText(d.id, x, y - 12);
        }
    }

    // --- НОВЕ: Логіка групування та малювання працівників ---
    function drawMiners() {
        clickableMiners = []; // Очищаємо масив
        const time = Date.now();
        const pulse = (Math.sin(time / 150) + 1) / 2; // Від 0 до 1, для пульсації
        
        let clusters = {};
        activeMiners.forEach(m => {
            if (!clusters[m.ap_id]) clusters[m.ap_id] = [];
            clusters[m.ap_id].push(m);
        });

        for (const [ap_id, minersArray] of Object.entries(clusters)) {
            let apCoords = null;
            const findAP = (list) => list.find(d => d.id === ap_id);
            
            if (mapData.devices) apCoords = findAP(mapData.devices);
            if (!apCoords && mapData.tunnels) {
                for (let t of mapData.tunnels) {
                    if (t.devices) {
                        apCoords = findAP(t.devices);
                        if (apCoords) break;
                    }
                }
            }
            if (!apCoords) continue;

            const cx = apCoords.x * 10;
            const cy = apCoords.y * 10 - 15; 
            const count = minersArray.length;

            if (count === 1 || scale < ZOOM_THRESHOLD) {
                let clusterColor = '#00c851'; 
                if (minersArray.some(m => m.status === 'WARNING')) clusterColor = '#ffbb33'; 
                if (minersArray.some(m => m.status === 'SOS')) clusterColor = '#ff4444'; 

                let hasSOS = minersArray.some(m => m.status === 'SOS');
                let hasWarn = minersArray.some(m => m.status === 'WARNING');
                let cRadius = hasSOS ? 50 : (hasWarn ? 40 : (count > 1 ? 16 : 14));

                // НОВЕ: Зберігаємо координати прямо в DATA (як у репітерів)
                if (count === 1) {
                    minersArray[0].map_x = cx;
                    minersArray[0].map_y = cy;
                    clickableMiners.push({ type: 'miner', data: minersArray[0] });
                } else {
                    clickableMiners.push({ 
                        type: 'cluster', 
                        data: { count: count, ap_id: ap_id, map_x: cx, map_y: cy } 
                    });
                }

                if (hasSOS || hasWarn) {
                    ctx.beginPath();
                    let auraR = hasSOS ? 70 : 60;
                    auraR += 15 * pulse; // Анімація розширення аури
                    let alpha = 0.2 + 0.4 * pulse; // Анімація мигання (прозорість)
                    ctx.arc(cx, cy, auraR, 0, Math.PI * 2);
                    ctx.fillStyle = hasSOS ? `rgba(255, 68, 68, ${alpha})` : `rgba(255, 187, 51, ${alpha})`;
                    ctx.fill();
                }

                ctx.beginPath();
                ctx.arc(cx, cy, cRadius, 0, Math.PI * 2);
                ctx.fillStyle = clusterColor;
                ctx.fill();
                
                const isSelected = selectedObject && (
                    (count === 1 && selectedObject.data === minersArray[0]) ||
                    (count > 1 && selectedObject.data.ap_id === ap_id)
                );
                
                ctx.strokeStyle = isSelected ? '#fff' : 'rgba(255,255,255,0.7)';
                ctx.lineWidth = isSelected ? 3 : 1.5;
                ctx.stroke();

                ctx.fillStyle = '#fff';
                ctx.font = 'bold 14px Arial';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(count > 1 ? count.toString() : 'P', cx, cy);
            } 
            else {
                // АНІМАЦІЯ "ВИБУХУ" (Spiderify)
                let animProgress = 1.0;
                // Якщо масштаб ледь перейшов рубіж — крапки повільно випливають з центру
                if (scale < ZOOM_THRESHOLD + 0.3) {
                    animProgress = (scale - ZOOM_THRESHOLD) / 0.3;
                    animProgress = 1 - Math.pow(1 - animProgress, 3); // easeOutCubic
                }
                const spreadRadius = 32 * animProgress; 
                
                minersArray.forEach((m, index) => {
                    const angle = index * (Math.PI * 2 / count) - (Math.PI / 2); // Починаємо зверху
                    const mx = cx + spreadRadius * Math.cos(angle);
                    const my = cy + spreadRadius * Math.sin(angle);

                    let mColor = m.status === 'SOS' ? '#ff4444' : (m.status === 'WARNING' ? '#ffbb33' : '#00c851');

                    let isSOS = m.status === 'SOS';
                    let isWarn = m.status === 'WARNING';
                    let mRadius = isSOS ? 40 : (isWarn ? 30 : 12);

                    // НОВЕ: Зберігаємо координати прямо в DATA
                    m.map_x = mx;
                    m.map_y = my;
                    clickableMiners.push({ type: 'miner', data: m });

                    if (isSOS || isWarn) {
                        ctx.beginPath();
                        let auraR = isSOS ? 60 : 45;
                        auraR += 15 * pulse; // Анімація розширення
                        let alpha = 0.2 + 0.4 * pulse; // Анімація мигання
                        ctx.arc(mx, my, auraR, 0, Math.PI * 2);
                        ctx.fillStyle = isSOS ? `rgba(255, 68, 68, ${alpha})` : `rgba(255, 187, 51, ${alpha})`;
                        ctx.fill();
                    }

                    ctx.beginPath();
                    ctx.arc(mx, my, mRadius, 0, Math.PI * 2);
                    ctx.fillStyle = mColor;
                    ctx.fill();
                    
                    const isSelected = selectedObject && selectedObject.data === m;
                    ctx.strokeStyle = isSelected ? '#fff' : 'rgba(255,255,255,0.5)';
                    ctx.lineWidth = isSelected ? 2 : 1;
                    ctx.stroke();

                    ctx.fillStyle = '#fff';
                    ctx.font = 'bold 12px Arial';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText('P', mx, my);
                });
            }
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

        //  NEW --- Перевіряємо, чи мишка не над шахтарем або кластером ---
        // --- Перевіряємо кластери та шахтарів ---
        clickableMiners.forEach(item => {
            const dist = Math.hypot(item.data.map_x - wx, item.data.map_y - wy);
            if (dist < 22 / scale + 5) { // Збільшена зона (hitbox) для зручнішого кліку
                hoveredObject = item;
                canvas.style.cursor = 'pointer';
            }
        });
        
        if (hoveredObject) return;

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
        
        // --- НОВЕ: Вмикаємо/вимикаємо старий дизайн залежно від об'єкта ---
        if (selectedObject.type === 'miner' || selectedObject.type === 'cluster') {
            popup.classList.add('miner-mode');
        } else {
            popup.classList.remove('miner-mode');
        }
        
        // --- ТАБЛИЧНО-БЛОЧНИЙ ДИЗАЙН ДЛЯ ПРАЦІВНИКА ---
        if (selectedObject.type === 'miner') {
            const m = selectedObject.data;
            
            let isSOS = m.status === 'SOS';
            let isWarn = m.status === 'WARNING';
            
            let headerClass = isSOS ? 'bg-danger text-white' : (isWarn ? 'bg-warning text-dark' : 'bg-success text-white');
            let statusText = isSOS ? 'КРИТИЧНА ТРИВОГА' : (isWarn ? 'ПЕРЕВИЩЕННЯ НОРМ' : 'У ШАХТІ (НОРМА)');
            
            let gasClass = m.gas >= 50 ? 'text-danger fw-bold' : (m.gas > 17 ? 'text-warning fw-bold' : 'text-success');
            let batClass = m.battery < 20 ? 'text-danger fw-bold' : (m.battery < 50 ? 'text-warning' : 'text-light');
            let batIcon = m.battery < 20 ? 'fa-battery-empty' : (m.battery < 50 ? 'fa-battery-quarter' : (m.battery < 85 ? 'fa-battery-half' : 'fa-battery-full'));
            
            let t = m.temp !== null ? m.temp : '--';
            let h = m.hum !== null ? m.hum : '--';

            html = `
                <div class="card border-0 miner-popup-card">
                    
                    <div class="card-header ${headerClass} p-2 text-center miner-popup-header">
                        <h6 class="mb-0 fw-bold miner-popup-title"><i class="fas fa-user-hard-hat me-2"></i>${m.name}</h6>
                        <small class="miner-popup-subtitle">${m.position}</small>
                    </div>
                    
                    <div class="card-body p-0">
                        <div class="text-center p-2 miner-popup-status-wrap">
                            <span class="badge ${isSOS ? 'bg-danger pulse-sos' : (isWarn ? 'bg-warning text-dark' : 'bg-success')} w-100 py-2 miner-popup-badge">
                                ${isSOS ? '<i class="fas fa-exclamation-triangle"></i> ' : ''}${statusText}
                            </span>
                        </div>
                        
                        <table class="table table-sm table-dark table-borderless mb-0 miner-popup-table">
                            <tbody>
                                <tr class="miner-popup-row">
                                    <td class="text-secondary align-middle ps-3 col-label"><small>ЛОКАЦІЯ</small></td>
                                    <td class="text-end pe-3 fw-bold text-info"><i class="fas fa-map-marker-alt"></i> ${m.ap_id}</td>
                                </tr>
                                <tr class="miner-popup-row">
                                    <td class="text-secondary align-middle ps-3"><small>МЕТАН (CH4)</small></td>
                                    <td class="text-end pe-3 ${gasClass}"><i class="fas fa-fire"></i> ${m.gas} % LEL</td>
                                </tr>
                                <tr class="miner-popup-row">
                                    <td class="text-secondary align-middle ps-3"><small>БАТАРЕЯ</small></td>
                                    <td class="text-end pe-3 ${batClass}"><i class="fas ${batIcon}"></i> ${m.battery}%</td>
                                </tr>
                                <tr>
                                    <td class="text-secondary align-middle ps-3 py-2"><small>КЛІМАТ</small></td>
                                    <td class="text-end pe-3 py-2">
                                        <span class="text-warning me-2"><i class="fas fa-temperature-half"></i> ${t}°C</span>
                                        <span class="text-primary"><i class="fas fa-droplet"></i> ${h}%</span>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
            
        } else if (selectedObject.type === 'cluster') {
            const c = selectedObject.data;
            html = `
                <div class="card border-0 bg-dark text-white cluster-popup-card">
                    <div class="card-header bg-info text-dark fw-bold text-center p-2">
                        <i class="fas fa-users"></i> Скупчення (${c.count} чол.)
                    </div>
                    <div class="card-body p-2 text-center">
                        <div class="mb-2 text-secondary"><small>ЛОКАЦІЯ:</small> <span class="text-info fw-bold">${c.ap_id}</span></div>
                        <div class="text-warning cluster-popup-hint"><i class="fas fa-search-plus"></i> Наблизьте карту (скрол), щоб побачити кожного!</div>
                    </div>
                </div>
            `;
                    
        } else if (selectedObject.type === 'device') {
            const d = selectedObject.data;
            html = `<div class="popup-title"><i class="fas fa-wifi text-info"></i> ${d.id}</div>
                    <div class="popup-row"><span class="popup-label">Тип:</span> WiFi Repeater</div>
                    <div class="popup-row"><span class="popup-label">Статус:</span> <span class="badge bg-success">Online</span></div>`;
        } else if (selectedObject.type === 'tunnel') {
            const t = selectedObject.data;
            html = `<div class="popup-title"><i class="fas fa-road text-warning"></i> ${t.name}</div>`;
        }

        // --- ВИДАЛЕНО старі inline стилі (popup.style.padding = '0'), щоб не ламати репітери ---
        popup.style.padding = '';
        popup.style.background = '';
        popup.style.border = '';
        popup.style.boxShadow = '';

        popup.innerHTML = html;
        popup.style.display = 'block';
        
        updatePopupPosition();
    }

    // --- РОЗУМНЕ ПОЗИЦІОНУВАННЯ (ЩОБ НЕ ВИЛАЗИЛО ЗА ЕКРАН) ---
    function updatePopupPosition() {
        if (!selectedObject || popup.style.display === 'none') return;

        let wx, wy;
        
        if (selectedObject.type === 'miner' || selectedObject.type === 'cluster') {
            wx = selectedObject.data.map_x;
            wy = selectedObject.data.map_y;
        } else if (selectedObject.type === 'device') {
            wx = selectedObject.data.x * 10;
            wy = selectedObject.data.y * 10;
        } else {
            const t = selectedObject.data;
            wx = (t.x1 + t.x2) / 2 * 10;
            wy = (t.y1 + t.y2) / 2 * 10;
        }

        // Базові координати (центр об'єкта)
        const canvasRect = canvas.getBoundingClientRect();
        const cssScaleX = canvas.width ? (canvasRect.width / canvas.width) : 1;
        const cssScaleY = canvas.height ? (canvasRect.height / canvas.height) : 1;

        let px = (wx * scale + offsetX) * cssScaleX;
        let py = (wy * scale + offsetY) * cssScaleY;

        // Даємо браузеру координати, щоб він прорахував ширину/висоту віконця
        popup.style.left = px + 'px';
        popup.style.top = py + 'px';

        // Вимірюємо розміри екрану та віконця
        const mapAreaEl = document.getElementById('map-area');
        const mapRect = mapAreaEl.getBoundingClientRect();
        const mapWidth = mapRect.width;
        const mapHeight = mapRect.height;
        const pWidth = popup.offsetWidth;
        const pHeight = popup.offsetHeight;
        
        const padding = 15; // Безпечний відступ від країв екрану

        // Коригуємо по горизонталі (щоб не вилазило за правий/лівий край)
        let leftEdge = px - pWidth / 2;
        let rightEdge = px + pWidth / 2;

        if (leftEdge < padding) {
            px = pWidth / 2 + padding; 
        } else if (rightEdge > mapWidth - padding) {
            px = mapWidth - pWidth / 2 - padding; 
        }

        // Коригуємо по вертикалі (якщо вилазить за верх екрану — кидаємо ПІД курсор)
        let topEdge = py - pHeight - 15; 
        
        if (topEdge < padding) {
            py = py + pHeight + 30; // Віконце з'явиться знизу від працівника
        }

        // Застосовуємо фінальні безпечні координати
        popup.style.left = px + 'px';
        popup.style.top = py + 'px';
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
        flyTo(x, y, scale, 400); // Використовуємо нову плавну анімацію
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
            const targetScale = (rangeX === 0 && rangeY === 0) ? 1.0 : Math.min(scaleX, scaleY, 2.0);
            
            flyTo(centerX * 10, centerY * 10, targetScale, 800); // Кінематографічне віддалення камери
        } else {
            flyTo(0, 0, 1.0, 500);
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