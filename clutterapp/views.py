from django.shortcuts import render,redirect
from django.http import HttpResponse, HttpResponseForbidden
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth  
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.contrib.auth import login,authenticate
from django.contrib.auth import logout
from django.shortcuts import render
from clutterapp.models import *
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash, login
from .models import SIZE_CHOICES
from django.shortcuts import render, get_object_or_404
from django.forms import modelformset_factory
from .forms import *
from django.core.mail import send_mail, EmailMessage
from django.core.validators import validate_email
from django.conf import settings
from random import randint
import string
from django.urls import reverse
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST
from django.db import IntegrityError
from django.contrib.admin.views.decorators import staff_member_required
from datetime import datetime
from datetime import timedelta
import requests
from django.core.mail import mail_admins
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum
from django.http import Http404
from django.db.models import Avg
from django.db.models import Count
from django.db.models import Sum, Count, F,DecimalField, ExpressionWrapper
from decimal import Decimal
import razorpay









# Create your views here.
##########################################LOGIN/SIGNUP#########################################################

User = get_user_model()

def generate_otp():
    """Generate 6-digit OTP"""
    return ''.join(random.choices("0123456789", k=6))

def loginandsignup(request):
    return render(request, "loginandsignup.html")

def send_otp(request):
    if request.method == "POST":
        email = request.POST.get("email")
        if not email:
            messages.error(request, "Email is required")
            return redirect("login")

        otp = generate_otp()
        print("Generated OTP:", otp)

        request.session['email'] = email  # keep in session for verify

        user, created = User.objects.get_or_create(email=email, defaults={"name": ""})
        user.otp = otp
        user.otp_created_at = timezone.now()
        user.save()

        try:
            send_mail(
                "Your OTP Code",
                f"Your OTP code is {otp}. It will expire in 5 minutes.",
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            messages.success(request, "OTP sent successfully")
        except Exception as e:
            messages.error(request, f"Error sending email: {e}")

        return redirect("login")


User = get_user_model()

def get_device_type(request):
    """Detect device type from user agent."""
    if not request:
        return 'Unknown'
    ua = request.META.get('HTTP_USER_AGENT', '').lower()
    if any(mobile in ua for mobile in ['iphone', 'android', 'blackberry', 'mobile']):
        return 'Mobile'
    elif any(tablet in ua for tablet in ['ipad', 'tablet', 'kindle']):
        return 'Tablet'
    else:
        return 'Desktop'


def verify_otp(request):
    if request.method == "POST":
        email = request.session.get("email")
        otp = request.POST.get("otp")

        if not email:
            messages.error(request, "Session expired. Please request a new OTP.")
            return redirect("login")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "No user found for this email")
            return redirect("login")

        if (
            user.otp == otp and
            user.otp_created_at and
            timezone.now() <= user.otp_created_at + timedelta(minutes=5)
        ):
            # OTP valid → update user info
            user.otp = None
            user.login_time = timezone.now()
            user.user_agent = request.META.get('HTTP_USER_AGENT', '')
            user.device_type = get_device_type(request)
            user.save()

            # Login user in session
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            messages.success(request, "OTP verified. Logged in successfully.")
            return redirect("/")
        else:
            messages.error(request, "Invalid or expired OTP")
            return redirect("login")
        
        
@login_required
def custom_logout(request):
    request.user.logout_time = timezone.now()
    request.user.save()
    logout(request)
    return redirect('/')  # or homepage

def custom_404(request, exception):
    return render(request, "404.html", status=404)

#################################################################################################################

def google_signup_start(request):
    # get ?role=buyer or seller, default to buyer
    role = request.GET.get('role', 'buyer')
    request.session['social_role'] = role
    request.session.modified = True
    # Redirect to actual Google OAuth start
    return redirect('social:begin', backend='google-oauth2')


#seller FUNCTIONS#######################################################################################



def seller_register(request):
    # If user is already authenticated, redirect to seller details page
    if request.user.is_authenticated:
        return redirect('seller_details')  # Replace with your URL name for seller_details.html



    return render(request, 'loginandsignup.html')


User = get_user_model()



@login_required
def seller_approval(request):
    user = request.user

    try:
        seller_profile = user.seller_profile  # via related_name='seller_profile'

        # If seller is already approved, redirect to dashboard
        if seller_profile.approved:
            return redirect('seller_dashbord')

        address = seller_profile.address

        context = {
            'user': user,
            'store_name': seller_profile.store_name,
            'phone': seller_profile.phone,
            'post_office': address.post_office,
            'city': address.city,
            'state': address.state,
            'country': address.country,
            'pin': address.pin,
            'extra_details': address.extra_details,
        }
        

        return render(request, 'seller/seller_approval.html', context)

    except SellerProfile.DoesNotExist:
        return redirect('seller_details')  # Redirect to form page


    
@login_required
def seller_dashbord(request):
    
    user = request.user
    if user.seller_profile.approved == False:
        return redirect('seller_approval')
   

    seller_profile = user.seller_profile
    total_products = Product.objects.filter(seller=seller_profile).count()
    
    # Get new products added in the last 7 days
   
    new_products_count = Product.objects.filter(
        seller=seller_profile,
        created_at__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    low_stock_products = Product.objects.filter(
        seller=seller_profile,
        stock_quantity__lte=5
    ).order_by('stock_quantity')
    
    
    # Current month (or last 30 days)
    today = timezone.now()
    start_of_month = today.replace(day=1)
    last_month_start = (start_of_month - timedelta(days=1)).replace(day=1)
    last_month_end = start_of_month - timedelta(days=1)

    # Pending orders this month
    current_count = Order.objects.filter(
        items__product__seller=seller_profile,
        status='pending',
        created_at__gte=start_of_month
    ).distinct().count()

    # Pending orders last month
    last_count = Order.objects.filter(
        items__product__seller=seller_profile,
        status='pending',
        created_at__range=(last_month_start, last_month_end)
    ).distinct().count()

    # Calculate percentage change
    if last_count == 0:
        percent_change = 100 if current_count > 0 else 0
    else:
        percent_change = ((current_count - last_count) / last_count) * 100

    # Determine arrow direction
    arrow_class = 'fa-arrow-up positive' if percent_change >= 0 else 'fa-arrow-down negative'
    percent_display = abs(round(percent_change, 1))
    
    # 1️⃣ Sales (units/orders shipped out)
    sales_total = (
        OrderItem.objects
        .filter(
            order__status__in=['shipped', 'delivered'],
            product__seller=seller_profile
        )
        .aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('price') * F('quantity'),
                    output_field=DecimalField(max_digits=12, decimal_places=2)
                )
            )
        )['total'] or 0
    )
   
    context = {
        'size_choices': SIZE_CHOICES,
        'total_products': total_products,
        'new_products_count': new_products_count,
        'low_stock_products': low_stock_products,
        'low_stock_count': low_stock_products.count(),
        'pending_orders_count': current_count,
        'pending_orders_change': percent_display,
        'pending_orders_arrow': arrow_class,  
        'sales_total': sales_total,
        }
    
    return render(request, 'seller/dashbord.html', context)

def login_error(request):
    return render(request, 'login_error.html', {
        'message': 'This social account is already linked to another user.'
    })


# @login_required
# def seller_details(request):
#     # Only allow users who are not already sellers to submit
#     if request.method == 'POST':
#         # Set user type to seller if not already
#         if request.user.user_type != 'seller':
#             request.user.user_type = 'seller'
#             request.user.save()

