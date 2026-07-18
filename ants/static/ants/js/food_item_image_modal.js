(function () {
    var modalEl = document.getElementById('food-item-image-modal');
    if (!modalEl) return;

    var img = document.getElementById('food-item-image-modal-img');
    var label = document.getElementById('food-item-image-modal-label');
    var attributionWrap = document.getElementById('food-item-image-modal-attribution');
    var photoLabel = document.getElementById('food-item-image-modal-photo-label');
    var authorEl = document.getElementById('food-item-image-modal-author');
    var licenseEl = document.getElementById('food-item-image-modal-license');

    modalEl.addEventListener('show.bs.modal', function (event) {
        var trigger = event.relatedTarget;
        if (!trigger) return;

        var name = trigger.dataset.name || '';
        var author = trigger.dataset.author || '';
        var licenseLabel = trigger.dataset.licenseLabel || '';
        var licenseHref = trigger.dataset.licenseHref || '';

        img.src = trigger.dataset.fullSrc || '';
        img.alt = name;
        label.textContent = name;

        authorEl.textContent = author;
        photoLabel.classList.toggle('d-none', !author);

        if (licenseLabel) {
            licenseEl.textContent = licenseLabel;
            licenseEl.href = licenseHref || '#';
            licenseEl.classList.remove('d-none');
        } else {
            licenseEl.classList.add('d-none');
        }

        attributionWrap.classList.toggle('d-none', !author && !licenseLabel);
    });
})();
