// Service worker mínimo, sin caché. Existe solo para cumplir el criterio
// de "instalable" de Chrome/Android al añadir la web a la pantalla de inicio.
// No cachea nada a propósito: esta app muestra disponibilidad de reservas
// en vivo, y servir respuestas cacheadas mostraría datos obsoletos.

self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', () => {
  // Sin respondWith(): deja pasar la petición normal a la red.
});

self.addEventListener('push', (event) => {
  let datos = {};
  try {
    datos = event.data ? event.data.json() : {};
  } catch (e) {
    datos = {};
  }
  const titulo = datos.titulo || 'Pádel';
  const opciones = {
    body: datos.cuerpo || '',
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/icon-192.png',
    data: { url: datos.url || '/' },
  };
  event.waitUntil(self.registration.showNotification(titulo, opciones));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || '/';
  event.waitUntil(self.clients.openWindow(url));
});
