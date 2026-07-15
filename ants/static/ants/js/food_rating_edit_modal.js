(function () {
    var modalEl = document.getElementById('foodRatingEditModal');
    if (!modalEl) return;
    var container = document.getElementById('food-rating-edit-form-container');

    // Clear stale content on close so reopening for a different submission
    // doesn't briefly flash the previous submission's data before hx-get refills it.
    modalEl.addEventListener('hidden.bs.modal', function () {
        if (container) container.innerHTML = '';
    });

    document.body.addEventListener('foodRatingEditSuccess', function () {
        var modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) modal.hide();
        var toastEl = document.getElementById('foodRatingEditSuccessToast');
        if (toastEl) new bootstrap.Toast(toastEl).show();
    });
})();
