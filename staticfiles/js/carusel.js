// Get references to carousel elements
const carouselInner = document.querySelector('.carousel-inner');
const items = document.querySelectorAll('.carousel-item');
let currentIndex = 0;

// Function to show the next slide
function showNextSlide() {
    // Remove the 'active' class from the current item
    items[currentIndex].classList.remove('active');

    // Increment index (with wrap-around)
    currentIndex = (currentIndex + 1) % items.length;

    // Add the 'active' class to the new item
    items[currentIndex].classList.add('active');
}

// Automatically change slides every 3 seconds
setInterval(showNextSlide, 2000);