#         # Create Address instance
#         address = SellerAddress.objects.create(
#             pin=request.POST.get('pin'),
#             post_office=request.POST.get('post_office'),
#             city=request.POST.get('city'),
#             state=request.POST.get('state'),
#             country=request.POST.get('country'),
#             extra_details=request.POST.get('extra_details', '')
#         )
        
#         # Create SellerProfile with the address
#         seller_profile = SellerProfile.objects.create(
#             user=request.user,
#             address=address,
#             store_name=request.POST.get('store_name'),
#             phone=request.POST.get('phone'),
#             approved=False
#         )
#         #  Send notification to admins (all staff users)
        
#         message_admin = (
#             f"A new seller '{seller_profile.store_name}' has applied for approval.\n\n"
#             f"Review here: {request.build_absolute_uri(f'/admin/clutterapp/sellerprofile/{seller_profile.id}/change/')}"
#         )
#         subject_admin = "New Seller Application"
        
#         admin_emails = list(User.objects.filter(is_staff=True).values_list("email", flat=True))

#         if admin_emails:
#             send_mail(
#                 subject_admin,
#                 message_admin,
#                 settings.DEFAULT_FROM_EMAIL,
#                 admin_emails,
#                 fail_silently=False,
#             )


        
#         messages.success(request, 'Your seller application has been submitted!')
#         return redirect('seller_approval')
    
#     # If user is not a seller yet, show the form
#     if request.user.user_type != 'seller':
#         return render(request, 'seller/seller_details.html')
    
#     # If already a seller, redirect or show a message
#     messages.info(request, 'You are already registered as a seller.')
#     return redirect('seller_dashbord')  # Replace with your desired page


@login_required
def seller_details(request):
    if request.method == 'POST':
        phone = request.POST.get('phone').strip()

        # ✅ Check if phone already exists
        if SellerProfile.objects.filter(phone=phone).exists():
            messages.error(request, "⚠️ This phone number is already registered. Please use another one.", extra_tags="phone_error")
            return redirect('seller_details')

        # Set user type to seller if not already
        if request.user.user_type != 'seller':
            request.user.user_type = 'seller'
            request.user.save()

        # Create Address instance
        address = SellerAddress.objects.create(
            pin=request.POST.get('pin'),
            post_office=request.POST.get('post_office'),
            city=request.POST.get('city'),
            state=request.POST.get('state'),
            country=request.POST.get('country'),
            extra_details=request.POST.get('extra_details', '')
        )

        try:
            # Create SellerProfile with the address
            seller_profile = SellerProfile.objects.create(
                user=request.user,
                address=address,
                store_name=request.POST.get('store_name'),
                phone=phone,
                approved=False
            )
        except IntegrityError:
            messages.error(request, "⚠️ Could not create profile. Try again with a different phone number.", extra_tags="phone_error")
            return redirect('seller_details')

        # Notify admins
        message_admin = (
            f"A new seller '{seller_profile.store_name}' has applied for approval.\n\n"
            f"Review here: {request.build_absolute_uri(f'/admin/clutterapp/sellerprofile/{seller_profile.id}/change/')}"
        )
        subject_admin = "New Seller Application"
        admin_emails = list(User.objects.filter(is_staff=True).values_list("email", flat=True))

        if admin_emails:
            send_mail(
                subject_admin,
                message_admin,
                settings.DEFAULT_FROM_EMAIL,
                admin_emails,
                fail_silently=False,
            )

        messages.success(request, '✅ Your seller application has been submitted!')
        return redirect('seller_approval')

    if request.user.user_type != 'seller':
        return render(request, 'seller/seller_details.html')

    messages.info(request, 'You are already registered as a seller.')
    return redirect('seller_dashbord')

@login_required
def change_profile(request, profile_id):
    profile = get_object_or_404(SellerProfile, id=profile_id)

    if request.method == "POST":
        store_name = request.POST.get("store_name", "").strip()
        phone = request.POST.get("phone", "").strip()

        # ✅ Check duplicate phone
        if phone:
            exists = SellerProfile.objects.filter(phone=phone).exclude(id=profile.id).exists()
            if exists:
                messages.error(
                    request,
                    "⚠️ This phone number is already in use. Please enter another one.",
                    extra_tags="phone_error"
                )
                return redirect("change_profile", profile_id=profile.id)  # redirect back to form

            profile.phone = phone

        # update other fields
        profile.store_name = store_name
        profile.save()

        messages.success(request, "✅ Profile updated successfully!")
        return redirect("seller_dashbord")  

    return render(request, "seller/change_profile.html", {"tt": profile})

@login_required
def change_address(request, address_id):
    address = get_object_or_404(SellerAddress, id=address_id)
    
    if request.method == 'POST':
        address.pin = request.POST.get('pin')
        address.post_office = request.POST.get('post_office')
        address.city = request.POST.get('city')
        address.state = request.POST.get('state')
        address.country = request.POST.get('country')
        address.extra_details = request.POST.get('extra_details', '')
        address.save()
        # messages.success(request, 'Address updated successfully!')
        return redirect('seller_dashbord')  # or wherever you want to redirect

    return render(request, 'seller/edit_address.html', {'address': address})


@login_required
def seller_inventory(request):
    user = request.user
     # or show error

    seller_profile = user.seller_profile
    products = Product.objects.filter(seller=seller_profile).prefetch_related('images', 'variants')
    
    low_stock_count = Product.objects.filter(
        seller=seller_profile,
        stock_quantity__lte=5
    ).count()

    for product in products:
        product.total_stock = sum(variant.stock for variant in product.variants.all())

    context = {
        'size_choices': SIZE_CHOICES,
        'products': products,
        'low_stock_count': low_stock_count
    }

    
    return render(request, 'seller/inventory.html',context)

def export_inventory_pdf(request):
    # Create the HttpResponse object with PDF headers.
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="inventory.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # Title
    elements.append(Paragraph("Seller Inventory Report", styles['Title']))
    elements.append(Spacer(1, 12))

    # Table data
    data = [["Product ID", "Name", "Stock", "Status"]]
    products = Product.objects.all()

    for p in products:
        if p.stock_quantity == 0:
            status = "Sold Out"
        elif p.stock_quantity <= 2:
            status = "Very Low"
        elif p.stock_quantity <= 5:
            status = "Low Stock"
        else:
            status = "Available"

        data.append([f"PROD-{p.id}", p.name, str(p.stock_quantity), status])

    # Build table
    table = Table(data, colWidths=[80, 200, 80, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
    ]))

    elements.append(table)
    doc.build(elements)

    return response

@login_required
def seller_products(request):
    user = request.user
      # or show error

    seller_profile = user.seller_profile  #

    products = Product.objects.filter(seller=seller_profile).prefetch_related('images', 'variants')
    for product in products:
        product.total_stock = sum(variant.stock for variant in product.variants.all())
        
    today = timezone.now().date()
    active_flat_sales = FlatSale.objects.filter(
        products__seller=seller_profile,
        
    ).distinct()
    category_choices = ProductCategory.objects.all()
    subcategory_choices = SubCategory.objects.all()
    subsubcategories = SubSubCategory.objects.all()


    context = {
        'size_choices': SIZE_CHOICES,
        'products': products,
        'active_flat_sales': active_flat_sales,
        'category_choices': category_choices,
        'subcategory_choices': subcategory_choices,
        'subsubcategories': subsubcategories,
        
    }
    return render(request, 'seller/products.html',context)

