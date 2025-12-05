// Alertas Manager - Sistema de notificaciones en tiempo real
class AlertasManager {
    constructor() {
        this.alertCount = document.getElementById("alertCount");
        this.alertList = document.getElementById("alertList");
        this.notificationSound = new Audio('/static/sounds/notification.mp3');
        this.lastUpdate = new Date();
        this.cache = new Map();
        this.retryDelay = 5000;
        this.maxRetries = 3;
        this.audioEnabled = localStorage.getItem('alertas_sound') !== 'disabled';

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.cargarAlertas();
        this.initWebSocket();
        this.setupPeriodicRefresh();
    }

    setupEventListeners() {
        // Toggle sonido de notificaciones
        const soundToggle = document.getElementById('alertSoundToggle');
        if (soundToggle) {
            soundToggle.checked = this.audioEnabled;
            soundToggle.addEventListener('change', (e) => {
                this.audioEnabled = e.target.checked;
                localStorage.setItem('alertas_sound', e.target.checked ? 'enabled' : 'disabled');
            });
        }

        // Marcar como leída
        document.addEventListener('click', (e) => {
            if (e.target.matches('.mark-read-alert')) {
                e.preventDefault();
                const alertId = e.target.dataset.alertId;
                this.marcarComoLeida(alertId);
            }
        });

        // Filtros rápidos
        const quickFilters = document.querySelectorAll('.alert-quick-filter');
        quickFilters.forEach(filter => {
            filter.addEventListener('click', (e) => {
                e.preventDefault();
                const tipo = e.target.dataset.tipo;
                this.filtrarPorTipo(tipo);
            });
        });
    }

    async cargarAlertas(retry = 0) {
        try {
            const response = await fetch("/alertas/api/");
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const data = await response.json();
            this.actualizarUI(data);
            this.cache.clear();
            data.alertas.forEach(alerta => this.cache.set(alerta.id, alerta));
            
            return data;
        } catch (error) {
            console.error("🔴 Error cargando alertas:", error);
            
            if (retry < this.maxRetries) {
                console.log(`Reintentando en ${this.retryDelay/1000}s... (intento ${retry + 1}/${this.maxRetries})`);
                setTimeout(() => this.cargarAlertas(retry + 1), this.retryDelay);
            } else {
                this.mostrarErrorUI("No se pudieron cargar las alertas. Por favor, recarga la página.");
            }
        }
    }

    actualizarUI(data) {
        const { count, alertas } = data;

        // Actualizar contador
        if (this.alertCount) {
            if (count > 0) {
                this.alertCount.textContent = count;
                this.alertCount.classList.remove("d-none");
                this.alertCount.classList.add("animate__animated", "animate__bounce");
                setTimeout(() => this.alertCount.classList.remove("animate__animated", "animate__bounce"), 1000);
            } else {
                this.alertCount.classList.add("d-none");
            }
        }

        // Actualizar lista de alertas
        if (this.alertList) {
            const nuevasAlertas = alertas.filter(alerta => !this.cache.has(alerta.id));
            
            if (nuevasAlertas.length > 0 && this.audioEnabled) {
                this.reproducirSonido();
            }

            this.alertList.innerHTML = this.generarHTMLAlertas(alertas);
            this.inicializarTooltips();
        }

        // Actualizar timestamp
        this.lastUpdate = new Date();
        document.querySelector('.last-update-time')?.setAttribute(
            'data-bs-original-title', 
            `Última actualización: ${this.lastUpdate.toLocaleTimeString()}`
        );
    }

    generarHTMLAlertas(alertas) {
        if (alertas.length === 0) {
            return `
                <li class="dropdown-header text-center">
                    <i class="fas fa-check-circle text-success fa-2x mb-2"></i>
                    <p class="mb-0">No hay alertas pendientes</p>
                </li>
            `;
        }

        return `
            <li class="dropdown-header d-flex justify-content-between align-items-center px-3">
                <span class="fw-bold text-danger">
                    <i class="fas fa-bell me-2"></i>Alertas Recientes
                </span>
                <div class="btn-group btn-group-sm">
                    <button type="button" class="btn btn-outline-secondary btn-sm alert-quick-filter" data-tipo="all">
                        <i class="fas fa-list"></i>
                    </button>
                    <button type="button" class="btn btn-outline-danger btn-sm alert-quick-filter" data-tipo="critica">
                        <i class="fas fa-exclamation-triangle"></i>
                    </button>
                </div>
            </li>
            <li><hr class="dropdown-divider"></li>
            ${alertas.map(alerta => this.generarAlertaHTML(alerta)).join("")}
            <li><hr class="dropdown-divider"></li>
            <li class="text-center p-2">
                <a href="/alertas/" class="btn btn-sm btn-outline-success w-100">
                    <i class="fas fa-external-link-alt me-2"></i>Ver todas las alertas
                </a>
            </li>
        `;
    }

