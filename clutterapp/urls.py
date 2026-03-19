from django.urls import path
from clutterapp import views


urlpatterns = [
 #SELLER START################################################################################
    path('seller_register', views.seller_register, name='seller_register'),
    path('login-error', views.login_error, name='login_error'),
    
    path('verify_otp/<uuid:token>/', views.verify_otp, name='verify_otp'),
    path('change_password',views.change_password,name='change_password'),
    path('change_address/<int:address_id>/',views.change_address,name='change_address'),
   


   
    
    path('dashboard', views.seller_dashbord, name='seller_dashbord'),
    path('seller_inventory', views.seller_inventory, name='seller_inventory'),
    path('seller_products', views.seller_products, name='seller_products'),
    path('seller_orders', views.seller_orders, name='seller_orders'),
    path('seller_report', views.seller_report, name='seller_report'),   
    path('seller_details', views.seller_details, name='seller_details'),
    path('seller_approval', views.seller_approval, name='seller_approval'),
    
    
    path('add_Flatsale', views.add_flat_sale, name='add_flat_sale'),
    path('add_product', views.add_product, name='add_product'),
    path('product_view/<int:product_id>/', views.product_view, name='product_view'),
    path('product_edit/<int:product_id>/', views.product_edit, name='product_edit'),
    path('products/delete/<int:product_id>/',views.delete_product, name='delete_product'),
    
    
   path('flat_product',views.flat_product_list,name='flat_product_list'),
   path('seller/flat-sale/delete/<int:sale_id>/', views.delete_flat_sale, name='delete_flat_sale'),
   path('seller/flat-sale/edit/<int:sale_id>/', views.edit_flat_sale, name='edit_flat_sale'),
   path('seller/export-pdf/', views.export_products_pdf, name='export_products_pdf'),

   
   
   
 #SELLER END################################################################################   
#user#################################################################################
   path('',views.homepage,name='homepage'),
   path('Sell Dress',views.sellerwindow,name='sellerwindow'),
   path('product_details/<int:pk>/',views.product_details,name='product_details'),
   path('shopnow',views.shopnow,name='shopnow'),
   # path('userlogin',views.userlogin,name='userlogin'),
   # path('usersignup',views.usersignup,name='usersignup'),
   # path('userlogout',views.userlogout,name='userlogout'),
   # path('userpassword',views.userpassword,name='userpassword'),
   # path('editprofile',views.edit_buyer_profile,name='edit_buyer_profile'),
   # path('addaddress',views.add_address,name='add_address'),
   path("delete-address/", views.delete_address, name="delete_address"),

   path("login/", views.loginandsignup, name="login"),

   


   path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
   path('cart/add/<int:product_id>/<int:variant_id>/', views.add_to_cart, name='add_to_cart_variant'),

]