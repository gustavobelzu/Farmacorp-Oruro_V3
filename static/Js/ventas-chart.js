function initVentasChart() {
    try {
        const canvas = document.getElementById('ventasChart');
        if (!canvas) {
            console.error('Canvas element not found');
            return;
        }

        const ventasData = JSON.parse('{{ ventas_por_mes|escapejs }}');
        
        const labels = ventasData.map(item => {
            const fecha = new Date(item.mes);
            return fecha.toLocaleDateString('es-ES', { month: 'long', year: 'numeric' });
        });
        
        const montos = ventasData.map(item => item.total);

        const data = {
            labels: labels,
            datasets: [{
                label: 'Monto de Compras',
                data: montos,
                fill: true,
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                tension: 0.4
            }]
        };

        const config = {
            type: 'line',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                label += new Intl.NumberFormat('es-BO', {
                                    style: 'currency',
                                    currency: 'BOB'
                                }).format(context.parsed.y);
                                return label;
                            }
                        }
                    },
                    legend: {
                        position: 'top',
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return new Intl.NumberFormat('es-BO', {
                                    style: 'currency',
                                    currency: 'BOB'
                                }).format(value);
                            }
                        }
                    }
                }
            }
        };

        new Chart(canvas, config);
    } catch (error) {
        console.error('Error initializing chart:', error);
    }
}

// Inicializar el gráfico cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', initVentasChart);