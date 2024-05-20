$(document).ready(function() {
    $('#downloadForm').on('submit', function(e) {
        e.preventDefault();
        $(this).find(':submit').attr('disabled', 'disabled');  // Disable the submit button after first submission to not overload the app 
        $.ajax({
            url: $(this).attr('action'),
            type: $(this).attr('method'),
            data: $(this).serialize(),
            success: function(data) {
                $('#flashMessages').html('<ul class="flashes"><li>' + data.message + '</li></ul>');
            },
            complete: function() {
                $('#downloadForm').find(':submit').removeAttr('disabled');  // Enable the submit button again when the AJAX request is complete
            }
        });
    });
});