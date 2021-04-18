(function() {
    initScroolUp();
    activatePopevers();

    function initScroolUp() {
         // ===== Scroll to Top ==== 
        $(window).scroll(function() {
            if ($(this).scrollTop() >= 250) {        // If page is scrolled more than 50px
                $('#return-to-top').fadeIn(200);    // Fade in the arrow
            } else {
                $('#return-to-top').fadeOut(200);   // Else fade out the arrow
            }
        });
        $('#return-to-top').click(function() {      // When arrow is clicked
            $('body,html').animate({
                scrollTop : 0                       // Scroll to top of body
            }, 100, 'linear');
        });
    }
    function activatePopevers() {
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
        const popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl)
        })
    }
})();