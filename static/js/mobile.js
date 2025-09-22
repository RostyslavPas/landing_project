function checkScreenSize() {
  if (window.innerWidth > 768) {
    if (window.location.pathname.includes("/mobile/")) {
      window.location.href = "{% url 'index' %}";
    }
  }
}
checkScreenSize();
window.addEventListener("resize", checkScreenSize);

// =============================
// Dropdown menu
// =============================

document.addEventListener('DOMContentLoaded', () => {
  const menuButton = document.querySelector('.menu-button');
  const dropdownMenu = document.querySelector('.dropdown-menu');
  const overlay = document.querySelector('.menu-overlay');

  if (!menuButton || !dropdownMenu || !overlay) return;

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
});