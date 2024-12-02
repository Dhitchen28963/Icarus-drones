$(document).ready(function() {
    const countryField = $('#id_default_country');
    const loyaltyPointsField = $('#id_loyalty_points');

    if (!countryField.val()) {
        countryField.css('color', '#aab7c4');
    } else {
        countryField.css('color', '#000');
    }
    loyaltyPointsField.css('color', '#000');

    countryField.change(function() {
        if (!$(this).val()) {
            $(this).css('color', '#aab7c4');
        } else {
            $(this).css('color', '#000');
        }
    });
});