@login_required
def seller_orders(request):
    seller_profile = request.user.seller_profile  # seller profile
    orders = Order.objects.filter(
        items__product__seller=seller_profile
    ).distinct().order_by("-created_at")

    return render(request, "seller/order.html", {"orders": orders})

@login_required
def seller_order_detail(request, order_id):
    seller_profile = request.user.seller_profile
    order = get_object_or_404(Order, id=order_id)

    # Only include items from this seller
    seller_items = order.items.filter(product__seller=seller_profile)

    if not seller_items.exists():
        raise Http404("No items for you in this order")

    # Calculate totals
    total_quantity = sum(item.quantity for item in seller_items)
    total_revenue = sum(item.total_price for item in seller_items)

    return render(request, "seller/order_detail.html", {
        "order": order,
        "seller_items": seller_items,
        "total_quantity": total_quantity,
        "total_revenue": total_revenue,
    })


@login_required
def seller_update_shipping(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.method == "POST":
        tracking_number = request.POST.get("tracking_number")
        courier_name = request.POST.get("courier_name")
        status = request.POST.get("status")

        # save in the Order model
        order.tracking_number = tracking_number
        order.courier_name = courier_name
        order.status = status
        order.save()

        # ✅ send email to buyer
        subject = f"Clutter&Co — Your Order #{order.id} Has Shipped!"
        message = (
            f"Hello {order.shipping_name},\n\n"
            f"We’re excited to let you know that your order #{order.id} has been shipped!\n\n"
            f"📦 Status: {status}\n"
            f"🚚 Courier: {courier_name}\n"
            f"🔎 Tracking Number: {tracking_number}\n\n"
            f"You can track your shipment directly on the courier’s website using the tracking number above.\n\n"
            f"Thank you for choosing Clutter&Co. We hope you enjoy your purchase!\n\n"
            f"Warm regards,\n"
            f"The Clutter&Co Team"
        )
        recipient = order.buyer.user.email  # assuming AccountProfile → user → email

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=False,
        )

        return redirect("seller_orders")  # back to seller's order list

    return render(request, "seller/update_shipping.html", {"order": order})




@login_required
def seller_report(request):
    # Get the current seller
    seller = request.user.seller_profile

    # Get orders that include products belonging to this seller
    seller_orders = Order.objects.filter(
        items__product__seller=seller
    ).distinct()  # distinct to avoid duplicates if order has multiple products

    # Count orders by status
    order_status_counts = seller_orders.values('status').annotate(count=Count('id'))
    status_data = {status['status']: status['count'] for status in order_status_counts}

    # Total sales from delivered orders
    delivered_orders = seller_orders.filter(status='delivered')
    delivered_sales = sum([order.total_after_discount for order in delivered_orders], Decimal('0.00'))

    return render(request, 'seller/report.html', {
        'status_data': status_data,
        'delivered_sales': delivered_sales,
    })



@login_required
def export_products_pdf(request):
    user = request.user
    

    seller_profile = user.seller_profile
    products = Product.objects.filter(seller=seller_profile).prefetch_related('variants')

    # Create HTTP response with PDF headers
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="products.pdf"'

    # Set up PDF document
    doc = SimpleDocTemplate(response, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Product List", styles['Heading1']))
    elements.append(Spacer(1, 12))

    # Table data
    data = [['Product Name', 'Category', 'Total Stock', 'Created At']]
    for product in products:
        total_stock = sum(v.stock for v in product.variants.all())
        data.append([
            product.name,
            f"{product.category} / {product.subcategory}",
            str(total_stock),
            product.created_at.strftime('%Y-%m-%d'),
        ])

    # Table styling
    table = Table(data, hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))

    elements.append(table)
    doc.build(elements)

    return response

@login_required
def add_product(request):
    user = request.user
    seller_profile = user.seller_profile

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            # Create the product but don't commit yet
            product = form.save(commit=False)
            product.seller = seller_profile
            product.save()

            # Handle images (max 5)
            for i in range(1, 6):
                image = request.FILES.get(f'image{i}')
                if image:
                    ProductImage.objects.create(product=product, image=image)

            # Track variant stocks
            variant_stocks = []
            for size_code, _ in SIZE_CHOICES:
                stock_val = request.POST.get(f'stock_{size_code}')
                if stock_val:
                    try:
                        stock_int = int(stock_val)
                        ProductVariant.objects.create(
                            product=product,
                            size=size_code,
                            stock=stock_int
                        )
                        variant_stocks.append(stock_int)
                    except Exception as e:
                        print(f"Error adding variant for {size_code}: {e}")

            # If variants exist → set product stock as sum of variant stocks
            if variant_stocks:
                product.stock_quantity = sum(variant_stocks)
                product.save(update_fields=["stock_quantity"])

            return redirect('seller_products')
    else:
        form = ProductForm()

    # Prepare choices for template
    category_choices = ProductCategory.objects.all()
    subcategory_choices = SubCategory.objects.all()

    return render(request, 'seller/products.html', {
        'form': form,
        'size_choices': SIZE_CHOICES,
        'category_choices': category_choices,
        'subcategory_choices': subcategory_choices,
    })

@login_required
def add_flat_sale(request):
    user = request.user

    seller = user.seller_profile
    products = Product.objects.filter(seller=seller)

    if request.method == 'POST':
        product_ids = request.POST.getlist('products')
        discount_type = request.POST.get('discount_type')
        discount_value = request.POST.get('discount_value')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        event_banner = request.FILES.get('event_banner')
        event_name = request.POST.get('event_name')

        if not product_ids or not discount_value or not start_date or not end_date or not event_banner or not event_name:
            return render(request, 'seller/products.html', {
                'error': 'All fields are required',
                'products': products,
            })

        flat_sale = FlatSale.objects.create(
            discount_type=discount_type,
            discount_value=discount_value,
            start_date=start_date,
            end_date=end_date,
            event_banner=event_banner,
            event_name=event_name,
            approved=False  # ✅ Needs admin approval

        )
        flat_sale.products.set(Product.objects.filter(id__in=product_ids))
        flat_sale.save()

       # ✅ Send notification to admins (all staff users)
        admin_users = CustomUser.objects.filter(is_staff=True)
        for admin in admin_users:
            Notification.objects.create(
                user=admin,
                message=f"Seller '{seller.store_name}' created a new flat sale: {flat_sale.event_name}",
                link=f"/admin/clutterapp/flatsale/{flat_sale.id}/change/"
            )

        # ✅ Send email to all staff users
        recipient_emails = admin_users.values_list('email', flat=True)
        send_mail(
            subject="New Flat Sale Created",
            message=f"Seller '{seller.store_name}' created a flat sale '{flat_sale.event_name}'.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=list(recipient_emails),
            fail_silently=True
        )

        return redirect('seller_products')

    return render(request, 'seller/products.html', {
        'products': products,
    })

