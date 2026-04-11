document.addEventListener('DOMContentLoaded', function () {
    const initializeChart = () => {
        const chartElement = document.getElementById('alertsChart');
        if (!chartElement) return;

        const labelsData = document.getElementById('chart-labels');
        const valuesData = document.getElementById('chart-values');

        if (!labelsData || !valuesData) return;

        const labels = JSON.parse(labelsData.textContent);
        const values = JSON.parse(valuesData.textContent);

        const ctx = chartElement.getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Кількість тривог',
                    data: values,
                    backgroundColor: 'rgba(77, 171, 247, 0.5)',
                    borderColor: 'rgba(77, 171, 247, 1)',
                    borderWidth: 1
                }]
            },
            options: { scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } }
        });
    };

    initializeChart();
});