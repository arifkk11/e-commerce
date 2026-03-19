from django.urls import path
from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),

    path('profile/', views.buyerprofile, name='buyerprofile'),
    path('address/', views.address_list, name='address_list'),
    path('wishlist/', views.wishlist, name='wishlist'),

    path('cart/', views.cart, name='cart'),
    path('myorders/', views.my_orders, name='myorders'),
    path('mycoins', views.mycoins, name='mycoins'),
    
    
    path("addresses/save/", views.save_address, name="save_address"),
    path("address/delete/<int:address_id>/",views.delete_address, name="delete_address"),
    path("address/save-current/",views.save_current_location, name="save_current_location"),

    path('add_to_wishlist/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    
    # URL to remove a product from the wishlist
    path('remove_from_wishlist/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),

    path('flat_product',views.flat_product_list,name='flat_product_list'),

    
    path('sell-dress', views.sellerwindow, name='sellerwindow'),
    path('product_details/<int:pk>/', views.product_details, name='product_details'),
    path("store/<int:pk>/", views.store_detail, name="store_detail"),

    path('submit_review/<int:product_id>/', views.submit_review, name='submit_review'),
    path("feedback/submit/", views.submit_feedback, name="submit_feedback"),
    path('shopnow', views.shopnow, name='shopnow'),
   
    path('declutter', views.declutter_page, name='declutter_page'),
    path('declutter_window', views.declutter_window, name='declutter_window'),
    
    path("login/", views.loginandsignup, name="login"),
    path("send-otp/", views.send_otp, name="send_otp"),
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    path('logout/', views.custom_logout, name='custom_logout'),
    
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/add/<int:product_id>/<int:variant_id>/', views.add_to_cart, name='add_to_cart_variant'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path("cart/save-for-later/<int:product_id>/", views.save_for_later, name="save_for_later"),
    path("cart/update/<int:item_id>/", views.update_cart_item, name="update_cart_item"),


    
    
    path("buy-now/<int:product_id>/", views.buy_now, name="buy_now"),
    path("order/<int:order_id>/update-address/", views.update_order_address, name="update_order_address"),
    path("checkout/<int:order_id>/", views.checkout_page, name="checkout_page"),
    path('checkout_from_cart/', views.checkout_from_cart, name='checkout_from_cart'),
    path("order/<int:order_id>/payment/", views.payment_page, name="payment_page"),
    path('ordersuccess/<int:order_id>/', views.order_success, name='order_success'),
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),
    path("payment/success/", views.payment_success, name="payment_success"),  # ✅ this fixes it





]
