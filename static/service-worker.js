const CACHE_NAME = 'pasue-v2'; // 👈 міняй номер версії при оновленні
const URLS_TO_CACHE = [
  '/',
  '/static/images/apple-touch-icon.png',
  '/static/images/pasue_favicon.png',
  '/static/css/subscription.css',
  '/static/css/subscription_mobile.css',
  '/static/js/subscription.js',
];

// 📦 Встановлення та кешування
self.addEventListener('install', (event) => {
  console.log('🪄 Service Worker встановлено');
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(URLS_TO_CACHE))
  );
});

// ♻️ Активуємо нову версію і очищаємо старі кеші
self.addEventListener('activate', (event) => {
  console.log('♻️ Service Worker активовано');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => {
            console.log('🧹 Видаляємо старий кеш:', name);
            return caches.delete(name);
          })
      );
    })
  );
});

// ⚡ Обробка запитів (спочатку з кешу, потім із мережі)
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) return cachedResponse;
      return fetch(event.request)
        .then((response) => {
          // 🧠 Можна кешувати динамічно, якщо треба
          return response;
        })
        .catch(() => cachedResponse);
    })
  );
});
