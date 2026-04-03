document.addEventListener('DOMContentLoaded', function () {
    // 1. Отримуємо змінні, які Django безпечно сховав у HTML
    const alertId = JSON.parse(document.getElementById('alert-id-data').textContent);
    const repeaterId = JSON.parse(document.getElementById('alert-repeater-data').textContent);
    const alertStatus = JSON.parse(document.getElementById('alert-status-data').textContent);

    let minerPulseSize = 0;
    let pulseDirection = 1;

    const canvas = document.getElementById('miniMapCanvas');
    
    // Перевіряємо, чи є canvas і чи прив'язаний репітер
    if (canvas && repeaterId) {
        const ctx = canvas.getContext('2d');
        function animate() {
            canvas.width = canvas.offsetWidth;
            canvas.height = canvas.offsetHeight;
            const x = canvas.width / 2;
            const y = canvas.height / 2;
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Сітка
            ctx.strokeStyle = '#1a1a1a';
            for (let i = 0; i < canvas.width; i += 25) { ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, canvas.height); ctx.stroke(); }
            for (let i = 0; i < canvas.height; i += 25) { ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(canvas.width, i); ctx.stroke(); }

            // Репітер
            ctx.beginPath();
            ctx.arc(x, y, 60, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(77, 171, 247, 0.05)';
            ctx.fill();
            ctx.fillStyle = '#4dabf7';
            ctx.beginPath(); ctx.arc(x, y, 5, 0, Math.PI * 2); ctx.fill();

            // Шахтар
            const minerX = x + 30; const minerY = y - 20;
            minerPulseSize += 0.4 * pulseDirection;
            if (minerPulseSize > 15 || minerPulseSize < 0) pulseDirection *= -1;
            ctx.beginPath();
            ctx.arc(minerX, minerY, 8 + minerPulseSize, 0, Math.PI * 2);
            ctx.strokeStyle = `rgba(255, 77, 77, ${0.5 - minerPulseSize / 30})`;
            ctx.lineWidth = 2; ctx.stroke();
            ctx.beginPath(); ctx.arc(minerX, minerY, 6, 0, Math.PI * 2);
            ctx.fillStyle = '#ff4d4d'; ctx.fill();

            requestAnimationFrame(animate);
        }
        animate();
    }

    // 2. Логіка оновлення даних (якщо тривогу ще не закрито)
    if (alertStatus !== "RESOLVED") {
        setInterval(function () {
            fetch(`/diploma/alert/${alertId}/api/`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'ok') {
                      const gasEl = document.querySelector('[data-type="gas"]');
                      if (gasEl) gasEl.innerText = data.gas + " % LEL";

                      const tempEl = document.querySelector('[data-type="temp"]');
                      if (tempEl) tempEl.innerText = data.temp + " °C";

                      const timeEl = document.querySelector('[data-type="timestamp"]');
                      if (timeEl) timeEl.innerText = data.timestamp;

                      const rssiEl = document.querySelector('[data-type="rssi"]');
                      if (rssiEl) rssiEl.innerText = data.rssi + " dBm";

                      const repEl = document.querySelector('[data-type="repeater"]');
                      if (repEl) repEl.innerHTML = `<i class="fas fa-wifi text-success"></i> ${data.repeater}`;
                  }
                });
        }, 3000);
    }
});