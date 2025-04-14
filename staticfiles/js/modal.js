
    // Получаем элементы
    const modal = document.getElementById("reservationModal");
    const openModalButtons = document.querySelectorAll(".reserve-button");
    const closeModal = document.querySelector(".close");

    // Открытие модального окна
    openModalButtons.forEach(button => {
        button.addEventListener("click", () => {
            modal.style.display = "block";
        });
    });

    // Закрытие модального окна
    closeModal.addEventListener("click", () => {
        modal.style.display = "none";
    });

    // Закрытие при нажатии вне окна
    window.addEventListener("click", (event) => {
        if (event.target === modal) {
            modal.style.display = "none";
        }
    });

