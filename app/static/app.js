document.addEventListener("DOMContentLoaded", () => {

    // =========================================================
    // COMMON HELPERS
    // =========================================================

    const isBlank = (value) => {
        return !value || value.trim() === "";
    };


    // =========================================================
    // CONFIRMATION HANDLERS
    //
    // Works with:
    //
    // data-confirm="Are you sure?"
    //
    // on forms and buttons.
    // =========================================================

    const bindConfirmations = () => {

        document
            .querySelectorAll("[data-confirm]")
            .forEach((element) => {

                if (
                    element.dataset.confirmBound === "true"
                ) {
                    return;
                }

                element.dataset.confirmBound = "true";

                element.addEventListener(
                    "submit",
                    (event) => {

                        const message =
                            element.dataset.confirm
                            || "Are you sure?";

                        if (!window.confirm(message)) {

                            event.preventDefault();

                        }

                    }
                );

            });


        document
            .querySelectorAll(
                "[data-confirm-click]"
            )
            .forEach((element) => {

                if (
                    element.dataset.confirmClickBound
                    === "true"
                ) {
                    return;
                }

                element.dataset.confirmClickBound =
                    "true";

                element.addEventListener(
                    "click",
                    (event) => {

                        const message =
                            element.dataset.confirmClick
                            || "Are you sure?";

                        if (!window.confirm(message)) {

                            event.preventDefault();

                        }

                    }
                );

            });

    };


    // =========================================================
    // DATE/TIME VALIDATION
    // =========================================================

    const validateDateRange = (
        startId,
        endId,
        messageId
    ) => {

        const start =
            document.getElementById(
                startId
            );

        const end =
            document.getElementById(
                endId
            );

        const message =
            messageId
                ? document.getElementById(
                    messageId
                )
                : null;


        if (!start || !end) {

            return () => true;

        }


        const validate = () => {

            if (
                !start.value
                ||
                !end.value
            ) {

                end.setCustomValidity("");

                if (message) {

                    message.textContent = "";

                    message.classList.add(
                        "hidden"
                    );

                }

                return true;

            }


            const invalid =
                end.value <= start.value;


            end.setCustomValidity(
                invalid
                    ? "End time must be after start time."
                    : ""
            );


            if (message) {

                message.textContent =
                    invalid
                        ? "End time must be after start time."
                        : "";

                message.classList.toggle(
                    "hidden",
                    !invalid
                );

            }


            return !invalid;

        };


        start.addEventListener(
            "change",
            validate
        );

        start.addEventListener(
            "input",
            validate
        );


        end.addEventListener(
            "change",
            validate
        );

        end.addEventListener(
            "input",
            validate
        );


        return validate;

    };


    // =========================================================
    // REQUIRED-FIELD BUTTON CONTROL
    // =========================================================

    const setupRequiredButton = (
        formId,
        buttonId,
        fieldIds
    ) => {

        const form =
            document.getElementById(
                formId
            );

        const button =
            document.getElementById(
                buttonId
            );


        if (!form || !button) {

            return;

        }


        const fields =
            fieldIds
                .map(
                    (id) =>
                        document.getElementById(id)
                )
                .filter(Boolean);


        const update = () => {

            const missing =
                fields.some(
                    (field) =>
                        isBlank(
                            field.value
                        )
                );


            button.disabled =
                missing;

        };


        fields.forEach(
            (field) => {

                field.addEventListener(
                    "input",
                    update
                );

                field.addEventListener(
                    "change",
                    update
                );

            }
        );


        update();

    };


    // =========================================================
    // AVAILABILITY FORM
    // =========================================================

    const setupAvailabilityForm = () => {

        const form =
            document.getElementById(
                "availabilityForm"
            );


        if (!form) {

            return;

        }


        const resource =
            document.getElementById(
                "resource_id"
            );

        const date =
            document.getElementById(
                "date"
            );

        const start =
            document.getElementById(
                "start_time"
            );

        const end =
            document.getElementById(
                "end_time"
            );

        const button =
            document.getElementById(
                "checkAvailabilityButton"
            );


        if (
            !resource
            ||
            !date
            ||
            !start
            ||
            !end
            ||
            !button
        ) {

            return;

        }


        const validateRange = () => {

            if (
                !start.value
                ||
                !end.value
            ) {

                end.setCustomValidity("");

                return true;

            }


            const invalid =
                end.value <= start.value;


            end.setCustomValidity(
                invalid
                    ? "End time must be after start time."
                    : ""
            );


            return !invalid;

        };


        const updateButton = () => {

            const missing =
                !resource.value
                ||
                !date.value
                ||
                !start.value
                ||
                !end.value;


            const invalid =
                !validateRange();


            button.disabled =
                missing || invalid;

        };


        [
            resource,
            date,
            start,
            end
        ].forEach(
            (field) => {

                field.addEventListener(
                    "input",
                    updateButton
                );

                field.addEventListener(
                    "change",
                    updateButton
                );

            }
        );


        form.addEventListener(
            "submit",
            (event) => {

                if (
                    !resource.value
                    ||
                    !date.value
                    ||
                    !start.value
                    ||
                    !end.value
                    ||
                    !validateRange()
                ) {

                    event.preventDefault();

                    form.reportValidity();

                }

            }
        );


        updateButton();

    };


    // =========================================================
    // MULTI-RESOURCE REQUEST FORM
    // =========================================================

    const setupMultiResourceForm = () => {

        const form =
            document.getElementById(
                "requestForm"
            );


        if (!form) {

            return;

        }


        const rowsContainer =
            document.getElementById(
                "resourceRows"
            );

        const addButton =
            document.getElementById(
                "addResourceBtn"
            );

        const error =
            document.getElementById(
                "resourceError"
            );


        if (
            !rowsContainer
            ||
            !addButton
        ) {

            return;

        }


        // =====================================================
        // SHOW ERROR
        // =====================================================

        const showError = (
            message
        ) => {

            if (!error) {
                return;
            }

            error.textContent =
                message;

            error.classList.remove(
                "hidden"
            );

        };


        const hideError = () => {

            if (!error) {
                return;
            }

            error.textContent = "";

            error.classList.add(
                "hidden"
            );

        };


        // =====================================================
        // FILTER SPECIFIC RESOURCES
        // =====================================================

        const filterSpecificResources = (
            row
        ) => {

            const typeSelect =
                row.querySelector(
                    ".resource-type"
                );

            const resourceSelect =
                row.querySelector(
                    ".specific-resource"
                );


            if (
                !typeSelect
                ||
                !resourceSelect
            ) {

                return;

            }


            const selectedType =
                typeSelect.value;


            resourceSelect
                .querySelectorAll(
                    "option[data-resource-type]"
                )
                .forEach(
                    (option) => {

                        const matches =
                            !selectedType
                            ||
                            option.dataset
                                .resourceType
                                === selectedType;


                        option.hidden =
                            !matches;


                        if (
                            !matches
                            &&
                            option.selected
                        ) {

                            resourceSelect.value =
                                "";

                        }

                    }
                );

        };


        // =====================================================
        // DUPLICATE TYPES
        // =====================================================

        const validateDuplicateTypes = () => {

            const seen =
                new Set();


            let duplicate =
                false;


            rowsContainer
                .querySelectorAll(
                    ".resource-type"
                )
                .forEach(
                    (select) => {

                        if (!select.value) {

                            return;

                        }


                        if (
                            seen.has(
                                select.value
                            )
                        ) {

                            duplicate =
                                true;

                        }


                        seen.add(
                            select.value
                        );

                    }
                );


            if (duplicate) {

                showError(
                    "Each resource type can be added only once. " +
                    "Increase its quantity instead."
                );


                return false;

            }


            hideError();


            return true;

        };


        // =====================================================
        // UPDATE REMOVE BUTTONS
        // =====================================================

        const updateRemoveButtons = () => {

            const rows =
                rowsContainer.querySelectorAll(
                    ".resource-row"
                );


            rows.forEach(
                (row) => {

                    const button =
                        row.querySelector(
                            ".remove-resource-btn"
                        );


                    if (!button) {

                        return;

                    }


                    const onlyRow =
                        rows.length === 1;


                    button.disabled =
                        onlyRow;


                    button.classList.toggle(
                        "opacity-50",
                        onlyRow
                    );


                    button.classList.toggle(
                        "cursor-not-allowed",
                        onlyRow
                    );

                }
            );

        };


        // =====================================================
        // BIND RESOURCE ROW
        // =====================================================

        const bindRow = (
            row
        ) => {

            const typeSelect =
                row.querySelector(
                    ".resource-type"
                );

            const removeButton =
                row.querySelector(
                    ".remove-resource-btn"
                );


            if (typeSelect) {

                typeSelect.addEventListener(
                    "change",
                    () => {

                        filterSpecificResources(
                            row
                        );

                        validateDuplicateTypes();

                    }
                );

            }


            if (removeButton) {

                removeButton.addEventListener(
                    "click",
                    () => {

                        const rows =
                            rowsContainer.querySelectorAll(
                                ".resource-row"
                            );


                        if (
                            rows.length <= 1
                        ) {

                            return;

                        }


                        row.remove();


                        updateRemoveButtons();

                        validateDuplicateTypes();

                    }
                );

            }


            filterSpecificResources(
                row
            );

        };


        // =====================================================
        // INITIAL ROWS
        // =====================================================

        rowsContainer
            .querySelectorAll(
                ".resource-row"
            )
            .forEach(
                bindRow
            );


        updateRemoveButtons();


        // =====================================================
        // ADD ROW
        // =====================================================

        addButton.addEventListener(
            "click",
            () => {

                const firstRow =
                    rowsContainer.querySelector(
                        ".resource-row"
                    );


                if (!firstRow) {

                    return;

                }


                const newRow =
                    firstRow.cloneNode(
                        true
                    );


                const typeSelect =
                    newRow.querySelector(
                        ".resource-type"
                    );


                const quantity =
                    newRow.querySelector(
                        "input[name='quantity']"
                    );


                const specific =
                    newRow.querySelector(
                        ".specific-resource"
                    );


                if (typeSelect) {

                    typeSelect.value =
                        "";

                }


                if (quantity) {

                    quantity.value =
                        "1";

                }


                if (specific) {

                    specific.value =
                        "";

                    specific
                        .querySelectorAll(
                            "option"
                        )
                        .forEach(
                            (option) => {

                                option.hidden =
                                    false;

                            }
                        );

                }


                rowsContainer.appendChild(
                    newRow
                );


                bindRow(
                    newRow
                );


                updateRemoveButtons();

            }
        );


        // =====================================================
        // SUBMIT VALIDATION
        // =====================================================

        form.addEventListener(
            "submit",
            (event) => {

                hideError();


                const eventId =
                    form.querySelector(
                        "#event_id"
                    );


                const start =
                    form.querySelector(
                        "#requested_start"
                    );


                const end =
                    form.querySelector(
                        "#requested_end"
                    );


                // ---------------------------------------------
                // Required event
                // ---------------------------------------------

                if (
                    eventId
                    &&
                    !eventId.value
                ) {

                    event.preventDefault();

                    showError(
                        "Please select an event."
                    );

                    eventId.focus();

                    return;

                }


                // ---------------------------------------------
                // Date/time
                // ---------------------------------------------

                if (
                    start
                    &&
                    end
                    &&
                    start.value
                    &&
                    end.value
                    &&
                    end.value <= start.value
                ) {

                    event.preventDefault();

                    end.setCustomValidity(
                        "End time must be after start time."
                    );

                    end.reportValidity();

                    return;

                }


                // ---------------------------------------------
                // Resource rows
                // ---------------------------------------------

                const rows =
                    rowsContainer.querySelectorAll(
                        ".resource-row"
                    );


                if (!rows.length) {

                    event.preventDefault();

                    showError(
                        "Please add at least one resource."
                    );

                    return;

                }


                // ---------------------------------------------
                // Validate every row
                // ---------------------------------------------

                for (
                    const row of rows
                ) {

                    const type =
                        row.querySelector(
                            ".resource-type"
                        );

                    const quantity =
                        row.querySelector(
                            "input[name='quantity']"
                        );


                    if (
                        !type
                        ||
                        !type.value
                    ) {

                        event.preventDefault();

                        showError(
                            "Please select a resource type for every row."
                        );

                        if (type) {

                            type.focus();

                        }

                        return;

                    }


                    const quantityValue =
                        Number(
                            quantity.value
                        );


                    if (
                        !Number.isInteger(
                            quantityValue
                        )
                        ||
                        quantityValue <= 0
                    ) {

                        event.preventDefault();

                        showError(
                            "Every resource quantity must be a positive whole number."
                        );

                        quantity.focus();

                        return;

                    }

                }


                // ---------------------------------------------
                // Duplicate resource types
                // ---------------------------------------------

                if (
                    !validateDuplicateTypes()
                ) {

                    event.preventDefault();

                }

            }
        );

    };


    // =========================================================
    // INITIALIZE EVERYTHING
    // =========================================================

    bindConfirmations();


    validateDateRange(
        "requested_start",
        "requested_end",
        "requestDateError"
    );


    validateDateRange(
        "start_dt",
        "end_dt",
        "eventDateError"
    );


    validateDateRange(
        "start",
        "end",
        "availabilityDateError"
    );


    setupAvailabilityForm();

    setupMultiResourceForm();

});