(function () {
    function initLightbox() {
        var modalEl = document.getElementById('journal-image-lightbox');
        if (!modalEl) return;

        var img = document.getElementById('journal-image-lightbox-img');
        var caption = document.getElementById('journal-image-lightbox-caption');
        var originalLink = document.getElementById('journal-image-lightbox-original');
        var prevBtn = document.getElementById('journal-image-lightbox-prev');
        var nextBtn = document.getElementById('journal-image-lightbox-next');

        var modal = (window.bootstrap && bootstrap.Modal)
            ? (bootstrap.Modal.getOrCreateInstance ? bootstrap.Modal.getOrCreateInstance(modalEl) : new bootstrap.Modal(modalEl))
            : null;

        var gallery = [];
        var index = 0;

        function show(newIndex) {
            if (!gallery.length) return;
            index = (newIndex + gallery.length) % gallery.length;
            var item = gallery[index];

            if (img) {
                img.src = item.fullSrc;
                img.alt = item.caption || '';
            }
            if (originalLink) {
                originalLink.href = item.fullSrc;
            }

            if (caption) {
                caption.textContent = item.caption || '';
                caption.classList.toggle('d-none', !item.caption);
            }

            var multiple = gallery.length > 1;
            if (prevBtn) prevBtn.classList.toggle('d-none', !multiple);
            if (nextBtn) nextBtn.classList.toggle('d-none', !multiple);
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

            if (modal) {
                modal.show();
            } else if (window.bootstrap && bootstrap.Modal) {
                modal = bootstrap.Modal.getOrCreateInstance(modalEl);
                modal.show();
            }
        });

        if (prevBtn) {
            prevBtn.addEventListener('click', function () { show(index - 1); });
        }
        if (nextBtn) {
            nextBtn.addEventListener('click', function () { show(index + 1); });
        }

        document.addEventListener('keydown', function (e) {
            if (!modalEl.classList.contains('show')) return;
            if (e.key === 'ArrowLeft') {
                show(index - 1);
            } else if (e.key === 'ArrowRight') {
                show(index + 1);
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initLightbox);
    } else {
        initLightbox();
    }
})();
