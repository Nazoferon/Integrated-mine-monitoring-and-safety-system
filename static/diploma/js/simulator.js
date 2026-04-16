document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('simulatorForm');
    const apiUrl = form.dataset.apiUrl;
    
    const btnNormal = document.getElementById('btnSendNormal');
    const btnSos = document.getElementById('btnSendSos');
    const btnCancelSos = document.getElementById('btnCancelSos');
    const btnAutoPing = document.getElementById('btnAutoPing');
    const statusDiv = document.getElementById('simStatus');

    let autoInterval = null;

    function showStatus(message, isError = false) {
        statusDiv.textContent = message;
        statusDiv.classList.remove('error', 'success');
        statusDiv.classList.add('show', isError ? 'error' : 'success');
        
        // Якщо це не повідомлення про авто-режим, ховаємо через 4 секунди
        if (!autoInterval || isError) {
            setTimeout(() => { 
                if(!autoInterval) {
                    statusDiv.classList.remove('show'); 
                }
            }, 4000);
        }
    }

    // --- ОНОВЛЕННЯ ЗНАЧЕНЬ ПОВЗУНКІВ ---
    function setupSliderListeners() {
        const sliders = {
            'simBattery': { el: 'valBattery', unit: '%' },
            'simTemp': { el: 'valTemp', unit: ' °C' },
            'simRssi': { el: 'valRssi', unit: ' dBm' }
        };

        for (const sliderId in sliders) {
            const slider = document.getElementById(sliderId);
            if (slider) {
                const displayEl = document.getElementById(sliders[sliderId].el);
                const unit = sliders[sliderId].unit;
                // Оновлюємо значення при завантаженні сторінки
                displayEl.innerText = slider.value + unit;
                // Додаємо слухача для майбутніх змін
                slider.addEventListener('input', function() {
                    displayEl.innerText = this.value + unit;
                });
            }
        }
    }

    const simGas = document.getElementById('simGas');
    const valGas = document.getElementById('valGas');
    const simGasIcon = document.getElementById('simGasIcon');

    if (simGas) {
        simGas.addEventListener('input', function() {
            const val = parseFloat(this.value);
            // Використовуємо toFixed(1) для значень з десятковою частиною
            valGas.innerText = val.toFixed(1) + ' % LEL';
            
            valGas.classList.remove('text-success', 'border-success', 'text-warning', 'border-warning', 'text-danger', 'border-danger');
            simGasIcon.className = 'fas';
            
            if (val >= 50) {
                valGas.classList.add('text-danger', 'border-danger');
                simGasIcon.classList.add('fa-fire', 'text-danger');
            } else if (val > 17) {
                valGas.classList.add('text-warning', 'border-warning');
                simGasIcon.classList.add('fa-burn', 'text-warning');
            } else {
                valGas.classList.add('text-success', 'border-success');
                simGasIcon.classList.add('fa-cloud', 'text-success');
            }
        });
        // Ініціалізуємо значення при завантаженні
        simGas.dispatchEvent(new Event('input'));
    }

    function collectData() {
        const mac = document.getElementById('simMacAddress').value;
        const ap = document.getElementById('simApUid').value;
        
        if (!mac || !ap) {
            showStatus("Будь ласка, оберіть пристрій та репітер зі списку!", true);
            return null;
        }

        return {
            mac_address: mac,
            ap_uid: ap,
            battery: parseInt(document.getElementById('simBattery').value),
            gas_level: parseFloat(document.getElementById('simGas').value),
            temperature: parseFloat(document.getElementById('simTemp').value),
            humidity: 50.0, // Жорстко задана, якщо немає повзунка
            rssi: parseInt(document.getElementById('simRssi').value),
            fw_version: document.getElementById('simFwVersion').value,
            is_moving: document.getElementById('simIsMoving').checked,
            is_sos: false,
            reason: "Normal"
        };
    }

    async function sendTelemetry(data) {
        try {
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-API-Key': 'SecretMineKey2026'
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            if (response.ok && result.status === 'success') {
                showStatus(`✅ Успішно: ${result.message || 'Пакет телеметрії відправлено'}`);
            } else {
                showStatus(`❌ Помилка серверу: ${result.message || 'Невідома помилка'}`, true);
            }
        } catch (error) {
            showStatus(`❌ Помилка мережі: ${error.message}`, true);
        }
    }

    btnNormal.addEventListener('click', () => {
        const data = collectData();
        if (data) sendTelemetry(data);
    });

    btnSos.addEventListener('click', () => {
        const data = collectData();
        if (data) {
            data.is_sos = true;
            data.reason = "MANUAL_SOS";
            sendTelemetry(data);
        }
    });

    btnCancelSos.addEventListener('click', () => {
        const data = collectData();
        if (data) {
            data.is_sos = false;
            data.reason = "SOS_CANCELLED";
            sendTelemetry(data);
        }
    });

    btnAutoPing.addEventListener('click', () => {
        if (autoInterval) {
            clearInterval(autoInterval);
            autoInterval = null;
            btnAutoPing.innerHTML = '<i class="fas fa-robot"></i> Авто-симуляція (5с)';
            showStatus("Авто-симуляцію зупинено");
        } else {
            btnNormal.click(); // Відправити перший пакет одразу
            autoInterval = setInterval(() => { btnNormal.click(); }, 5000);
            btnAutoPing.innerHTML = '<i class="fas fa-stop-circle text-danger"></i> Зупинити авто-симуляцію';
            showStatus("⏳ Авто-симуляція активна (відправка кожні 5 секунд)...");
        }
    });

    // Ініціалізація всіх повзунків
    setupSliderListeners();
});