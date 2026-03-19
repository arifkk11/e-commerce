from django.db import models
from django.contrib.auth.models import AbstractUser
import random
import string
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
import uuid
from django.core.exceptions import ValidationError
from phonenumber_field.modelfields import PhoneNumberField
from django.db.models import Q
from django.db import models, transaction
from decimal import Decimal





# Create your models here.


#CUSTOMEUSER TABLE#############################################################################################################
def generate_klutter_id():
    """Generate unique 8-digit Klutter ID"""
    return ''.join(random.choices(string.digits, k=8))


class CustomUserManager(BaseUserManager):
    def create_user(self, email, name=None, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)

        # Ensure unique klutter_id
        extra_fields.setdefault("klutter_id", generate_klutter_id())
        while CustomUser.objects.filter(klutter_id=extra_fields["klutter_id"]).exists():
            extra_fields["klutter_id"] = generate_klutter_id()

        user = self.model(email=email, name=name, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()     
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("user_type", "admin")

        if not password:
            raise ValueError("Superuser must have a password.")

        return self.create_user(email, name, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    # Primary key
    klutter_id = models.CharField(
        max_length=8,
        unique=True,
        editable=False,
        primary_key=True,
        default=generate_klutter_id
    )

    # Auth fields
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, blank=True, null=True)

    # Profile picture (hybrid: uploads + URL from OAuth)
    picture = models.ImageField(upload_to="users/", blank=True, null=True)   # for uploads
    picture_url = models.URLField(max_length=500, blank=True, null=True)     # for Google/Facebook/etc.

    auth_provider = models.CharField(max_length=50, default="email")  # email, google, facebook, etc.

    # Login/session tracking
    login_time = models.DateTimeField(blank=True, null=True)
    logout_time = models.DateTimeField(blank=True, null=True)
    login_status = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    device_type = models.CharField(max_length=50, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)

    # OTP
    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)
    
    @property
    def coins(self):
        if hasattr(self, "buyer_profile"):
            return self.buyer_profile.coins
        return 0

    # User classification
    USER_TYPES = [
        ("customer", "Customer"),
        ("seller", "Seller"),
        ("admin", "Admin"),
    ]
    user_type = models.CharField(max_length=50, choices=USER_TYPES, default="customer")
    is_new_user = models.BooleanField(default=True)

    # Django required fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    def __str__(self):
        return f"{self.email} ({self.klutter_id})"

    @property
    def profile_image(self):
        """Return uploaded picture if available, else external URL, else default avatar"""
        if self.picture:
            return self.picture.url
        if self.picture_url:
            return self.picture_url
        return "https://i.pinimg.com/736x/3e/79/ed/3e79edd8850e4f1d73052f548f2f399d.jpg"


    @property
    def is_admin(self):
        return self.is_staff

#SELLER TABLE#############################################################################################################    
class SellerAddress(models.Model):
    pin = models.CharField(max_length=10)
    post_office = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    extra_details = models.TextField(blank=True)
    def __str__(self):
        return self.post_office
    

class SellerProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='seller_profile')
    store_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, unique=True)
    address = models.OneToOneField(SellerAddress, on_delete=models.CASCADE, related_name='seller')  # linked
    approved = models.BooleanField(default=False)
    def __str__(self):
        return self.store_name
#PRODUCT TABLE#############################################################################################################

class ProductCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    class Meta:
        verbose_name = "Product Category (Level 1)"
        verbose_name_plural = "Product Categories (Level 1)"

    def __str__(self):
        return self.name


class SubCategory(models.Model):
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name="subcategories")
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "SubCategory (Level 2)"
        verbose_name_plural = "SubCategories (Level 2)"
        unique_together = ("category", "name")

    def __str__(self):
        return f"{self.category.name} → {self.name}"


class SubSubCategory(models.Model):
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name="subsubcategories")
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "SubSubCategory (Level 3)"
        verbose_name_plural = "SubSubCategories (Level 3)"
        unique_together = ("subcategory", "name")

    def __str__(self):
        return f"{self.subcategory.category.name} → {self.subcategory.name} → {self.name}"


