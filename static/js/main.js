/* ─── Sidebar Toggle ─────────────────────────────────────── */
function toggleSidebar() {
    var sidebar = document.getElementById('sidebar');
    var backdrop = document.querySelector('.sidebar-backdrop');

    if (!backdrop) {
        backdrop = document.createElement('div');
        backdrop.className = 'sidebar-backdrop';
        backdrop.onclick = function() { toggleSidebar(); };
        document.body.appendChild(backdrop);
    }

    if (window.innerWidth < 992) {
        sidebar.classList.toggle('open');
        backdrop.classList.toggle('show');
    } else {
        sidebar.classList.toggle('collapsed');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    /* Auto-close sidebar on route change (mobile) */
    if (window.innerWidth < 992) {
        document.querySelectorAll('.nav-link').forEach(function(link) {
            link.addEventListener('click', function() {
                var sidebar = document.getElementById('sidebar');
                var backdrop = document.querySelector('.sidebar-backdrop');
                if (sidebar) sidebar.classList.remove('open');
                if (backdrop) backdrop.classList.remove('show');
            });
        });
    }
});

/* ─── Dark Mode ──────────────────────────────────────────── */
function toggleDarkMode() {
    var html = document.documentElement;
    var current = html.getAttribute('data-theme');
    var theme = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    updateDarkModeIcon(theme);
}

function updateDarkModeIcon(theme) {
    var icon = document.getElementById('darkModeIcon');
    if (icon) {
        icon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
    }
}

document.addEventListener('DOMContentLoaded', function() {
    var savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateDarkModeIcon(savedTheme);
});

/* ─── Bootstrap Tooltips ─────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(el) {
        return new bootstrap.Tooltip(el);
    });
});

/* ─── Auto-dismiss alerts ────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.alert').forEach(function(alert) {
        setTimeout(function() {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

/* ─── Barcode Input Auto-Submit ──────────────────────────── */
document.addEventListener('DOMContentLoaded', function() {
    var barcodeInput = document.getElementById('barcode-input');
    if (barcodeInput) {
        barcodeInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                var form = this.closest('form');
                if (form) form.dispatchEvent(new Event('submit'));
            }
        });
    }
});

/* ─── Select2 Initialization ─────────────────────────────── */
document.addEventListener('DOMContentLoaded', function() {
    if (typeof $ !== 'undefined' && $.fn.select2) {
        $('select:not(.no-select2)').each(function() {
            if (!$(this).data('select2')) {
                $(this).select2({
                    theme: 'bootstrap-5',
                    width: '100%'
                });
            }
        });
    }
});

/* ─── Chart.js Defaults ──────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function() {
    if (typeof Chart !== 'undefined') {
        Chart.defaults.color = getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim() || '#64748b';
        Chart.defaults.borderColor = getComputedStyle(document.documentElement).getPropertyValue('--border-color').trim() || '#e2e8f0';
    }
});
