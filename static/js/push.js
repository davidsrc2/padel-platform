function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}

async function enviarAlServidor(url, cuerpo) {
  await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken'),
    },
    body: JSON.stringify(cuerpo),
  });
}

async function actualizarBotonPush() {
  const boton = document.getElementById('push-toggle');
  if (!boton) return;

  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    boton.textContent = 'Notificaciones push no disponibles en este navegador';
    boton.disabled = true;
    return;
  }

  const registro = await navigator.serviceWorker.ready;
  const suscripcion = await registro.pushManager.getSubscription();
  boton.textContent = suscripcion ? 'Desactivar notificaciones push' : 'Activar notificaciones push';
}

async function alternarPush() {
  const vapidKey = document.querySelector('meta[name=vapid-public-key]')?.content;
  if (!vapidKey) {
    alert('Las notificaciones push no están configuradas en este servidor todavía.');
    return;
  }

  const registro = await navigator.serviceWorker.ready;
  const suscripcionActual = await registro.pushManager.getSubscription();

  if (suscripcionActual) {
    await enviarAlServidor('/accounts/push/desuscribir/', { endpoint: suscripcionActual.endpoint });
    await suscripcionActual.unsubscribe();
    await actualizarBotonPush();
    return;
  }

  const permiso = await Notification.requestPermission();
  if (permiso !== 'granted') {
    alert('Has bloqueado los avisos. Actívalos desde los ajustes del navegador si cambias de idea.');
    return;
  }

  const nuevaSuscripcion = await registro.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(vapidKey),
  });
  await enviarAlServidor('/accounts/push/suscribir/', nuevaSuscripcion.toJSON());
  await actualizarBotonPush();
}

document.addEventListener('DOMContentLoaded', () => {
  const boton = document.getElementById('push-toggle');
  if (boton) {
    boton.addEventListener('click', alternarPush);
    actualizarBotonPush();
  }
});