@login_required
def edit_flat_sale(request, sale_id):
    flat_sale = get_object_or_404(FlatSale, id=sale_id)

    if flat_sale.created_by_admin:
        return HttpResponseForbidden("You can't edit admin-created flat sales.")
    user = request.user
  

    flat_sale = get_object_or_404(FlatSale, id=sale_id)

    # Make sure seller owns the products in the sale
    if not flat_sale.products.filter(seller=user.seller_profile).exists():
        return redirect('not_authorized')

    seller = user.seller_profile
    products = Product.objects.filter(seller=seller)

    if request.method == 'POST':
        product_ids = request.POST.getlist('products')
        flat_sale.discount_type = request.POST.get('discount_type')
        flat_sale.discount_value = request.POST.get('discount_value')
        flat_sale.start_date = request.POST.get('start_date')
        flat_sale.end_date = request.POST.get('end_date')
        flat_sale.event_name = request.POST.get('event_name')

        if 'event_banner' in request.FILES:
            flat_sale.event_banner = request.FILES['event_banner']

        flat_sale.save()
        flat_sale.products.set(Product.objects.filter(id__in=product_ids))

        return redirect('seller_products')

    return render(request, 'seller/edit_flat_sale.html', {
        'flat_sale': flat_sale,
        'products': products,
    })


@login_required
def delete_flat_sale(request, sale_id):


    sale = get_object_or_404(FlatSale, id=sale_id)
    if not sale.products.filter(seller=request.user.seller_profile).exists():
        return redirect('not_authorized')

    sale.delete()
    return redirect('seller_products')

@login_required
def change_profile_picture(request):
    if request.method == "POST" and request.FILES.get("picture"):
        request.user.picture = request.FILES["picture"]
        request.user.save()
    return redirect("seller_dashbord")  # or wherever you want to go
#PRODUCT VIEW/EDIT/DELETE#######################################################################################
@login_required
def product_view(request, product_id):
    product = get_object_or_404(Product.objects.prefetch_related('images', 'variants'), id=product_id)

    total_stock = sum(variant.stock for variant in product.variants.all())

    context = {
        'product': product,
        'variants': product.variants.all(),
        'images': product.images.all(),
        'total_stock': total_stock,
    }
    return render(request, 'seller/product_view.html', context)

@login_required
def product_edit(request, product_id):
    seller_profile = get_object_or_404(SellerProfile, user=request.user)
    
    # Ensure seller only edits their own product
    product = get_object_or_404(Product, id=product_id, seller=seller_profile)
    
    VariantFormSet = modelformset_factory(
        ProductVariant, 
        form=ProductVariantForm, 
        extra=1, 
        can_delete=True
    )
    ImageFormSet = modelformset_factory(
        ProductImage, 
        form=ProductImageForm, 
        extra=1, 
        can_delete=True,
        fields=('image',)
    )

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        variant_formset = VariantFormSet(
            request.POST, 
            prefix='variants',
            queryset=product.variants.all()
        )
        image_formset = ImageFormSet(
            request.POST, 
            request.FILES, 
            prefix='images',
            queryset=product.images.all()
        )

        if form.is_valid() and variant_formset.is_valid() and image_formset.is_valid():
            product = form.save(commit=False)
            product.seller = seller_profile
            product.save()
            
            # Save variants
            variants = variant_formset.save(commit=False)
            for variant in variants:
                variant.product = product
                variant.save()
            for variant in variant_formset.deleted_objects:
                variant.delete()
            
            # Save images
            images = image_formset.save(commit=False)
            for image in images:
                image.product = product
                image.save()
            for image in image_formset.deleted_objects:
                image.delete()

            # 🔹 Stock logic (SAME as add_product)
            if product.variants.exists():
                # Sum of all variants
                total_stock = product.variants.aggregate(total=models.Sum("stock"))["total"] or 0
                product.stock_quantity = total_stock
            # else → use the stock_quantity from form as-is
            product.save(update_fields=["stock_quantity"])

            return redirect('seller_products')

    else:
        form = ProductForm(instance=product)
        variant_formset = VariantFormSet(
            prefix='variants',
            queryset=product.variants.all()
        )
        image_formset = ImageFormSet(
            prefix='images',
            queryset=product.images.all()
        )

    context = {
        'form': form,
        'variant_formset': variant_formset,
        'image_formset': image_formset,
        'product': product,
        'user': request.user,
    }
    return render(request, 'seller/product_edit.html', context)


@login_required
def delete_product(request, product_id):
    # Get the product and verify it belongs to the current seller
    product = get_object_or_404(Product, id=product_id, seller=request.user.seller_profile)
    
    if request.method == 'POST':
        # Delete the product (this will cascade to variants and images)
        product.delete()
        messages.success(request, 'Product deleted successfully')
        return redirect('seller_products')
    
    # If not POST, redirect back to product view
    return redirect('product_view', product_id=product_id)




# End of seller views###################################################################################

#user views#############################################################################################

def homepage(request):
    show_popup = False

    if request.user.is_authenticated:
        try:
            profile = request.user.account_profile
        except AccountProfile.DoesNotExist:
            show_popup = True
            
    user = request.user
    buyer_profile = None
    addresses = []

    if user.is_authenticated:
        try:
            buyer_profile = AccountProfile.objects.get(user=user)
            addresses = buyer_profile.addresses.all()
        except AccountProfile.DoesNotExist:
            buyer_profile = None
            addresses = []

    today = timezone.now().date()
    flat_sales = FlatSale.objects.filter(start_date__lte=today, end_date__gte=today)
    featured_products = Product.objects.filter(is_featured=True)[:6]

    return render(request, 'user/homepage.html', {
        'featured_products': featured_products,
        'flat_sales': flat_sales,
        'buyer_profile': buyer_profile,
        'addresses': addresses,
        'show_popup': show_popup,
    })

def sellerwindow(request):
   
    return render(request,'user/sellerwindow.html')

