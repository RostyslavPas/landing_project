// --- Зберігаємо UTM у cookies ---
function saveUTMToCookies() {
  const params = new URLSearchParams(window.location.search);
  const utms = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"];
  utms.forEach(name => {
    const value = params.get(name);
    if (value) {
      document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${60 * 60 * 24 * 30}`;
    }
  });
}

// --- Отримуємо UTM з URL або cookies і підставляємо у форму ---
function getUTMParams() {
  const params = new URLSearchParams(window.location.search);
  const cookies = Object.fromEntries(document.cookie.split("; ").map(c => c.split("=")));
  const utms = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"];

  utms.forEach(name => {
    const input = document.getElementById(name);
    if (input) {
      const fromUrl = params.get(name);
      const fromCookie = cookies[name] ? decodeURIComponent(cookies[name]) : "";
      input.value = fromUrl || fromCookie || "";
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  saveUTMToCookies(); // SET
  getUTMParams();     // GET
});

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

    // --- CSRF cookie ---
    function getCookie(name) {
      let cookieValue = null;
      if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
          cookie = cookie.trim();
          if (cookie.startsWith(name + '=')) {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
            break;
          }
        }
      }
      return cookieValue;
    }

    // --- Форма квитка ---
    const form = document.querySelector('.ticket-form');
    const nameInput = document.getElementById('name');
    const emailInput = document.getElementById('email');
    const phoneInput = document.getElementById('phone');
    const nameError = document.getElementById('name-error');
    const emailError = document.getElementById('email-error');
    const phoneError = document.getElementById('phone-error');

    if (form && emailInput && phoneInput && nameInput) {

        // --- Автододавання +38 ---
        phoneInput.addEventListener('focus', () => {
            if (!phoneInput.value.startsWith('+38')) phoneInput.value = '+38';
            if (phoneInput.selectionStart < 3) phoneInput.setSelectionRange(3, 3);
        });

        phoneInput.addEventListener('click', () => {
            if (phoneInput.selectionStart < 3) phoneInput.setSelectionRange(3, 3);
        });

        phoneInput.addEventListener('keyup', () => {
            if (phoneInput.selectionStart < 3) phoneInput.setSelectionRange(3, 3);
        });

        // --- Форматування номера ---
        phoneInput.addEventListener('input', (e) => {
            let value = e.target.value.replace(/\D/g, '');
            if (value === "") {
                e.target.value = "+38";
                phoneInput.setSelectionRange(3, 3);
                return;
            }
            if (!value.startsWith("38")) value = "38" + value;
            value = "+" + value;
            if (value.length >= 4) value = value.replace(/(\+38)(\d{3})/, '$1($2)');
            if (value.length >= 9) value = value.replace(/(\+38\(\d{3}\))(\d{3})/, '$1$2-');
            if (value.length >= 13) value = value.replace(/(\+38\(\d{3}\)\d{3}-)(\d{2})/, '$1$2-');
            e.target.value = value.substring(0, 17);
            validatePhone();
        });

        // --- Backspace/Delete ---
        phoneInput.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace' || e.key === 'Delete') {
                let pos = phoneInput.selectionStart;
                let val = phoneInput.value;
                if (pos <= 3) {
                    e.preventDefault();
                    return;
                }
                if (pos > 0 && /[\-\(\)]/.test(val[pos - 1])) {
                    e.preventDefault();
                    phoneInput.value = val.slice(0, pos - 1) + val.slice(pos);
                    phoneInput.setSelectionRange(pos - 1, pos - 1);
                }
                if (phoneInput.value === "+38") {
                    e.preventDefault();
                    phoneInput.setSelectionRange(3, 3);
                }
            }
        });

        // --- Live валідація ---
        nameInput.addEventListener("input", validateName);
        emailInput.addEventListener("input", validateEmail);
        phoneInput.addEventListener("input", validatePhone);

        function validateName() {
            const nameValue = nameInput.value.trim();
            if (nameValue === "") {
                nameError.textContent = "Прізвище та Ім’я є обов’язковим полем";
                nameError.style.display = "block";
                nameInput.classList.add("input-error");
                return false;
            }
            nameError.style.display = "none";
            nameInput.classList.remove("input-error");
            return true;
        }

        function validateEmail() {
            const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!pattern.test(emailInput.value.trim())) {
                emailError.textContent = "Введіть коректну email адресу";
                emailError.style.display = "block";
                emailInput.classList.add("input-error");
                return false;
            }
            emailError.style.display = "none";
            emailInput.classList.remove("input-error");
            return true;
        }

        function validatePhone() {
            const digits = phoneInput.value.replace(/\D/g, "");
            if (!/^380\d{9}$/.test(digits)) {
                phoneError.textContent = "Номер телефону має бути у форматі +380XXXXXXXXX";
                phoneError.style.display = "block";
                phoneInput.classList.add("input-error");
                return false;
            }
            phoneError.style.display = "none";
            phoneInput.classList.remove("input-error");
            return true;
        }

        // --- Сабміт з WayForPay ---
        form.addEventListener("submit", async function (e) {
            e.preventDefault();

            const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
            const textWrapper = submitBtn.querySelector('.text-wrapper-14');

            if (submitBtn.disabled) return;
            submitBtn.disabled = true;
            if (textWrapper) textWrapper.textContent = 'Обробка...';

            if (!validateEmail() || !validatePhone() || !validateName()) {
                submitBtn.disabled = false;
                if (textWrapper) textWrapper.textContent = 'Оплатити';
                return;
            }

            const formData = new FormData(form);
            const csrfToken = getCookie('csrftoken');

            try {
                const response = await fetch('/submit-ticket/', {
                    method: 'POST',
                    body: formData,
                    headers: {'X-CSRFToken': csrfToken},
                    credentials: 'include'
                });

                const data = await response.json();

                if (data.success && data.wayforpay_params) {
                    // ✅ Якщо все добре — відправляємо на оплату 👇 Відправляємо подію в Meta Pixel

                    if (typeof fbq === 'function') {
                        fbq('track', 'Lead');
                    }

                    redirectToWayForPay(data.wayforpay_params);

                } else if (data.redirect_url) {
                    // ✅ Якщо квитки закінчились — редирект
                    window.location.href = data.redirect_url;

                } else {
                    console.log("❌ Сервер повернув помилку:", data.errors || data.error);
                    submitBtn.disabled = false;
                    if (textWrapper) textWrapper.textContent = 'Оплатити';
                }

            } catch (err) {
                console.log("❌ Fetch error:", err);
                submitBtn.disabled = false;
                if (textWrapper) textWrapper.textContent = 'Оплатити';
            }
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
/*WayForPay settings*/
function redirectToWayForPay(params) {
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = 'https://secure.wayforpay.com/pay';

    Object.keys(params).forEach(key => {
        const value = params[key];

        if (Array.isArray(value)) {
            value.forEach(item => {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = key;  // наприклад "productName[]"
                input.value = item;
                form.appendChild(input);
            });
        } else {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = key;
            input.value = value;
            form.appendChild(input);
        }
    });

    document.body.appendChild(form);
    form.submit();
}