$(document).on('input', '.firstname', function() {
    var name = $(this).val();
    var error_class = $(this).attr('name') + '_err';

    if (!/^[a-zA-Z]*$/.test(name)) {
        $('.' + error_class).show().text('Only letters are allowed.');
    } else {
        $('.' + error_class).hide().text('');
    }

    var sanitizedName = name.replace(/[^a-zA-Z]/g, '');

    if (sanitizedName.length > 0) {
        sanitizedName = sanitizedName.charAt(0).toUpperCase() + sanitizedName.slice(1).toLowerCase();
    }

    $(this).val(sanitizedName);
});

$(document).on('input', '.percentage', function() {
    var value = $(this).val();
    var error_class = $(this).attr('name') + '_err';

    // Allow only numbers with up to 2 decimal places
    if (!/^\d{0,2}(\.\d{0,2})?$/.test(value)) {
        $('.' + error_class).show().text('Enter a valid percentage (max 2 digits, up to 2 decimal places).');
    } else {
        $('.' + error_class).hide().text('');
    }

    // Remove non-numeric and multiple decimal points
    var sanitizedValue = value.replace(/[^0-9.]/g, ''); // Remove alphabets and special characters except '.'

    var parts = sanitizedValue.split('.');
    
    // Ensure only one decimal point
    if (parts.length > 2) {
        sanitizedValue = parts[0] + '.' + parts.slice(1).join('');
    }

    // Limit integer part to 2 digits
    if (parts[0].length > 2) {
        sanitizedValue = parts[0].slice(0, 2) + (parts.length > 1 ? '.' + parts[1] : '');
    }

    // Limit decimal part to 2 digits
    if (parts.length === 2 && parts[1].length > 2) {
        sanitizedValue = parts[0] + '.' + parts[1].substring(0, 2);
    }

    $(this).val(sanitizedValue);
});


$(document).on('input', '.name', function() {
    var name = $(this).val();
    var error_class = $(this).attr('name') + '_err';

    if (!/^[a-zA-Z ]*$/.test(name)) {
        $('.' + error_class).show().text('Only letters and spaces are allowed.');
    } else {
        $('.' + error_class).hide().text('');
    }

    var sanitizedName = name.replace(/[^a-zA-Z ]/g, '');

    sanitizedName = sanitizedName.replace(/^\s+/, '');

    sanitizedName = sanitizedName.replace(/\s{2,}/g, ' ');

    sanitizedName = sanitizedName.replace(/\b\w/g, function(match) {
        return match.toUpperCase();
    });

    $(this).val(sanitizedName);
});

$(document).on('input', '.username', function() {
    var username = $(this).val();
    var error_class = $(this).attr('name') + '_err';
    
    if (!/^[a-zA-Z0-9_]*$/.test(username)) {
        $('.' + error_class).show().text('Only numbers, letters, and underscore are allowed.');
    }else {
        $('.' + error_class).hide().text('');
    }
    
    var sanitizedUsername = username.replace(/[^a-zA-Z0-9_]/g, ''); 

    sanitizedUsername = sanitizedUsername.toLowerCase(); 
    $(this).val(sanitizedUsername); 
});

$(document).on('input', '.email', function() {
    var email = $(this).val().toLowerCase(); 
    var errorClass = $(this).attr('name') + '_err';

    var emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

    if (!emailRegex.test(email)) {
        $('.' + errorClass).show().text('Enter a valid email address.');
    } else {
        $('.' + errorClass).hide().text('');
    }
    

    $(this).val(email); // Update input with lowercase value
});

$(document).on('input', '.mobile', function() {
    var mobile = $(this).val();
    var error_class = $(this).attr('name') + '_err';

    // Remove non-numeric characters
    var sanitizedMobile = mobile.replace(/[^0-9]/g, '');

    // Max length 10 
    sanitizedMobile = sanitizedMobile.substring(0, 10);
    
    // Check if first digit is greater than 5
    if (sanitizedMobile.length > 0 && sanitizedMobile.charAt(0) <= '5') {
        $('.' + error_class).show().text('Invalid Mobile Number.');
    } else {
        $('.' + error_class).hide().text('');
    }

    $(this).val(sanitizedMobile);
});

