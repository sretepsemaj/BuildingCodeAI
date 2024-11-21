// Main JavaScript file

// Handle message dismissal
document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide messages after 5 seconds
    const messages = document.querySelectorAll('.messages .alert');
    messages.forEach(function(message) {
        setTimeout(function() {
            message.style.opacity = '0';
            setTimeout(function() {
                message.remove();
            }, 300);
        }, 5000);
    });

    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            const requiredFields = form.querySelectorAll('[required]');
            requiredFields.forEach(function(field) {
                if (!field.value) {
                    event.preventDefault();
                    field.classList.add('error');
                } else {
                    field.classList.remove('error');
                }
            });
        });
    });
});
