  $('nav .dropdown-menu, .shorting-dropdown-menu').on('click', function(event) {
      event.stopPropagation();
  });

// When dropdown is shown (opened)
$('.dropdown').on('shown.bs.dropdown', function () {
    $('.shorting-select').attr('aria-expanded', "true");
    $('.change-arrow').attr('src', 'assets/image/svg/up-arrow-icon.svg'); // Change to up arrow
});

// When dropdown is hidden (closed)
$('.dropdown').on('hidden.bs.dropdown', function () {
    $('.shorting-select').attr('aria-expanded', "false");
    $('.change-arrow').attr('src', 'assets/image/svg/down-arrow-icon.svg'); // Change back to down arrow
});


// increament and decrement counter with max limit
$('.quantity').each(function() {
    const container = $(this);
    const minus = container.find('.quantity_minus');
    const plus = container.find('.quantity_plus');
    const input = container.find('.quantity_input');
    const maxLimit = parseInt(container.attr('data-max')); // Get max limit

    function updateButtons() {
        let value = parseInt(input.val());
        minus.prop('disabled', value <= 1); // Disable minus at 1
        plus.prop('disabled', value >= maxLimit); // Disable plus at max limit
    }

    minus.click(function(e) {
        e.preventDefault();
        let value = parseInt(input.val());
        if (value > 1) {
            input.val(--value);
        }
        updateButtons();
    });

    plus.click(function(e) {
        e.preventDefault();
        let value = parseInt(input.val());
        if (value < maxLimit) {
            input.val(++value);
        }
        updateButtons();
    });

    updateButtons(); // Initialize button states
});

// 
$("#health-insurance-child").click(function() {
  if ($(this).is(":checked")) {
   $("li").closest(".increment-decreament").show();
  } else {
    $(".increment-decreament").hide();
  }
});


$('input[name="insurer-choose"]').change(function () {
    // Find the closest <li> and toggle its .increment-decreament div
$(this).closest('li').find('.increment-decreament').toggle(this.checked);
});

//Health journey new and renew policy 
$("#new-policy-btn").click(function(){
  $("#new-policy").css({"display":"flex"});
  $("#renew-policy").css({"display":"none"})
})
$("#renew-policy-btn").click(function(){
  $("#renew-policy").css({"display":"flex"})
  $("#new-policy").css({"display":"none"});
  
})