$(document).on('input', '.aadhar', function() {
    var aadhar = $(this).val();
    var error_class = $(this).attr('name') + '_err';

    // Remove non-numeric characters
    var sanitizedAadhar = aadhar.replace(/[^0-9]/g, '');

    // Max length 10 
    sanitizedAadhar = sanitizedAadhar.substring(0, 12);
    
    // Check if first digit is greater than 5
    if (sanitizedAadhar.length > 0 && sanitizedAadhar.charAt(0) == '0') {
        $('.' + error_class).show().text('Invalid Aadhar Number.');
    } else {
        $('.' + error_class).hide().text('');
    }

    $(this).val(sanitizedAadhar);
});

$(document).on('input', '.pan', function() {
    var panInput = $(this);
    var pan = panInput.val().replace(/[^a-zA-Z0-9]/g, ''); // remove non-alphanumeric characters
    pan = pan.toUpperCase().substring(0, 10); // convert to uppercase and limit to 10 characters

    var error_class = panInput.attr('name') + '_err';
    var panRegex = /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/;

    // Update the input with sanitized and formatted PAN
    panInput.val(pan);

    // Validate PAN format
    if (pan.length === 10 && !panRegex.test(pan)) {
        $('.' + error_class).show().text('Invalid PAN format.');
    } else {
        $('.' + error_class).hide().text('');
    }
});


$(document).on('input', '.number', function() {
    var value = $(this).val();
    var error_class = $(this).attr('name') + '_err';

    // Allow only numbers with up to 2 decimal places
    if (!/^\d{0,10}(\.\d{0,2})?$/.test(value)) {
        $('.' + error_class).show().text('Enter a valid percentage (max 2 digits, up to 2 decimal places).');
    } else {
        $('.' + error_class).hide().text('');
    }

    // Remove non-numeric and multiple decimal points
    var sanitizedValue = value.replace(/[^0-9.]/g, ''); // Remove alphabets and special characters except '.'

    var parts = sanitizedValue.split('.');
    
    // Ensure only one decimal point
    if (parts.length > 2) {
        sanitizedValue = parts[0] + '.' + parts.slice(1).join('');
    }

    // Limit integer part to 2 digits
    if (parts[0].length > 10) {
        sanitizedValue = parts[0].slice(0, 10) + (parts.length > 1 ? '.' + parts[1] : '');
    }

    // Limit decimal part to 2 digits
    if (parts.length === 2 && parts[1].length > 2) {
        sanitizedValue = parts[0] + '.' + parts[1].substring(0, 2);
    }

    $(this).val(sanitizedValue);
});


$(document).on('input', '.amount-number', function() {
    var value = $(this).val();
    var error_class = $(this).attr('name') + '_err';

    // Allow only numbers with up to 2 decimal places
    if (!/^\d{0,4}(\.\d{0,2})?$/.test(value)) {
        $('.' + error_class).show().text('Enter a valid percentage (max 2 digits, up to 2 decimal places).');
    } else {
        $('.' + error_class).hide().text('');
    }

    // Remove non-numeric and multiple decimal points
    var sanitizedValue = value.replace(/[^0-9.]/g, ''); // Remove alphabets and special characters except '.'

    var parts = sanitizedValue.split('.');
    
    // Ensure only one decimal point
    if (parts.length > 2) {
        sanitizedValue = parts[0] + '.' + parts.slice(1).join('');
    }

    // Limit integer part to 2 digits
    if (parts[0].length > 4) {
        sanitizedValue = parts[0].slice(0, 4) + (parts.length > 1 ? '.' + parts[1] : '');
    }

    // Limit decimal part to 2 digits
    if (parts.length === 2 && parts[1].length > 2) {
        sanitizedValue = parts[0] + '.' + parts[1].substring(0, 2);
    }

    $(this).val(sanitizedValue);
});