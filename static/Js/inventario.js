// Inventory Management JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize DataTable
    const inventarioTable = new DataTable('#inventarioTable', {
        language: {
            url: '//cdn.datatables.net/plug-ins/1.13.4/i18n/es-ES.json'
        },
        responsive: true,
        dom: '<"d-flex justify-content-between align-items-center mb-3"lf>rt<"d-flex justify-content-between align-items-center"ip>',
        pageLength: 10,
        order: [[5, 'desc']], // Order by last update by default
    });

    // Export to Excel functionality
    document.getElementById('exportExcel').addEventListener('click', function() {
        const workbook = XLSX.utils.table_to_book(document.getElementById('inventarioTable'));
        XLSX.writeFile(workbook, 'Inventario_' + new Date().toISOString().split('T')[0] + '.xlsx');
    });

    // Filter functionality
    const filterForm = document.getElementById('filterForm');
    if (filterForm) {
        filterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            applyFilters();
        });

        // Real-time filtering
        document.querySelectorAll('#filterForm input, #filterForm select').forEach(element => {
            element.addEventListener('change', () => applyFilters());
        });
    }

    // Delete confirmation
    window.confirmDelete = function(deleteUrl) {
        const modal = new bootstrap.Modal(document.getElementById('deleteModal'));
        document.getElementById('confirmDeleteBtn').href = deleteUrl;
        modal.show();
    };

    // Stock status indicators
    function updateStockStatus() {
        document.querySelectorAll('[data-stock-quantity]').forEach(element => {
            const quantity = parseInt(element.dataset.stockQuantity);
            const minStock = parseInt(element.dataset.minStock);
            
            let status, className;
            if (quantity === 0) {
                status = 'Sin Stock';
                className = 'bg-danger';
            } else if (quantity <= minStock) {
                status = 'Stock Bajo';
                className = 'bg-warning text-dark';
            } else {
                status = 'En Stock';
                className = 'bg-success';
            }
            
            element.querySelector('.stock-badge').className = `badge ${className} stock-badge`;
            element.querySelector('.stock-text').textContent = status;
        });
    }

    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // History modal functionality
    window.showHistory = async function(inventarioId) {
        const modal = new bootstrap.Modal(document.getElementById('historyModal'));
        const content = document.getElementById('historyContent');
        content.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div></div>';
        modal.show();

        try {
            const response = await fetch(`/api/inventario/${inventarioId}/history/`);
            if (!response.ok) throw new Error('Error al cargar el historial');
            const data = await response.json();
            
            content.innerHTML = createHistoryTable(data);
        } catch (error) {
            content.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    Error al cargar el historial: ${error.message}
                </div>`;
        }
    };

    function createHistoryTable(data) {
        return `
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Fecha</th>
                            <th>Tipo</th>
                            <th>Cantidad</th>
                            <th>Usuario</th>
                            <th>Detalles</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.map(item => `
                            <tr>
                                <td>${new Date(item.fecha).toLocaleString()}</td>
                                <td>
                                    <span class="badge ${item.tipo === 'entrada' ? 'bg-success' : 'bg-danger'}">
                                        ${item.tipo}
                                    </span>
                                </td>
                                <td>${item.cantidad}</td>
                                <td>${item.usuario}</td>
                                <td>${item.detalles || '-'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>`;
    }

    // Apply filters function
    function applyFilters() {
        const producto = document.getElementById('filterProducto').value.toLowerCase();
        const sucursal = document.getElementById('filterSucursal').value;
        const estado = document.getElementById('filterEstado').value;

        inventarioTable.search('').columns().search('').draw();

        if (producto) inventarioTable.column(0).search(producto);
        if (sucursal) inventarioTable.column(1).search(sucursal);
        if (estado) inventarioTable.column(4).search(estado);

        inventarioTable.draw();
    }

    // Initial status update
    updateStockStatus();
});