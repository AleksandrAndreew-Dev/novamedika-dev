document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById("reservationModal");
    const openModalButtons = document.querySelectorAll(".reserve-button");
    const closeModal = document.querySelector(".close");
    const consentCheckbox = document.querySelector("#reservationModal input[type='checkbox']"); // Checkbox element
    const submitButton = document.querySelector("#reservationModal button[type='submit']"); // Submit button

    // Disable submit button initially
    submitButton.disabled = true;

    // Enable or disable the submit button based on checkbox state
    if (consentCheckbox) {
        consentCheckbox.addEventListener("change", () => {
            submitButton.disabled = !consentCheckbox.checked;
        });
    }

    openModalButtons.forEach(button => {
        button.addEventListener("click", () => {
            const productName = button.dataset.productName;
            const pharmacyName = button.dataset.pharmacyName;
            const pharmacyAddress = button.dataset.pharmacyAddress;
            const pharmacyPhone = button.dataset.pharmacyPhone; // New phone attribute

            // Populate the modal
            document.querySelector("#reservationModal .product-name").innerText = `Товар: ${productName}`;
            document.querySelector("#reservationModal .pharmacy-name").innerText = `Аптека: ${pharmacyName}`;
            document.querySelector("#reservationModal .pharmacy-address").innerText = `Адрес: ${pharmacyAddress}`;
            document.querySelector("#reservationModal .pharmacy-phone").innerText = `Телефон: ${pharmacyPhone}`; // Update phone number

            // Show the modal
            modal.style.display = "block";
        });
    });

    // Close modal when the close button is clicked
    closeModal.addEventListener("click", () => {
        modal.style.display = "none";
    });

    // Close modal if user clicks outside of it
    window.addEventListener("click", (event) => {
        if (event.target === modal) {
            modal.style.display = "none";
        }
    });
});
