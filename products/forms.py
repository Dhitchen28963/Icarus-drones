from django import forms
from .models import Product, Category, Attachment

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Retrieve all categories and set them as choices for the category field
        categories = Category.objects.all()
        friendly_names = [(c.id, c.get_friendly_name()) for c in categories]
        self.fields['category'].choices = friendly_names

        # Apply consistent styling and set explicit IDs to ensure matching label `for` attributes
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'border-black rounded-0'
            field.widget.attrs['id'] = f'id_{field_name}'  # Corrected to `id_fieldname` for matching

    def clean_price(self):
        """ Custom validation for price field """
        price = self.cleaned_data.get('price')
        if price is None or price <= 0 or price > 9999.99:
            raise forms.ValidationError("Please enter a price between $0.01 and $9999.99.")
        return price

class AttachmentForm(forms.ModelForm):
    class Meta:
        model = Attachment
        fields = ['name', 'description', 'price', 'sku', 'image']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'border-black rounded-0'