    generarAlertaHTML(alerta) {
        const tipoClases = {
            CRITICA: 'danger',
            STOCK: 'warning',
            VENCIMIENTO: 'info'
        };

        const tipoIconos = {
            CRITICA: 'exclamation-triangle',
            STOCK: 'box',
            VENCIMIENTO: 'calendar-times'
        };

        const clase = tipoClases[alerta.tipo] || 'secondary';
        const icono = tipoIconos[alerta.tipo] || 'bell';

        return `
            <li class="px-3 py-2 alert-item ${alerta.leida ? 'bg-light' : ''}" data-alert-id="${alerta.id}">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <div class="d-flex align-items-center mb-1">
                            <span class="badge bg-${clase} me-2">
                                <i class="fas fa-${icono} me-1"></i>${alerta.tipo}
                            </span>
                            <small class="text-muted">
                                <i class="far fa-clock me-1"></i>${this.formatearTiempo(alerta.fecha)}
                            </small>
                        </div>
                        <p class="mb-1 text-dark">${alerta.descripcion}</p>
                        <small class="text-muted d-flex align-items-center">
                            <i class="fas fa-prescription-bottle me-1"></i>${alerta.producto}
                        </small>
                    </div>
                    <div class="ms-2">
                        <button class="btn btn-link btn-sm p-0 mark-read-alert" 
                                data-alert-id="${alerta.id}"
                                data-bs-toggle="tooltip"
                                title="Marcar como leída">
                            <i class="far fa-${alerta.leida ? 'check-circle text-success' : 'circle'}"></i>
                        </button>
                    </div>
                </div>
            </li>
        `;
    }

    formatearTiempo(fecha) {
        const ahora = new Date();
        const fechaAlerta = new Date(fecha);
        const diferencia = Math.floor((ahora - fechaAlerta) / 1000);

        if (diferencia < 60) return 'Hace un momento';
        if (diferencia < 3600) return `Hace ${Math.floor(diferencia / 60)} min`;
        if (diferencia < 86400) return `Hace ${Math.floor(diferencia / 3600)} h`;
        return fechaAlerta.toLocaleDateString();
    }

    async marcarComoLeida(alertId) {
        try {
            const response = await fetch(`/alertas/api/marcar-leida/${alertId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const data = await response.json();
            if (data.success) {
                const alertaElement = document.querySelector(`[data-alert-id="${alertId}"]`);
                if (alertaElement) {
                    alertaElement.classList.add('bg-light');
                    const iconElement = alertaElement.querySelector('.mark-read-alert i');
                    if (iconElement) {
                        iconElement.className = 'far fa-check-circle text-success';
                    }
                }
                this.actualizarContador(-1);
            }
        } catch (error) {
            console.error("🔴 Error marcando alerta como leída:", error);
            this.mostrarToast('Error', 'No se pudo marcar la alerta como leída', 'danger');
        }
    }

    actualizarContador(diferencia) {
        if (this.alertCount) {
            const currentCount = parseInt(this.alertCount.textContent) || 0;
            const newCount = Math.max(0, currentCount + diferencia);
            
            if (newCount === 0) {
                this.alertCount.classList.add('d-none');
            } else {
                this.alertCount.textContent = newCount;
            }
        }
    }

    filtrarPorTipo(tipo) {
        const alertItems = document.querySelectorAll('.alert-item');
        alertItems.forEach(item => {
            const alertaTipo = item.querySelector('.badge').textContent;
            item.style.display = (tipo === 'all' || alertaTipo.includes(tipo)) ? 'block' : 'none';
        });
    }

    reproducirSonido() {
        if (this.audioEnabled && this.notificationSound) {
            this.notificationSound.play().catch(e => console.log('Error reproduciendo sonido:', e));
        }
    }

    initWebSocket() {
        try {
            const ws = new WebSocket(`ws://${window.location.host}/ws/alertas/`);
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'nueva_alerta') {
                    this.cargarAlertas();
                }
            };

            ws.onclose = () => {
                console.log('WebSocket cerrado. Reintentando en 5s...');
                setTimeout(() => this.initWebSocket(), 5000);
            };
        } catch (error) {
            console.error('Error iniciando WebSocket:', error);
        }
    }

    setupPeriodicRefresh() {
        // Refresco periódico como fallback
        setInterval(() => this.cargarAlertas(), 60000);
    }

    inicializarTooltips() {
        const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltips.forEach(tooltip => new bootstrap.Tooltip(tooltip));
    }

    mostrarErrorUI(mensaje) {
        if (this.alertList) {
            this.alertList.innerHTML = `
                <li class="dropdown-header text-center">
                    <i class="fas fa-exclamation-circle text-danger fa-2x mb-2"></i>
                    <p class="text-danger mb-0">${mensaje}</p>
                </li>
            `;
        }
    }

    mostrarToast(titulo, mensaje, tipo = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${tipo} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <strong>${titulo}:</strong> ${mensaje}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        document.querySelector('.toast-container')?.appendChild(toast);
        new bootstrap.Toast(toast).show();
    }

    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    }
}

// Inicialización cuando el DOM está listo
document.addEventListener("DOMContentLoaded", () => {
    window.alertasManager = new AlertasManager();
});
