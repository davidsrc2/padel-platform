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
