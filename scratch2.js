function toggleDropdown() {
        document.getElementById('profileDropdown').classList.toggle('active');
    }
    window.addEventListener('click', function(event) {
        if (!event.target.matches('.profile-circle')) {
            var dropdowns = document.getElementsByClassName("dropdown-menu");
            for (var i = 0; i < dropdowns.length; i++) {
                var openDropdown = dropdowns[i];
                if (openDropdown.classList.contains('active')) {
                    openDropdown.classList.remove('active');
                }
            }
        }
    });