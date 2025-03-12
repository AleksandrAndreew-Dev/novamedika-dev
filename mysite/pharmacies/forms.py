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