class Product(models.Model):
    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name='products') 
    # Three category levels
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name="products", null=True, blank=True)
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name="products", null=True, blank=True)
    subsubcategory = models.ForeignKey(SubSubCategory, on_delete=models.CASCADE, related_name="products", null=True, blank=True)


    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock_quantity = models.PositiveIntegerField(null=True, blank=True)
    color = models.CharField(max_length=50)
    brand_name = models.CharField(max_length=100, null=True, blank=True)
    # material = models.CharField(max_length=100, null=True, blank=True)

    coin_discount = models.PositiveIntegerField(default=0)  # Price in coins
    is_featured = models.BooleanField(default=False)
    new_listings = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def get_first_image_url(self):
        # Get the first image related to the product (if available)
        first_image = self.images.first()  # 'images' is the related_name of ProductImage
        if first_image:
            return first_image.image.url
        return 'default-image.jpg'  # Fallback image URL if no images exist
    
    def __str__(self):
        return self.name
    
    def get_final_price(self):
        """Return the best possible price considering FlatSales and product discount_price."""
        price = self.price

        # Check active flat sales
        active_sales = self.flat_sales.filter(
            approved=True,
            start_date__lte=timezone.now().date(),
            end_date__gte=timezone.now().date()
        )

        if active_sales.exists():
            discounts = [sale.get_discounted_price(price) for sale in active_sales]
            return min(discounts)  # lowest wins

        # If no flat sale → consider discount_price
        if self.discount_price and self.discount_price < self.price:
            return self.discount_price

        # Default → original price
        return self.price

    def get_discount_percentage(self):
        """How much % off from original price?"""
        final_price = self.get_final_price()
        if self.price > 0 and final_price < self.price:
            discount = ((self.price - final_price) / self.price) * 100
            return round(discount)
        return 0

    #################################################################################################################

    
        
SIZE_CHOICES = [
    ('S', 'Small'),
    ('M', 'Medium'),
    ('L', 'Large'),
    ('XL', 'Extra Large'),
    ('XXL', 'Double Extra Large'),
    ('3XL', 'Triple Extra Large'),
    ('4XL', 'Quadruple Extra Large'),   
    ('5XL', 'Quintuple Extra Large'),
]
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=10,choices=SIZE_CHOICES)  # S, M, L, etc.
    stock = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"{self.product.name} ({self.size})"

    def get_final_price(self):
        """Variant price is the same as the product price (with discounts)."""
        return self.product.get_final_price()
    
   
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/')
###############################################################################################################

class Notification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="notifications")
    message = models.TextField()
    link = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.message}"
    
#FLATSALE TABLE##############################################################################################################    
class FlatSale(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]

    products = models.ManyToManyField('Product', related_name='flat_sales')
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)  # e.g., 20 for 20% or ₹20
    start_date = models.DateField()
    end_date = models.DateField()
    event_name = models.CharField(max_length=100, null=True, blank=True)
    event_banner = models.ImageField(upload_to='flat_sale_banners/', null=True, blank=True)
    created_by_admin = models.BooleanField(default=False)
    approved = models.BooleanField(default=False)  # ✅ New field

    def is_active(self):
        today = timezone.now().date()
        return self.approved and self.start_date <= today <= self.end_date

    def get_discounted_price(self, product_price):
        if self.discount_type == 'percentage':
            return product_price * (1 - self.discount_value / 100)
        elif self.discount_type == 'fixed':
            return max(product_price - self.discount_value, 0)
        return product_price
#BUYER/USERS###############################################################################################################    