def product_details(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    reviews = product.reviews.all()

    total_reviews = reviews.count()
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0

    has_purchased = False
    if request.user.is_authenticated and request.user.user_type == "customer":
        has_purchased = OrderItem.objects.filter(
            order__buyer=request.user.account_profile,
            product=product,
            order__status="delivered"
        ).exists()
    context = {
        'user': request.user,  # Ensure user is in context
        'product' : Product.objects.get(pk=pk),
        'reviews': ProductReview.objects.filter(product_id=pk).select_related('user').order_by('-created_at'),
        "has_purchased": has_purchased,
        "reviews": reviews,
        "total_reviews": total_reviews,
        "avg_rating": round(avg_rating, 1),  # 2.7
    }
    return render(request, 'user/product_details.html',context)


def store_detail(request, pk):
    seller = get_object_or_404(SellerProfile, pk=pk)
    products = Product.objects.filter(seller=seller)

    return render(request, "user/store_detail.html", {
        "seller": seller,
        "products": products,
    })

def shopnow(request):
    products=Product.objects.all()
    return render (request,'user/shopnow.html',{'products':products})



def flat_product_list(request):
    today = timezone.now().date()
    products = Product.objects.prefetch_related('flat_sales')

    product_data = []

    for product in products:
        active_sales = product.flat_sales.filter(
            start_date__lte=today,
            end_date__gte=today
        )

        # Apply the highest/first applicable discount
        if active_sales.exists():
            sale = active_sales.first()
            discounted_price = sale.get_discounted_price(product.price)
        else:
            sale = None
            discounted_price = None

        product_data.append({
            'product': product,
            'discounted_price': discounted_price,
            'active_sale': sale,
        })

    return render(request, 'user/flat_product.html', {
        'product_data': product_data
    })

     


#buyer profile view/edit#############################################################################################
# @login_required
# def buyerprofile(request):
#     user = request.user

#     # Get or create BuyerProfile for the user
#     buyer_profile, created = AccountProfile.objects.get_or_create(user=user)

#     if request.method == "POST":
#         # --- Update User fields ---
#         name = request.POST.get("name")
#         if name:
#             user.name = name
#         user.save()

#         # --- Update BuyerProfile fields safely ---
#         phone = request.POST.get("phone")
#         dob = request.POST.get("dob")
#         gender = request.POST.get("gender")

#         if phone.strip():  # Only update if not blank
#             buyer_profile.phone = phone
#         else:
#             buyer_profile.phone = None  # Optional field

#         if dob:
#             buyer_profile.dob = dob
#         else:
#             buyer_profile.dob = None

#         if gender:
#             buyer_profile.gender = gender
#         else:
#             buyer_profile.gender = None

#         # --- Handle profile picture ---
#         picture = request.FILES.get("picture")
#         remove_picture = request.POST.get("picture-clear")

#         if remove_picture:
#             if user.picture:
#                 user.picture.delete(save=False)
#             user.picture = None
#         elif picture:
#             user.picture = picture

#         # Save profile
#         buyer_profile.save()
#         user.save()

#         messages.success(request, "Profile updated successfully!")
#         return redirect("buyerprofile")  # Prevent form resubmission

#     # GET request: render profile page
#     return render(request, "user/buyerprofile.html", {
#         "user": user,
#         "buyer_profile": buyer_profile
#     })

@login_required
def buyerprofile(request):
    user = request.user
    buyer_profile, created = AccountProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        name = request.POST.get("name")
        if name:
            user.name = name

        phone = request.POST.get("phone")
        dob = request.POST.get("dob")
        gender = request.POST.get("gender")

        # ✅ Check duplicate before saving
        if phone and phone.strip():
            phone = phone.strip()
            exists = AccountProfile.objects.filter(phone=phone).exclude(user=user).exists()

            if exists:
                messages.error(request, "⚠️ This phone number is already in use. Please enter another one.", extra_tags="phone_error")
                return redirect("buyerprofile")  # stop here, no save

            buyer_profile.phone = phone
        else:
            buyer_profile.phone = None

        buyer_profile.dob = dob if dob else None
        buyer_profile.gender = gender if gender else None

        picture = request.FILES.get("picture")
        remove_picture = request.POST.get("picture-clear")

        if remove_picture:
            if user.picture:
                user.picture.delete(save=False)
            user.picture = None
        elif picture:
            user.picture = picture

        try:
            buyer_profile.save()
            user.save()
            messages.success(request, "Profile updated successfully!")
        except IntegrityError:
            # extra safety net
            messages.error(request, "Something went wrong. Try again with another phone number.", extra_tags="phone_error")

        return redirect("buyerprofile")

    return render(request, "user/buyerprofile.html", {
        "user": user,
        "buyer_profile": buyer_profile
    })
    
@login_required
def address_list(request):
    user = request.user
    buyer_profile, _ = AccountProfile.objects.get_or_create(user=user)

    # Get all addresses of this buyer
    addresses = buyer_profile.addresses.all()

    return render(request, 'user/address.html', {
        'buyer_profile': buyer_profile,
        'addresses': addresses
    })
    
    

@login_required
def save_address(request):
    user = request.user
    buyer_profile, _ = AccountProfile.objects.get_or_create(user=user)
    

    if request.method == "POST":
        address_id = request.POST.get("address_id")  # hidden field
        address_type = request.POST.get("address_type")
        pin = request.POST.get("pin")
        post_office = request.POST.get("post_office")
        city = request.POST.get("city")
        state = request.POST.get("state")
        country = request.POST.get("country")
        extra_details = request.POST.get("extra_details")

        if address_id:  
            # ✅ Update existing address
            address = get_object_or_404(UserAddress, id=address_id, buyer=buyer_profile)
            address.address_type = address_type
            address.pin = pin
            address.post_office = post_office
            address.city = city
            address.state = state
            address.country = country
            address.extra_details = extra_details
            address.save()
            messages.success(request, "Address updated successfully!")
        else:
            # ✅ Create new address
            UserAddress.objects.create(
                buyer=buyer_profile,
                address_type=address_type,
                pin=pin,
                post_office=post_office,
                city=city,
                state=state,
                country=country,
                extra_details=extra_details,
            )
            messages.success(request, "Address added successfully!")

        return redirect("address_list")  # go back to address list page

    return redirect("address_list")


@login_required
def delete_address(request, address_id):
    user = request.user
    buyer_profile, _ = AccountProfile.objects.get_or_create(user=user)

    address = get_object_or_404(UserAddress, id=address_id, buyer=buyer_profile)
    address.delete()
    messages.success(request, "Address deleted successfully!")

    return redirect("address_list")


@login_required
def save_current_location(request):
    user = request.user
    buyer_profile, _ = AccountProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        latitude = request.POST.get("latitude")
        longitude = request.POST.get("longitude")

        # Reverse geocoding using OpenStreetMap Nominatim API
        try:
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}"
            response = requests.get(url, headers={"User-Agent": "YourAppName"})
            data = response.json()

            # Extract address parts safely
            address_data = data.get("address", {})
            pin = address_data.get("postcode", "")
            city = address_data.get("city", address_data.get("town", address_data.get("village", "")))
            state = address_data.get("state", "")
            country = address_data.get("country", "")
            post_office = address_data.get("suburb", "")
            extra_details = data.get("display_name", "")

            # Save address
            UserAddress.objects.create(
                buyer=buyer_profile,
                address_type="home",
                pin=pin,
                post_office=post_office,
                city=city,
                state=state,
                country=country,
                extra_details=extra_details,
                latitude=latitude,
                longitude=longitude,
                is_current_location=True,
            )

            return JsonResponse({"success": True, "message": "Current location saved successfully!"})

        except Exception as e:
            return JsonResponse({"success": False, "message": f"Error fetching location: {str(e)}"})

    return JsonResponse({"success": False, "message": "Invalid request"})

@login_required
def wishlist(request):
    user_profile = request.user.account_profile
    
    # Get all wishlist items for the user
    wishlist_items = Wishlist.objects.filter(user=user_profile, is_active=True).select_related('product')

    return render(request, 'user/wishlist.html', {'wishlist_items': wishlist_items})

@login_required
def my_orders(request):
    orders = Order.objects.filter(buyer=request.user.account_profile).prefetch_related("items__product", "items__variant").order_by("-created_at")

    context = {
        "orders": orders
    }
    return render(request, "user/my_orders.html", context)


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, buyer=request.user.account_profile)

    return render(request, "user/order_detail.html", {
        "order": order
    })




@login_required
def mycoins(request):   
    # Fetch all transactions for the logged in user
    transactions = CoinTransaction.objects.filter(user=request.user).order_by('-date')
    
    # Calculate balance
    balance = transactions.aggregate(total=Sum('amount'))['total'] or 0
    buyer_profile = AccountProfile.objects.get(user=request.user)
    total_coins = buyer_profile.coins

    site_config = SiteConfig.objects.last()  # assuming you keep only one row
    coin_value = site_config.coin_value if site_config else 1  

    # Convert coins into currency
    coin_worth = total_coins * coin_value
     

    return render(request, 'user/mycoins.html', {
        'coin_transactions': transactions,
        'user_coin_balance': balance,
        'total_coins': total_coins,
        'coin_worth': coin_worth,   # send worth to template

    })
    
#declutter view#############################################################################################

def declutter_window(request):
    return render(request, 'user/declutter_window.html')


User = get_user_model()



