from django import forms
from .models import UserProfile

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        exclude = ('user',)

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
            'loyalty_points': 'Loyalty Points',
        }

        self.fields['default_phone_number'].widget.attrs['autofocus'] = True
        for field in self.fields:
            if field != 'default_country' and field != 'loyalty_points':
                placeholder = f"{placeholders.get(field, field)}{' *' if self.fields[field].required else ''}"
                self.fields[field].widget.attrs['placeholder'] = placeholder
            elif field == 'default_country':
                self.fields['default_country'].widget.attrs['style'] = 'color: #aab7c4;'
                
            self.fields[field].widget.attrs['class'] = 'border-black rounded-0 profile-form-input'
            self.fields[field].label = False

        self.fields['loyalty_points'].widget.attrs['readonly'] = 'readonly'
        self.fields['loyalty_points'].widget.attrs['placeholder'] = placeholders['loyalty_points']
