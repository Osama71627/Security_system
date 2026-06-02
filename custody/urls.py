from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Auth
    path('logout/', views.custom_logout, name='logout'),

    # Customer Auth
    path('customer/register/', views.customer_register, name='customer_register'),

    # Customer App
    path('customer/', views.customer_home, name='customer_home'),
    path('customer/deposit/', views.customer_deposit, name='customer_deposit'),
    path('customer/payment/<int:pk>/', views.customer_payment, name='customer_payment'),
    path('customer/success/<int:pk>/', views.customer_success, name='customer_success'),
    path('customer/deposit/<int:pk>/', views.customer_deposit_detail, name='customer_deposit_detail'),
    path('customer/invoice/<int:pk>/pay/', views.customer_invoice_pay, name='customer_invoice_pay'),

    # Admin Auth
    path('staff/login/', views.admin_login, name='admin_login'),
    path('staff/register/', views.admin_register, name='admin_register'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Deposits
    path('deposits/', views.DepositListView.as_view(), name='deposit_list'),
    path('deposits/new/', views.deposit_create, name='deposit_create'),
    path('deposits/<int:pk>/', views.deposit_detail, name='deposit_detail'),
    path('deposits/<int:pk>/edit/', views.deposit_edit, name='deposit_edit'),
    path('deposits/<int:pk>/delete/', views.deposit_delete, name='deposit_delete'),
    path('deposits/<int:pk>/update-status/', views.update_status, name='update_status'),

    # Barcode Delivery
    path('delivery/', views.barcode_delivery, name='barcode_delivery'),
    path('delivery/lookup/', views.barcode_lookup, name='barcode_lookup'),
    path('delivery/<int:pk>/confirm/', views.confirm_delivery, name='confirm_delivery'),

    # Invoices
    path('invoices/', views.InvoiceListView.as_view(), name='invoice_list'),
    path('invoices/new/', views.invoice_create, name='invoice_create'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/pdf/', views.invoice_pdf, name='invoice_pdf'),
    path('invoices/<int:pk>/mark-paid/', views.mark_invoice_paid, name='mark_invoice_paid'),

    # Receipts & Labels
    path('deposits/<int:pk>/receipt/', views.deposit_receipt, name='deposit_receipt'),
    path('deposits/<int:pk>/label/', views.deposit_label, name='deposit_label'),

    # Search
    path('search/', views.search_deposits, name='search'),

    # Reports
    path('reports/', views.reports_view, name='reports'),
    path('reports/export/', views.export_report, name='export_report'),

    # AJAX
    path('ajax/dashboard-stats/', views.ajax_dashboard_stats, name='ajax_dashboard_stats'),
    path('ajax/recent-activities/', views.ajax_recent_activities, name='ajax_recent_activities'),
    path('ajax/chart-data/', views.ajax_chart_data, name='ajax_chart_data'),

    # Admin Management
    path('admins/', views.admin_list, name='admin_list'),
    path('admins/new/', views.admin_create, name='admin_create'),

    # Customer Management
    path('customers/', views.customer_list, name='customer_list'),

    # Storage Box Management
    path('storage-boxes/', views.storage_box_list, name='storage_box_list'),
    path('storage-boxes/new/', views.storage_box_create, name='storage_box_create'),
    path('storage-boxes/<int:pk>/toggle/', views.storage_box_toggle, name='storage_box_toggle'),
    path('storage-boxes/<int:pk>/delete/', views.storage_box_delete, name='storage_box_delete'),

    # Settings
    path('settings/', views.system_settings_view, name='settings'),

    # Activity Log
    path('activity-log/', views.activity_log_view, name='activity_log'),
]