@login_required
def declutter_page(request):
    buyer_profile, _ = AccountProfile.objects.get_or_create(user=request.user)
    addresses = buyer_profile.addresses.all()

    # Serialize addresses for frontend usage
    addresses_json = json.dumps([
        {
            "id": addr.id,
            "type": addr.get_address_type_display(),
            "full_address": f"{addr.post_office}, {addr.city}, {addr.state}, {addr.country} - {addr.pin}",
            "pin": addr.pin,
            "city": addr.city,
            "state": addr.state,
            "country": addr.country
        }
        for addr in addresses
    ])

    if request.method == "POST":
        form = DeclutterRequestForm(request.POST, request.FILES)

        if form.is_valid():
            # Process pickup address
            address_id = request.POST.get("pickup_address")
            if address_id:
                address_obj = get_object_or_404(UserAddress, id=address_id, buyer=buyer_profile)
                pickup_address_text = (
                    f"{address_obj.get_address_type_display()} - {address_obj.post_office}, "
                    f"{address_obj.city}, {address_obj.state}, {address_obj.country} - {address_obj.pin}"
                )
            else:
                pickup_address_text = ""

            # Save declutter request
            declutter_request = form.save(commit=False)
            declutter_request.user = request.user
            declutter_request.pickup_address = pickup_address_text
            declutter_request.save()

            # Handle multiple image uploads
            item_images = request.FILES.getlist("item_images")
            for item_image in item_images:
                DeclutterImage.objects.create(request=declutter_request, image=item_image)

            # ---------------- EMAILS ----------------

            # User email
            user_name = request.user.name
            subject_user = "Your Declutter Request is Received"
            message_user = (
                f"Hi {user_name},\n\n"
                f"Your declutter request has been successfully submitted.\n"
                f"We will contact you soon regarding the pickup.\n\n"
                f"Thank you for using our service."
            )
            send_mail(
                subject_user,
                message_user,
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],  # Only the user
                fail_silently=False,
            )

            # Admin email
            subject_admin = f"New Declutter Request from {user_name}"
            message_admin = f"""
            New Declutter Request Submitted:

            User: {user_name} ({request.user.email})
            Phone: {declutter_request.mobile_number}

            Pickup Address:
            {declutter_request.pickup_address}

            Preferred Date & Time: {declutter_request.preferred_date} {declutter_request.preferred_time}

            Item Condition: {declutter_request.item_condition}
            Non-wearable Reason: {declutter_request.non_wearable_reason or '-'}

            Wearable Types: {', '.join(declutter_request.wearable_types or [])}
            Color Category: {declutter_request.color_category}
            Material Type: {declutter_request.material_type}
            """

            admin_emails = list(User.objects.filter(is_staff=True).values_list("email", flat=True))
            if admin_emails:
                # ✅ Removed fail_silently here
                email = EmailMessage(
                    subject=subject_admin,
                    body=message_admin.strip(),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=admin_emails,  # Only admins
                )

                # Attach all images from this request
                for img in declutter_request.images.all():
                    email.attach_file(img.image.path)

                # ✅ Use fail_silently here, not in constructor
                email.send(fail_silently=False)

            # Success message
            messages.success(request, "Declutter request submitted successfully! A confirmation email has been sent.")
            return redirect("declutter_window")

    else:
        form = DeclutterRequestForm()

    return render(request, "user/declutter.html", {
        "user": request.user,
        "buyer_profile": buyer_profile,
        "addresses": addresses,
        "addresses_json": addresses_json,
        "form": form,
    })
    
def chart_test_view(request):
    return render(request, 'chart_test.html')




def add_to_wishlist(request, product_id):
    # Get the logged-in user's profile
    user_profile = request.user.account_profile
    
    # Get the product to be added
    product = get_object_or_404(Product, id=product_id)
    
    # Check if the product is already in the user's wishlist
    wishlist_item, created = Wishlist.objects.get_or_create(user=user_profile, product=product)
    
    if created:
        return HttpResponse("Product added to wishlist", status=200)
    else:
        return HttpResponse("Product is already in your wishlist", status=400)
    

def remove_from_wishlist(request, product_id):
    user_profile = request.user.account_profile
    product = get_object_or_404(Product, id=product_id)

    try:
        # Remove the item from the wishlist
        wishlist_item = Wishlist.objects.get(user=user_profile, product=product)
        wishlist_item.delete()
        return HttpResponse("Product removed from wishlist", status=200)
    except Wishlist.DoesNotExist:
        return HttpResponse("Product not found in your wishlist", status=404)
    
    
#Cart view#############################################################################################
@login_required
def cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related('product', 'variant').all()

    # Subtotal = total of discounted prices * qty
    subtotal = sum(item.discounted_price * item.quantity for item in cart_items)
    
    #actual amount before discount
    original_total = sum(item.original_price * item.quantity for item in cart_items)

    # Example delivery charge rule
    delivery_charge = 50 if subtotal < 500 else 0

    # Discount = (original - discounted) * qty
    discount = sum((item.original_price - item.discounted_price) * item.quantity for item in cart_items)

    # Total = subtotal + delivery charge
    # (no need to minus discount because subtotal is already discounted)
    total = subtotal + delivery_charge

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'delivery_charge': delivery_charge,
        'discount': discount,
        'total': total,
        'original_total': original_total,
    }
    return render(request, 'user/cart.html', context)



@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    variant_id = request.POST.get('variant_id')

    # ✅ safe quantity parsing
    raw_quantity = request.POST.get("quantity")
    try:
        quantity = int(raw_quantity) if raw_quantity and raw_quantity.isdigit() else 1
    except ValueError:
        quantity = 1

    variant = None
    if variant_id:
        variant = get_object_or_404(ProductVariant, id=variant_id, product=product)

    cart, _ = Cart.objects.get_or_create(user=request.user)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        variant=variant,
        defaults={'quantity': quantity}
    )

    if not created:
        cart_item.quantity += quantity
        cart_item.save()

    messages.success(request, f"{product.name} added to cart!")
    return redirect('cart')

@login_required
def update_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "increase":
            cart_item.quantity += 1
            cart_item.save()
        elif action == "decrease":
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                cart_item.delete()  # remove item if it goes to 0

    return redirect("cart")  # back to cart page



@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    print("Removing item:", item_id, request.user)

    cart_item.delete()
    messages.success(request, "Item removed from cart!")
    return redirect('cart')

