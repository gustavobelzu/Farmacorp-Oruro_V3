// chart.js - Sistema de Visualización de Datos de Farmacorp
class DashboardCharts {
    constructor() {
        // Configuración de colores institucionales
        this.colors = {
            primary: {
                base: "#198754",
                light: "#24b36e",
                dark: "#146c43",
                gradient: ["#198754", "#24b36e"]
            },
            secondary: {
                base: "#c9a227",
                light: "#e0b942",
                dark: "#b28a1a",
                gradient: ["#c9a227", "#e0b942"]
            },
            accent: {
                base: "#0d6efd",
                light: "#3d8bfd",
                dark: "#0a58ca",
                gradient: ["#0d6efd", "#3d8bfd"]
            },
            neutral: {
                base: "#20c997",
                light: "#3dd5ac",
                dark: "#1aa179",
                gradient: ["#20c997", "#3dd5ac"]
            },
            warning: {
                base: "#fd7e14",
                light: "#fd9843",
                dark: "#ca6510",
                gradient: ["#fd7e14", "#fd9843"]
            },
            background: "#f8f9fa"
        };

        // Configuración común para los gráficos
        this.defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 20
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    titleFont: { size: 13 },
                    bodyFont: { size: 12 },
                    padding: 15,
                    cornerRadius: 5,
                    displayColors: true
                }
            }
        };

        this.init();
    }

    async init() {
        this.initializeCharts();
        this.setupEventListeners();
        await this.loadData();
        this.startAutoRefresh();
    }

    initializeCharts() {
        this.charts = {
            ventas: this.initVentasChart(),
            productos: this.initProductosChart(),
            clientes: this.initClientesChart(),
            ganancias: this.initGananciasChart()
        };
    }

    setupEventListeners() {
        // Cambio de período
        document.querySelectorAll('[data-period]').forEach(btn => {
            btn.addEventListener('click', async () => {
                const period = btn.dataset.period;
                await this.updateChartsByPeriod(period);
                this.updateActiveButton(btn);
            });
        });

        // Cambio de tipo de gráfico
        document.querySelectorAll('[data-chart-type]').forEach(btn => {
            btn.addEventListener('click', () => {
                const chartId = btn.dataset.target;
                const chartType = btn.dataset.chartType;
                this.updateChartType(chartId, chartType);
            });
        });

        // Exportar datos
        document.querySelectorAll('[data-export]').forEach(btn => {
            btn.addEventListener('click', () => {
                const format = btn.dataset.export;
                const chartId = btn.dataset.target;
                this.exportChartData(chartId, format);
            });
        });

        // Responsive
        window.addEventListener('resize', this.handleResize.bind(this));
    }

    async loadData(period = 'month') {
        try {
            const endpoints = {
                ventas: `/reportes/api/ventas/${period}/`,
                productos: '/reportes/api/productos_mas_vendidos/',
                clientes: '/clientes/api/top_clientes/',
                ganancias: `/reportes/api/ganancias/${period}/`
            };

            const data = await Promise.all(
                Object.entries(endpoints).map(async ([key, url]) => {
                    const response = await fetch(url);
                    if (!response.ok) throw new Error(`Error en ${key}: ${response.status}`);
                    return [key, await response.json()];
                })
            );

            this.data = Object.fromEntries(data);
            this.updateAllCharts();
        } catch (error) {
            console.error('Error cargando datos:', error);
            this.showError('Error cargando datos. Por favor, recarga la página.');
        }
    }

    initVentasChart() {
        const canvas = document.getElementById("ventasChart");
        if (!canvas) return null;

        return new Chart(canvas.getContext("2d"), {
            type: "bar",
            data: {
                labels: [],
                datasets: [{
                    label: "Ventas por Sucursal (Bs)",
                    data: [],
                    backgroundColor: this.colors.primary.gradient,
                    borderColor: this.colors.primary.dark,
                    borderWidth: 2,
                    borderRadius: 5,
                    hoverOffset: 4
                }]
            },
            options: {
                ...this.defaultOptions,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0,0,0,0.05)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                },
                plugins: {
                    ...this.defaultOptions.plugins,
                    title: {
                        display: true,
                        text: 'Ventas por Sucursal',
                        font: { size: 16, weight: 'bold' }
                    }
                }
            }
        });
    }

    initGananciasChart() {
        const canvas = document.getElementById("gananciasChart");
        if (!canvas) return null;

        return new Chart(canvas.getContext("2d"), {
            type: "bar",
            data: {
                labels: ["Ingresos", "Costos", "Ganancia Neta"],
                datasets: [{
                    label: "Monto (Bs)",
                    data: [],
                    backgroundColor: [
                        this.colors.accent.base,
                        this.colors.secondary.base,
                        this.colors.primary.base
                    ],
                    borderColor: [
                        this.colors.accent.dark,
                        this.colors.secondary.dark,
                        this.colors.primary.dark
                    ],
                    borderWidth: 2,
                    borderRadius: 5
                }]
            },
            options: {
                ...this.defaultOptions,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0,0,0,0.05)'
                        },
                        ticks: {
                            callback: value => `Bs ${this.formatNumber(value)}`
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                },
                plugins: {
                    ...this.defaultOptions.plugins,
                    title: {
                        display: true,
                        text: 'Análisis Financiero',
                        font: { size: 16, weight: 'bold' }
                    },
                    tooltip: {
                        callbacks: {
                            label: context => `Bs ${this.formatNumber(context.raw)}`
                        }
                    }
                }
            }
        });
    }

    initProductosChart() {
        const canvas = document.getElementById("productosChart");
        if (!canvas) return null;

        return new Chart(canvas.getContext("2d"), {
            type: "doughnut",
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        this.colors.primary.base,
                        this.colors.secondary.base,
                        this.colors.accent.base,
                        this.colors.neutral.base,
                        this.colors.warning.base
                    ],
                    borderColor: this.colors.background,
                    borderWidth: 2,
                    hoverOffset: 4
                }]
            },
            options: {
                ...this.defaultOptions,
                cutout: '65%',
                plugins: {
                    ...this.defaultOptions.plugins,
                    title: {
                        display: true,
                        text: 'Productos Más Vendidos',
                        font: { size: 16, weight: 'bold' }
                    }
                }
            }
        });
    }

    initClientesChart() {
        const canvas = document.getElementById("clientesChart");
        if (!canvas) return null;

        return new Chart(canvas.getContext("2d"), {
            type: "bar",
            data: {
                labels: [],
                datasets: [{
                    label: "Compras Totales (Bs)",
                    data: [],
                    backgroundColor: this.colors.neutral.gradient,
                    borderColor: this.colors.neutral.dark,
                    borderWidth: 2,
                    borderRadius: 5,
                    maxBarThickness: 50
                }]
            },
            options: {
                ...this.defaultOptions,
                indexAxis: 'y',
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0,0,0,0.05)'
                        },
                        ticks: {
                            callback: value => `Bs ${this.formatNumber(value)}`
                        }
                    },
                    y: {
                        grid: {
                            display: false
                        }
                    }
                },
                plugins: {
                    ...this.defaultOptions.plugins,
                    title: {
                        display: true,
                        text: 'Top 5 Clientes',
                        font: { size: 16, weight: 'bold' }
                    }
                }
            }
        });
    }

    updateAllCharts() {
        if (this.data) {
            this.updateVentasChart(this.data.ventas);
            this.updateProductosChart(this.data.productos);
            this.updateClientesChart(this.data.clientes);
            this.updateGananciasChart(this.data.ganancias);
        }
    }

    updateVentasChart(data) {
        if (!this.charts.ventas || !data) return;
        
        const chart = this.charts.ventas;
        chart.data.labels = data.labels;
        chart.data.datasets[0].data = data.values;
        chart.update();
    }

    updateProductosChart(data) {
        if (!this.charts.productos || !data) return;
        
        const chart = this.charts.productos;
        chart.data.labels = data.labels;
        chart.data.datasets[0].data = data.values;
        chart.update();
    }

    updateClientesChart(data) {
        if (!this.charts.clientes || !data) return;
        
        const chart = this.charts.clientes;
        chart.data.labels = data.labels;
        chart.data.datasets[0].data = data.values;
        chart.update();
    }

    updateGananciasChart(data) {
        if (!this.charts.ganancias || !data) return;
        
        const chart = this.charts.ganancias;
        chart.data.datasets[0].data = [
            data.ingresos,
            data.costos,
            data.ganancia
        ];
        chart.update();
    }

    async updateChartsByPeriod(period) {
        try {
            await this.loadData(period);
            this.showSuccess(`Datos actualizados para período: ${period}`);
        } catch (error) {
            console.error('Error actualizando período:', error);
            this.showError('Error actualizando los datos');
        }
    }

    updateChartType(chartId, newType) {
        const chart = this.charts[chartId];
        if (!chart) return;

        const data = chart.data;
        chart.destroy();

        this.charts[chartId] = new Chart(chart.canvas, {
            type: newType,
            data: data,
            options: this.getOptionsForType(newType)
        });
    }

    getOptionsForType(type) {
        const baseOptions = { ...this.defaultOptions };

        switch (type) {
            case 'bar':
                return {
                    ...baseOptions,
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(0,0,0,0.05)' }
                        },
                        x: { grid: { display: false } }
                    }
                };
            case 'line':
                return {
                    ...baseOptions,
                    elements: {
                        line: {
                            tension: 0.4
                        }
                    }
                };
            case 'pie':
            case 'doughnut':
                return {
                    ...baseOptions,
                    cutout: '65%'
                };
            default:
                return baseOptions;
        }
    }

    exportChartData(chartId, format) {
        const chart = this.charts[chartId];
        if (!chart) return;

        switch (format) {
            case 'png':
                this.downloadChartImage(chart);
                break;
            case 'csv':
                this.downloadChartData(chart);
                break;
            default:
                console.error('Formato de exportación no soportado');
        }
    }

    downloadChartImage(chart) {
        const link = document.createElement('a');
        link.download = `chart-${Date.now()}.png`;
        link.href = chart.canvas.toDataURL('image/png');
        link.click();
    }

    downloadChartData(chart) {
        const data = chart.data;
        const csv = [
            ['Label', 'Value'],
            ...data.labels.map((label, i) => [
                label,
                data.datasets[0].data[i]
            ])
        ].map(row => row.join(',')).join('\n');

        const blob = new Blob([csv], { type: 'text/csv' });
        const link = document.createElement('a');
        link.download = `chart-data-${Date.now()}.csv`;
        link.href = URL.createObjectURL(blob);
        link.click();
    }

    formatNumber(value) {
        return new Intl.NumberFormat('es-BO').format(value);
    }

    handleResize() {
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.resize();
        });
    }

    showSuccess(message) {
        this.showToast(message, 'success');
    }

    showError(message) {
        this.showToast(message, 'danger');
    }

    showToast(message, type = 'info') {
        // Implementar según el sistema de notificaciones de tu aplicación
        console.log(`[${type.toUpperCase()}] ${message}`);
    }

    startAutoRefresh() {
        // Actualizar datos cada 5 minutos
        setInterval(() => this.loadData(), 300000);
    }
}

// Inicialización cuando el DOM está listo
document.addEventListener("DOMContentLoaded", () => {
    window.dashboardCharts = new DashboardCharts();
});
