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
        link.addEventListener('click', function (e) {
            e.preventDefault();
            let popupId = "popup-" + this.dataset.popup;
            document.getElementById(popupId).style.display = "flex";
        });
    });

    document.querySelectorAll('.popup-close').forEach(btn => {
        btn.addEventListener('click', function () {
            this.closest('.popup').style.display = "none";
        });
    });

    window.addEventListener('click', function (e) {
        if (e.target.classList.contains('popup')) {
            e.target.style.display = "none";
        }
    });

  // --- Форма квитка ---
    const form = document.querySelector('.ticket-form');
    const nameInput = document.getElementById('name');
    const emailInput = document.getElementById('email');
    const phoneInput = document.getElementById('phone');

    if (form && emailInput && phoneInput && nameInput) {

      // --- Автододавання +38 ---
      const setCursorAfterCode = () => {
        if (phoneInput.selectionStart < 3) phoneInput.setSelectionRange(3, 3);
      };

      phoneInput.addEventListener('focus', () => {
        if (!phoneInput.value.startsWith('+38')) phoneInput.value = '+38';
        setCursorAfterCode();
      });

      phoneInput.addEventListener('click', setCursorAfterCode);
      phoneInput.addEventListener('keyup', setCursorAfterCode);

      // --- Форматування номера ---
      phoneInput.addEventListener('input', (e) => {
        let value = e.target.value.replace(/\D/g, '');
        if (value === "") { e.target.value = "+38"; setCursorAfterCode(); return; }
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
          if (pos <= 3) { e.preventDefault(); return; }
          if (pos > 0 && /[\-\(\)]/.test(val[pos - 1])) {
            e.preventDefault();
            phoneInput.value = val.slice(0, pos - 1) + val.slice(pos);
            phoneInput.setSelectionRange(pos - 1, pos - 1);
          }
          if (phoneInput.value === "+38") { e.preventDefault(); setCursorAfterCode(); }
        }
      });

      // --- Live валідація ---
      const validateName = () => {
        if (nameInput.value.trim() === "") {
          nameInput.classList.add("input-error");
          nameInput.classList.remove("input-valid");
          return false;
        }
        nameInput.classList.remove("input-error");
        nameInput.classList.add("input-valid");
        return true;
      };

      const validateEmail = () => {
        const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!pattern.test(emailInput.value.trim())) {
          emailInput.classList.add("input-error");
          emailInput.classList.remove("input-valid");
          return false;
        }
        emailInput.classList.remove("input-error");
        emailInput.classList.add("input-valid");
        return true;
      };

      const validatePhone = () => {
        const digits = phoneInput.value.replace(/\D/g, "");
        if (!/^380\d{9}$/.test(digits)) {
          phoneInput.classList.add("input-error");
          phoneInput.classList.remove("input-valid");
          return false;
        }
        phoneInput.classList.remove("input-error");
        phoneInput.classList.add("input-valid");
        return true;
      };

      nameInput.addEventListener("input", validateName);
      emailInput.addEventListener("input", validateEmail);
      phoneInput.addEventListener("input", validatePhone);

      // --- Сабміт з WayForPay ---
      form.addEventListener("submit", async function(e) {
        e.preventDefault();

        let isValid = true;
      // Перевірка name
        if (nameInput.value.trim() === "") {
            nameInput.classList.add("input-error");
            nameInput.classList.remove("input-valid");
            isValid = false;
        } else {
            nameInput.classList.remove("input-error");
            nameInput.classList.add("input-valid");
        }

      // Перевірка email
        if (emailInput.value.trim() === "") {
            emailInput.classList.add("input-error");
            emailInput.classList.remove("input-valid");
            isValid = false;
          } else {
            const isEmailValid = validateEmail();
            if (!isEmailValid) {
              isValid = false;
            }
          }

      // Перевірка телефону
        if (phoneInput.value.trim() === "" || phoneInput.value === "+38") {
            phoneInput.classList.add("input-error");
            phoneInput.classList.remove("input-valid");
            isValid = false;
          } else {
            const isPhoneValid = validatePhone();
            if (!isPhoneValid) {
              isValid = false;
            }
          }

        if (!isValid) return; // блокуємо сабміт

        // if (!isEmailValid || !isPhoneValid) return; // блокуємо сабміт

        const formData = new FormData(form);
        const csrfToken = getCookie('csrftoken');

        try {
          const response = await fetch('/submit-ticket/', {
            method: 'POST',
            body: formData,
            headers: { 'X-CSRFToken': csrfToken },
            credentials: 'include'
          });

          if (!response.ok) {
            console.log("❌ Помилка від сервера:", response.status);
            return; // alert прибрано
          }

          const data = await response.json();

          if (data.success && data.wayforpay_params) {
            redirectToWayForPay(data.wayforpay_params);
          } else {
            // Підсвічуємо поля червоним, якщо сервер повернув помилку
            if (data.errors?.name) nameInput.classList.add("input-error");
            if (data.errors?.email) emailInput.classList.add("input-error");
            if (data.errors?.phone) phoneInput.classList.add("input-error");
            console.log("❌ Сервер повернув помилку:", data.errors);
          }

        } catch (err) {
          console.log("❌ Fetch error:", err); // alert прибрано
        } finally {
          form.classList.remove("loading");
        }
      });
    }
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

document.querySelector('.ticket-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);

    const response = await fetch('/submit-ticket/', {
        method: 'POST',
        body: formData,
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        credentials: 'include'
    });

    const data = await response.json();
    if (data.success) {
        redirectToWayForPay(data.wayforpay_params);
    } else {
        alert('Помилка форми');
    }
});
