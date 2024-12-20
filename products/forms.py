from django import forms
from .models import Product, Category, Attachment, ProductReview


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Retrieve all categories for the category field
        categories = Category.objects.all()
        friendly_names = [
            (c.id, c.get_friendly_name()) for c in categories
        ]
        self.fields['category'].choices = friendly_names

        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'border-black rounded-0'
            field.widget.attrs['id'] = f'id_{field_name}'

    def clean_price(self):
        """ Custom validation for price field """
        price = self.cleaned_data.get('price')
        if price is None or price <= 0 or price > 9999.99:
            raise forms.ValidationError(
                "Please enter a price between $0.01 and $9999.99."
            )
        return price


class AttachmentForm(forms.ModelForm):
    class Meta:
        model = Attachment
        fields = ['name', 'description', 'price', 'sku', 'image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'border-black rounded-0'


class ProductReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.NumberInput(attrs={
                'id': 'id_rating',
                'class': 'form-control',
                'min': 1,
                'max': 5,
                'placeholder': 'Rate this product (1-5)',
            }),
            'comment': forms.Textarea(attrs={
                'id': 'id_comment',
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Write your review here...',
            }),
        }
