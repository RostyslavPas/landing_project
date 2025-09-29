# forms.py
from django import forms
from django.core.validators import EmailValidator
import re


class TicketOrderForm(forms.Form):
    email = forms.EmailField(
        validators=[EmailValidator()],
        widget=forms.EmailInput(attrs={
            'placeholder': 'user@example.com',
            'class': 'form-control',
            'required': False
        }),
        error_messages={
            'required': "Email є обов'язковим полем",
            'invalid': 'Введіть коректну email адресу'
        }
    )

    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'placeholder': '+38(XXX)XXX-XX-XX',
            'class': 'form-control',
            'required': False
        }),
        error_messages={
            'required': "Номер телефону є обов'язковим полем",
            'invalid': 'Введіть коректний номер телефону'
        }
    )

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            # Видаляємо всі символи, крім цифр
            digits = re.sub(r'\D', '', phone)
            if not digits.startswith('380') or len(digits) != 12:
                raise forms.ValidationError(
                    'Номер телефону має бути у форматі +380XXXXXXXXX'
                )
            # Повертаємо у стандартному форматі +380XXXXXXXXX
            return f'+{digits}'
        return phone

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            return email.lower()
        return email
