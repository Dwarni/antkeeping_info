(function () {
    var modalEl = document.getElementById('journal-image-lightbox');
    if (!modalEl) return;

    var img = document.getElementById('journal-image-lightbox-img');
    var caption = document.getElementById('journal-image-lightbox-caption');
    var originalLink = document.getElementById('journal-image-lightbox-original');
    var prevBtn = document.getElementById('journal-image-lightbox-prev');
    var nextBtn = document.getElementById('journal-image-lightbox-next');

    var modal = new bootstrap.Modal(modalEl);
    var gallery = [];
    var index = 0;

    function show(newIndex) {
        if (!gallery.length) return;
        index = (newIndex + gallery.length) % gallery.length;
        var item = gallery[index];

        img.src = item.fullSrc;
        img.alt = item.caption;
        originalLink.href = item.fullSrc;

        caption.textContent = item.caption;
        caption.classList.toggle('d-none', !item.caption);

        var multiple = gallery.length > 1;
        prevBtn.classList.toggle('d-none', !multiple);
        nextBtn.classList.toggle('d-none', !multiple);
    }

    document.addEventListener('click', function (e) {
        var trigger = e.target.closest('.journal-photo-thumb');
        if (!trigger) return;
        e.preventDefault();

        var galleryKey = trigger.dataset.gallery || '';
        var nodes = galleryKey
            ? document.querySelectorAll('.journal-photo-thumb[data-gallery="' + CSS.escape(galleryKey) + '"]')
            : [trigger];

        gallery = Array.prototype.map.call(nodes, function (node) {
            return {
                fullSrc: node.dataset.fullSrc,
                caption: node.dataset.caption || ''
            };
        });

        var clickedIndex = Array.prototype.indexOf.call(nodes, trigger);
        show(clickedIndex < 0 ? 0 : clickedIndex);
        modal.show();
    });

    prevBtn.addEventListener('click', function () { show(index - 1); });
    nextBtn.addEventListener('click', function () { show(index + 1); });

    modalEl.addEventListener('keydown', function (e) {
        if (e.key === 'ArrowLeft') {
            show(index - 1);
        } else if (e.key === 'ArrowRight') {
            show(index + 1);
        }
    });
})();
