(function () {
    function initPhotoPicker(root) {
        var fileInput = root.querySelector('.photo-picker-file-input');
        var thumbs = root.querySelector('.photo-picker-thumbs');
        var addTile = root.querySelector('.photo-picker-add-tile');
        var maxFiles = parseInt(root.dataset.maxFiles, 10) || 6;
        var files = [];
        var dragIndex = null;

        function syncInputFiles() {
            var dt = new DataTransfer();
            files.forEach(function (file) { dt.items.add(file); });
            fileInput.files = dt.files;
        }

        function render() {
            thumbs.querySelectorAll('.photo-picker-thumb').forEach(function (el) { el.remove(); });

            files.forEach(function (file, index) {
                var thumb = document.createElement('div');
                thumb.className = 'photo-picker-thumb';
                thumb.draggable = true;
                thumb.dataset.index = String(index);

                var img = document.createElement('img');
                img.src = URL.createObjectURL(file);
                img.alt = '';
                thumb.appendChild(img);

                var removeBtn = document.createElement('button');
                removeBtn.type = 'button';
                removeBtn.className = 'btn-close btn-close-white photo-picker-remove';
                removeBtn.setAttribute('aria-label', 'Remove photo');
                thumb.appendChild(removeBtn);

                thumbs.insertBefore(thumb, addTile);
            });

            addTile.disabled = files.length >= maxFiles;
        }

        addTile.addEventListener('click', function () {
            fileInput.click();
        });

        fileInput.addEventListener('change', function () {
            var remaining = maxFiles - files.length;
            Array.prototype.slice.call(fileInput.files, 0, remaining).forEach(function (file) {
                files.push(file);
            });
            syncInputFiles();
            render();
        });

        thumbs.addEventListener('click', function (e) {
            var btn = e.target.closest('.photo-picker-remove');
            if (!btn) return;
            var thumb = btn.closest('.photo-picker-thumb');
            files.splice(parseInt(thumb.dataset.index, 10), 1);
            syncInputFiles();
            render();
        });

        thumbs.addEventListener('dragstart', function (e) {
            var thumb = e.target.closest('.photo-picker-thumb');
            if (!thumb) return;
            dragIndex = parseInt(thumb.dataset.index, 10);
            thumb.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
        });

        thumbs.addEventListener('dragend', function (e) {
            var thumb = e.target.closest('.photo-picker-thumb');
            if (thumb) thumb.classList.remove('dragging');
            dragIndex = null;
        });

        thumbs.addEventListener('dragover', function (e) {
            if (dragIndex === null) return;
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
        });

        thumbs.addEventListener('drop', function (e) {
            var thumb = e.target.closest('.photo-picker-thumb');
            if (!thumb || dragIndex === null) return;
            e.preventDefault();
            var dropIndex = parseInt(thumb.dataset.index, 10);
            if (dropIndex === dragIndex) return;
            var moved = files.splice(dragIndex, 1)[0];
            files.splice(dropIndex, 0, moved);
            dragIndex = null;
            syncInputFiles();
            render();
        });

        render();
    }

    // Existing (already-uploaded) photos: reordering/removal is pure DOM
    // manipulation, no requests. The hidden "existing_image" input inside
    // each thumbnail travels with it when dragged, so submitting the
    // surrounding form (only on the entry's own Save click) is what
    // actually persists the resulting order/removal server-side.
    function initExistingPhotos(root) {
        var container = root.querySelector('.existing-photos-thumbs');
        if (!container) return;
        var dragEl = null;

        container.addEventListener('dragstart', function (e) {
            var thumb = e.target.closest('.photo-picker-thumb');
            if (!thumb) return;
            dragEl = thumb;
            thumb.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
        });

        container.addEventListener('dragend', function () {
            if (dragEl) dragEl.classList.remove('dragging');
            dragEl = null;
        });

        container.addEventListener('dragover', function (e) {
            if (!dragEl) return;
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            var target = e.target.closest('.photo-picker-thumb');
            if (!target || target === dragEl) return;
            var rect = target.getBoundingClientRect();
            var before = (e.clientX - rect.left) < rect.width / 2;
            container.insertBefore(dragEl, before ? target : target.nextSibling);
        });

        container.addEventListener('click', function (e) {
            var btn = e.target.closest('.photo-picker-remove');
            if (!btn) return;
            var thumb = btn.closest('.photo-picker-thumb');
            if (thumb) thumb.remove();
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('.journal-photo-picker').forEach(initPhotoPicker);
        document.querySelectorAll('.journal-existing-photos').forEach(initExistingPhotos);
    });
})();
