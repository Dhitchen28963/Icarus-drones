from django import forms
from .models import UserProfile

class UserProfileForm(forms.ModelForm):
    full_name = forms.CharField(
        max_length=100,
        required=False,
        label="Full Name"
    )

    class Meta:
        model = UserProfile
        exclude = ('user', 'loyalty_points')

    def __init__(self, *args, **kwargs):
        """
        Add placeholders and classes, remove auto-generated
        labels, and set autofocus on the first field.
        """
        super().__init__(*args, **kwargs)
        placeholders = {
            'default_phone_number': 'Phone Number',
            'default_postcode': 'Postal Code',
            'default_town_or_city': 'Town or City',
            'default_street_address1': 'Street Address 1',
            'default_street_address2': 'Street Address 2',
            'default_county': 'County, State or Locality',
            'default_country': 'Country',
        }

        self.fields['default_phone_number'].widget.attrs['autofocus'] = True

        for field in self.fields:
            if field != 'default_country':
                placeholder = f"{placeholders.get(field, field)}{' *' if self.fields[field].required else ''}"
                self.fields[field].widget.attrs['placeholder'] = placeholder
            elif field == 'default_country':
                self.fields[field].widget.attrs['style'] = 'color: #aab7c4;'

            self.fields[field].widget.attrs['class'] = 'border-black rounded-0 profile-form-input'
            self.fields[field].label = False
