document.addEventListener('DOMContentLoaded', () => {
    // --- Dropdown меню ---
    const menuToggle = document.querySelector('.menu-toggle');
    const dropdownMenu = document.getElementById('dropdown-menu');
    const menuItems = document.querySelectorAll('.menu-item');

    if (menuToggle && dropdownMenu) {
        menuToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdownMenu.classList.toggle('active');
        });

        document.addEventListener('click', (e) => {
            if (!e.target.closest('.menu-container')) {
                dropdownMenu.classList.remove('active');
            }
        });

        menuItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                dropdownMenu.classList.remove('active');

                const targetId = item.getAttribute('href').substring(1);
                const targetElement = document.getElementById(targetId);
                if (targetElement) {
                    targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            });
        });
    }

    // --- Попапи ---
    document.querySelectorAll('[data-popup]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const popupId = "popup-" + link.dataset.popup;
            const popup = document.getElementById(popupId);
            if (popup) popup.style.display = "flex";
        });
    });

    document.querySelectorAll('.popup-close').forEach(btn => {
        btn.addEventListener('click', () => {
            const popup = btn.closest('.popup');
            if (popup) popup.style.display = "none";
        });
    });

    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('popup')) {
            e.target.style.display = "none";
        }
    });

    // --- Форма квитка ---
    const form = document.querySelector('.ticket-form');
    const emailInput = document.getElementById('email');
    const phoneInput = document.getElementById('phone');

    if (form && emailInput && phoneInput) {
        // Форматування номера телефону
        phoneInput.addEventListener('input', (e) => {
            let value = e.target.value.replace(/\D/g, '');
            if (value === "") { e.target.value = ""; return; }
            if (!value.startsWith("38")) value = "38" + value;
            value = "+" + value;
            if (value.length >= 4) value = value.replace(/(\+38)(\d{3})/, '$1($2)');
            if (value.length >= 9) value = value.replace(/(\+38\(\d{3}\))(\d{3})/, '$1$2-');
            if (value.length >= 13) value = value.replace(/(\+38\(\d{3}\)\d{3}-)(\d{2})/, '$1$2-');
            e.target.value = value.substring(0, 17);
        });

        phoneInput.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace' || e.key === 'Delete') {
                let pos = phoneInput.selectionStart;
                let val = phoneInput.value;
                if (pos > 0 && /[\-\(\)\s]/.test(val[pos-1])) {
                    e.preventDefault();
                    phoneInput.value = val.slice(0, pos-1) + val.slice(pos);
                    phoneInput.setSelectionRange(pos-1, pos-1);
                }
                if (phoneInput.value === "+38") {
                    e.preventDefault();
                    phoneInput.value = "";
                }
            }
        });

        // Відправка форми
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const formData = new FormData();
            formData.append('email', emailInput.value);
            formData.append('phone', phoneInput.value);
            formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));

            const submitBtn = form.querySelector('.submit-ticket-btn');
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
    }

    // --- Масштабування сторінки для desktop ---
    const wrapper = document.querySelector('.scale-wrapper');
    if (wrapper && window.innerWidth > 1024) {
        function scalePage() {
            const baseWidth = 1800;
            let scale = window.innerWidth / baseWidth;
            wrapper.style.transform = `scale(${scale}) translateX(-50%)`;
            wrapper.style.transformOrigin = 'top left';
            wrapper.style.position = 'absolute';
            wrapper.style.top = '0';
            wrapper.style.left = '50%';
            document.body.style.height = (wrapper.offsetHeight * scale) + 'px';
            document.body.style.width = '100%';
            document.body.style.margin = '0';
            document.body.style.padding = '0';
            document.body.style.overflowX = 'hidden';
        }

        window.addEventListener('resize', scalePage);
        window.addEventListener('load', scalePage);
        scalePage();
    }
});

// --- Глобальні функції ---
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        document.cookie.split(';').forEach(cookie => {
            cookie = cookie.trim();
            if (cookie.startsWith(name + '=')) {
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
        if (!input) return;
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