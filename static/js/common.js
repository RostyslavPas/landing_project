function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function showValidationErrors(errors) {
    document.querySelectorAll('.error-message').forEach(el => el.remove());

    Object.keys(errors).forEach(field => {
        const input = document.getElementById(field);
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.style.color = 'red';
        errorDiv.style.fontSize = '12px';
        errorDiv.style.marginTop = '5px';
        errorDiv.textContent = errors[field][0];

        input.parentNode.appendChild(errorDiv);
        input.style.borderColor = 'red';
    });
}

function redirectToWayForPay(params) {
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = 'https://secure.wayforpay.com/pay';

    Object.keys(params).forEach(key => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = key;
        input.value = Array.isArray(params[key]) ? params[key][0] : params[key];
        form.appendChild(input);
    });

    document.body.appendChild(form);
    form.submit();
}

// =============================
// Popups
// =============================

document.querySelectorAll('[data-popup]').forEach(link => {
      link.addEventListener('click', function(e) {
        e.preventDefault();
        let popupId = "popup-" + this.dataset.popup;
        document.getElementById(popupId).style.display = "flex";
      });
    });

    document.querySelectorAll('.popup-close').forEach(btn => {
      btn.addEventListener('click', function() {
        this.closest('.popup').style.display = "none";
      });
    });

    window.addEventListener('click', function(e) {
      if (e.target.classList.contains('popup')) {
        e.target.style.display = "none";
      }
    });

// =============================
// Ticket Form
// =============================

document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('.ticket-form');
    const emailInput = document.getElementById('email');
    const phoneInput = document.getElementById('phone');

    // Форматування номера телефону під час введення
    phoneInput.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, '');

        // Якщо поле стерли — залишаємо порожнім
        if (value === "") {
            e.target.value = "";
            return;
        }

        // Якщо користувач починає вводити не з 38 — підставимо +38
        if (!value.startsWith("38")) {
            value = "38" + value;
        }

        value = "+" + value;

        // Форматування: +38(0XX)XXX-XX-XX
        if (value.length >= 4) {
            value = value.replace(/(\+38)(\d{3})/, '$1($2)');
        }
        if (value.length >= 9) {
            value = value.replace(/(\+38\(\d{3}\))(\d{3})/, '$1$2-');
        }
        if (value.length >= 13) {
            value = value.replace(/(\+38\(\d{3}\)\d{3}-)(\d{2})/, '$1$2-');
        }

        e.target.value = value.substring(0, 17);
    });

    // Додаємо підтримку видалення
    phoneInput.addEventListener('keydown', function(e) {
        if (e.key === 'Backspace' || e.key === 'Delete') {
            let pos = this.selectionStart;
            let val = this.value;

            // Якщо перед курсором спецсимвол – видаляємо його теж
            if (pos > 0 && /[-()\s]/.test(val.charAt(pos - 1))) {
                e.preventDefault();
                this.value = val.slice(0, pos-1) + val.slice(pos);
                this.setSelectionRange(pos-1, pos-1);
            }

            // Якщо залишився тільки +38 і далі видаляють — очищаємо поле
            if (this.value === "+38") {
                e.preventDefault();
                this.value = "";
            }
        }
    });

    // Обробка відправки форми
    form.addEventListener('submit', function(e) {
        e.preventDefault();

        const formData = new FormData();
        formData.append('email', emailInput.value);
        formData.append('phone', phoneInput.value);
        formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));

        // Показуємо індикатор завантаження
        const submitBtn = form.querySelector('.submit-button');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Обробка...';
        submitBtn.disabled = true;

        fetch('/submit-ticket/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                redirectToWayForPay(data.wayforpay_params);
            } else {
                showValidationErrors(data.errors);
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Виникла помилка. Спробуйте ще раз.');
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        });
    });
});