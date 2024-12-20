from django import forms
from .models import UserProfile, OrderIssue, ContactMessage, RepairRequest


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
                placeholder = (
                    f"{placeholders.get(field, field)}"
                    f"{' *' if self.fields[field].required else ''}"
                )
                self.fields[field].widget.attrs['placeholder'] = placeholder
            elif field == 'default_country':
                self.fields[field].widget.attrs['style'] = 'color: #aab7c4;'

            self.fields[field].widget.attrs['class'] = (
                'border-black rounded-0 profile-form-input'
            )
            self.fields[field].label = False


class OrderIssueForm(forms.ModelForm):
    class Meta:
        model = OrderIssue
        fields = ['issue_type', 'description']
        widgets = {
            'issue_type': forms.Select(attrs={
                'class': 'form-control',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Describe the issue in detail...',
                'rows': 4,
            }),
        }


class OrderIssueResponseForm(forms.ModelForm):
    class Meta:
        model = OrderIssue
        fields = ['response', 'status']
        widgets = {
            'response': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Write your response here...'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control',
            }),
        }
        labels = {
            'response': 'Response',
            'status': 'Status',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("Status field choices:", self.fields['status'].choices)
        self.fields['response'].widget = forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Write your response here...',
        })
        self.fields['status'].widget = forms.Select(attrs={
            'class': 'form-control',
        })


class RepairRequestResponseForm(forms.ModelForm):
    response = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Write your response here...'
        }),
        label='Response',
        required=True
    )

    class Meta:
        model = RepairRequest
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-control',
            }),
        }
        labels = {
            'status': 'Status',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("Status field choices:", self.fields['status'].choices)
        self.fields['status'].widget = forms.Select(attrs={
            'class': 'form-control',
        })


class ContactMessageResponseForm(forms.ModelForm):
    response = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Write your response here...'
        }),
        label='Response',
        required=True
    )

    class Meta:
        model = ContactMessage
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-control',
            }),
        }
        labels = {
            'status': 'Status',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("Status field choices:", self.fields['status'].choices)
        self.fields['status'].widget = forms.Select(attrs={
            'class': 'form-control',
        })
