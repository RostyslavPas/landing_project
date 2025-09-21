from django import forms
from django.core.validators import EmailValidator
import re


class TicketOrderForm(forms.Form):
    email = forms.EmailField(
        validators=[EmailValidator()],
        widget=forms.EmailInput(attrs={
            'placeholder': 'user@example.com',
            'class': 'form-control',
            'required': True
        }),
        error_messages={
            'required': 'Email є обов\'язковим полем',
            'invalid': 'Введіть коректний email адрес'
        }
    )

    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'placeholder': '+38(xxx)xxx-xx-xx',
            'class': 'form-control',
            'required': True
        }),
        error_messages={
            'required': 'Номер телефону є обов\'язковим полем',
            'invalid': 'Введіть коректний номер телефону'
        }
    )

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            # Видаляємо всі символи крім цифр та +
            cleaned_phone = re.sub(r'[^\d+]', '', phone)

            # Перевіряємо формат українського номера
            if not re.match(r'^\+380\d{9}$', cleaned_phone):
                raise forms.ValidationError(
                    'Номер телефону має бути у форматі +380xxxxxxxxx'
                )
            return cleaned_phone
        return phone

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            return email.lower()
        return email