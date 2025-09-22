 // JavaScript for dropdown menu functionality
  document.addEventListener('DOMContentLoaded', function() {
    const menuToggle = document.querySelector('.menu-toggle');
    const dropdownMenu = document.getElementById('dropdown-menu');
    const menuItems = document.querySelectorAll('.menu-item');

    // Toggle dropdown menu
    menuToggle.addEventListener('click', function(e) {
      e.stopPropagation();
      dropdownMenu.classList.toggle('active');
    });

    // Close menu when clicking outside
    document.addEventListener('click', function(e) {
      if (!e.target.closest('.menu-container')) {
        dropdownMenu.classList.remove('active');
      }
    });

    // Close menu after clicking menu item and smooth scroll
    menuItems.forEach(item => {
      item.addEventListener('click', function(e) {
        e.preventDefault();
        dropdownMenu.classList.remove('active');

        const targetId = this.getAttribute('href').substring(1);
        const targetElement = document.getElementById(targetId);

        if (targetElement) {
          targetElement.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
          });
        }
      });
    });
  });

function checkScreenSize() {
  if (window.innerWidth <= 768) {
    if (!window.location.pathname.includes("/mobile/")) {
      window.location.href = "{% url 'mobile' %}";
    }
  }
}
checkScreenSize();
window.addEventListener("resize", checkScreenSize);

// =============================
// Scale
// =============================

function scalePage() {
    const baseWidth = 1800;
    const wrapper = document.querySelector('.scale-wrapper');

    // обчислюємо масштаб пропорційно ширині вікна
    let scale = window.innerWidth / baseWidth;

    // застосовуємо масштаб
    wrapper.style.transform = `scale(${scale})`;
    wrapper.style.transformOrigin = 'top left';
    wrapper.style.position = 'absolute';
    wrapper.style.top = '0';
    wrapper.style.left = '50%';
    wrapper.style.transform += ' translateX(-50%)'; // центр по горизонталі

    // встановлюємо body розміри, щоб уникнути білого відступу
    const wrapperHeight = wrapper.offsetHeight * scale;
    document.body.style.height = wrapperHeight + 'px';
    document.body.style.width = '100%';
    document.body.style.margin = '0';
    document.body.style.padding = '0';
    document.body.style.overflowX = 'hidden'; // прибираємо горизонтальний скрол
}

// запуск тільки на desktop
if(window.innerWidth > 1024){
    window.addEventListener('resize', scalePage);
    window.addEventListener('load', scalePage);
}