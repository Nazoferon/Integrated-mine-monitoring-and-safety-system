function sendData(isSos) {
    const badge = document.getElementById('simEmployee').value;
    const ap = document.getElementById('simAP').value;
    const battery = document.getElementById('simBattery').value;
    const gas = document.getElementById('simGas').value;
    const statusDiv = document.getElementById('simStatus');
    
    // НОВЕ: Читаємо URL безпосередньо з атрибута форми!
    const form = document.getElementById('simulatorForm');
    const apiUrl = form.dataset.url; 

    if (!badge || !ap) {
        statusDiv.innerHTML = '<span class="text-warning">Будь ласка, оберіть працівника та репітер!</span>';
        return;
    }

    statusDiv.innerHTML = '<span class="text-info"><i class="fas fa-spinner fa-spin"></i> Відправка даних...</span>';

    const payload = {
        mac_address: badge,
        ap_uid: ap,
        battery: battery,
        gas_co: gas,
        is_sos: isSos
    };

    // Використовуємо прочитаний URL
    fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    // ... далі код без змін (.then ... .catch) ...
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            statusDiv.innerHTML = isSos 
                ? '<span class="text-danger fw-bold"><i class="fas fa-check"></i> Тривога (SOS) надіслана успішно!</span>' 
                : '<span class="text-success fw-bold"><i class="fas fa-check"></i> Телеметрію успішно записано в БД.</span>';
        } else {
            statusDiv.innerHTML = `<span class="text-danger">Помилка API: ${data.message}</span>`;
        }
    })
    .catch(err => {
        statusDiv.innerHTML = `<span class="text-danger">Помилка з'єднання: ${err}</span>`;
    });
}