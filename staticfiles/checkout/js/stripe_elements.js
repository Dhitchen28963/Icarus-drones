/* jshint esversion: 6 */
/* global Stripe */
// Extract public key and client secret
var stripePublicKey = $('#id_stripe_public_key').text().slice(1, -1);
var clientSecret = $('#id_client_secret').text().slice(1, -1);

// Initialize Stripe with the required beta flag and API version
var stripe = Stripe(stripePublicKey, {
    apiVersion: '2023-10-16',
    betas: ['payment_intent_beta_v3']
});

// Initialize elements and styling
var elements = stripe.elements();
var style = {
    base: {
        color: '#000',
        fontFamily: '"Helvetica Neue", Helvetica, sans-serif',
        fontSmoothing: 'antialiased',
        fontSize: '16px',
        '::placeholder': {
            color: '#aab7c4'
        }
    },
    invalid: {
        color: '#dc3545',
        iconColor: '#dc3545'
    }
};
var card = elements.create('card', { style: style });

card.mount('#card-element');

// Handle real-time validation errors
card.addEventListener('change', function (event) {
    var errorDiv = document.getElementById('card-errors');
    if (event.error) {
        var html = `
            <span class="icon" role="alert">
                <i class="fas fa-times"></i>
            </span>
            <span>${event.error.message}</span>
        `;
        $(errorDiv).html(html);
    } else {
        errorDiv.textContent = '';
    }
});

// Modify loyalty points input handling
document.getElementById('loyalty-points-input').addEventListener('input', function () {
    const points = parseInt(this.value) || 0;
    const hiddenInput = document.getElementById('hidden-loyalty-points');
    hiddenInput.value = points;

    const discountPerPoint = 0.10;
    const discountAmount = (points * discountPerPoint).toFixed(2);

    const discountDisplay = document.getElementById('discount-display');
    if (discountDisplay) {
        discountDisplay.textContent = `$${discountAmount}`;
    }

    if (clientSecret) {
        const total = parseFloat($('[data-total]').data('total'));
        const newAmount = Math.round((total - discountAmount) * 100);

        stripe.retrievePaymentIntent(clientSecret)
            .then(function (result) {
                const paymentIntent = result.paymentIntent;

                if (['requires_payment_method', 'requires_confirmation', 'requires_action'].includes(paymentIntent.status)) {
                    return fetch('/checkout/update_payment_intent/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                        },
                        body: JSON.stringify({
                            client_secret: clientSecret,
                            amount: newAmount
                        })
                    })
                        .then(response => {
                            if (!response.ok) {
                                return response.text().then(text => {
                                    throw new Error(`Server Error: ${text}`);
                                });
                            }
                            return response.json();
                        })
                        .then(data => {
                            if (data.client_secret) {
                                clientSecret = data.client_secret;
                            }
                        })
                        .catch(error => console.error('Fetch Error:', error));
                }
            })
            .catch(function (error) {
                console.error('PaymentIntent Update Error:', error);
            });
    }
});

// Handle form submission
var form = document.getElementById('payment-form');
form.addEventListener('submit', function (ev) {
    ev.preventDefault();

    card.update({ 'disabled': true });
    $('#submit-button').attr('disabled', true);
    $('#payment-form').fadeToggle(100);
    $('#loading-overlay').fadeToggle(100);

    const points = parseInt(document.getElementById('loyalty-points-input').value) || 0;
    document.getElementById('hidden-loyalty-points').value = points;

    const saveInfo = Boolean($('#id-save-info').attr('checked'));
    const csrfToken = $('input[name="csrfmiddlewaretoken"]').val();

    var postData = {
        'csrfmiddlewaretoken': csrfToken,
        'client_secret': clientSecret,
        'save_info': saveInfo,
        'loyalty_points': points
    };

    // Send loyalty points and save info to backend
    $.ajax({
        url: '/checkout/cache_checkout_data/',
        type: 'POST',
        data: postData,
        success: function () {
            stripe.confirmCardPayment(clientSecret, {
                payment_method: {
                    card: card,
                    billing_details: {
                        name: $.trim(form.full_name.value),
                        phone: $.trim(form.phone_number.value),
                        email: $.trim(form.email.value),
                        address: {
                            line1: $.trim(form.street_address1.value),
                            line2: $.trim(form.street_address2.value),
                            city: $.trim(form.town_or_city.value),
                            country: $.trim(form.country.value),
                            state: $.trim(form.county.value),
                        }
                    }
                },
                shipping: {
                    name: $.trim(form.full_name.value),
                    phone: $.trim(form.phone_number.value),
                    address: {
                        line1: $.trim(form.street_address1.value),
                        line2: $.trim(form.street_address2.value),
                        city: $.trim(form.town_or_city.value),
                        country: $.trim(form.country.value),
                        postal_code: $.trim(form.postcode.value),
                        state: $.trim(form.county.value),
                    }
                }
            }).then(function (result) {
                if (result.error) {
                    var errorDiv = document.getElementById('card-errors');
                    var html = `
                        <span class="icon" role="alert">
                            <i class="fas fa-times"></i>
                        </span>
                        <span>${result.error.message}</span>`;
                    $(errorDiv).html(html);
                    $('#payment-form').fadeToggle(100);
                    $('#loading-overlay').fadeToggle(100);
                    card.update({ 'disabled': false });
                    $('#submit-button').attr('disabled', false);
                } else {
                    if (result.paymentIntent.status === 'succeeded') {
                        form.submit();
                    }
                }
            });
        },
        error: function () {
            location.reload();
        }
    });
});
