from django import forms
from .models import *
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'price', 'discount_price', 
            'category', 'subcategory', 'subsubcategory', 'color','brand_name','stock_quantity'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'subcategory': forms.Select(attrs={'class': 'form-select'}),
            'subsubcategory': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['discount_price'].required = False

        # Ensure subcategory field shows all subcategories
        self.fields['subcategory'].queryset = SubCategory.objects.all()

        # Initialize subsubcategory field
        self.fields['subsubcategory'].queryset = SubSubCategory.objects.none()

        # Case 1: form submitted (POST)
        if 'subcategory' in self.data:
            try:
                subcategory_id = int(self.data.get('subcategory'))
                self.fields['subsubcategory'].queryset = SubSubCategory.objects.filter(subcategory_id=subcategory_id)
            except (ValueError, TypeError):
                self.fields['subsubcategory'].queryset = SubSubCategory.objects.none()
        # Case 2: editing existing product
        elif self.instance.pk:
            if self.instance.subcategory:
                self.fields['subsubcategory'].queryset = SubSubCategory.objects.filter(subcategory=self.instance.subcategory)
            else:
                self.fields['subsubcategory'].queryset = SubSubCategory.objects.all()



class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ['size','stock']
        widgets = {
            'size': forms.Select(attrs={'class': 'form-select'}),
            'stock': forms.NumberInput(attrs={'min': '0'}),
        }

class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image']
    
    image = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['image'].label = ''
class ManualSignupForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['name', 'email']   # ✅ only fields that exist

    def save(self, commit=True):
        user = super().save(commit=False)
        # No "username" field in AbstractBaseUser → just ensure email is set
        user.name = self.cleaned_data.get("name")
        if commit:
            user.save()
        return user


class DeclutterRequestForm(forms.ModelForm):
    class Meta:
        model = DeclutterRequest
        fields = [
            "item_condition",
            "non_wearable_reason",
            "wearable_types",
            "color_category",
            "material_type",
            "name",
            "mobile_number",
            "preferred_date",
            "preferred_time",
        ]

    material_type = forms.ModelChoiceField(
        queryset=MaterialType.objects.all(),
        widget=forms.RadioSelect,   # you already render custom HTML anyway
        required=True
    )


class ProductCategoryForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'subcategory', 'name', 'price', 'description', 'stock_quantity', 'color']