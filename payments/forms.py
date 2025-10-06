# forms.py
from django import forms
from django.core.validators import EmailValidator
import re


class TicketOrderForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Прізвище Ім’я',
            'class': 'form-control',
            'required': False
        }),
        error_messages={
            'required': "Ім’я є обов'язковим полем",
        }
    )

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

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError("Поле ім’я не може бути порожнім.")
        if len(name) < 2:
            raise forms.ValidationError("Ім’я має містити мінімум 2 символи.")
        return name

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
