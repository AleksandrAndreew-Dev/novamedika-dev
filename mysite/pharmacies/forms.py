# pharmacies/forms.py
from django import forms

class ProductSearchForm(forms.Form):
    q = forms.CharField(
        label=False,
        max_length=255,
        required=False,
        initial='Введите название продукта',
        widget=forms.TextInput(attrs={'class': 'search-input', 'placeholder': 'Введите название продукта'}),
        error_messages={
            'required': 'Это поле обязательно для заполнения',
            'max_length': 'Максимальная длина - 255 символов',
        }
    )

class ReserveForm(forms.Form):
    user_name = forms.CharField(max_length=100)
    user_surname = forms.CharField(max_length=100)
    user_phone = forms.CharField(max_length=100)
    quantity = forms.IntegerField(min_value=1)
    product_name = forms.CharField(max_length=100)
    product_price = forms.DecimalField(max_digits=10, decimal_places=2)
    pharmacy_name = forms.CharField(max_length=100)
    pharmacy_number = forms.IntegerField()