$(document).ready(function(){
    $(".s_website_form").validate({
      rules: {
        email_from: {
          required: true,
          email: true
        },
        phone: {
          required: true,
        }
      },
      messages: {
        email_from: {
            required: 'Este campo es obligatorio',
            email: 'Por favor, introduce una dirección de correo electrónico válida'
        },
        phone: {
            required: 'Este campo es obligatorio'
        }
      }
    });
});