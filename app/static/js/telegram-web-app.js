/**
 * Fallback-заглушка Telegram WebApp SDK.
 *
 * Используется, когда telegram.org недоступен (Россия, блокировки).
 * В реальном Telegram SDK перезапишет этот объект поверх.
 *
 * Все методы — пустышки. `initDataUnsafe.user` пуст.
 * Игра работает в браузере, но без вибрации и реального telegram_id.
 */
window.Telegram = window.Telegram || {};
window.Telegram.WebApp = window.Telegram.WebApp || {
    ready: function() {},
    expand: function() {},
    close: function() {},
    disableVerticalSwipes: function() {},
    initData: '',
    initDataUnsafe: {},
    HapticFeedback: null,
    openInvoice: function(url, cb) { if (cb) cb('failed'); },
};
