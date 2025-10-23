document.addEventListener('DOMContentLoaded', () => {
    // --- Dropdown меню ---
    const menuToggle = document.querySelector('.menu-toggle');
    const dropdownMenu = document.getElementById('dropdown-menu');
    const menuItems = document.querySelectorAll('.menu-item');

    if (menuToggle && dropdownMenu) {
        menuToggle.addEventListener('click', () => {
            dropdownMenu.classList.toggle('show');
        });

        // Закриття меню при кліку поза ним
        document.addEventListener('click', (e) => {
            if (!menuToggle.contains(e.target) && !dropdownMenu.contains(e.target)) {
                dropdownMenu.classList.remove('show');
            }
        });

        // Плавна прокрутка до секцій
        menuItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = item.getAttribute('href');
                if (targetId.startsWith('#')) {
                    const targetElement = document.querySelector(targetId);
                    if (targetElement) {
                        targetElement.scrollIntoView({
                            behavior: 'smooth',
                            block: 'start'
                        });
                    }
                }
                dropdownMenu.classList.remove('show');
            });
        });
    }

    // --- Popup функціональність ---
    const popupTriggers = document.querySelectorAll('[data-popup]');
    const popups = document.querySelectorAll('.popup');
    const popupCloses = document.querySelectorAll('.popup-close');

    popupTriggers.forEach(trigger => {
        trigger.addEventListener('click', (e) => {
            e.preventDefault();
            const popupId = trigger.getAttribute('data-popup');
            const popup = document.getElementById(`popup-${popupId}`);
            if (popup) {
                popup.classList.add('show');
                document.body.style.overflow = 'hidden';
            }
        });
    });

    popupCloses.forEach(close => {
        close.addEventListener('click', () => {
            const popup = close.closest('.popup');
            if (popup) {
                popup.classList.remove('show');
                document.body.style.overflow = '';
            }
        });
    });

    popups.forEach(popup => {
        popup.addEventListener('click', (e) => {
            if (e.target === popup) {
                popup.classList.remove('show');
                document.body.style.overflow = '';
            }
        });
    });

    // --- Валідація форми ---
    const form = document.querySelector('.subscription-form');
    const nameInput = document.getElementById('name');
    const emailInput = document.getElementById('email');
    const phoneInput = document.getElementById('phone');

    function validateName() {
        const name = nameInput.value.trim();
        const nameError = document.getElementById('name-error');
        
        if (name.length < 2) {
            nameError.textContent = 'Ім\'я повинно містити мінімум 2 символи';
            nameError.style.display = 'block';
            nameInput.style.borderColor = '#ff4757';
            return false;
        }
        
        nameError.style.display = 'none';
        nameInput.style.borderColor = 'rgba(243, 236, 236, 0.2)';
        return true;
    }

    function validateEmail() {
        const email = emailInput.value.trim();
        const emailError = document.getElementById('email-error');
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        
        if (!emailRegex.test(email)) {
            emailError.textContent = 'Введіть коректний email';
            emailError.style.display = 'block';
            emailInput.style.borderColor = '#ff4757';
            return false;
        }
        
        emailError.style.display = 'none';
        emailInput.style.borderColor = 'rgba(243, 236, 236, 0.2)';
        return true;
    }

    function validatePhone() {
        const phone = phoneInput.value.trim();
        const phoneError = document.getElementById('phone-error');
        const phoneRegex = /^[\+]?[0-9\s\-\(\)]{10,}$/;
        
        if (!phoneRegex.test(phone)) {
            phoneError.textContent = 'Введіть коректний номер телефону';
            phoneError.style.display = 'block';
            phoneInput.style.borderColor = '#ff4757';
            return false;
        }
        
        phoneError.style.display = 'none';
        phoneInput.style.borderColor = 'rgba(243, 236, 236, 0.2)';
        return true;
    }

    // Валідація в реальному часі
    if (nameInput) nameInput.addEventListener('blur', validateName);
    if (emailInput) emailInput.addEventListener('blur', validateEmail);
    if (phoneInput) phoneInput.addEventListener('blur', validatePhone);

    // --- Функція для отримання CSRF токена ---
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

    // --- Telegram функція ---
    window.openTelegram = function(event) {
        event.preventDefault();
        window.open('https://t.me/+380684437882', '_blank');
    };

    // --- Плавна прокрутка для CTA кнопок ---
    const ctaButtons = document.querySelectorAll('a[href^="#"]');
    ctaButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = button.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
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