from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *
from django.utils.html import format_html
from django.utils.safestring import mark_safe
import json
from django.db.models import Sum, F
from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import EmailMessage





# ---------- Custom User Admin ----------
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("email", "klutter_id", "user_type", "is_staff", "is_active","otp", "created_at")
    list_filter = ("user_type", "is_staff", "is_active")
    search_fields = ("email", "klutter_id", "name")
    ordering = ("email",)

    fieldsets = (
        (None, {"fields": ("email", "password", "name", "picture")}),
        ("Permissions", {"fields": ("is_staff", "is_superuser", "is_active", "groups", "user_permissions")}),
        ("User Info", {"fields": ("user_type", "is_new_user", "auth_provider")}),
        ("Tracking", {"fields": ("login_time", "logout_time", "login_status", "ip_address", "device_type", "location")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "is_staff", "is_superuser", "user_type"),
        }),
    )



class UserAddressInline(admin.TabularInline):   # or admin.StackedInline for bigger form
    model = UserAddress
    extra = 0   # don’t show extra empty forms
    fields = ("address_type", "pin", "post_office", "city", "state", "country", "is_current_location")
    readonly_fields = ("latitude", "longitude")  # make lat/lng view-only (if you want)

@admin.register(AccountProfile)
class BuyerProfileAdmin(admin.ModelAdmin):
    list_display = ( "user_email", "phone", "gender", "coins")
    search_fields = ("user__email", "phone")
    list_filter = ("gender",)
    ordering = ("user",)
    inlines = [UserAddressInline]  # ✅ show addresses inline in detail page

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.exclude(user__is_staff=True)

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "Email"



# Optional: make SellerProfile editable inline with SellerAddress
class SellerProfileInline(admin.StackedInline):
    model = SellerProfile
    can_delete = False
    verbose_name_plural = 'Seller Profile'

@admin.register(SellerAddress)
class SellerAddressAdmin(admin.ModelAdmin):
    list_display = ('post_office', 'city', 'state', 'country', 'pin')
    search_fields = ('post_office', 'city', 'state', 'pin')
    inlines = [SellerProfileInline]  # Show linked seller profile inline

@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ('store_name', 'user', 'phone', 'approved')
    list_filter = ('approved',)
    search_fields = ('store_name', 'user__email', 'phone')

    # override save_model to detect approval change
    def save_model(self, request, obj, form, change):
        if change:
            old_obj = SellerProfile.objects.get(pk=obj.pk)
            if not old_obj.approved and obj.approved:  # approved just now
                send_mail(
                    subject="Welcome to Clutter&Co Seller! 🎉",
                    message=(
                        f"Hello {obj.store_name},\n\n"
                        f"Congratulations! Your seller account has been approved.\n\n"
                        f"You can now log in and start selling on Clutter&Co.\n\n"
                        f"Best regards,\n"
                        f"The Clutter&Co Team"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[obj.user.email],
                    fail_silently=True, 
                )
        super().save_model(request, obj, form, change)
    
    

@admin.register(FlatSale)
class FlatSaleAdmin(admin.ModelAdmin):
    list_display = ('event_name', 'discount_type', 'discount_value', 'start_date', 'end_date', 'approved', 'banner_preview')
    list_filter = ('approved', 'start_date', 'end_date', 'discount_type')
    search_fields = ('event_name',)

    readonly_fields = ('banner_preview',)  # Show preview in detail view

    # Display a small clickable banner thumbnail
    def banner_preview(self, obj):
        if obj.event_banner:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="height: 50px;"/></a>',
                obj.event_banner.url,
                obj.event_banner.url
            )
        return "-"
    banner_preview.short_description = "Event Banner"
    

# Unregister the default registration (if it exists)

# Now register with your custom admin
@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    list_display = ("buyer_email", "address_type", "city", "state", "country", "is_current_location")
    search_fields = ("buyer_email","city")

    def buyer_email(self, obj):
        return obj.buyer.user.email  # Access email from CustomUser
    buyer_email.short_description = "Buyer Email"

    fieldsets = (
        (None, {
            "fields": (
                "buyer", "address_type", "pin", "post_office", "city", "state", "country", "extra_details"
            )
        }),
        ("Current Location", {
            "fields": ("latitude", "longitude", "is_current_location", "current_location_map"),
        }),
    )

    readonly_fields = ("current_location_map",)

    def current_location_map(self, obj):
        if obj.is_current_location and obj.latitude and obj.longitude:
            return format_html(
                '<iframe width="100%" height="300" frameborder="0" style="border:0" '
                'src="https://www.google.com/maps?q={},{}&output=embed" allowfullscreen>'
                '</iframe>',
                obj.latitude,
                obj.longitude
            )
        return "No current location saved"

    current_location_map.short_description = "Current Location Map"


