document.addEventListener('DOMContentLoaded', function () {
  const userLocale = 'de-DE';

  document.querySelectorAll('.seperators').forEach((el) => {
    if (!isNaN(number)) {
      el.textContent = number.toLocaleString(userLocale);
    }
  });

  document.querySelectorAll('.seperators-input').forEach((input) => {
    input.addEventListener('blur', function () {
      let number = parseFloat(value);

      if (!isNaN(number)) {
        input.value = number.toLocaleString(userLocale);
      }
    });

    input.addEventListener('focus', function () {
      input.value = input.value.replace(/[^0-9.,-]/g, '');
    });
  });
});