class AccountProfile(models.Model):
    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    )

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='account_profile')
    phone = PhoneNumberField(region='IN', unique=True, null=True, blank=True)  # Default region set to India
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    coins= models.BigIntegerField(default=0)  # For rewards system
    
    @property
    def is_complete(self):
        """Check if all required fields are filled"""
        required_fields = [self.phone, self.dob, self.gender]
        return all(required_fields)
    
   
    def is_profile_complete(self):
        """Check if all required fields are filled"""
        return self.phone and self.dob and self.gender

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Check if profile complete and bonus not already given
        if self.is_profile_complete():
            from .models import CoinTransaction  # avoid circular import
            already_given = CoinTransaction.objects.filter(
                user=self.user,
                description="Profile completion bonus"
            ).exists()

            if not already_given:
                with transaction.atomic():
                    self.coins += 50
                    super().save(update_fields=['coins'])

                    CoinTransaction.objects.create(
                        user=self.user,
                        description="Profile completion bonus",
                        amount=50
                    )

    
class UserAddress(models.Model):
    ADDRESS_TYPES = [
        ("home", "Home"),
        ("work", "Work"),
        ("other", "Other"),
    ]
    buyer  = models.ForeignKey(AccountProfile, on_delete=models.CASCADE, related_name='addresses')
    address_type = models.CharField(max_length=10,choices=ADDRESS_TYPES,default="home")
    # Manual address fields
    pin = models.CharField(max_length=10)
    post_office = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    extra_details = models.TextField(blank=True)

    # Current location (auto-detected GPS)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_current_location = models.BooleanField(default=False)

    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.post_office}, {self.city} ({self.address_type})"

    @property
    def full_address(self):
        
        return f"{self.extra_details}, {self.post_office}, {self.city}, {self.state}, {self.country} - {self.pin}"
    
#DECLUTTER################################################################################################################    
     
class MaterialType(models.Model):
    code = models.SlugField(max_length=50, unique=True)   # e.g. "cotton"
    label = models.CharField(max_length=100)              # e.g. "Cotton"
    icon_class = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.label

    
class DeclutterRequest(models.Model):
    CONDITION_CHOICES = [
        ('wearable', 'Wearable'),
        ('non_wearable', 'Non-Wearable'),
    ]
    NON_WEARABLE_REASON_CHOICES = [
        ('torn', 'Torn'),
        ('faded', 'Faded'),
        ('stained', 'Stained'),
        ('damaged_fabric', 'Damaged Fabric'),
    ]
    COLOR_CHOICES = [
        ('white', 'White'),
        ('solid_color', 'Solid Color'),
        ('multicolor', 'Multicolor'),
    ]


    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    item_condition = models.CharField(max_length=20, choices=CONDITION_CHOICES)
    non_wearable_reason = models.CharField(max_length=50, choices=NON_WEARABLE_REASON_CHOICES, blank=True, null=True)
    wearable_types = models.JSONField(blank=True, null=True)  # store multiple selected
    color_category = models.CharField(max_length=20, choices=COLOR_CHOICES)
    material_type = models.ForeignKey(MaterialType, on_delete=models.SET_NULL, null=True, blank=True)
    
    name = models.CharField(max_length=100)
    mobile_number = models.CharField(max_length=15)
    pickup_address = models.TextField()  # Store full address as free text
    preferred_date = models.DateField(null=True, blank=True )  # Optional date
    preferred_time = models.TimeField(null=True, blank=True)  # Optional time
    request_accepted = models.BooleanField(default=False)
    reward_coins = models.PositiveIntegerField(default=0)
    # Coins awarded for decluttering
    
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Declutter Request by {self.user} on {self.created_at.strftime('%Y-%m-%d')}"
    def save(self, *args, **kwargs):
    # Check if status changed to accepted
        if self.pk:  # existing object
            old_instance = DeclutterRequest.objects.get(pk=self.pk)
            if not old_instance.request_accepted and self.request_accepted:
                # Create a CoinTransaction when request is accepted
                CoinTransaction.objects.create(
                    user=self.user,
                    description=f"Reward for decluttering ",
                    amount=self.reward_coins
                )
        super().save(*args, **kwargs)
   


class DeclutterImage(models.Model):
    request = models.ForeignKey(DeclutterRequest, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="declutter_items/")

    def __str__(self):
        return f"Image for Request {self.request.id}"
    