@login_required
def save_for_later(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    profile = request.user.account_profile

    # Remove from cart
    request.user.cart.items.filter(product=product).delete()

    # Add to wishlist if not already
    Wishlist.objects.get_or_create(user=profile, product=product)

    return redirect("cart")  # back to cart

@login_required
def buy_now(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    raw_quantity = request.POST.get("quantity")
    try:
        quantity = int(raw_quantity) if raw_quantity and raw_quantity.isdigit() else 1
    except ValueError:
        quantity = 1

    variant_id = request.POST.get("variant_id")
    variant = get_object_or_404(ProductVariant, id=variant_id, product=product) if variant_id else None

    with transaction.atomic():
        order = Order.objects.create(
            buyer=request.user.account_profile,
            shipping_name="",
            shipping_phone="",
            shipping_address_type="home",
            shipping_pin="",
            shipping_post_office="",
            shipping_city="",
            shipping_state="",
            shipping_country="",
        )

        final_price = variant.get_final_price() if variant else product.get_final_price()

        # ✅ Create item but DO NOT deduct stock here
        OrderItem.objects.create(
            order=order,
            product=product,
            variant=variant,
            quantity=quantity,
            price=final_price,
        )


    return redirect("checkout_page", order_id=order.id)


# @login_required
# def checkout_page(request, order_id):
#     order = get_object_or_404(Order, id=order_id, buyer=request.user.account_profile)
#     addresses = request.user.account_profile.addresses.all()
#     site_config = SiteConfig.objects.first()
#     coin_value = Decimal(site_config.coin_value) if site_config else Decimal("1.0")

#     user_profile = request.user.account_profile
#     max_allowed_coins = sum(item.product.coin_discount for item in order.items.all())

#     if request.method == "POST":
#         if "apply_coins" in request.POST:
#             coins_requested = int(request.POST.get("coins_used", 0))

#             # ✅ Clamp to limits
#             coins_requested = min(coins_requested, user_profile.coins, max_allowed_coins)

#             order.coins_used = coins_requested
#             order.save(update_fields=["coins_used"])

#             messages.success(request, f"{coins_requested} coins applied to order.")
#             return redirect("checkout_page", order_id=order.id)


#         payment_method = request.POST.get("payment_method", "cod")

#         if payment_method == "cod":
#             with transaction.atomic():
#                 order.deduct_stock()

#                 # ✅ Deduct coins in transaction
#                 if order.coins_used > 0:
#                     CoinTransaction.objects.create(
#                         user=request.user,
#                         description=f"Redeemed for Order #{order.id}",
#                         amount=-order.coins_used
#                     )

#                 order.status = "paid"
#                 order.save()
#                 # ✅ send email to buyer
#                 subject = f"Clutter&Co — Your Order #{order.id} Has Recived!"
#                 message = (
#                         f"Hello {order.shipping_name},\n\n"
#                         f"Thank you for shopping with Clutter&Co! 🎉\n\n"
#                         f"We’ve received your order #{order.id} and it’s now being processed.\n\n"
#                         f"🛒 Order Summary:\n"
#                         f" 🔢 Order Number: {order.id}\n"
#                         f" 📅 Order Date: {order.created_at.strftime('%B %d, %Y')}\n"
#                         f" 🚚 Shipping To: {order.shipping_full_address}\n\n"
#                         f"You’ll receive another update as soon as your items are on their way.\n\n"
#                         f"If you have any questions, simply reply to this email and our team will be happy to help.\n\n"
#                         f"Warm regards,\n"
#                         f"The Clutter&Co Team"
#                     )
#                 recipient = order.buyer.user.email  # assuming AccountProfile → user → email

#                 send_mail(
#                     subject,
#                     message,
#                     settings.DEFAULT_FROM_EMAIL,
#                     [recipient],
#                     fail_silently=False,
#                 )
                
#                 # ✅ send email to sellers (one per seller, with their items)
#                 for seller, items in {}.fromkeys([item.product.seller for item in order.items.all()]).items():
#                     # Build seller's item list
#                     seller_items = order.items.filter(product__seller=seller)
#                     item_lines = "\n".join([
#                         f" - {item.quantity} x {item.product.name} @ {item.price} each"
#                         for item in seller_items
#                     ])

#                     subject = f"Clutter&Co — New Order Received (Order #{order.id})"

#                     message = (
#                         f"Hello {seller.store_name},\n\n"
#                         f"Good news! You’ve received a new order on Clutter&Co.\n\n"
#                         f"🛒 Order Details:\n"
#                         f" - Order Number: {order.id}\n"
#                         f" - Buyer: {order.buyer.user.email}\n"
#                         f"     {order.buyer.phone or '-'}\n"
#                         f" - Order Date: {order.created_at.strftime('%B %d, %Y')}\n\n"
#                         f"📦 Items Ordered:\n"
#                         f"{item_lines}\n\n"
#                         f"📍 Shipping Address:\n"
#                         f"{order.shipping_full_address}\n\n"
#                         f"Please prepare these items for shipment. Once you’ve shipped the order, "
#                         f"don’t forget to update the status with courier and tracking details.\n\n"
#                         f"Thank you for selling with Clutter&Co!\n\n"
#                         f"Best regards,\n"
#                         f"The Clutter&Co Team"
#                     )

#                     recipient = seller.user.email  # SellerProfile → user → email
#                     send_mail(
#                         subject,
#                         message,
#                         settings.DEFAULT_FROM_EMAIL,
#                         [recipient],
#                         fail_silently=False,
#                     )


                

#             return redirect("order_success", order_id=order.id)

#         elif payment_method == "online":
#             return redirect("payment_page", order_id=order.id)


#     return render(request, "user/checkout_page.html", {
#         "order": order,
#         "addresses": addresses,
#         "coin_value": coin_value,
#         "user_coins": user_profile.coins,
#         "max_allowed_coins": max_allowed_coins,
#     })


# --- helper ---
def has_sufficient_stock(order):
    """Check if all order items have enough stock before confirming."""
    for item in order.items.select_related("variant", "product"):
        if item.variant:
            if item.variant.stock < item.quantity:
                return False, f"Not enough stock for {item.variant}"
        else:
            if not item.product.stock_quantity or item.product.stock_quantity < item.quantity:
                return False, f"Not enough stock for {item.product}"
    return True, None


@login_required
def checkout_page(request, order_id):
    order = get_object_or_404(Order, id=order_id, buyer=request.user.account_profile)
    addresses = request.user.account_profile.addresses.all()
    site_config = SiteConfig.objects.first()
    coin_value = Decimal(site_config.coin_value) if site_config else Decimal("1.0")

    user_profile = request.user.account_profile
    max_allowed_coins = sum(item.product.coin_discount for item in order.items.all())

    if request.method == "POST":
        if "apply_coins" in request.POST:
            coins_requested = int(request.POST.get("coins_used", 0))
            coins_requested = min(coins_requested, user_profile.coins, max_allowed_coins)

            order.coins_used = coins_requested
            order.save(update_fields=["coins_used"])

            messages.success(request, f"{coins_requested} coins applied to order.")
            return redirect("checkout_page", order_id=order.id)

        payment_method = request.POST.get("payment_method", "cod")

        # ✅ Pre-validate stock before trying to process
        ok, error_msg = has_sufficient_stock(order)
        if not ok:
            messages.error(request, error_msg)
            return redirect("checkout_page", order_id=order.id)

        if payment_method == "cod":
            try:
                with transaction.atomic():
                    order.deduct_stock()

                    # ✅ Deduct coins
                    if order.coins_used > 0:
                        CoinTransaction.objects.create(
                            user=request.user,
                            description=f"Redeemed for Order #{order.id}",
                            amount=-order.coins_used
                        )

                    order.status = "cod_pending"
                    order.save()

                    # ✅ send email to buyer
                    subject = f"Clutter&Co — Your Order #{order.id} Has Recived!"
                    message = (
                        f"Hello {order.shipping_name},\n\n"
                        f"Thank you for shopping with Clutter&Co! 🎉\n\n"
                        f"We’ve received your order #{order.id} and it’s now being processed.\n\n"
                        f"🛒 Order Summary:\n"
                        f" 🔢 Order Number: {order.id}\n"
                        f" 📅 Order Date: {order.created_at.strftime('%B %d, %Y')}\n"
                        f" 🚚 Shipping To: {order.shipping_full_address}\n\n"
                        f"You’ll receive another update as soon as your items are on their way.\n\n"
                        f"If you have any questions, simply reply to this email and our team will be happy to help.\n\n"
                        f"Warm regards,\n"
                        f"The Clutter&Co Team"
                    )
                    recipient = order.buyer.user.email
                    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=False)

                    # ✅ send email to sellers
                    for seller in {item.product.seller for item in order.items.all()}:
                        seller_items = order.items.filter(product__seller=seller)
                        item_lines = "\n".join([
                            f" - {item.variant}x {item.quantity}  @ {item.price} each"
                            for item in seller_items
                        ])

                        subject = f"Clutter&Co — New Order Received (Order #{order.id})"
                        message = (
                            f"Hello {seller.store_name},\n\n"
                            f"Good news! You’ve received a new order on Clutter&Co.\n\n"
                            f"🛒 Order Details:\n"
                            f" - Order Number: {order.id}\n"
                            f" - Buyer: {order.buyer.user.email}\n"
                            f"     {order.buyer.phone or '-'}\n"
                            f" - Order Date: {order.created_at.strftime('%B %d, %Y')}\n\n"
                            f"📦 Items Ordered:\n"
                            f"{item_lines}\n\n"
                            f"📍 Shipping Address:\n"
                            f"{order.shipping_full_address}\n\n"
                            f"Please prepare these items for shipment. Once you’ve shipped the order, "
                            f"don’t forget to update the status with courier and tracking details.\n\n"
                            f"Thank you for selling with Clutter&Co!\n\n"
                            f"Best regards,\n"
                            f"The Clutter&Co Team"
                        )
                        recipient = seller.user.email
                        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=False)

                return redirect("order_success", order_id=order.id)

            except ValueError as e:
                # ✅ Catch stock race condition
                messages.error(request, str(e))
                return redirect("checkout_page", order_id=order.id)

        elif payment_method == "online":
            return redirect("payment_page", order_id=order.id)

    return render(request, "user/checkout_page.html", {
        "order": order,
        "addresses": addresses,
        "coin_value": coin_value,
        "user_coins": user_profile.coins,
        "max_allowed_coins": max_allowed_coins,
    })