# Inline for Product Images
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1  # number of empty forms to show

# Admin for Product

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)
    search_fields = ('name',)

@admin.register(SubSubCategory)
class SubSubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'subcategory', 'get_category')
    list_filter = ('subcategory__category',)
    search_fields = ('name',)

    def get_category(self, obj):
        return obj.subcategory.category.name
    get_category.short_description = 'Category'
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'discount_price', 'stock_quantity', 'image_tag','coin_discount')
    inlines = [ProductImageInline]

    # To show the first image in list view
    def image_tag(self, obj):
        first_image = obj.images.first()  # 'images' is the related_name
        if first_image:
            return format_html('<img src="{}" width="50" height="50" />'.format(first_image.image.url))
        return "-"
    image_tag.short_description = 'Image'
    


@admin.register(MaterialType)
class MaterialTypeAdmin(admin.ModelAdmin):
    list_display = ("label", "code", "icon_class")
    search_fields = ("label", "code")
  
class DeclutterImageInline(admin.TabularInline):
    model = DeclutterImage
    extra = 1  # to show 1 empty form by default for adding images
@admin.register(DeclutterRequest)
class DeclutterRequestAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'item_condition',
        'color_category',
        'material_type',
        'preferred_date',
        'preferred_time',
        'current_location',  # new column for location
        'image_tag'
    )
    list_filter = ('item_condition', 'color_category', 'material_type', 'preferred_date')
    search_fields = ('user__username', 'name', 'mobile_number')

    inlines = [DeclutterImageInline]

   
    def image_tag(self, obj):
        first_image = obj.images.first()
        if first_image:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" width="50" height="50" style="object-fit: cover;"/></a>',
                first_image.image.url,  # link to full-size image
                first_image.image.url   # thumbnail
            )
        return "-"
    image_tag.short_description = 'Image'

    # New method to show current location
    def current_location(self, obj):
        # Get the buyer profile of the user
        buyer_profile = getattr(obj.user, 'buyer_profile', None)  # use correct related_name
        if buyer_profile:
            # Get the current location address if it exists
            current_address = buyer_profile.addresses.filter(is_current_location=True).first()
            if current_address and current_address.latitude and current_address.longitude:
                # Create a clickable Google Maps link
                return format_html(
                    '<a href="https://www.google.com/maps?q={},{}" target="_blank">📍Location</a>',
                    current_address.latitude,
                    current_address.longitude
                )
        return "N/A"
    current_location.short_description = "Current Location"

@admin.register(CoinTransaction)
class CoinTransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "description", "amount", "date")
    list_filter = ("date",)
    search_fields = ("user__username", "description", "declutter_request__id")
    ordering = ("-date",)




@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    list_display = ('coin_value',)
    

@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("user__email", "product__name", "comment")
    ordering = ("-created_at",)
    

class OrderItemInline(admin.TabularInline):  # or StackedInline for more detail
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "variant", "quantity", "price", "subtotal", "total_price")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "buyer_email", "status", "created_at", "total_before_discount", "coin_discount_value", "total_after_discount")
    list_filter = ("status", "created_at")
    search_fields = ("buyer__user__email", "shipping_name", "shipping_phone")
    inlines = [OrderItemInline]
    date_hierarchy = "created_at"

    def buyer_email(self, obj):
        return obj.buyer.user.email
    buyer_email.admin_order_field = "buyer__user__email"  # allows sorting
    buyer_email.short_description = "Buyer Email"

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "status", "created_at")
    list_filter = ("status", "created_at", "product")
    search_fields = ("user__email", "product__name", "message")
    ordering = ("-created_at",)
    actions = ["approve_feedback", "reject_feedback"]

    @admin.action(description="✅ Approve selected feedback and notify seller")
    def approve_feedback(self, request, queryset):
        for feedback in queryset:
            feedback.status = "approved"
            feedback.save()

            seller_email = feedback.product.seller.user.email

            # Create email
            email = EmailMessage(
                subject=f"🔔 New Feedback of {feedback.product.name}",
                body=(
                    f"Hello {feedback.product.seller.store_name},\n\n"
                    f"A new feedback has been get on  your product: {feedback.product.name}.\n\n"
                    f"From: {feedback.user.email}\n"
                    f"Message: {feedback.message}\n\n"
                    f"Please log in to your seller account for details.\n"
                    f"Check The Product."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[seller_email],
            )

            # Attach image if exists
            if feedback.image:
                email.attach_file(feedback.image.path)

            # Send email
            email.send(fail_silently=True)

    @admin.action(description="❌ Reject selected feedback")
    def reject_feedback(self, request, queryset):
        queryset.update(status="rejected")