#COIN TRANSACTION###########################################################################################################   
class CoinTransaction(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="coin_transactions")
    description = models.CharField(max_length=255)
    amount = models.IntegerField()  # positive = earned, negative = redeemed
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} | {self.amount} Coins"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        profile, _ = AccountProfile.objects.get_or_create(user=self.user)
        profile.coins = profile.user.coin_transactions.aggregate(total=models.Sum('amount'))['total'] or 0
        profile.save(update_fields=['coins'])

#FEEDBACK#########################################################################################################################
    
class Feedback(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='feedbacks')
    product = models.ForeignKey(Product, on_delete=models.CASCADE,related_name='feedbacks',default=1)
    status = models.CharField(max_length=10,choices=STATUS_CHOICES,default='pending')
    message = models.TextField()
    image= models.ImageField(upload_to='feedback_images/', null=True, blank=True)
    admin_notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
         return f"Feedback from {self.user.email} - {self.product.name} ({self.status})"
    
    
#Wishlist#########################################################################################################################

class Wishlist(models.Model):
    user = models.ForeignKey(AccountProfile, related_name="wishlists", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="wishlists", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)  # Flag to indicate if the product is still in the wishlist

    class Meta:
        unique_together = ('user', 'product')  # Ensure each user can only have one instance of a product in the wishlist

#CART#########################################################################################################################

class Cart(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
   
    @property
    def total_price(self):
        """Total payable price (after discounts, based on CartItems)."""
        return sum(item.total_price for item in self.items.all())

    @property
    def total_original_price(self):
        """Total without discounts."""
        return sum(item.original_price * item.quantity for item in self.items.all())

    @property
    def total_discount(self):
        """How much discount in money (original - discounted)."""
        return self.total_original_price - self.total_price

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)    
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def unit_price(self):
        """Respect product/variant discounts (using your get_final_price)."""
        if self.variant:
            return self.variant.get_final_price()
        return self.product.get_final_price()

    @property
    def total_price(self):
        return self.unit_price * self.quantity

    @property
    def original_price(self):
        """Base price before discounts."""
        if self.variant:
            return self.variant.product.price
        return self.product.price

    @property
    def discount_percentage(self):
        return self.product.get_discount_percentage()

    @property
    def discounted_price(self):
        return self.unit_price
    
#order#########################################################################################################################

