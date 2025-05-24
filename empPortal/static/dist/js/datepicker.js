$('.dob_datepicker').datepicker({
    // format: 'dd/mm/yyyy' 
    dateFormat: 'yy-mm-dd',
    changeMonth: true,
    changeYear: true,
    yearRange: "-100:+0", // last hundred years
    maxDate: 0,
});
$('.datepicker_common').datepicker({
    dateFormat: 'yy-mm-dd',
    changeMonth: true,
    changeYear: true,
});

$('.policy_dates_datepicker').datepicker({
    dateFormat: 'yy-mm-dd',
    changeMonth: true,
    changeYear: true,
    yearRange: "-5:+5", // 5 years last and 5 years forward
});
$('.datepicker_common').datepicker({
    dateFormat: 'yy-mm-dd',
    changeMonth: true,
    changeYear: true,
});