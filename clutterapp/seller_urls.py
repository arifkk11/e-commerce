from django.urls import path
from . import views

urlpatterns = [
    path('register', views.seller_register, name='seller_register'),
    path('login-error', views.login_error, name='login_error'),
  
    path('change_address/<int:address_id>/', views.change_address, name='change_address'),
    path("change_profile/<int:profile_id>/", views.change_profile, name="change_profile"),
    

    path('dashboard', views.seller_dashbord, name='seller_dashbord'),
    path("change-profile-picture/", views.change_profile_picture, name="change_profile_picture"),

    path('inventory', views.seller_inventory, name='seller_inventory'),
    path('export-inventory-pdf/', views.export_inventory_pdf, name='export_inventory_pdf'),

    path('products', views.seller_products, name='seller_products'),
    path('orders', views.seller_orders, name='seller_orders'),
    path("seller/orders/<int:order_id>/", views.seller_order_detail, name="seller_order_detail"),
    path("orders/<int:order_id>/update-shipping/", views.seller_update_shipping, name="seller_update_shipping"),


    path('report', views.seller_report, name='seller_report'),
    path('details', views.seller_details, name='seller_details'),
    path('approval', views.seller_approval, name='seller_approval'),

    path('add_Flatsale', views.add_flat_sale, name='add_flat_sale'),
    path('add_product', views.add_product, name='add_product'),
    path('product_view/<int:product_id>/', views.product_view, name='product_view'),
    path('product_edit/<int:product_id>/', views.product_edit, name='product_edit'),
    path('products/delete/<int:product_id>/', views.delete_product, name='delete_product'),

    path('flat_product', views.flat_product_list, name='flat_product_list'),
    path('flat-sale/delete/<int:sale_id>/', views.delete_flat_sale, name='delete_flat_sale'),
    path('flat-sale/edit/<int:sale_id>/', views.edit_flat_sale, name='edit_flat_sale'),
    path('export-pdf/', views.export_products_pdf, name='export_products_pdf'),
    path('logout/', views.custom_logout, name='custom_logout'),
    
    
]