@login_required
def checkout_from_cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related('product', 'variant').all()

    if not cart_items.exists():
        return redirect("cart")

    with transaction.atomic():
        order = Order.objects.create(buyer=request.user.account_profile)

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                variant=item.variant,
                quantity=item.quantity,
                price=item.discounted_price  # snapshot price
            )

        # Clear cart only if order was created successfully
    cart_items.delete()

    return redirect("checkout_page", order_id=order.id)

# @login_required
# def update_order_address(request, order_id):
#     """Save selected shipping address snapshot to order"""
#     order = get_object_or_404(Order, id=order_id, buyer=request.user.account_profile)

#     if request.method == "POST":
#         address_id = request.POST.get("address_id")
#         address = UserAddress.objects.filter(buyer=request.user.account_profile, id=address_id).first()

#         if not address:
#             return HttpResponse("Invalid address", status=400)

#         # snapshot shipping info
#         order.shipping_name = request.user.name or request.user.username
#         order.shipping_phone = request.user.account_profile.phone
#         order.shipping_address_type = address.address_type
#         order.shipping_pin = address.pin
#         order.shipping_post_office = address.post_office
#         order.shipping_city = address.city
#         order.shipping_state = address.state
#         order.shipping_country = address.country
#         order.shipping_extra_details = address.extra_details
#         order.save()      
#     return redirect("checkout_page", order_id=order.id)

@login_required
def update_order_address(request, order_id):
    order = get_object_or_404(Order, id=order_id, buyer=request.user.account_profile)

    if request.method == "POST":
        address_id = request.POST.get("address_id")
        address = UserAddress.objects.filter(buyer=request.user.account_profile, id=address_id).first()

        if not address:
            messages.error(request, "Invalid address.", extra_tags="checkout_page")
            return redirect("checkout_page", order_id=order.id)

        # snapshot shipping info
        order.shipping_name = request.user.name or request.user.username
        order.shipping_phone = request.user.account_profile.phone
        order.shipping_address_type = address.address_type
        order.shipping_pin = address.pin
        order.shipping_post_office = address.post_office
        order.shipping_city = address.city
        order.shipping_state = address.state
        order.shipping_country = address.country
        order.shipping_extra_details = address.extra_details
        order.save()

        messages.success(request, "Address saved successfully!", extra_tags="checkout_page")

    return redirect("checkout_page", order_id=order.id)


@login_required
def payment_page(request, order_id):
    order = get_object_or_404(Order, id=order_id, buyer=request.user.account_profile)
    
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    
    # amount in paise (multiply by 100)
    amount = int(order.total_after_discount * 100)
    razorpay_order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": "1"
    })
    
    return render(request, "user/payment_page.html", {
        "order": order,
        "razorpay_order_id": razorpay_order["id"],
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "amount": amount,
    })


@csrf_exempt
def payment_success(request):
    if request.method == "POST":
        data = request.POST
        params_dict = {
            "razorpay_order_id": data.get("razorpay_order_id"),
            "razorpay_payment_id": data.get("razorpay_payment_id"),
            "razorpay_signature": data.get("razorpay_signature")
        }

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        try:
            # Will raise an error if the signature doesn’t match
            client.utility.verify_payment_signature(params_dict)

            # ✅ Signature valid → mark order as paid
            return JsonResponse({"status": "Payment Verified!"})

        except razorpay.errors.SignatureVerificationError:
            # ❌ Invalid signature → possible tampering
            return JsonResponse({"status": "Payment Verification Failed!"}, status=400)

@login_required
def order_success(request, order_id):
    """Order success page"""
    order = get_object_or_404(Order, id=order_id, buyer=request.user.account_profile)
    site_config = SiteConfig.objects.first()
    coin_value = Decimal(site_config.coin_value) if site_config else Decimal("1.0")

    total_coin_discount = order.coins_used * coin_value

    return render(request, "user/order_success.html", {
        "order": order,
        "coin_value": coin_value,
        "total_coin_discount": total_coin_discount,
        "total_paid": order.total_after_discount,
    })    
    
#review submission view#############################################################################################
@login_required
def submit_review(request, product_id):
    if request.method == 'POST':
        rating = int(request.POST.get('rating'))
        comment = request.POST.get('comment', '').strip()
        
        
        if rating < 1 or rating > 5:
            return HttpResponse("Invalid rating", status=400)
        
        product = get_object_or_404(Product, id=product_id)
        user = request.user
        
        # Check if user has purchased this product
        has_purchased = OrderItem.objects.filter(
            order__buyer=request.user.account_profile,
            product=product,
            order__status='delivered'
        ).exists()
        
        if not has_purchased:
            return HttpResponse("You can only review products you have purchased", status=403)
        
        # Create or update review
        review, created = ProductReview.objects.update_or_create(
            user=request.user,
            product=product,
            defaults={'rating': rating, 'comment': comment}
        )
        print("User:", request.user)
        print("Product:", product)
        print("Has purchased:", has_purchased)
        return redirect('product_details',product_id)
    
    return HttpResponse("Invalid request", status=400)


def submit_feedback(request):
    if request.method == "POST":
        product_id = request.POST.get("product_id")
        product = get_object_or_404(Product, id=product_id)

        Feedback.objects.create(
            user=request.user,
            product=product,
            message=request.POST.get("message"),
            image=request.FILES.get("image")  # handle file upload
        )

        messages.success(request, "✅ Your feedback has been submitted and is pending admin approval.")
        return redirect("product_details", product_id)