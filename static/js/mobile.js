document.addEventListener('DOMContentLoaded', () => {
    // --- Меню ---
    const menuButton = document.querySelector('.menu-button');
    const dropdownMenu = document.querySelector('.dropdown-menu');
    const overlay = document.querySelector('.menu-overlay');

    if (menuButton && dropdownMenu && overlay) {
        function openMenu() {
            dropdownMenu.classList.add('open');
            overlay.classList.add('active');
            menuButton.setAttribute('aria-expanded', 'true');
        }

        function closeMenu() {
            dropdownMenu.classList.remove('open');
            overlay.classList.remove('active');
            menuButton.setAttribute('aria-expanded', 'false');
        }

        menuButton.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdownMenu.classList.contains('open') ? closeMenu() : openMenu();
        });

        overlay.addEventListener('click', closeMenu);

        dropdownMenu.querySelectorAll('.menu-item').forEach(item => {
            item.addEventListener('click', closeMenu);
        });
    }

    // --- Попапи ---
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

    // --- Форма квитка ---
    const form = document.querySelector('.ticket-form');
    if (!form) return;

    const emailInput = document.getElementById('email');
    const phoneInput = document.getElementById('phone');

    // Форматування номера телефону
    phoneInput.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, '');
        if (value === "") { e.target.value = ""; return; }
        if (!value.startsWith("38")) value = "38" + value;
        value = "+" + value;

        if (value.length >= 4) value = value.replace(/(\+38)(\d{3})/, '$1($2)');
        if (value.length >= 9) value = value.replace(/(\+38\(\d{3}\))(\d{3})/, '$1$2-');
        if (value.length >= 13) value = value.replace(/(\+38\(\d{3}\)\d{3}-)(\d{2})/, '$1$2-');

        e.target.value = value.substring(0, 17);
    });

    phoneInput.addEventListener('keydown', function(e) {
        if (e.key === 'Backspace' || e.key === 'Delete') {
            let pos = this.selectionStart;
            let val = this.value;
            if (pos > 0 && /[\-\(\)\s]/.test(val[pos-1])) {
                e.preventDefault();
                this.value = val.slice(0, pos-1) + val.slice(pos);
                this.setSelectionRange(pos-1, pos-1);
            }
            if (this.value === "+38") { e.preventDefault(); this.value = ""; }
        }
    });

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData();
        formData.append('email', emailInput.value);
        formData.append('phone', phoneInput.value);
        formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));

        const submitBtn = form.querySelector('.submit-button');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Обробка...';
        submitBtn.disabled = true;

        fetch('/submit-ticket/', {
            method: 'POST',
            body: formData,
            headers: { 'X-CSRFToken': getCookie('csrftoken') }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) redirectToWayForPay(data.wayforpay_params);
            else {
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

// --- Глобальні функції ---
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        document.cookie.split(';').forEach(cookie => {
            cookie = cookie.trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
            }
        });
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