class Order(models.Model):
    buyer = models.ForeignKey(AccountProfile, on_delete=models.CASCADE, related_name="orders")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),           # order created, checkout not completed
            ('cod_pending', 'COD Pending'),   # checkout complete, COD chosen, waiting for seller
            ('paid', 'Paid'),                 # online payment completed
            ('shipped', 'Shipped'),           # seller shipped
            ('delivered', 'Delivered'),       # buyer received
            ('cancelled', 'Cancelled'),       # cancelled by buyer or seller
            ('abandoned', 'Abandoned'),       # buyer left checkout, auto-marked
            ('failed', 'Failed'),             # payment failed

        ],
        default='pending'
    )

    coins_used = models.PositiveIntegerField(default=0)
    

    # snapshot of address at checkout
    shipping_name = models.CharField(max_length=255, blank=True, null=True)
    shipping_phone = models.CharField(max_length=20, blank=True, null=True)
    shipping_address_type = models.CharField(max_length=10, choices=UserAddress.ADDRESS_TYPES,blank=True,null=True)
    shipping_pin = models.CharField(max_length=10)
    shipping_post_office = models.CharField(max_length=100)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_country = models.CharField(max_length=100)
    shipping_extra_details = models.TextField(blank=True, null=True)
    last_seen = models.DateTimeField(default=timezone.now)
    def __str__(self):
        return f"Order #{self.id} by {self.buyer.user.email}"

    @property
    def shipping_full_address(self):
        return f"{self.shipping_extra_details}, {self.shipping_post_office}, {self.shipping_city}, {self.shipping_state}, {self.shipping_country} - {self.shipping_pin}"


    def calculate_totals(self):
        """Recalculate order totals from items + coins"""
        total = sum([item.total_price for item in self.items.all()])
        self.total_before_discount = total

        # get current coin value from SiteConfig
        from .models import SiteConfig
        coin_value = Decimal(SiteConfig.objects.first().coin_value) if SiteConfig.objects.exists() else Decimal("1.0")

        discount = Decimal(self.coins_used) * coin_value
        if discount > total:
            discount = total

        self.total_after_discount = total - discount
        return self.total_after_discount
    
    


    @property
    def total_after_discount(self):
        from .models import SiteConfig
        site_config = SiteConfig.objects.first()
        coin_value = Decimal(site_config.coin_value or "1.0") if site_config else Decimal("1.0")
        discount = Decimal(self.coins_used) * coin_value
        return max(self.total_before_discount - discount, Decimal("0.00"))
    
    def deduct_stock(self):
        """Deduct stock safely when order is confirmed (variant-aware)."""
        for item in self.items.select_related("variant", "product"):

            if item.variant:
                # ✅ Lock the selected variant row
                variant = ProductVariant.objects.select_for_update().get(pk=item.variant.pk)

                if variant.stock < item.quantity:
                    raise ValueError(f"Not enough stock for {variant}")
    
                # Deduct from the selected variant
                variant.stock -= item.quantity
                variant.save(update_fields=["stock"])

                # ✅ Sync total product stock = sum of all variants
                total_variant_stock = item.product.variants.aggregate(
                    total=models.Sum("stock")
                )["total"] or 0
                item.product.stock_quantity = total_variant_stock
                item.product.save(update_fields=["stock_quantity"])

            else:
                # ✅ No variants → deduct from product stock directly
                product = Product.objects.select_for_update().get(pk=item.product.pk)

                if not product.stock_quantity or product.stock_quantity < item.quantity:
                    raise ValueError(f"Not enough stock for {product}")

                product.stock_quantity -= item.quantity
                product.save(update_fields=["stock_quantity"])
                
        
    @property
    def total_before_discount(self):
        return sum(item.total_price for item in self.items.all())
       

    @property
    def coin_discount_value(self):
        """How much money is reduced by applied coins"""
        site_config = SiteConfig.objects.first()
        coin_value = Decimal(site_config.coin_value) if site_config else Decimal("1.0")
        return Decimal(self.coins_used) * coin_value

    @property
    def total_after_discount(self):
        total = self.total_before_discount
        discount = min(self.coin_discount_value, total)
        return max(total - discount, Decimal("0.00"))        




class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("Product", on_delete=models.CASCADE)
    variant = models.ForeignKey("ProductVariant", on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # unit price at time of order

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding

        if is_new and not self.price:
            # lock price once when creating
            if self.variant and hasattr(self.variant, "get_final_price"):
                self.price = self.variant.get_final_price()
            else:
                self.price = self.product.get_final_price()

        # ✅ Do NOT deduct stock here
        super().save(*args, **kwargs)

    
    @property
    def subtotal(self):
        if self.price is None or self.quantity is None:
            return Decimal("0.00")
        return self.price * self.quantity

    @property
    def total_price(self):
        if self.price is None or self.quantity is None:
            return Decimal("0.00")
        return self.price * Decimal(self.quantity)
    
    #######$###########################################################################################################

   



    
#coinvalidation###########################################################################################################
class SiteConfig(models.Model):
    coin_value = models.DecimalField(max_digits=10, decimal_places=2, default=1.0)  
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"1 coin = {self.coin_value} currency"

    class Meta:
        verbose_name = "Site Config"
        verbose_name_plural = "Site Config"    
    

#REVIEW###########################################################################################################
class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="product_reviews")
    rating = models.PositiveIntegerField()  # 1 to 5
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("product", "user")  # one review per user per product

    def __str__(self):
        return f"Review by {self.user.email} for {self.product.name}"

    def clean(self):
        if self.rating < 1 or self.rating > 5:
            raise ValidationError("Rating must be between 1 and 5")

    def save(self, *args, **kwargs):
        self.full_clean()  # validate before saving
        super().save(*args, **kwargs)